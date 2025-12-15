###########################################################################
## LARA-I : Levantador Automático de Recursos Administrativos Interativo ##
###########################################################################
import asyncio
import os.path
import re
import json
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any

import requests
from loguru import logger
from playwright.async_api import async_playwright, ElementHandle, Browser, Page

from core.services.aws_service import S3Service

@dataclass
class ConfiguracaoLara:
    """Configurações do LARA-I"""

    timeout_navegacao: int = 220_000
    timeout_seletor: int = 180_000
    timeout_preenchimento: int = 180_000
    timeout_press: int = 180_000
    timeout_load_state: int = 180_000
    arquivo_orgaos: str = None
    termos_pesquisa: Dict[str, List[str]] = None
    inputs_pesquisa: List[str] = None
    s3_service: S3Service = None

    def __post_init__(self):
        self.s3_service = S3Service(logger=logger)
        path = ""

        if self.arquivo_orgaos is None:
            base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
            path = os.path.join(base_dir, 'data', 'lara', 'orgaos_gdf_links.json')

            os.makedirs(os.path.dirname(path), exist_ok=True)
            if not os.path.exists(path):
                sucesso = self.s3_service.download_object(
                    bucket='agir-bucket',
                    object_name='lara-config/orgaos_gdf_links.json',
                    file_path=path
                )
                if not sucesso:
                    logger.error("Falha ao baixar o arquivo órgãos do S3.")
                else:
                    logger.info("Arquivo de órgãos baixado do S3 com sucesso.")
        else:
            logger.info("Arquivo de órgãos já existe localmente.")

        self.arquivo_orgaos = path
            
        self.termos_pesquisa = self.termos_pesquisa or {
            "cig": [
                "cig atas",
                "Comitê Interno de Governança",
                "cigp",
                "Reuniões: Atas",
                "Relatórios de Reuniões de Governança"
            ],
            "pg": [
                "programa de integridade",
                "programa integridade",
                "integridade e compliance"
            ],
            "compliance": [
                "plano de compliance",
                "plano compliance",
                "compliance",
                "plano de integridade e compliance"
            ]
        }

        self.inputs_pesquisa = self.inputs_pesquisa or ["s", "q", "searchword"]

class LaraI:
    """Classe principal do LARA-I para extração de atas de órgãos do GDF"""
    
    def __init__(self, config: Optional[ConfiguracaoLara] = None):
        self.config = config or ConfiguracaoLara()
        self._setup_logger()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.output_files = os.path.join(base_dir, 'data', 'dani', 'docs', 'input')

        os.makedirs(self.output_files, exist_ok=True)
        
        self.site_domain = ""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }

    def _setup_logger(self):
        """Configura o logger do sistema"""

        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
        log_path = os.path.join(base_dir, 'logs', 'lara-i_logs.log')

        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        logger.add(
            log_path,
            rotation="1 MB",
            retention="7 days",
            level="INFO",
            encoding="utf-8"
        )
        logger.info("🚀 Iniciando LARA-I...")

    async def __aenter__(self):
        """Context manager para inicialização do browser"""

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--single-process", "--ignore-certificate-errors"]
        )
        self.context = await self.browser.new_context(ignore_https_errors=True)
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager para limpeza de recursos"""

        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def processar_orgaos(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Processa todos os órgãos e retorna os resultados"""

        orgaos = self._carregar_orgaos()
        resultados = {}
        verificacao = {}
        links_detalhados = {}
        programas_de_integridade = {}
        planos_compliance = {}
        programas_integridade_links = {}

        async with self:
            for i, (sigla, dados) in enumerate(orgaos.items()):
                if limit and i >= limit:
                    break

                url = dados.get("link")
                self.site_domain = url.rstrip("/")
                possui_atas = dados.get("possui_atas")
                possui_repositorio = dados.get("possui_repositorio")

                if not url:
                    logger.warning(f"⚠️ URL não encontrada para: {sigla}")
                    resultados[sigla] = None
                    links_detalhados[sigla] = None
                    continue

                logger.info(f"--- Processando {sigla} ({i + 1}/{len(orgaos)}) ---")
                try:
                    if possui_repositorio:
                        link_repo = dados.get("link_repo")

                        logger.info(f"Órgão {sigla} possui repositório. Extraindo links diretamente...")

                        await self.page.goto(url, timeout=self.config.timeout_navegacao)
                        resultados[sigla] = "não foi preciso."
                        links_detalhados[sigla] = await self.extrair_links_cig(link_repo)

                        if links_detalhados[sigla]:
                            logger.info(f"Baixando PDFs para {sigla}...")
                            self._baixar_pdfs(links_detalhados[sigla], sigla)

                        programas_de_integridade[sigla] = await self.possui_programa_integridade(url)
                        
                        # Buscar e baixar Programa de Integridade
                        links_pg = await self.buscar_links_programa_integridade(url)
                        programas_integridade_links[sigla] = links_pg
                        if links_pg:
                            logger.info(f"Extraindo links detalhados de Programa de Integridade para {sigla}...")
                            links_pg_detalhados = await self.extrair_links_cig(links_pg)
                            if links_pg_detalhados:
                                logger.info(f"Baixando PDFs de Programa de Integridade para {sigla}...")
                                self._baixar_pdfs(links_pg_detalhados, sigla)
                        
                        # Buscar e baixar Plano de Compliance
                        links_compliance = await self.buscar_links_plano_compliance(url)
                        planos_compliance[sigla] = links_compliance
                        if links_compliance:
                            logger.info(f"Extraindo links detalhados de Plano de Compliance para {sigla}...")
                            links_compliance_detalhados = await self.extrair_links_cig(links_compliance)
                            if links_compliance_detalhados:
                                logger.info(f"Baixando PDFs de Plano de Compliance para {sigla}...")
                                self._baixar_pdfs(links_compliance_detalhados, sigla)
                    else:
                        if not possui_atas:
                            logger.warning(f"⚠️ Órgão {sigla} não possui atas")
                            resultados[sigla] = None
                            links_detalhados[sigla] = None
                        else:
                            programas_de_integridade[sigla] = await self.possui_programa_integridade(url)

                            links = await self.buscar_links_atas_cig(url)
                            resultados[sigla] = links

                            if links:
                                logger.info(f"Extraindo links detalhados para {sigla}...")
                                links_detalhados[sigla] = await self.extrair_links_cig(links)
                                print(links_detalhados[sigla])

                                if links_detalhados[sigla]:
                                    logger.info(f"Baixando PDFs para {sigla}...")
                                    self._baixar_pdfs(links_detalhados[sigla], sigla)
                            else:
                                links_detalhados[sigla] = None
                        
                        # Buscar e baixar Programa de Integridade (sempre tenta, independente de ter atas)
                        links_pg = await self.buscar_links_programa_integridade(url)
                        programas_integridade_links[sigla] = links_pg
                        if links_pg:
                            logger.info(f"Extraindo links detalhados de Programa de Integridade para {sigla}...")
                            links_pg_detalhados = await self.extrair_links_cig(links_pg)
                            if links_pg_detalhados:
                                logger.info(f"Baixando PDFs de Programa de Integridade para {sigla}...")
                                self._baixar_pdfs(links_pg_detalhados, sigla)
                        
                        # Buscar e baixar Plano de Compliance (sempre tenta, independente de ter atas)
                        links_compliance = await self.buscar_links_plano_compliance(url)
                        planos_compliance[sigla] = links_compliance
                        if links_compliance:
                            logger.info(f"Extraindo links detalhados de Plano de Compliance para {sigla}...")
                            links_compliance_detalhados = await self.extrair_links_cig(links_compliance)
                            if links_compliance_detalhados:
                                logger.info(f"Baixando PDFs de Plano de Compliance para {sigla}...")
                                self._baixar_pdfs(links_compliance_detalhados, sigla)

                    verificacao[sigla] = self._verificar_resultado(possui_atas, resultados[sigla], possui_repositorio)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar {sigla}: {str(e)}")
                    resultados[sigla] = None
                    links_detalhados[sigla] = None
                    verificacao[sigla] = "❌ Erro: falha no processamento"

        return {
            "resultados": resultados,
            "verificacao": verificacao,
            "links_detalhados": links_detalhados,
            "programas_de_integridade": programas_de_integridade,
            "programas_integridade_links": programas_integridade_links,
            "planos_compliance": planos_compliance,
        }

    def _carregar_orgaos(self) -> Dict[str, Dict[str, Any]]:
        """Carrega os dados dos órgãos do arquivo JSON"""

        try:
            with open(self.config.arquivo_orgaos, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Erro ao carregar arquivo de órgãos: {str(e)}")
            return {}

    def _verificar_resultado(self, possui_atas: bool, links: Optional[List[str]], possui_repositorio: bool) -> str:
        """Verifica a consistência dos resultados"""

        tem_links = links is not None and len(links) > 0

        if possui_repositorio:
            return "✅ OK" if tem_links else "❌ Erro: nenhum link encontrado no repositório"

        if (possui_atas and not tem_links) or (not possui_atas and tem_links):
            return "❌ Erro: inconsistência"
        return "✅ OK"

    async def buscar_links_atas_cig(self, url: str) -> Optional[List[str]]:
        """Busca links de atas em uma URL específica"""
        await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
        links_coletados = []

        input_name = await self._encontrar_input_pesquisa()
        if not input_name:
            logger.warning(f"Nenhum input de pesquisa encontrado em {url}")
            return None

        for termo in self.config.termos_pesquisa.get('cig'):
            logger.info(f"Pesquisando por '{termo}'...")
            try:
                all_elements_links = await self._buscar_elementos_por_input(input_name, termo)

                link_valido, link_titulo, tem_ano = await self._verificar_titulos_cig(all_elements_links)
                if link_valido:
                    if tem_ano:
                        links_anos = await self._coletar_links_por_ano()
                        links_coletados.extend(links_anos)
                        return links_coletados
                    else:
                        return [link_titulo]
  
                await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de atas encontrado para URL: {url}")
        return links_coletados if links_coletados else None

    async def possui_programa_integridade(self, url: str) -> bool:
        """Verifica se o órgão possui programa de integridade"""

        await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
        links_coletados = []

        input_name = await self._encontrar_input_pesquisa()
        if not input_name:
            logger.warning(f"Nenhum input de pesquisa encontrado em {url}")
            return None

        for termo in self.config.termos_pesquisa.get("pg"):
            logger.info(f"Pesquisando por '{termo}'...")
            try:
                all_elements_links = await self._buscar_elementos_por_input(input_name, termo)

                tem_pg = await self._verificar_titulos_pg(all_elements_links)

                return tem_pg

            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de atas encontrado para URL: {url}")
        return False

    async def buscar_links_programa_integridade(self, url: str) -> Optional[List[str]]:
        """Busca links de Programa de Integridade em uma URL específica"""
        await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
        links_coletados = []

        input_name = await self._encontrar_input_pesquisa()
        if not input_name:
            logger.warning(f"Nenhum input de pesquisa encontrado em {url}")
            return None

        for termo in self.config.termos_pesquisa.get("pg"):
            logger.info(f"Pesquisando Programa de Integridade por '{termo}'...")
            try:
                all_elements_links = await self._buscar_elementos_por_input(input_name, termo)

                link_valido, link_titulo, tem_ano = await self._verificar_titulos_programa_integridade(all_elements_links)
                if link_valido:
                    if tem_ano:
                        links_anos = await self._coletar_links_por_ano()
                        links_coletados.extend(links_anos)
                        return links_coletados
                    else:
                        return [link_titulo]
  
                await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de Programa de Integridade encontrado para URL: {url}")
        return links_coletados if links_coletados else None

    async def buscar_links_plano_compliance(self, url: str) -> Optional[List[str]]:
        """Busca links de Plano de Compliance em uma URL específica"""
        await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
        links_coletados = []

        input_name = await self._encontrar_input_pesquisa()
        if not input_name:
            logger.warning(f"Nenhum input de pesquisa encontrado em {url}")
            return None

        for termo in self.config.termos_pesquisa.get("compliance"):
            logger.info(f"Pesquisando Plano de Compliance por '{termo}'...")
            try:
                all_elements_links = await self._buscar_elementos_por_input(input_name, termo)

                link_valido, link_titulo, tem_ano = await self._verificar_titulos_plano_compliance(all_elements_links)
                if link_valido:
                    if tem_ano:
                        links_anos = await self._coletar_links_por_ano()
                        links_coletados.extend(links_anos)
                        return links_coletados
                    else:
                        return [link_titulo]
  
                await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de Plano de Compliance encontrado para URL: {url}")
        return links_coletados if links_coletados else None

    async def _buscar_elementos_por_input(self, input_name: str, termo: str):
        """Busca links e paragrafos da página e retorna elementos tratados"""

        await self.page.fill(f"input[name='{input_name}']", termo, timeout=self.config.timeout_preenchimento)
        await self.page.press(f"input[name='{input_name}']", "Enter", timeout=self.config.timeout_press)
        await self.page.wait_for_load_state('networkidle', timeout=self.config.timeout_load_state)

        links = await self.page.query_selector_all(
            "li h3 a, li h4 a, div.row div.col div.col a, h2.genericItemTitle a"
        )

        paragrafos = await self.page.query_selector_all("li p, div.row div.col div.col span")

        all_elements_links = []
        if paragrafos:
            for link, paragrafo in zip(links, paragrafos):
                all_elements_links.append(await self._get_element_data(link, paragrafo))
        else:
            for link in links:
                all_elements_links.append(await self._get_element_data(link))

        return all_elements_links

    async def _encontrar_input_pesquisa(self) -> Optional[str]:
        """Encontra o input de pesquisa disponível na página"""

        for input_name in self.config.inputs_pesquisa:
            if await self.page.query_selector(f"input[name='{input_name}']"):
                return input_name
        return None

    async def _get_element_data(self, link: ElementHandle, paragrafo: ElementHandle = "") -> dict:
        """Extrai dados de um elemento da página"""

        if paragrafo:
            return {
                'text': (await link.text_content() or "").strip().lower(),
                'paragraph': (await paragrafo.text_content() or "").strip().lower(),
                'href': await link.get_attribute('href') or "",
            }

        return {
            'text': (await link.text_content() or "").strip().lower(),
            'paragraph': "",
            'href': await link.get_attribute('href') or "",
        }

    async def _verificar_titulos_cig(self, elements: list[dict]) -> Tuple[bool, Optional[str], bool]:
        """Verifica os títulos dos resultados"""

        for element in elements:
            link = element['href']
            titulo = element['text']
            paragrafo = element['paragraph']

            termos_busca = [
                "comitê interno de governança",
                "comitê de governança",
                "atas",
                "atas das reuniões",
                "atas de reuniões",
                "governança pública"
            ]

            if (any(termo in titulo.lower() for termo in termos_busca) or
                any(termo in paragrafo.lower() for termo in termos_busca)):
                link_valido = link
                tem_ano = bool(re.search(r'\b(20\d{2})\b', titulo))
                return True, link_valido, tem_ano

        return False, None, False

    async def _verificar_titulos_pg(self, elements: list[dict]) -> bool:
        """Verifica os títulos dos resultados"""

        for element in elements:
            titulo = element['text']

            termos_busca = [
                "integridade e compliance",
                "integridade",
                "programa de integridade"
            ]

            if any(termo in titulo.lower() for termo in termos_busca):
                return True

        return False

    async def _verificar_titulos_programa_integridade(self, elements: list[dict]) -> Tuple[bool, Optional[str], bool]:
        """Verifica os títulos dos resultados de Programa de Integridade"""

        for element in elements:
            link = element['href']
            titulo = element['text']
            paragrafo = element.get('paragraph', '')

            termos_busca = [
                "programa de integridade",
                "programa integridade",
                "integridade e compliance",
                "integridade",
                "compliance e integridade"
            ]

            if (any(termo in titulo.lower() for termo in termos_busca) or
                any(termo in paragrafo.lower() for termo in termos_busca)):
                link_valido = link
                tem_ano = bool(re.search(r'\b(20\d{2})\b', titulo))
                return True, link_valido, tem_ano

        return False, None, False

    async def _verificar_titulos_plano_compliance(self, elements: list[dict]) -> Tuple[bool, Optional[str], bool]:
        """Verifica os títulos dos resultados de Plano de Compliance"""

        for element in elements:
            link = element['href']
            titulo = element['text']
            paragrafo = element.get('paragraph', '')

            termos_busca = [
                "plano de compliance",
                "plano compliance",
                "compliance",
                "plano de integridade e compliance",
                "plano integridade compliance"
            ]

            if (any(termo in titulo.lower() for termo in termos_busca) or
                any(termo in paragrafo.lower() for termo in termos_busca)):
                link_valido = link
                tem_ano = bool(re.search(r'\b(20\d{2})\b', titulo))
                return True, link_valido, tem_ano

        return False, None, False

    async def _coletar_links_por_ano(self) -> List[str]:
        """Coleta links organizados por ano"""

        links_anos = []
        elementos = await self.page.query_selector_all(
            "li h3 a.title, li h4 a, [class*='title'] a, div.row div.col div.col a"
        )

        for elemento in elementos:
            titulo = await elemento.inner_text()
            if re.search(r'\b(20\d{2})\b', titulo):
                if link := await elemento.get_attribute("href"):
                    links_anos.append(link)

        seen = set()
        return [x for x in links_anos if not (x in seen or seen.add(x))]

    async def extrair_links_cig(self, links_atas: List[str] | str) -> List[Dict[str, str]]:
        """Extrai links de documentos PDF das páginas de atas do CIG"""

        if isinstance(links_atas, str):
            links_atas = [links_atas]
            
        links_extraidos = []
        
        for url in links_atas:
            try:
                await self.page.goto(url, timeout=self.config.timeout_navegacao)
                await self.page.wait_for_load_state('networkidle', timeout=self.config.timeout_load_state)

                elementos = await self._extrair_elementos_pdf_avancado()

                for elemento in elementos:
                    if link_info := await self._processar_elemento_pdf(elemento):
                        links_extraidos.append(link_info)
                        
            except Exception as e:
                logger.error(f"Erro ao processar página {url}: {str(e)}")
                continue
                
        return self._filtrar_links_duplicados(links_extraidos)

    async def _extrair_elementos_pdf_avancado(self) -> List[ElementHandle]:
        """Versão mais robusta que também verifica o conteúdo e contexto dos links"""

        elementos = []

        todos_links = await self.page.query_selector_all("a[href]")

        for link in todos_links:
            try:
                href = await link.get_attribute("href")
                texto = await link.inner_text()

                if self._e_provavel_pdf(href, texto):
                    elementos.append(link)

            except Exception as e:
                logger.debug(f"Erro ao verificar link: {str(e)}")

        return elementos

    async def _extrair_elementos_pdf(self) -> List[ElementHandle]:
        """Extrai todos os elementos que podem conter links para PDFs"""

        elementos = []

        seletores = [
            "a[href$='.pdf']",
            "a[href*='.pdf']",

            "a[href$='-pdf']",

            "a[href*='/documents/'][href$='-pdf']",

            "a[href*='/documents/d/'][href$='-pdf']",

            "a:contains('PDF')",
            "a:contains('pdf')",

            "a[href*='documento']",
            "a[href*='ata']",
            "a[href*='reuniao']",
        ]
        
        for seletor in seletores:
            try:
                elementos.extend(await self.page.query_selector_all(seletor))
            except Exception as e:
                logger.debug(f"Erro ao buscar elementos com seletor {seletor}: {str(e)}")
                
        return elementos

    def _e_provavel_pdf(self, href: str, texto: str) -> bool:
        """Determina se um link provavelmente aponta para um PDF"""

        if not href:
            return False

        href_lower = href.lower()
        texto_lower = texto.lower()

        criterios_url = [
            href_lower.endswith('.pdf'),
            '.pdf' in href_lower,
            href_lower.endswith('-pdf'),
            '/documents/' in href_lower,
            'documento' in href_lower,
            'ata' in href_lower,
            'reuniao' in href_lower,
        ]

        criterios_texto = [
            'pdf' in texto_lower,
            'ata' in texto_lower,
            'reunião' in texto_lower,
            'relatório' in texto_lower,
        ]

        contra_criterios_texto = [
            'diário' in texto_lower,
            'plano' in texto_lower,
            'instrução' in texto_lower,
            'portaria' in texto_lower,
            'resolução' in texto_lower,
            'apresentação' in texto_lower,
            'decreto' in texto_lower,
            'política' in texto_lower,
            'certificado' in texto_lower,
            'retificação' in texto_lower,
            'plano' in texto_lower,
            'organograma' in texto_lower,
            'pesquisa' in texto_lower,
            'cartilhas' in texto_lower,
            'guia' in texto_lower,
            'certidão' in texto_lower,
            'manual' in texto_lower,
        ]

        if any(contra_criterios_texto):
            return False

        return any(criterios_url) or any(criterios_texto)

    async def _processar_elemento_pdf(self, elemento: ElementHandle) -> Optional[Dict[str, str]]:
        """Processa um elemento de link e extrai informações do PDF"""

        try:
            href = await elemento.get_attribute("href")
            titulo = await elemento.text_content()
            
            if not href or not titulo:
                return None

            href = self._normalizar_url(href)

            if not self._eh_link_pdf(href):
                return None

            #is_link_ata, portaria = self._eh_link_ata(titulo)
            #if portaria:
            #    return None

            data = self._extrair_data_documento(titulo)

            return {
                "url": href,
                "titulo": titulo,
                "data": ""
                #**({"portaria": portaria} if portaria else {})
            }

        except Exception as e:
            logger.debug(f"Erro ao processar elemento: {str(e)}")
            return None

    def _eh_link_pdf(self, url: str) -> bool:
        """Verifica se o link é realmente um PDF"""

        if not url:
            return False

        url_lower = url.lower()

        if url_lower.endswith('.pdf'):
            return True

        if '.pdf' in url_lower:
            partes = url_lower.split('.pdf')
            if len(partes) > 1 and not any(c.isalnum() for c in partes[1][:1]):
                return True

        if url_lower.endswith('-pdf'):
            return True

        padroes_pdf = [
            '/documents/',
            '/documento',
            '/ata',
            '/reuniao',
            '/relatorio',
            '/arquivo',
            'pdf-',
            '_pdf',
            'download',
        ]

        if any(padrao in url_lower for padrao in padroes_pdf):
            terminacoes_documento = ['-pdf', '_pdf', '-doc', '_doc', 'documento', 'ata', 'reuniao', 'relatorio']
            if any(url_lower.endswith(term) for term in terminacoes_documento):
                return True

        return False

    def _eh_link_ata(self, titulo: str) -> tuple[bool, str]:
        """Verifica se o link é de uma ata CIG"""

        if not titulo:
            return False, None

        titulo_lower = titulo.lower()

        palavras_exclusao = [
            "resolução",
            "governança",
            "portaria"
        ]

        if any(palavra in titulo_lower for palavra in palavras_exclusao):
            return False, None

        palavras_ata = [
            "ata",
            "reunião",
            "reuniao",
            "sessão",
            "sessao",
            "encontro",
            "assembleia",
            "conselho",
            "comissão",
            "comissao",
            "colegiado",
            "plenária",
            "plenaria"
        ]

        for palavra in palavras_ata:
            if palavra in titulo_lower:
                return True, titulo_lower

        padroes_numericos = [
            "º", "ª",
            "ordinária", "ordinaria",
            "extraordinária", "extraordinaria",
            "especial"
        ]

        if any(padrao in titulo_lower for padrao in padroes_numericos):
            if any(char.isdigit() for char in titulo):
                return True, titulo_lower

        return False, None

    def _extrair_data_documento(self, titulo: str) -> Optional[str]:
        """Extrai a data do documento do título ou contexto"""

        padroes_data = [
            r'\b\d{2}/\d{2}/\d{4}\b',
            r'\b\d{2}-\d{2}-\d{4}\b',
            r'\b\d{2}\.\d{2}\.\d{4}\b',
            r'\b\d{2} de [A-Za-zçÇ]+ de \d{4}\b',
            r'\b[A-Za-zçÇ]+ de \d{4}\b',
            r'\b\d{4}\b'
        ]

        texto_completo = titulo
        
        for padrao in padroes_data:
            if match := re.search(padrao, texto_completo):
                return match.group(0)
                
        return None

    def _normalizar_url(self, url: str) -> str:
        """Normaliza URLs relativas e absolutas"""

        if not url:
            return url

        url = url.strip()

        if url.startswith("//"):
            return f"https:{url}"
        elif url.startswith("/"):
            return f"{self.site_domain}{url}"

        return url

    def _filtrar_links_duplicados(self, links: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Remove links duplicados mantendo apenas a primeira ocorrência"""

        urls_vistas = set()
        links_unicos = []
        
        for link in links:
            url_normalizada = link["url"].lower().split('?')[0]
            
            if url_normalizada not in urls_vistas:
                urls_vistas.add(url_normalizada)
                links_unicos.append(link)
                
        return links_unicos

    def _baixar_pdfs(self, links: List[Dict[str, str]], sigla: str) -> None:
        """Baixa PDFs dos links"""

        for link in links:
            of_tratado = os.path.join(self.output_files, sigla.upper())
            if not os.path.exists(of_tratado):
                os.makedirs(of_tratado)
                logger.info(f"📂 Diretório '{of_tratado}' criado.")

            url = link['url']
            titulo = link['titulo']
            data = link['data']

            if not url:
                logger.warning(f"⚠ URL não encontrada para: {titulo}. Pulando...")
                continue

            try :
                response = requests.get(url, stream=True, verify=False, headers=self.headers)
                response.raise_for_status()

                nome_arquivo_tratado = "".join(c if c.isalnum() or c in (' ', '.', '_') else '_' for c in titulo)
                if data:
                    nome_arquivo = f"{data.replace('/', '-')}_{nome_arquivo_tratado}.pdf"
                else:
                    nome_arquivo = f"{nome_arquivo_tratado}.pdf"

                caminho_completo = os.path.join(of_tratado, nome_arquivo)

                with open(caminho_completo, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                logger.info(f"'{nome_arquivo}' salvo em '{of_tratado}'")
            except requests.exceptions.Timeout:
                logger.error(f"⏰ Timeout ao baixar {url}. Continuando com próximo...")
                continue

            except requests.exceptions.ConnectionError:
                logger.error(f"🔌 Erro de conexão ao baixar {url}. Continuando com próximo...")
                continue

            except requests.exceptions.HTTPError as e:
                logger.error(f"🌐 Erro HTTP ao baixar {url}: {e.response.status_code}. Continuando com próximo...")
                continue

            except requests.exceptions.RequestException as e:
                logger.error(f"🌐 Erro de requisição ao baixar {url}: {str(e)}. Continuando com próximo...")
                continue

            except OSError as e:
                logger.error(f"💾 Erro de sistema ao salvar '{titulo}': {str(e)}. Continuando com próximo...")
                continue

            except Exception as e:
                logger.error(f"⚠ Erro inesperado ao processar '{titulo}': {str(e)}. Continuando com próximo...")
                continue
        logger.info(f"📂 Baixando PDF: {link['url']}")

    async def upload_pdfs_s3(self):
        """Envia PDFs para S3"""

        pdfs_path = self.output_files
        logger.debug(f"📂 Caminho de saída: {pdfs_path}")

        os.makedirs(pdfs_path, exist_ok=True)
        if not os.path.exists(pdfs_path):
            logger.error("❌ Falha ao enviar pdfs para o S3. PDFs não encontrados.")
            return False

        entries = os.listdir(pdfs_path)
        for entry in entries:
            logger.debug(f"📁 Diretório de órgão encontrado: {entry}")
            orgao_path = os.path.join(pdfs_path, entry)
            if os.path.isdir(orgao_path):
                pdfs = os.listdir(orgao_path)
                for pdf in pdfs:
                    file_path = os.path.join(orgao_path, pdf)
                    object_name = f'dani-docs/{entry}/{pdf}'

                    if self.config.s3_service.object_exists(
                        bucket='agir-bucket',
                        object_name=object_name
                    ):
                        logger.warning(f"⚠ Arquivo já existe na S3 e será ignorado: {object_name}")
                        continue

                    logger.debug(f"📄 Enviando PDF: {pdf}")
                    self.config.s3_service.upload_object(
                        bucket='agir-bucket',
                        object_name=object_name,
                        file_path=file_path
                    )
        return True

async def main():
    """Função principal para execução do LARA-I"""
    logger.success("Iniciando LARA-I...")
    config = ConfiguracaoLara()
    lara = LaraI(config)
    
    try:
        resultados = await lara.processar_orgaos()
        #logger.info("✅ Resultados finais:")
        logger.info(json.dumps(resultados, indent=2, ensure_ascii=False))

        #await lara.upload_pdfs_s3()
        #logger.info("✅ PDFs salvos com sucesso na S3")
    except Exception as e:
        logger.error(f"Erro durante a execução do LARA-I: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())