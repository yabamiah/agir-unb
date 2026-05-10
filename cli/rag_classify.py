"""
CLI da Sprint 7 para classificacao normativa e indicadores IMGA.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from core.services.rag_classification_service import RagClassificationService
from core.services.rag_index_service import TIPOS_DOCUMENTO_VALIDOS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classifica evidencias da Sprint 6 e gera indicadores comparativos da Sprint 7."
    )
    parser.add_argument(
        "--criterios-file",
        default="estrutura_criterios.json",
        help="Arquivo JSON de criterios normativos.",
    )
    parser.add_argument(
        "--criterio",
        help="Processa apenas um criterio especifico.",
    )
    parser.add_argument(
        "--orgao",
        action="append",
        help="Filtra um orgao. Pode ser informado mais de uma vez.",
    )
    parser.add_argument(
        "--tipos",
        nargs="+",
        choices=TIPOS_DOCUMENTO_VALIDOS,
        help=f"Filtra por tipos documentais. Opcoes: {', '.join(TIPOS_DOCUMENTO_VALIDOS)}",
    )
    parser.add_argument(
        "--max-criterios",
        type=int,
        help="Limita a quantidade de criterios processados.",
    )
    parser.add_argument(
        "--max-orgaos",
        type=int,
        help="Limita a quantidade de orgaos processados quando --orgao nao for informado.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Quantidade de evidencias recuperadas por criterio.",
    )
    parser.add_argument(
        "--min-score-atende",
        type=float,
        default=0.85,
        help="Score minimo de recuperacao para classificar como atende quando houver termos suficientes.",
    )
    parser.add_argument(
        "--min-score-parcial",
        type=float,
        default=0.55,
        help="Score minimo para considerar evidencia parcial sem termos-chave.",
    )
    parser.add_argument(
        "--min-keyword-hits-atende",
        type=int,
        default=2,
        help="Quantidade minima de palavras-chave esperadas para classificar como atende.",
    )
    parser.add_argument(
        "--manual-sample-size",
        type=int,
        default=20,
        help="Quantidade de linhas exportadas para validacao manual.",
    )
    parser.add_argument(
        "--output-dir",
        help="Diretorio de saida. Padrao: data/rag/sprint7.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger.info("Iniciando Sprint 7: classificacao e indicadores.")

    service = RagClassificationService(
        min_score_atende=args.min_score_atende,
        min_score_parcial=args.min_score_parcial,
        min_keyword_hits_atende=args.min_keyword_hits_atende,
        evidence_top_k=args.top_k,
    )
    report = service.build_report(
        criteria_path=args.criterios_file,
        orgaos=args.orgao,
        tipos_documento=args.tipos,
        codigo=args.criterio,
        max_criterios=args.max_criterios,
        max_orgaos=args.max_orgaos,
        manual_sample_size=args.manual_sample_size,
        output_dir=args.output_dir,
    )

    logger.info("Sprint 7 concluida com sucesso.")
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
