"""
CLI da Sprint 5 para construir a base auditavel e o indice vetorial local.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger

from core.services.rag_index_service import RagIndexService, TIPOS_DOCUMENTO_VALIDOS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Constroi a base auditavel do AGIR-RAG Lite e o indice vetorial local da Sprint 5."
    )
    parser.add_argument(
        "--tipos",
        nargs="+",
        default=list(TIPOS_DOCUMENTO_VALIDOS),
        help=f"Tipos documentais a indexar. Opcoes: {', '.join(TIPOS_DOCUMENTO_VALIDOS)}",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Recria SQLite/Parquet e a collection do Qdrant.",
    )
    parser.add_argument(
        "--orgaos",
        nargs="+",
        help="Indexa apenas os orgaos informados. Exemplo: --orgaos SEAGRI CGDF",
    )
    parser.add_argument(
        "--max-documents",
        type=int,
        help="Limita a quantidade total de PDFs processados para execucao piloto.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1200,
        help="Tamanho alvo dos chunks em caracteres.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=200,
        help="Sobreposicao entre chunks em caracteres.",
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
    parser.add_argument(
        "--enable-ocr",
        action="store_true",
        help="Habilita OCR em PDFs escaneados. Desabilitado por padrao para manter a indexacao piloto rapida.",
    )
    parser.add_argument(
        "--max-pages-per-document",
        type=int,
        default=40,
        help="Limite de paginas extraidas por PDF. Use 0 para processar o documento inteiro.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger.info("Iniciando Sprint 5: base auditavel e indexacao AGIR-RAG Lite.")

    service = RagIndexService(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        collection_name=args.collection,
        embedding_dimensions=args.embedding_dimensions,
        enable_ocr=args.enable_ocr,
        max_pages_per_document=args.max_pages_per_document or None,
    )
    manifest = service.build_index(
        reset=args.reset,
        tipos_documento=args.tipos,
        orgaos=args.orgaos,
        max_documents=args.max_documents,
    )

    logger.info("Indexacao concluida com sucesso.")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
