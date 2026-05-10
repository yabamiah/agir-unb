"""
Processador de PDF Otimizado - Módulo DANI
Suporta múltiplas estratégias de extração de texto: PyMuPDF, pdfplumber, OCR.
"""

import os
import shutil
from typing import List, Tuple

from core.utils.pdf_handler import PdfReader

# Bibliotecas otimizadas para PDF
try:
    import pymupdf as fitz

    PYMUPDF_AVAILABLE = True
except ImportError:
    try:
        import fitz

        PYMUPDF_AVAILABLE = True
    except ImportError:
        PYMUPDF_AVAILABLE = False
        fitz = None

try:
    import pdfplumber

    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    pdfplumber = None


class OptimizedPdfProcessor:
    """
    Processador de PDF otimizado com múltiplas estratégias de extração.

    Estratégias (em ordem de preferência):
    1. PyMuPDF - Muito rápido para PDFs com texto embutido
    2. pdfplumber - Boa para PDFs estruturados
    3. OCR (Tesseract) - Fallback para PDFs escaneados
    """

    def __init__(self, logger, enable_ocr: bool = True, max_pages: int | None = None):
        self.logger = logger
        self.cache = {}  # Cache simples para evitar reprocessamento
        self.fallback_processor = PdfReader()
        self.enable_ocr = enable_ocr
        self.max_pages = max_pages
        self.ocr_available = enable_ocr and shutil.which("tesseract") is not None
        self._ocr_warning_emitted = False

    def extract_text_fast(self, file_path: str) -> Tuple[List[str], int]:
        """
        Extrai texto usando a estratégia mais rápida disponível.

        Args:
            file_path: Caminho para o arquivo PDF

        Returns:
            Tupla (lista_de_paginas, total_palavras)
        """
        # Verificar cache primeiro
        file_hash = self._get_file_hash(file_path)
        if file_hash in self.cache:
            self.logger.debug(f"Cache hit para {os.path.basename(file_path)}")
            return self.cache[file_hash]

        pages_text = []
        total_words = 0

        # Estratégia 1: PyMuPDF (mais rápido para PDFs com texto)
        if PYMUPDF_AVAILABLE:
            try:
                pages_text, total_words = self._extract_with_pymupdf(file_path)
                if pages_text and total_words > 0:
                    self.logger.debug(
                        f"PyMuPDF extraiu {len(pages_text)} páginas de {os.path.basename(file_path)}"
                    )
                    self.cache[file_hash] = (pages_text, total_words)
                    return pages_text, total_words
            except Exception as e:
                self.logger.warning(f"PyMuPDF falhou para {file_path}: {e}")

        # Estratégia 2: pdfplumber (boa para PDFs estruturados)
        if PDFPLUMBER_AVAILABLE:
            try:
                pages_text, total_words = self._extract_with_pdfplumber(file_path)
                if pages_text and total_words > 0:
                    self.logger.debug(
                        f"pdfplumber extraiu {len(pages_text)} páginas de {os.path.basename(file_path)}"
                    )
                    self.cache[file_hash] = (pages_text, total_words)
                    return pages_text, total_words
            except Exception as e:
                self.logger.warning(f"pdfplumber falhou para {file_path}: {e}")

        # Estratégia 3: Fallback para OCR (mais lento, exige Tesseract instalado)
        if not self.ocr_available:
            if not self._ocr_warning_emitted:
                if self.enable_ocr:
                    self.logger.warning(
                        "Tesseract nao encontrado no PATH. PDFs escaneados serao ignorados na indexacao RAG. "
                        "Instale tesseract-ocr e tesseract-ocr-por para habilitar OCR."
                    )
                else:
                    self.logger.warning(
                        "OCR desabilitado para esta execucao. PDFs escaneados serao ignorados."
                    )
                self._ocr_warning_emitted = True
            return [], 0

        try:
            pages_text = self.fallback_processor.pdf_to_string(file_path)
            total_words = self.fallback_processor.get_total_words_pdf()
            self.logger.debug(
                f"OCR extraiu {len(pages_text)} páginas de {os.path.basename(file_path)}"
            )
            self.cache[file_hash] = (pages_text, total_words)
            return pages_text, total_words
        except Exception as e:
            self.logger.error(f"Todas as estratégias falharam para {file_path}: {e}")
            return [], 0

    def _extract_with_pymupdf(self, file_path: str) -> Tuple[List[str], int]:
        """Extrai texto usando PyMuPDF (muito rápido)."""
        doc = fitz.open(file_path)
        pages_text = []
        total_words = 0

        page_count = (
            min(doc.page_count, self.max_pages) if self.max_pages else doc.page_count
        )

        for page_num in range(page_count):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                pages_text.append(text.lower())
                total_words += len(text.split())

        doc.close()
        return pages_text, total_words

    def _extract_with_pdfplumber(self, file_path: str) -> Tuple[List[str], int]:
        """Extrai texto usando pdfplumber (boa para PDFs estruturados)."""
        pages_text = []
        total_words = 0

        with pdfplumber.open(file_path) as pdf:
            pages = pdf.pages[: self.max_pages] if self.max_pages else pdf.pages
            for page in pages:
                text = page.extract_text()
                if text and text.strip():
                    pages_text.append(text.lower())
                    total_words += len(text.split())

        return pages_text, total_words

    def _get_file_hash(self, file_path: str) -> str:
        """Gera hash do arquivo para cache."""
        try:
            stat = os.stat(file_path)
            return f"{os.path.basename(file_path)}_{stat.st_size}_{stat.st_mtime}"
        except Exception:
            return os.path.basename(file_path)

    def clear_cache(self):
        """Limpa o cache de arquivos processados."""
        self.cache.clear()
