"""
Servicos para a Sprint 7 do AGIR-RAG Lite.

Transforma evidencias recuperadas na Sprint 6 em classificacoes normativas,
indicadores por orgao/eixo IMGA e relatorios comparativos auditaveis.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from core.services.rag_retrieval_service import (EvidenceRecord,
                                                 RagRetrievalService)

CLASSIFICATION_POINTS = {
    "atende": 1.0,
    "atende_parcialmente": 0.5,
    "nao_atende": 0.0,
    "nao_encontrado": 0.0,
}

NEGATIVE_PATTERNS = (
    r"\bnao\s+(ha|existe|possui|consta|foi|foram|identificado|identificada)\b",
    r"\binexist(e|em|encia|ente|entes)\b",
    r"\bausencia\s+de\b",
    r"\bsem\s+(evidencia|registro|previsao|comprovacao|formalizacao)\b",
)


@dataclass
class CriterionClassification:
    orgao: str
    criterio: str
    pergunta: str
    titulo: str | None
    eixo_imga: str
    peso_criterio: float
    classificacao: str
    pontuacao: float
    score_ponderado: float
    score_recuperacao: float
    evidencias_total: int
    palavras_chave_encontradas: list[str]
    justificativa: str
    evidencias: list[dict]


@dataclass
class OrganizationIndicator:
    orgao: str
    criterios_avaliados: int
    peso_total: float
    score_total: float
    conformidade_percentual: float
    classificacoes: dict[str, int]
    pontuacao_por_eixo: dict[str, float]
    criterios_por_eixo: dict[str, int]
    imga_global: float
    faixa: str


@dataclass
class Sprint7Report:
    gerado_em: str
    criterios_file: str
    output_dir: str
    parametros: dict
    indicadores_orgaos: list[OrganizationIndicator]
    classificacoes: list[CriterionClassification]
    arquivos: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "gerado_em": self.gerado_em,
            "criterios_file": self.criterios_file,
            "output_dir": self.output_dir,
            "parametros": self.parametros,
            "indicadores_orgaos": [
                asdict(indicador) for indicador in self.indicadores_orgaos
            ],
            "classificacoes": [
                asdict(classificacao) for classificacao in self.classificacoes
            ],
            "arquivos": self.arquivos,
        }


class RagClassificationService:
    def __init__(
        self,
        data_dir: str | None = None,
        retrieval_service: RagRetrievalService | None = None,
        min_score_atende: float = 0.85,
        min_score_parcial: float = 0.55,
        min_keyword_hits_atende: int = 2,
        evidence_top_k: int = 5,
    ) -> None:
        self.repo_root = Path(__file__).resolve().parents[2]
        self.data_dir = Path(
            data_dir or os.getenv("DATA_DIR", str(self.repo_root / "data"))
        )
        self.rag_dir = self.data_dir / "rag"
        self.sqlite_path = self.rag_dir / "agir_rag.db"
        self.output_dir = self.rag_dir / "sprint7"
        self.retrieval_service = retrieval_service or RagRetrievalService(
            data_dir=str(self.data_dir)
        )
        self.min_score_atende = min_score_atende
        self.min_score_parcial = min_score_parcial
        self.min_keyword_hits_atende = min_keyword_hits_atende
        self.evidence_top_k = evidence_top_k

    def build_report(
        self,
        criteria_path: str | Path,
        orgaos: Iterable[str] | None = None,
        tipos_documento: Iterable[str] | None = None,
        codigo: str | None = None,
        max_criterios: int | None = None,
        max_orgaos: int | None = None,
        manual_sample_size: int = 20,
        output_dir: str | Path | None = None,
    ) -> Sprint7Report:
        criteria_file = Path(criteria_path)
        criteria_payload, criteria = self._load_criteria(criteria_file)
        criteria = self._filter_criteria(criteria, codigo, max_criterios)
        selected_orgaos = self._resolve_orgaos(orgaos, max_orgaos)
        target_output_dir = Path(output_dir) if output_dir else self.output_dir
        target_output_dir.mkdir(parents=True, exist_ok=True)

        classificacoes: list[CriterionClassification] = []
        for orgao in selected_orgaos:
            for criterion in criteria:
                pergunta = (
                    criterion.get("pergunta_normativa")
                    or criterion.get("pergunta")
                    or criterion.get("titulo")
                )
                if not pergunta:
                    continue

                tipos_prioritarios = tipos_documento or criterion.get(
                    "tipos_documento_prioritarios"
                )
                response = self.retrieval_service.search(
                    pergunta=pergunta,
                    criterio=criterion.get("codigo"),
                    orgao=orgao,
                    tipos_documento=tipos_prioritarios,
                    top_k=self.evidence_top_k,
                )
                classificacoes.append(
                    self._classify_criterion(orgao, criterion, response.evidencias)
                )

        indicadores = self._calculate_indicators(classificacoes, criteria_payload)
        arquivos = self._write_outputs(
            target_output_dir,
            criteria_file,
            classificacoes,
            indicadores,
            manual_sample_size,
        )

        return Sprint7Report(
            gerado_em=datetime.now(timezone.utc).isoformat(),
            criterios_file=str(criteria_file),
            output_dir=str(target_output_dir),
            parametros={
                "orgaos": selected_orgaos,
                "tipos_documento": list(tipos_documento) if tipos_documento else None,
                "criterio": codigo,
                "max_criterios": max_criterios,
                "max_orgaos": max_orgaos,
                "manual_sample_size": manual_sample_size,
                "thresholds": {
                    "min_score_atende": self.min_score_atende,
                    "min_score_parcial": self.min_score_parcial,
                    "min_keyword_hits_atende": self.min_keyword_hits_atende,
                    "evidence_top_k": self.evidence_top_k,
                },
            },
            indicadores_orgaos=indicadores,
            classificacoes=classificacoes,
            arquivos=arquivos,
        )

    def _classify_criterion(
        self,
        orgao: str,
        criterion: dict,
        evidencias: list[EvidenceRecord],
    ) -> CriterionClassification:
        keywords = [str(keyword) for keyword in criterion.get("palavras_chave", [])]
        keyword_hits = self._keyword_hits(keywords, evidencias)
        top_score = max((evidence.score for evidence in evidencias), default=0.0)
        has_negative = any(
            self._has_negative_signal(evidence.trecho) for evidence in evidencias[:2]
        )

        has_insufficient_retrieval = (
            top_score < self.min_score_parcial and not keyword_hits
        )

        if not evidencias or has_insufficient_retrieval:
            classificacao = "nao_encontrado"
            justificativa = (
                "Nao foram encontradas evidencias suficientes para o criterio."
            )
        elif has_negative:
            classificacao = "nao_atende"
            justificativa = "As evidencias recuperadas indicam ausencia, inexistencia ou falta de formalizacao."
        elif (
            top_score >= self.min_score_atende
            and len(keyword_hits) >= self.min_keyword_hits_atende
        ):
            classificacao = "atende"
            justificativa = "Ha evidencia documental especifica com recuperacao forte e termos esperados do criterio."
        else:
            classificacao = "atende_parcialmente"
            justificativa = "Ha evidencia relacionada, mas ela e parcial, generica ou insuficiente para aderencia plena."

        pontuacao = CLASSIFICATION_POINTS[classificacao]
        peso_criterio = float(criterion.get("peso_criterio") or 1.0)
        evidence_payload = [self._evidence_to_dict(evidence) for evidence in evidencias]

        return CriterionClassification(
            orgao=orgao,
            criterio=str(criterion.get("codigo") or ""),
            pergunta=str(
                criterion.get("pergunta_normativa") or criterion.get("pergunta") or ""
            ),
            titulo=criterion.get("titulo"),
            eixo_imga=str(
                criterion.get("eixo_imga") or criterion.get("eixo") or "SEM_EIXO"
            ),
            peso_criterio=peso_criterio,
            classificacao=classificacao,
            pontuacao=pontuacao,
            score_ponderado=round(pontuacao * peso_criterio, 4),
            score_recuperacao=round(top_score, 6),
            evidencias_total=len(evidencias),
            palavras_chave_encontradas=keyword_hits,
            justificativa=justificativa,
            evidencias=evidence_payload,
        )

    def _calculate_indicators(
        self,
        classificacoes: list[CriterionClassification],
        criteria_payload: dict,
    ) -> list[OrganizationIndicator]:
        axis_weights = self._axis_weights(criteria_payload)
        indicators: list[OrganizationIndicator] = []

        by_org: dict[str, list[CriterionClassification]] = {}
        for classification in classificacoes:
            by_org.setdefault(classification.orgao, []).append(classification)

        for orgao, rows in sorted(by_org.items()):
            peso_total = sum(row.peso_criterio for row in rows)
            score_total = sum(row.score_ponderado for row in rows)
            conformidade = (score_total / peso_total * 100) if peso_total else 0.0
            classificacoes_count = {key: 0 for key in CLASSIFICATION_POINTS}
            axis_totals: dict[str, dict[str, float]] = {}

            for row in rows:
                classificacoes_count[row.classificacao] = (
                    classificacoes_count.get(row.classificacao, 0) + 1
                )
                axis = axis_totals.setdefault(
                    row.eixo_imga, {"peso": 0.0, "score": 0.0, "criterios": 0.0}
                )
                axis["peso"] += row.peso_criterio
                axis["score"] += row.score_ponderado
                axis["criterios"] += 1

            pontuacao_por_eixo = {
                axis: round(
                    (values["score"] / values["peso"] * 100) if values["peso"] else 0.0,
                    2,
                )
                for axis, values in sorted(axis_totals.items())
            }
            criterios_por_eixo = {
                axis: int(values["criterios"])
                for axis, values in sorted(axis_totals.items())
            }
            imga_global = round(
                sum(
                    pontuacao_por_eixo.get(axis, 0.0) * weight
                    for axis, weight in axis_weights.items()
                ),
                2,
            )

            indicators.append(
                OrganizationIndicator(
                    orgao=orgao,
                    criterios_avaliados=len(rows),
                    peso_total=round(peso_total, 4),
                    score_total=round(score_total, 4),
                    conformidade_percentual=round(conformidade, 2),
                    classificacoes=classificacoes_count,
                    pontuacao_por_eixo=pontuacao_por_eixo,
                    criterios_por_eixo=criterios_por_eixo,
                    imga_global=imga_global,
                    faixa=self._faixa(imga_global),
                )
            )

        return sorted(indicators, key=lambda item: item.imga_global, reverse=True)

    def _write_outputs(
        self,
        output_dir: Path,
        criteria_file: Path,
        classificacoes: list[CriterionClassification],
        indicadores: list[OrganizationIndicator],
        manual_sample_size: int,
    ) -> dict[str, str]:
        classifications_path = output_dir / "classificacoes.json"
        indicators_path = output_dir / "indicadores_orgaos.csv"
        matrix_path = output_dir / "criterios_orgaos.csv"
        manual_sample_path = output_dir / "validacao_manual_amostra.csv"
        summary_path = output_dir / "sprint7_report.json"

        classifications_payload = [asdict(item) for item in classificacoes]
        indicators_payload = [asdict(item) for item in indicadores]

        with open(classifications_path, "w", encoding="utf-8") as fp:
            json.dump(classifications_payload, fp, ensure_ascii=False, indent=2)

        pd.DataFrame(indicators_payload).to_csv(indicators_path, index=False)

        matrix_rows = [
            {
                "orgao": item.orgao,
                "criterio": item.criterio,
                "eixo_imga": item.eixo_imga,
                "classificacao": item.classificacao,
                "pontuacao": item.pontuacao,
                "peso_criterio": item.peso_criterio,
                "score_ponderado": item.score_ponderado,
                "score_recuperacao": item.score_recuperacao,
                "evidencias_total": item.evidencias_total,
                "documento_top": (
                    item.evidencias[0]["documento"] if item.evidencias else ""
                ),
                "pagina_top": item.evidencias[0]["pagina"] if item.evidencias else "",
                "trecho_top": item.evidencias[0]["trecho"] if item.evidencias else "",
            }
            for item in classificacoes
        ]
        matrix_df = pd.DataFrame(matrix_rows)
        matrix_df.to_csv(matrix_path, index=False)

        sample_df = matrix_df.head(max(0, manual_sample_size)).copy()
        if not sample_df.empty:
            sample_df["classificacao_validada"] = ""
            sample_df["ajuste_necessario"] = ""
            sample_df["observacao_validador"] = ""
            sample_df["validador"] = ""
        sample_df.to_csv(manual_sample_path, index=False)

        summary_payload = {
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "criterios_file": str(criteria_file),
            "classificacoes_total": len(classificacoes),
            "orgaos_total": len(indicadores),
            "arquivos": {
                "classificacoes": str(classifications_path),
                "indicadores_orgaos": str(indicators_path),
                "criterios_orgaos": str(matrix_path),
                "validacao_manual_amostra": str(manual_sample_path),
            },
        }
        with open(summary_path, "w", encoding="utf-8") as fp:
            json.dump(summary_payload, fp, ensure_ascii=False, indent=2)

        summary_payload["arquivos"]["relatorio"] = str(summary_path)
        return summary_payload["arquivos"]

    def _resolve_orgaos(
        self, orgaos: Iterable[str] | None, max_orgaos: int | None
    ) -> list[str]:
        if orgaos:
            selected = [str(orgao).strip() for orgao in orgaos if str(orgao).strip()]
        else:
            selected = self._list_indexed_orgaos()

        if max_orgaos is not None:
            selected = selected[:max_orgaos]
        if not selected:
            raise ValueError(
                "Nenhum orgao encontrado. Execute a Sprint 5 ou informe --orgao."
            )
        return selected

    def _list_indexed_orgaos(self) -> list[str]:
        if not self.sqlite_path.exists():
            raise FileNotFoundError(
                f"Base SQLite nao encontrada em {self.sqlite_path}. Execute a Sprint 5 antes da Sprint 7."
            )

        conn = sqlite3.connect(self.sqlite_path)
        try:
            rows = conn.execute(
                "SELECT DISTINCT orgao FROM documents ORDER BY orgao"
            ).fetchall()
        finally:
            conn.close()
        return [str(row[0]) for row in rows if row[0]]

    def _load_criteria(self, criteria_path: Path) -> tuple[dict, list[dict]]:
        with open(criteria_path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)

        if isinstance(payload, dict):
            criteria = payload.get("criterios", [])
        elif isinstance(payload, list):
            criteria = payload
            payload = {"criterios": criteria}
        else:
            criteria = []

        if not isinstance(criteria, list):
            raise ValueError(f"Arquivo de criterios invalido: {criteria_path}")
        return payload, criteria

    def _filter_criteria(
        self, criteria: list[dict], codigo: str | None, max_criterios: int | None
    ) -> list[dict]:
        filtered = criteria
        if codigo:
            filtered = [
                criterion for criterion in filtered if criterion.get("codigo") == codigo
            ]
            if not filtered:
                raise ValueError(f"Criterio nao encontrado: {codigo}")
        if max_criterios is not None:
            filtered = filtered[:max_criterios]
        return filtered

    def _keyword_hits(
        self, keywords: list[str], evidencias: list[EvidenceRecord]
    ) -> list[str]:
        haystack = self._normalize_text(
            " ".join(evidence.trecho for evidence in evidencias)
        )
        hits = []
        for keyword in keywords:
            normalized = self._normalize_text(keyword)
            if normalized and normalized in haystack:
                hits.append(keyword)
        return sorted(set(hits))

    def _has_negative_signal(self, text: str) -> bool:
        normalized = self._normalize_text(text)
        return any(re.search(pattern, normalized) for pattern in NEGATIVE_PATTERNS)

    def _axis_weights(self, criteria_payload: dict) -> dict[str, float]:
        eixos = (
            criteria_payload.get("eixos_imga", {})
            if isinstance(criteria_payload, dict)
            else {}
        )
        weights = {}
        if isinstance(eixos, dict):
            for axis, payload in eixos.items():
                if isinstance(payload, dict):
                    weights[axis] = float(payload.get("peso_eixo") or 0.0) / 100

        if weights:
            return weights

        return {
            "E1": 0.10,
            "E2": 0.10,
            "E3": 0.15,
            "E4": 0.20,
            "E5": 0.10,
            "E6": 0.15,
            "E7": 0.10,
            "E8": 0.10,
        }

    def _evidence_to_dict(self, evidence: EvidenceRecord) -> dict:
        payload = asdict(evidence)
        payload["score_recuperacao"] = payload.pop("score")
        return payload

    def _faixa(self, score: float) -> str:
        if score >= 75:
            return "Avancada"
        if score >= 50:
            return "Intermediaria"
        if score >= 25:
            return "Basica"
        return "Incipiente"

    @staticmethod
    def _normalize_text(text: str) -> str:
        text = (text or "").lower()
        replacements = str.maketrans(
            "áàâãéêíóôõúç",
            "aaaaeeiooouc",
        )
        text = text.translate(replacements)
        return re.sub(r"\s+", " ", text).strip()
