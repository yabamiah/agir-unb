"""
Conversor DOCX para PDF - Módulo DANI
Suporta conversão usando LibreOffice ou pypandoc.
"""

import os
import shutil
import subprocess
import traceback
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple

import pypandoc


class DocxConverter:
    """
    Conversor de DOCX para PDF usando múltiplas estratégias.
    
    Estratégias (em ordem de preferência):
    1. LibreOffice (headless) - Mais confiável para formatação complexa
    2. pypandoc com engines LaTeX - Alternativa quando LibreOffice não está disponível
    """
    
    def __init__(self, logger, pdf_workers: int = 3):
        self.logger = logger
        self.pdf_workers = pdf_workers
    
    def check_pandoc_available(self) -> bool:
        """Verifica se pandoc está disponível no sistema."""
        try:
            result = subprocess.run(['pandoc', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def check_libreoffice_available(self) -> bool:
        """Verifica se LibreOffice está disponível no sistema."""
        try:
            result = subprocess.run(['libreoffice', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False

    def _convert_with_libreoffice(self, docx_file_path: str, pdf_output_path: str) -> bool:
        """Conversão usando LibreOffice via linha de comando."""
        try:
            output_dir = os.path.dirname(pdf_output_path)
            os.makedirs(output_dir, exist_ok=True)
            
            cmd = [
                'libreoffice',
                '--headless',
                '--convert-to', 'pdf',
                '--outdir', output_dir,
                docx_file_path
            ]
            
            self.logger.debug(f"Executando comando LibreOffice: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                expected_pdf = os.path.join(output_dir, 
                                          os.path.splitext(os.path.basename(docx_file_path))[0] + '.pdf')
                
                if os.path.exists(expected_pdf):
                    if expected_pdf != pdf_output_path:
                        shutil.move(expected_pdf, pdf_output_path)
                    
                    self.logger.info(f"✅ [LibreOffice] Convertido: {os.path.basename(docx_file_path)}")
                    return True
                else:
                    self.logger.error(f"❌ [LibreOffice] PDF não foi criado: {expected_pdf}")
                    return False
            else:
                self.logger.error(f"❌ [LibreOffice] Erro na conversão: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"❌ [LibreOffice] Timeout na conversão de {docx_file_path}")
            return False
        except Exception as e:
            self.logger.error(f"❌ [LibreOffice] Erro inesperado: {str(e)}")
            return False

    def _convert_with_pypandoc(self, docx_file_path: str, pdf_output_path: str) -> bool:
        """Conversão usando pypandoc com diferentes engines."""
        engines = ['xelatex', 'pdflatex', 'lualatex']
        
        for engine in engines:
            try:
                self.logger.debug(f"Tentando conversão com pypandoc usando {engine}")
                
                pypandoc.convert_file(
                    docx_file_path,
                    'pdf',
                    outputfile=pdf_output_path,
                    extra_args=[f'--pdf-engine={engine}']
                )

                if os.path.exists(pdf_output_path) and os.path.getsize(pdf_output_path) > 0:
                    self.logger.info(f"✅ [pypandoc-{engine}] Convertido: {os.path.basename(docx_file_path)}")
                    return True
                else:
                    self.logger.warning(f"⚠️ [pypandoc-{engine}] PDF vazio ou não criado")
                    
            except Exception as e:
                self.logger.warning(f"⚠️ [pypandoc-{engine}] Falhou: {str(e)}")
                continue
        
        return False

    def docx_to_pdf(self, docx_file_path: str, pdf_output_path: str) -> bool:
        """
        Conversão robusta de DOCX para PDF.
        
        Args:
            docx_file_path: Caminho do arquivo DOCX
            pdf_output_path: Caminho para salvar o PDF
            
        Returns:
            True se conversão foi bem-sucedida
        """
        try:
            if not os.path.exists(docx_file_path):
                self.logger.error(f"❌ Arquivo DOCX não encontrado: {docx_file_path}")
                return False

            if os.path.getsize(docx_file_path) == 0:
                self.logger.error(f"❌ Arquivo DOCX está vazio: {docx_file_path}")
                return False

            self.logger.debug(f"🔄 Iniciando conversão: {os.path.basename(docx_file_path)}")

            # Método 1: LibreOffice
            if self.check_libreoffice_available():
                self.logger.debug("📝 Tentando conversão com LibreOffice...")
                if self._convert_with_libreoffice(docx_file_path, pdf_output_path):
                    return True
            else:
                self.logger.warning("⚠️ LibreOffice não está disponível")

            # Método 2: pypandoc
            if self.check_pandoc_available():
                self.logger.debug("📝 Tentando conversão com pypandoc...")
                if self._convert_with_pypandoc(docx_file_path, pdf_output_path):
                    return True
            else:
                self.logger.warning("⚠️ Pandoc não está disponível")

            self.logger.error(f"❌ Todos os métodos de conversão falharam para: {os.path.basename(docx_file_path)}")
            return False

        except Exception as e:
            self.logger.error(f"❌ Erro crítico na conversão de {docx_file_path}: {str(e)}")
            return False

    def convert_single_docx(self, docx_file_path: str, pdf_output_dir: str) -> bool:
        """
        Converte um único arquivo DOCX para PDF.
        
        Args:
            docx_file_path: Caminho completo para o arquivo DOCX
            pdf_output_dir: Diretório onde o PDF será salvo
            
        Returns:
            True se conversão foi bem-sucedida
        """
        try:
            if not os.path.exists(docx_file_path):
                self.logger.warning(f"Arquivo DOCX não encontrado: {docx_file_path}")
                return False

            try:
                file_size = os.path.getsize(docx_file_path)
                if file_size == 0:
                    self.logger.warning(f"Arquivo DOCX está vazio: {docx_file_path}")
                    return False
                elif file_size < 1024:
                    self.logger.warning(f"Arquivo DOCX muito pequeno: {docx_file_path} ({file_size} bytes)")
            except OSError as e:
                self.logger.error(f"Erro ao verificar arquivo DOCX: {docx_file_path} - {str(e)}")
                return False

            os.makedirs(pdf_output_dir, exist_ok=True)

            pdf_filename = os.path.splitext(os.path.basename(docx_file_path))[0] + '.pdf'
            pdf_output_path = os.path.join(pdf_output_dir, pdf_filename)

            if os.path.exists(pdf_output_path):
                self.logger.info(f"📄 PDF já existe, pulando conversão: {pdf_filename}")
                return True

            self.logger.debug(f"🔄 Convertendo: {os.path.basename(docx_file_path)} → {pdf_filename}")
            
            success = self.docx_to_pdf(docx_file_path, pdf_output_path)
            
            if success and os.path.exists(pdf_output_path) and os.path.getsize(pdf_output_path) > 0:
                self.logger.info(f"✅ Conversão bem-sucedida: {pdf_filename}")
                return True
            else:
                self.logger.error(f"❌ Falha na conversão: {os.path.basename(docx_file_path)}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erro inesperado ao converter {docx_file_path}: {str(e)}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def convert_orgao_docx(self, docx_dir: str, pdf_dir: str, orgao_name: str) -> Tuple[int, int, int]:
        """
        Converte todos os arquivos DOCX de um órgão para PDF.
        
        Returns:
            Tupla (sucessos, falhas, total)
        """
        if not os.path.exists(docx_dir):
            self.logger.warning(f"Diretório não encontrado para {orgao_name}: {docx_dir}")
            return (0, 0, 0)

        all_files = os.listdir(docx_dir)
        docx_files = [f for f in all_files if f.endswith('.docx') and os.path.getsize(os.path.join(docx_dir, f)) > 0]

        if not docx_files:
            self.logger.info(f"Nenhum arquivo DOCX válido encontrado para {orgao_name}")
            return (0, 0, 0)

        self.logger.info(f"📁 Convertendo {len(docx_files)} arquivos DOCX do órgão: {orgao_name}")

        sucessos = 0
        falhas = 0
        arquivos_ja_existentes = 0

        max_workers = min(self.pdf_workers, 3)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {}

            for docx_file in docx_files:
                docx_path = os.path.join(docx_dir, docx_file)
                pdf_filename = os.path.splitext(docx_file)[0] + '.pdf'
                pdf_path = os.path.join(pdf_dir, pdf_filename)
                
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
                    arquivos_ja_existentes += 1
                    continue
                
                future = executor.submit(self.convert_single_docx, docx_path, pdf_dir)
                future_to_file[future] = docx_file

            for future in as_completed(future_to_file):
                try:
                    if future.result():
                        sucessos += 1
                    else:
                        falhas += 1
                except Exception as e:
                    self.logger.error(f"❌ Erro no processamento: {str(e)}")
                    falhas += 1

        total = len(docx_files)
        self.logger.info(f"📊 Órgão {orgao_name}: {sucessos}/{total} conversões bem-sucedidas")
        if arquivos_ja_existentes > 0:
            self.logger.info(f"📄 {arquivos_ja_existentes} PDFs já existiam e foram pulados")

        return (sucessos, falhas, total)

    def convert_all_orgaos(self, docx_base_path: str, pdf_base_path: str) -> Dict[str, Dict[str, int]]:
        """
        Converte todos os arquivos DOCX de todos os órgãos para PDF.
        
        Returns:
            Estatísticas da conversão por órgão
        """
        if not os.path.exists(docx_base_path):
            self.logger.error(f"Diretório de DOCX não encontrado: {docx_base_path}")
            return {}

        orgaos_dirs = [d for d in os.listdir(docx_base_path)
                       if os.path.isdir(os.path.join(docx_base_path, d))]

        if not orgaos_dirs:
            self.logger.warning("Nenhum diretório de órgão encontrado")
            return {}

        self.logger.info(f"🚀 Iniciando conversão DOCX→PDF para {len(orgaos_dirs)} órgãos")
        start_time = time.time()

        estatisticas = {}
        total_sucessos = 0
        total_falhas = 0
        total_arquivos = 0

        for orgao in orgaos_dirs:
            docx_dir = os.path.join(docx_base_path, orgao)
            pdf_dir = os.path.join(pdf_base_path, orgao)
            
            sucessos, falhas, total = self.convert_orgao_docx(docx_dir, pdf_dir, orgao)

            estatisticas[orgao] = {
                'sucessos': sucessos,
                'falhas': falhas,
                'total': total,
                'taxa_sucesso': (sucessos / total * 100) if total > 0 else 0
            }

            total_sucessos += sucessos
            total_falhas += falhas
            total_arquivos += total

        end_time = time.time()
        duracao = end_time - start_time

        self.logger.info("=" * 60)
        self.logger.info(f"📈 RESUMO DA CONVERSÃO DOCX → PDF")
        self.logger.info("=" * 60)
        self.logger.info(f"⏱️  Tempo total: {duracao:.2f} segundos")
        self.logger.info(f"📁 Órgãos processados: {len(orgaos_dirs)}")
        self.logger.info(f"📄 Total de arquivos: {total_arquivos}")
        self.logger.info(f"✅ Sucessos: {total_sucessos}")
        self.logger.info(f"❌ Falhas: {total_falhas}")
        if total_arquivos > 0:
            self.logger.info(f"📊 Taxa de sucesso: {(total_sucessos / total_arquivos * 100):.1f}%")
        self.logger.info("=" * 60)

        return estatisticas

    def check_dependencies(self) -> None:
        """Verifica e reporta o status das dependências para conversão DOCX→PDF."""
        self.logger.info("🔍 Verificando dependências para conversão DOCX→PDF...")
        
        libreoffice_available = self.check_libreoffice_available()
        pandoc_available = self.check_pandoc_available()
        
        if libreoffice_available:
            self.logger.info("✅ LibreOffice disponível - será usado como método principal")
        else:
            self.logger.warning("⚠️ LibreOffice não encontrado")
            self.logger.info("💡 Para instalar: sudo apt-get install libreoffice")
        
        if pandoc_available:
            self.logger.info("✅ Pandoc disponível - será usado como método alternativo")
        else:
            self.logger.warning("⚠️ Pandoc não encontrado")
            self.logger.info("💡 Para instalar: sudo apt-get install pandoc")
        
        if not libreoffice_available and not pandoc_available:
            self.logger.error("❌ Nenhuma ferramenta de conversão disponível!")
        else:
            self.logger.info("🎉 Pelo menos uma ferramenta de conversão está disponível")
