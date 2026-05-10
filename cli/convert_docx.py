#!/usr/bin/env python3
"""
Utilitário para conversão de todos os arquivos DOCX para PDF
Usa o sistema de conversão do DANI com múltiplas abordagens
"""

import argparse
import os
import sys
import time

# Adicionar o diretório core ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from loguru import logger

from core.models.dani import Dani


def find_docx_files(base_path: str) -> list:
    """
    Encontra todos os arquivos DOCX recursivamente

    Args:
        base_path: Caminho base para buscar arquivos

    Returns:
        Lista de tuplas (caminho_completo, diretorio_relativo, nome_arquivo)
    """
    docx_files = []

    if not os.path.exists(base_path):
        logger.error(f"❌ Diretório não encontrado: {base_path}")
        return docx_files

    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.lower().endswith(".docx"):
                full_path = os.path.join(root, file)
                rel_dir = os.path.relpath(root, base_path)
                docx_files.append((full_path, rel_dir, file))

    return docx_files


def convert_single_file(dani_instance: Dani, docx_path: str, output_base: str) -> bool:
    """
    Converte um único arquivo DOCX para PDF

    Args:
        dani_instance: Instância do DANI
        docx_path: Caminho do arquivo DOCX
        output_base: Diretório base de saída

    Returns:
        True se a conversão foi bem-sucedida
    """
    try:
        # Determinar diretório de saída
        rel_path = os.path.relpath(docx_path, output_base)
        rel_dir = os.path.dirname(rel_path)

        pdf_filename = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
        pdf_output_dir = os.path.join(output_base, "pdf_output", rel_dir)
        pdf_output_path = os.path.join(pdf_output_dir, pdf_filename)

        # Verificar se o PDF já existe
        if os.path.exists(pdf_output_path) and os.path.getsize(pdf_output_path) > 0:
            logger.info(f"📄 PDF já existe, pulando: {pdf_filename}")
            return True

        # Criar diretório de saída
        os.makedirs(pdf_output_dir, exist_ok=True)

        # Converter
        logger.info(f"🔄 Convertendo: {os.path.basename(docx_path)}")
        success = dani_instance.docx_to_pdf(docx_path, pdf_output_path)

        if (
            success
            and os.path.exists(pdf_output_path)
            and os.path.getsize(pdf_output_path) > 0
        ):
            logger.info(f"✅ Convertido com sucesso: {pdf_filename}")
            return True
        else:
            logger.error(f"❌ Falha na conversão: {os.path.basename(docx_path)}")
            return False

    except Exception as e:
        logger.error(f"❌ Erro ao converter {docx_path}: {e}")
        return False


def convert_all_docx(
    input_path: str, output_path: str = None, max_workers: int = 4
) -> dict:
    """
    Converte todos os arquivos DOCX encontrados para PDF

    Args:
        input_path: Caminho onde buscar arquivos DOCX
        output_path: Caminho de saída (opcional)
        max_workers: Número máximo de workers para processamento paralelo

    Returns:
        Dicionário com estatísticas da conversão
    """
    logger.info("🚀 Iniciando conversão em massa DOCX→PDF")
    logger.info(f"📁 Diretório de entrada: {input_path}")

    if output_path:
        logger.info(f"📁 Diretório de saída: {output_path}")
    else:
        output_path = input_path
        logger.info(f"📁 Diretório de saída: {output_path} (mesmo da entrada)")

    # Encontrar todos os arquivos DOCX
    logger.info("🔍 Buscando arquivos DOCX...")
    docx_files = find_docx_files(input_path)

    if not docx_files:
        logger.warning("⚠️ Nenhum arquivo DOCX encontrado")
        return {"total": 0, "sucessos": 0, "falhas": 0, "pulados": 0}

    logger.info(f"📄 Encontrados {len(docx_files)} arquivos DOCX")

    # Criar instância do DANI
    try:
        dani = Dani(max_workers=max_workers)
        logger.info("✅ Instância do DANI criada com sucesso")
    except Exception as e:
        logger.error(f"❌ Erro ao criar instância do DANI: {e}")
        return {"total": 0, "sucessos": 0, "falhas": 0, "pulados": 0}

    # Processar arquivos
    start_time = time.time()
    sucessos = 0
    falhas = 0
    pulados = 0

    logger.info("🔄 Iniciando conversão...")

    for i, (docx_path, rel_dir, filename) in enumerate(docx_files, 1):
        logger.info(f"📊 Progresso: {i}/{len(docx_files)} - {filename}")

        # Verificar se o arquivo é válido
        try:
            if os.path.getsize(docx_path) == 0:
                logger.warning(f"⚠️ Arquivo vazio, pulando: {filename}")
                pulados += 1
                continue
        except OSError:
            logger.warning(f"⚠️ Erro ao acessar arquivo, pulando: {filename}")
            pulados += 1
            continue

        # Converter arquivo
        if convert_single_file(dani, docx_path, output_path):
            sucessos += 1
        else:
            falhas += 1

        # Log de progresso a cada 10 arquivos
        if i % 10 == 0:
            logger.info(
                f"📈 Progresso: {i}/{len(docx_files)} | ✅ {sucessos} | ❌ {falhas} | ⏭️ {pulados}"
            )

    end_time = time.time()
    duracao = end_time - start_time

    # Estatísticas finais
    total = len(docx_files)
    estatisticas = {
        "total": total,
        "sucessos": sucessos,
        "falhas": falhas,
        "pulados": pulados,
        "duracao": duracao,
        "taxa_sucesso": (sucessos / total * 100) if total > 0 else 0,
    }

    return estatisticas


def main():
    """Função principal do utilitário"""
    parser = argparse.ArgumentParser(
        description="Utilitário para conversão DOCX→PDF usando DANI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python convert_docx_to_pdf.py /caminho/para/docx
  python convert_docx_to_pdf.py /caminho/para/docx -o /caminho/para/pdf
  python convert_docx_to_pdf.py /caminho/para/docx -w 8
        """,
    )

    parser.add_argument("input_path", help="Diretório onde buscar arquivos DOCX")

    parser.add_argument(
        "-o", "--output", help="Diretório de saída (padrão: mesmo da entrada)"
    )

    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        default=4,
        help="Número de workers para processamento paralelo (padrão: 4)",
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Modo verboso (mais logs)"
    )

    args = parser.parse_args()

    # Configurar nível de log
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    logger.info("=" * 80)
    logger.info("🔄 UTILITÁRIO DE CONVERSÃO DOCX→PDF - DANI")
    logger.info("=" * 80)

    try:
        # Verificar se o diretório de entrada existe
        if not os.path.exists(args.input_path):
            logger.error(f"❌ Diretório de entrada não encontrado: {args.input_path}")
            return 1

        # Executar conversão
        estatisticas = convert_all_docx(
            input_path=args.input_path,
            output_path=args.output,
            max_workers=args.workers,
        )

        # Exibir resultados
        logger.info("=" * 80)
        logger.info("📊 RESULTADOS DA CONVERSÃO")
        logger.info("=" * 80)
        logger.info(f"⏱️  Tempo total: {estatisticas['duracao']:.2f} segundos")
        logger.info(f"📄 Total de arquivos: {estatisticas['total']}")
        logger.info(f"✅ Conversões bem-sucedidas: {estatisticas['sucessos']}")
        logger.info(f"❌ Falhas: {estatisticas['falhas']}")
        logger.info(f"⏭️  Arquivos pulados: {estatisticas['pulados']}")
        logger.info(f"📊 Taxa de sucesso: {estatisticas['taxa_sucesso']:.1f}%")

        if estatisticas["sucessos"] > 0:
            tempo_medio = estatisticas["duracao"] / estatisticas["sucessos"]
            logger.info(f"⚡ Tempo médio por conversão: {tempo_medio:.2f} segundos")

        logger.info("=" * 80)

        if estatisticas["falhas"] == 0:
            logger.info("🎉 CONVERSÃO CONCLUÍDA COM SUCESSO!")
            return 0
        else:
            logger.warning(f"⚠️ CONVERSÃO CONCLUÍDA COM {estatisticas['falhas']} FALHAS")
            return 1

    except KeyboardInterrupt:
        logger.info("\n⚠️ Conversão interrompida pelo usuário")
        return 1
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
