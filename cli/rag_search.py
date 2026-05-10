"""
CLI da Sprint 6 para recuperacao hibrida e evidencias do AGIR-RAG Lite.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from core.services.rag_index_service import TIPOS_DOCUMENTO_VALIDOS
from core.services.rag_retrieval_service import RagRetrievalService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa busca hibrida em SQLite FTS5 + Qdrant local e retorna evidencias auditaveis."
    )
    parser.add_argument(
        "--pergunta",
        help="Pergunta normativa livre para recuperar evidencias.",
    )
    parser.add_argument(
        "--criterio",
        help="Codigo do criterio associado a pergunta livre ou filtro no arquivo de criterios.",
    )
    parser.add_argument(
        "--criterios-file",
        default="estrutura_criterios.json",
        help="Arquivo JSON de criterios normativos para teste em lote.",
    )
    parser.add_argument(
        "--usar-criterios",
        action="store_true",
        help="Executa perguntas normativas reais a partir do arquivo de criterios.",
    )
    parser.add_argument(
        "--max-criterios",
        type=int,
        help="Limita a quantidade de criterios processados no teste em lote.",
    )
    parser.add_argument(
        "--orgao",
        help="Filtra evidencias por orgao.",
    )
    parser.add_argument(
        "--tipos",
        nargs="+",
        choices=TIPOS_DOCUMENTO_VALIDOS,
        help=f"Filtra por tipos documentais. Opcoes: {', '.join(TIPOS_DOCUMENTO_VALIDOS)}",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Quantidade de evidencias retornadas por pergunta.",
    )
    parser.add_argument(
        "--collection",
        default="agir_chunks",
        help="Nome da collection no Qdrant.",
    )
    parser.add_argument(
        "--embedding-dimensions",
        type=int,
        default=384,
        help="Dimensao do vetor local gerado pelo embedder leve.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.pergunta and not args.usar_criterios:
        parser.error("informe --pergunta ou use --usar-criterios")

    logger.info("Iniciando Sprint 6: recuperacao hibrida e evidencias.")

    service = RagRetrievalService(
        collection_name=args.collection,
        embedding_dimensions=args.embedding_dimensions,
    )

    if args.usar_criterios:
        responses = service.search_criteria_file(
            criteria_path=args.criterios_file,
            codigo=args.criterio,
            orgao=args.orgao,
            tipos_documento=args.tipos,
            top_k=args.top_k,
            max_criterios=args.max_criterios,
        )
        payload = [response.to_dict() for response in responses]
    else:
        response = service.search(
            pergunta=args.pergunta,
            criterio=args.criterio,
            orgao=args.orgao,
            tipos_documento=args.tipos,
            top_k=args.top_k,
        )
        payload = response.to_dict()

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
