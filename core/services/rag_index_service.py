"""
Servicos para a Sprint 5 do AGIR-RAG Lite.

Constroi uma base auditavel em SQLite/Parquet e um indice vetorial local
em Qdrant a partir dos PDFs ja validados por LARA-I e DANI.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

import pandas as pd
from loguru import logger
from sklearn.feature_extraction.text import HashingVectorizer

from core.processors.pdf_processor import OptimizedPdfProcessor


TIPOS_DOCUMENTO_VALIDOS = ("cig", "pg", "compliance", "integridade")


@dataclass
class DocumentRecord:
    document_id: str
    orgao: str
    tipo_documento: str
    arquivo: str
    caminho_absoluto: str
    caminho_relativo: str
    sha256: str
    paginas: int
    palavras_total: int
    caracteres_total: int
    processado_em: str


@dataclass
class ChunkRecord:
    chunk_id: str
    document_id: str
    orgao: str
    tipo_documento: str
    arquivo: str
    caminho_relativo: str
    pagina_inicial: int
    pagina_final: int
    ordem: int
    texto: str
    texto_busca: str
    hash_texto: str
    palavras: int
    caracteres: int
    processado_em: str


class LocalTextEmbedder:
    """
    Embedder local leve para o primeiro indice vetorial da Sprint 5.

    Usa HashingVectorizer para gerar vetores deterministas sem fit, sem GPU
    e sem dependencia de APIs externas. Pode ser trocado depois por
    Sentence Transformers mantendo a mesma interface.
    """

    def __init__(self, dimensions: int = 384):
        if dimensions <= 0:
            raise ValueError("dimensions deve ser maior que zero")
        self.dimensions = dimensions
        self.vectorizer = HashingVectorizer(
            n_features=dimensions,
            alternate_sign=False,
            norm=None,
            lowercase=True,
            token_pattern=r"(?u)\b\w+\b",
        )

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        matrix = self.vectorizer.transform(texts)
        vectors: List[List[float]] = []

        for row in matrix:
            dense = row.toarray()[0].astype(float)
            norm = math.sqrt(float((dense ** 2).sum()))
            if norm > 0:
                dense /= norm
            vectors.append(dense.tolist())

        return vectors


class RagIndexService:
    def __init__(
        self,
        data_dir: str | None = None,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        collection_name: str = "agir_chunks",
        embedding_dimensions: int = 384,
        enable_ocr: bool = False,
        max_pages_per_document: int | None = 40,
    ) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.data_dir = Path(data_dir or os.getenv("DATA_DIR", str(self.repo_root / "data")))
        self.docs_dir = self.data_dir / "dani" / "docs"
        self.input_dir = self.docs_dir / "input"
        self.integridade_dir = self.docs_dir / "integridade"
        self.rag_dir = self.data_dir / "rag"
        self.sqlite_path = self.rag_dir / "agir_rag.db"
        self.parquet_documents_path = self.rag_dir / "documents.parquet"
        self.parquet_chunks_path = self.rag_dir / "chunks.parquet"
        self.manifest_path = self.rag_dir / "index_manifest.json"
        self.qdrant_path = self.rag_dir / "qdrant"
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.processor = OptimizedPdfProcessor(
            logger,
            enable_ocr=enable_ocr,
            max_pages=max_pages_per_document,
        )
        self.embedder = LocalTextEmbedder(dimensions=embedding_dimensions)
        self.enable_ocr = enable_ocr
        self.max_pages_per_document = max_pages_per_document

    def build_index(
        self,
        reset: bool = False,
        tipos_documento: Iterable[str] | None = None,
        orgaos: Iterable[str] | None = None,
        max_documents: int | None = None,
    ) -> dict:
        tipos = self._resolve_tipos(tipos_documento)
        orgaos_normalizados = self._resolve_orgaos(orgaos)
        self._ensure_dirs(reset=reset)
        document_records, chunk_records = self._extract_records(tipos, orgaos_normalizados, max_documents)
        self._write_sqlite(document_records, chunk_records, reset=reset)
        self._write_parquet(document_records, chunk_records)
        qdrant_summary = self._write_qdrant(chunk_records, reset=reset)
        manifest = self._write_manifest(
            document_records,
            chunk_records,
            tipos,
            qdrant_summary,
            orgaos_normalizados,
            max_documents,
        )
        return manifest

    def _resolve_tipos(self, tipos_documento: Iterable[str] | None) -> List[str]:
        if tipos_documento is None:
            return list(TIPOS_DOCUMENTO_VALIDOS)

        tipos_normalizados = []
        for tipo in tipos_documento:
            tipo_limpo = str(tipo).strip().lower()
            if tipo_limpo not in TIPOS_DOCUMENTO_VALIDOS:
                raise ValueError(
                    f"Tipo de documento invalido: {tipo_limpo}. "
                    f"Use um ou mais de: {', '.join(TIPOS_DOCUMENTO_VALIDOS)}"
                )
            tipos_normalizados.append(tipo_limpo)
        return tipos_normalizados

    def _resolve_orgaos(self, orgaos: Iterable[str] | None) -> list[str] | None:
        if orgaos is None:
            return None

        orgaos_normalizados = []
        for orgao in orgaos:
            orgao_limpo = str(orgao).strip()
            if orgao_limpo:
                orgaos_normalizados.append(orgao_limpo.upper())
        return orgaos_normalizados or None

    def _ensure_dirs(self, reset: bool) -> None:
        self.rag_dir.mkdir(parents=True, exist_ok=True)
        self.qdrant_path.mkdir(parents=True, exist_ok=True)

        if reset:
            for path in (self.sqlite_path, self.parquet_documents_path, self.parquet_chunks_path, self.manifest_path):
                if path.exists():
                    path.unlink()

    def _extract_records(
        self,
        tipos_documento: List[str],
        orgaos: list[str] | None,
        max_documents: int | None,
    ) -> tuple[list[DocumentRecord], list[ChunkRecord]]:
        document_records: list[DocumentRecord] = []
        chunk_records: list[ChunkRecord] = []
        processado_em = datetime.now(timezone.utc).isoformat()
        pdfs_visitados = 0

        for tipo_documento, pdf_path in self._iter_pdf_files(tipos_documento, orgaos):
            if max_documents is not None and pdfs_visitados >= max_documents:
                logger.info(f"Limite de {max_documents} documentos atingido. Encerrando indexacao piloto.")
                break

            pdfs_visitados += 1
            orgao = pdf_path.parent.name
            caminho_relativo = pdf_path.relative_to(self.data_dir).as_posix()
            sha256 = self._hash_file(pdf_path)

            logger.info(f"Indexando PDF RAG: {caminho_relativo}")
            pages_text, total_words = self.processor.extract_text_fast(str(pdf_path))
            cleaned_pages = [self._normalize_whitespace(page) for page in pages_text if self._normalize_whitespace(page)]

            if not cleaned_pages:
                logger.warning(f"Nenhum texto extraido de {pdf_path}")
                continue

            caracteres_total = sum(len(page) for page in cleaned_pages)
            document_id = hashlib.sha1(f"{caminho_relativo}:{sha256}".encode("utf-8")).hexdigest()

            document_records.append(
                DocumentRecord(
                    document_id=document_id,
                    orgao=orgao,
                    tipo_documento=tipo_documento,
                    arquivo=pdf_path.name,
                    caminho_absoluto=str(pdf_path),
                    caminho_relativo=caminho_relativo,
                    sha256=sha256,
                    paginas=len(cleaned_pages),
                    palavras_total=total_words,
                    caracteres_total=caracteres_total,
                    processado_em=processado_em,
                )
            )

            chunk_records.extend(
                self._build_chunks(
                    document_id=document_id,
                    orgao=orgao,
                    tipo_documento=tipo_documento,
                    arquivo=pdf_path.name,
                    caminho_relativo=caminho_relativo,
                    pages=cleaned_pages,
                    processado_em=processado_em,
                )
            )

        logger.info(
            f"Sprint 5: {len(document_records)} documentos e {len(chunk_records)} chunks preparados para indexacao."
        )
        return document_records, chunk_records

    def _iter_pdf_files(
        self,
        tipos_documento: List[str],
        orgaos: list[str] | None = None,
    ) -> Iterable[tuple[str, Path]]:
        for tipo in tipos_documento:
            if tipo == "integridade":
                base_dir = self.integridade_dir
            else:
                base_dir = self.input_dir / tipo

            if not base_dir.exists():
                logger.warning(f"Diretorio ausente para tipo {tipo}: {base_dir}")
                continue

            for pdf_path in sorted(base_dir.rglob("*.pdf")):
                if pdf_path.is_file() and (orgaos is None or pdf_path.parent.name.upper() in orgaos):
                    yield tipo, pdf_path

    def _build_chunks(
        self,
        document_id: str,
        orgao: str,
        tipo_documento: str,
        arquivo: str,
        caminho_relativo: str,
        pages: List[str],
        processado_em: str,
    ) -> list[ChunkRecord]:
        chunk_records: list[ChunkRecord] = []
        ordem = 0

        for page_index, page_text in enumerate(pages, start=1):
            for chunk_text in self._chunk_text(page_text):
                ordem += 1
                hash_texto = hashlib.sha1(chunk_text.encode("utf-8")).hexdigest()
                chunk_id = hashlib.sha1(
                    f"{document_id}:{page_index}:{ordem}:{hash_texto}".encode("utf-8")
                ).hexdigest()
                chunk_records.append(
                    ChunkRecord(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        orgao=orgao,
                        tipo_documento=tipo_documento,
                        arquivo=arquivo,
                        caminho_relativo=caminho_relativo,
                        pagina_inicial=page_index,
                        pagina_final=page_index,
                        ordem=ordem,
                        texto=chunk_text,
                        texto_busca=chunk_text.lower(),
                        hash_texto=hash_texto,
                        palavras=len(chunk_text.split()),
                        caracteres=len(chunk_text),
                        processado_em=processado_em,
                    )
                )

        return chunk_records

    def _chunk_text(self, text: str) -> List[str]:
        text = self._normalize_whitespace(text)
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: List[str] = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            candidate = sentence if not current else f"{current} {sentence}"
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue

            if current:
                chunks.append(current)
                overlap_text = current[-self.chunk_overlap :].strip() if self.chunk_overlap > 0 else ""
                current = f"{overlap_text} {sentence}".strip() if overlap_text else sentence
            else:
                chunks.extend(self._hard_split(sentence))
                current = ""

        if current:
            chunks.append(current)

        return [chunk.strip() for chunk in chunks if chunk.strip()]

    def _hard_split(self, text: str) -> List[str]:
        chunks = []
        step = max(1, self.chunk_size - self.chunk_overlap)
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks

    def _write_sqlite(
        self,
        document_records: list[DocumentRecord],
        chunk_records: list[ChunkRecord],
        reset: bool,
    ) -> None:
        conn = sqlite3.connect(self.sqlite_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._create_schema(conn, reset=reset)
            self._insert_documents(conn, document_records)
            self._insert_chunks(conn, chunk_records)
            conn.commit()
        finally:
            conn.close()

    def _create_schema(self, conn: sqlite3.Connection, reset: bool) -> None:
        if reset:
            conn.executescript(
                """
                DROP TABLE IF EXISTS chunks_fts;
                DROP TABLE IF EXISTS chunks;
                DROP TABLE IF EXISTS documents;
                """
            )

        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                orgao TEXT NOT NULL,
                tipo_documento TEXT NOT NULL,
                arquivo TEXT NOT NULL,
                caminho_absoluto TEXT NOT NULL,
                caminho_relativo TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                paginas INTEGER NOT NULL,
                palavras_total INTEGER NOT NULL,
                caracteres_total INTEGER NOT NULL,
                processado_em TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                orgao TEXT NOT NULL,
                tipo_documento TEXT NOT NULL,
                arquivo TEXT NOT NULL,
                caminho_relativo TEXT NOT NULL,
                pagina_inicial INTEGER NOT NULL,
                pagina_final INTEGER NOT NULL,
                ordem INTEGER NOT NULL,
                texto TEXT NOT NULL,
                texto_busca TEXT NOT NULL,
                hash_texto TEXT NOT NULL,
                palavras INTEGER NOT NULL,
                caracteres INTEGER NOT NULL,
                processado_em TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                texto,
                tokenize = 'unicode61'
            );

            CREATE INDEX IF NOT EXISTS idx_documents_orgao_tipo ON documents(orgao, tipo_documento);
            CREATE INDEX IF NOT EXISTS idx_chunks_documento ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_orgao_tipo ON chunks(orgao, tipo_documento);
            """
        )

    def _insert_documents(self, conn: sqlite3.Connection, records: list[DocumentRecord]) -> None:
        conn.execute("DELETE FROM documents")
        if not records:
            return

        conn.executemany(
            """
            INSERT OR REPLACE INTO documents (
                document_id, orgao, tipo_documento, arquivo, caminho_absoluto,
                caminho_relativo, sha256, paginas, palavras_total,
                caracteres_total, processado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r.document_id,
                    r.orgao,
                    r.tipo_documento,
                    r.arquivo,
                    r.caminho_absoluto,
                    r.caminho_relativo,
                    r.sha256,
                    r.paginas,
                    r.palavras_total,
                    r.caracteres_total,
                    r.processado_em,
                )
                for r in records
            ],
        )

    def _insert_chunks(self, conn: sqlite3.Connection, records: list[ChunkRecord]) -> None:
        conn.execute("DELETE FROM chunks")
        if not records:
            conn.execute("DELETE FROM chunks_fts")
            return

        conn.execute("DELETE FROM chunks_fts")
        conn.executemany(
            """
            INSERT OR REPLACE INTO chunks (
                chunk_id, document_id, orgao, tipo_documento, arquivo,
                caminho_relativo, pagina_inicial, pagina_final, ordem,
                texto, texto_busca, hash_texto, palavras, caracteres, processado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    r.chunk_id,
                    r.document_id,
                    r.orgao,
                    r.tipo_documento,
                    r.arquivo,
                    r.caminho_relativo,
                    r.pagina_inicial,
                    r.pagina_final,
                    r.ordem,
                    r.texto,
                    r.texto_busca,
                    r.hash_texto,
                    r.palavras,
                    r.caracteres,
                    r.processado_em,
                )
                for r in records
            ],
        )
        conn.executemany(
            "INSERT INTO chunks_fts (chunk_id, texto) VALUES (?, ?)",
            [(r.chunk_id, r.texto_busca) for r in records],
        )

    def _write_parquet(
        self,
        document_records: list[DocumentRecord],
        chunk_records: list[ChunkRecord],
    ) -> None:
        documents_df = pd.DataFrame([record.__dict__ for record in document_records])
        chunks_df = pd.DataFrame([record.__dict__ for record in chunk_records])

        documents_df.to_parquet(self.parquet_documents_path, index=False)
        chunks_df.to_parquet(self.parquet_chunks_path, index=False)

    def _write_qdrant(self, chunk_records: list[ChunkRecord], reset: bool) -> dict:
        if not chunk_records:
            return {"enabled": False, "indexed_chunks": 0, "reason": "Nenhum chunk gerado"}

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, PointStruct, VectorParams
        except ImportError:
            logger.warning("qdrant-client nao instalado. Pulando indice vetorial.")
            return {"enabled": False, "indexed_chunks": 0, "reason": "qdrant-client ausente"}

        client = QdrantClient(path=str(self.qdrant_path))
        collection_exists = self.collection_name in {c.name for c in client.get_collections().collections}

        if collection_exists:
            client.delete_collection(self.collection_name)
            collection_exists = False

        if not collection_exists:
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedder.dimensions,
                    distance=Distance.COSINE,
                ),
            )

        vectors = self.embedder.embed([record.texto for record in chunk_records])
        points = []

        for record, vector in zip(chunk_records, vectors):
            point_id = int(record.chunk_id[:16], 16)
            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload={
                        "chunk_id": record.chunk_id,
                        "document_id": record.document_id,
                        "orgao": record.orgao,
                        "tipo_documento": record.tipo_documento,
                        "arquivo": record.arquivo,
                        "caminho_relativo": record.caminho_relativo,
                        "pagina_inicial": record.pagina_inicial,
                        "pagina_final": record.pagina_final,
                        "ordem": record.ordem,
                    },
                )
            )

        client.upsert(collection_name=self.collection_name, points=points)
        return {
            "enabled": True,
            "collection_name": self.collection_name,
            "indexed_chunks": len(points),
            "vector_size": self.embedder.dimensions,
            "path": str(self.qdrant_path),
        }

    def _write_manifest(
        self,
        document_records: list[DocumentRecord],
        chunk_records: list[ChunkRecord],
        tipos_documento: list[str],
        qdrant_summary: dict,
        orgaos: list[str] | None = None,
        max_documents: int | None = None,
    ) -> dict:
        by_type = {}
        for record in document_records:
            current = by_type.setdefault(record.tipo_documento, {"documentos": 0, "orgaos": set()})
            current["documentos"] += 1
            current["orgaos"].add(record.orgao)

        manifest = {
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "tipos_documento_indexados": tipos_documento,
            "orgaos_filtrados": orgaos,
            "max_documents": max_documents,
            "documentos_total": len(document_records),
            "chunks_total": len(chunk_records),
            "sqlite_path": str(self.sqlite_path),
            "parquet_documents_path": str(self.parquet_documents_path),
            "parquet_chunks_path": str(self.parquet_chunks_path),
            "qdrant": qdrant_summary,
            "resumo_por_tipo": {
                tipo: {
                    "documentos": values["documentos"],
                    "orgaos": sorted(values["orgaos"]),
                }
                for tipo, values in by_type.items()
            },
        }

        with open(self.manifest_path, "w", encoding="utf-8") as fp:
            json.dump(manifest, fp, ensure_ascii=False, indent=2)

        return manifest

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def _hash_file(file_path: Path) -> str:
        digest = hashlib.sha256()
        with open(file_path, "rb") as fp:
            for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
