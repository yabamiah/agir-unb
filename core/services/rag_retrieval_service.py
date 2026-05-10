"""
Servicos para a Sprint 6 do AGIR-RAG Lite.

Executa recuperacao hibrida sobre a base auditavel criada na Sprint 5:
busca lexical via SQLite FTS5, busca semantica via Qdrant local e fusao
ranqueada das evidencias documentais.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from loguru import logger

from core.services.rag_index_service import LocalTextEmbedder, TIPOS_DOCUMENTO_VALIDOS


@dataclass
class EvidenceRecord:
    chunk_id: str
    trecho: str
    documento: str
    pagina: int
    pagina_final: int
    orgao: str
    tipo_documento: str
    caminho_relativo: str
    score: float
    score_lexical: float
    score_semantico: float
    fontes: list[str]


@dataclass
class HybridSearchResponse:
    criterio: str | None
    pergunta: str
    filtros: dict
    evidencias: list[EvidenceRecord]
    diagnostico: dict

    def to_dict(self) -> dict:
        return {
            "criterio": self.criterio,
            "pergunta": self.pergunta,
            "filtros": self.filtros,
            "evidencias": [asdict(evidence) for evidence in self.evidencias],
            "diagnostico": self.diagnostico,
        }


class RagRetrievalService:
    def __init__(
        self,
        data_dir: str | None = None,
        collection_name: str = "agir_chunks",
        embedding_dimensions: int = 384,
        lexical_weight: float = 0.55,
        semantic_weight: float = 0.45,
        rrf_k: int = 60,
    ) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.data_dir = Path(data_dir or os.getenv("DATA_DIR", str(self.repo_root / "data")))
        self.rag_dir = self.data_dir / "rag"
        self.sqlite_path = self.rag_dir / "agir_rag.db"
        self.qdrant_path = self.rag_dir / "qdrant"
        self.manifest_path = self.rag_dir / "index_manifest.json"
        self.collection_name = collection_name
        self.embedder = LocalTextEmbedder(dimensions=embedding_dimensions)
        self.lexical_weight = lexical_weight
        self.semantic_weight = semantic_weight
        self.rrf_k = rrf_k

    def search(
        self,
        pergunta: str,
        criterio: str | None = None,
        orgao: str | None = None,
        tipos_documento: Iterable[str] | None = None,
        top_k: int = 5,
        lexical_limit: int = 30,
        semantic_limit: int = 30,
    ) -> HybridSearchResponse:
        pergunta = self._normalize_whitespace(pergunta)
        if not pergunta:
            raise ValueError("pergunta nao pode ser vazia")

        tipos = self._resolve_tipos(tipos_documento)
        filtros = {
            "orgao": orgao,
            "tipos_documento": tipos,
        }

        lexical_results = self._search_lexical(pergunta, orgao, tipos, lexical_limit)
        semantic_results, semantic_status = self._search_semantic(pergunta, orgao, tipos, semantic_limit)
        evidencias = self._merge_results(lexical_results, semantic_results, top_k)

        return HybridSearchResponse(
            criterio=criterio,
            pergunta=pergunta,
            filtros=filtros,
            evidencias=evidencias,
            diagnostico={
                "lexical_resultados": len(lexical_results),
                "semantico_resultados": len(semantic_results),
                "semantico_status": semantic_status,
                "sqlite_path": str(self.sqlite_path),
                "qdrant_path": str(self.qdrant_path),
                "collection_name": self.collection_name,
                "pesos": {
                    "lexical": self.lexical_weight,
                    "semantico": self.semantic_weight,
                    "rrf_k": self.rrf_k,
                },
            },
        )

    def search_criteria_file(
        self,
        criteria_path: str | Path,
        codigo: str | None = None,
        orgao: str | None = None,
        tipos_documento: Iterable[str] | None = None,
        top_k: int = 5,
        max_criterios: int | None = None,
    ) -> list[HybridSearchResponse]:
        criteria = self._load_criteria(criteria_path)
        if codigo:
            criteria = [criterion for criterion in criteria if criterion.get("codigo") == codigo]
            if not criteria:
                raise ValueError(f"Criterio nao encontrado: {codigo}")

        if max_criterios is not None:
            criteria = criteria[:max_criterios]

        responses = []
        for criterion in criteria:
            pergunta = criterion.get("pergunta_normativa") or criterion.get("pergunta") or criterion.get("titulo")
            if not pergunta:
                continue

            tipos_prioritarios = tipos_documento or criterion.get("tipos_documento_prioritarios")
            responses.append(
                self.search(
                    pergunta=pergunta,
                    criterio=criterion.get("codigo"),
                    orgao=orgao,
                    tipos_documento=tipos_prioritarios,
                    top_k=top_k,
                )
            )
        return responses

    def _search_lexical(
        self,
        pergunta: str,
        orgao: str | None,
        tipos_documento: list[str] | None,
        limit: int,
    ) -> list[dict]:
        if not self.sqlite_path.exists():
            raise FileNotFoundError(
                f"Base SQLite nao encontrada em {self.sqlite_path}. Execute a Sprint 5 antes da Sprint 6."
            )

        fts_query = self._build_fts_query(pergunta)
        if not fts_query:
            return []

        where_clauses = ["chunks_fts MATCH ?"]
        params: list[object] = [fts_query]

        if orgao:
            where_clauses.append("c.orgao = ?")
            params.append(orgao)

        if tipos_documento:
            placeholders = ", ".join("?" for _ in tipos_documento)
            where_clauses.append(f"c.tipo_documento IN ({placeholders})")
            params.extend(tipos_documento)

        params.append(limit)

        sql = f"""
            SELECT
                c.chunk_id,
                c.document_id,
                c.orgao,
                c.tipo_documento,
                c.arquivo,
                c.caminho_relativo,
                c.pagina_inicial,
                c.pagina_final,
                c.ordem,
                c.texto,
                bm25(chunks_fts) AS lexical_rank
            FROM chunks_fts
            JOIN chunks c ON c.chunk_id = chunks_fts.chunk_id
            WHERE {' AND '.join(where_clauses)}
            ORDER BY lexical_rank
            LIMIT ?
        """

        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError as exc:
            logger.warning(f"Consulta FTS falhou ({exc}). Tentando busca LIKE como fallback.")
            rows = self._search_lexical_like(conn, pergunta, orgao, tipos_documento, limit)
        finally:
            conn.close()

        results = []
        for position, row in enumerate(rows, start=1):
            item = dict(row)
            item["lexical_position"] = position
            item["lexical_score"] = self._rrf_score(position, self.lexical_weight)
            results.append(item)
        return results

    def _search_lexical_like(
        self,
        conn: sqlite3.Connection,
        pergunta: str,
        orgao: str | None,
        tipos_documento: list[str] | None,
        limit: int,
    ) -> list[sqlite3.Row]:
        tokens = self._query_tokens(pergunta)
        if not tokens:
            return []

        token_clauses = []
        params: list[object] = []
        for token in tokens[:8]:
            token_clauses.append("c.texto_busca LIKE ?")
            params.append(f"%{token.lower()}%")

        where_clauses = [f"({' OR '.join(token_clauses)})"]

        if orgao:
            where_clauses.append("c.orgao = ?")
            params.append(orgao)

        if tipos_documento:
            placeholders = ", ".join("?" for _ in tipos_documento)
            where_clauses.append(f"c.tipo_documento IN ({placeholders})")
            params.extend(tipos_documento)

        params.append(limit)
        sql = f"""
            SELECT
                c.chunk_id,
                c.document_id,
                c.orgao,
                c.tipo_documento,
                c.arquivo,
                c.caminho_relativo,
                c.pagina_inicial,
                c.pagina_final,
                c.ordem,
                c.texto,
                0.0 AS lexical_rank
            FROM chunks c
            WHERE {' AND '.join(where_clauses)}
            LIMIT ?
        """
        return conn.execute(sql, params).fetchall()

    def _search_semantic(
        self,
        pergunta: str,
        orgao: str | None,
        tipos_documento: list[str] | None,
        limit: int,
    ) -> tuple[list[dict], dict]:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import FieldCondition, Filter, MatchAny, MatchValue
        except ImportError:
            return [], {"enabled": False, "reason": "qdrant-client ausente"}

        if not self.qdrant_path.exists():
            return [], {"enabled": False, "reason": "diretorio qdrant ausente"}

        try:
            client = QdrantClient(path=str(self.qdrant_path))
            collections = {collection.name for collection in client.get_collections().collections}
            if self.collection_name not in collections:
                return [], {"enabled": False, "reason": "collection ausente"}

            query_filter = self._build_qdrant_filter(orgao, tipos_documento, FieldCondition, Filter, MatchAny, MatchValue)
            query_vector = self.embedder.embed([pergunta])[0]

            query_response = client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            points = query_response.points
        except Exception as exc:
            logger.warning(f"Busca semantica indisponivel: {exc}")
            return [], {"enabled": False, "reason": str(exc)}

        chunk_ids = [point.payload.get("chunk_id") for point in points if point.payload and point.payload.get("chunk_id")]
        chunks = self._fetch_chunks_by_ids(chunk_ids)
        results = []

        for position, point in enumerate(points, start=1):
            chunk_id = point.payload.get("chunk_id") if point.payload else None
            if not chunk_id or chunk_id not in chunks:
                continue
            item = chunks[chunk_id]
            item["semantic_position"] = position
            item["semantic_raw_score"] = float(point.score or 0.0)
            item["semantic_score"] = self._rrf_score(position, self.semantic_weight)
            results.append(item)

        return results, {"enabled": True, "resultados": len(results)}

    def _fetch_chunks_by_ids(self, chunk_ids: list[str]) -> dict[str, dict]:
        if not chunk_ids:
            return {}

        placeholders = ", ".join("?" for _ in chunk_ids)
        sql = f"""
            SELECT
                chunk_id,
                document_id,
                orgao,
                tipo_documento,
                arquivo,
                caminho_relativo,
                pagina_inicial,
                pagina_final,
                ordem,
                texto
            FROM chunks
            WHERE chunk_id IN ({placeholders})
        """
        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(sql, chunk_ids).fetchall()
        finally:
            conn.close()

        return {row["chunk_id"]: dict(row) for row in rows}

    def _merge_results(self, lexical_results: list[dict], semantic_results: list[dict], top_k: int) -> list[EvidenceRecord]:
        merged: dict[str, dict] = {}

        for item in lexical_results:
            current = merged.setdefault(item["chunk_id"], dict(item))
            current["score_lexical"] = max(current.get("score_lexical", 0.0), item.get("lexical_score", 0.0))
            current.setdefault("fontes", set()).add("lexical")

        for item in semantic_results:
            current = merged.setdefault(item["chunk_id"], dict(item))
            current["score_semantico"] = max(current.get("score_semantico", 0.0), item.get("semantic_score", 0.0))
            current["semantic_raw_score"] = item.get("semantic_raw_score", current.get("semantic_raw_score", 0.0))
            current.setdefault("fontes", set()).add("semantica")

        evidencias = []
        for item in merged.values():
            score_lexical = float(item.get("score_lexical", 0.0))
            score_semantico = float(item.get("score_semantico", 0.0))
            score = score_lexical + score_semantico
            evidencias.append(
                EvidenceRecord(
                    chunk_id=item["chunk_id"],
                    trecho=item["texto"],
                    documento=item["arquivo"],
                    pagina=int(item["pagina_inicial"]),
                    pagina_final=int(item["pagina_final"]),
                    orgao=item["orgao"],
                    tipo_documento=item["tipo_documento"],
                    caminho_relativo=item["caminho_relativo"],
                    score=round(score, 6),
                    score_lexical=round(score_lexical, 6),
                    score_semantico=round(score_semantico, 6),
                    fontes=sorted(item.get("fontes", set())),
                )
            )

        return sorted(evidencias, key=lambda evidence: evidence.score, reverse=True)[:top_k]

    def _load_criteria(self, criteria_path: str | Path) -> list[dict]:
        path = Path(criteria_path)
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)

        if isinstance(payload, dict):
            criteria = payload.get("criterios", [])
        elif isinstance(payload, list):
            criteria = payload
        else:
            criteria = []

        if not isinstance(criteria, list):
            raise ValueError(f"Arquivo de criterios invalido: {path}")
        return criteria

    def _build_fts_query(self, pergunta: str) -> str:
        tokens = self._query_tokens(pergunta)
        if not tokens:
            return ""
        return " OR ".join(f'"{token}"' for token in tokens[:16])

    def _query_tokens(self, text: str) -> list[str]:
        stopwords = {
            "a",
            "as",
            "ao",
            "aos",
            "como",
            "com",
            "da",
            "das",
            "de",
            "do",
            "dos",
            "e",
            "em",
            "ha",
            "na",
            "nas",
            "no",
            "nos",
            "o",
            "os",
            "ou",
            "para",
            "por",
            "possui",
            "previsto",
            "que",
            "se",
            "um",
            "uma",
        }
        tokens = re.findall(r"(?u)\b[\w-]{3,}\b", text.lower())
        return [token for token in tokens if token not in stopwords]

    def _resolve_tipos(self, tipos_documento: Iterable[str] | None) -> list[str] | None:
        if tipos_documento is None:
            return None

        tipos = []
        for tipo in tipos_documento:
            tipo_limpo = str(tipo).strip().lower()
            if not tipo_limpo:
                continue
            if tipo_limpo not in TIPOS_DOCUMENTO_VALIDOS:
                raise ValueError(
                    f"Tipo de documento invalido: {tipo_limpo}. "
                    f"Use um ou mais de: {', '.join(TIPOS_DOCUMENTO_VALIDOS)}"
                )
            tipos.append(tipo_limpo)
        return tipos or None

    def _build_qdrant_filter(
        self,
        orgao: str | None,
        tipos_documento: list[str] | None,
        field_condition_class,
        filter_class,
        match_any_class,
        match_value_class,
    ):
        must = []
        if orgao:
            must.append(
                field_condition_class(
                    key="orgao",
                    match=match_value_class(value=orgao),
                )
            )
        if tipos_documento:
            must.append(
                field_condition_class(
                    key="tipo_documento",
                    match=match_any_class(any=tipos_documento),
                )
            )
        return filter_class(must=must) if must else None

    def _rrf_score(self, position: int, weight: float) -> float:
        return weight * ((self.rrf_k + 1) / (self.rrf_k + position))

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
