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
                "programa de integridade"
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
                    else:
                        if not possui_atas:
                            logger.warning(f"⚠️ Órgão {sigla} não possui atas")
                            resultados[sigla] = None
                            links_detalhados[sigla] = None
                            continue

                        programas_de_integridade[sigla] = await self.possui_programa_integridade(url)

                        links = await self.buscar_links_atas_cig(url)
                        resultados[sigla] = links

                        if links:
                            logger.info(f"Extraindo links detalhados para {sigla}...")
                            links_detalhados[sigla] = await self.extrair_links_cig(links)

                            if links_detalhados[sigla]:
                                logger.info(f"Baixando PDFs para {sigla}...")
                                self._baixar_pdfs(links_detalhados[sigla], sigla)
                        else:
                            links_detalhados[sigla] = None

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
                print("Tem pq:", tem_pg)

                return tem_pg

            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de atas encontrado para URL: {url}")
        return False

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

                elementos = await self._extrair_elementos_pdf()

                for elemento in elementos:
                    if link_info := await self._processar_elemento_pdf(elemento):
                        links_extraidos.append(link_info)
                        
            except Exception as e:
                logger.error(f"Erro ao processar página {url}: {str(e)}")
                continue
                
        return self._filtrar_links_duplicados(links_extraidos)

    async def _extrair_elementos_pdf(self) -> List[ElementHandle]:
        """Extrai todos os elementos que podem conter links para PDFs"""

        elementos = []

        seletores = [
            "a[href$='.pdf']",
            "a[href*='.pdf']",
            "a[href*='download']",
            "a[href*='documento']",
            "a[href*='arquivo']",
            "a[href*='publicacao']",
            "a[href*='publicação']",
            "a[href*='ata']",
            "a[href*='reuniao']",
            "a[href*='reunião']"
        ]
        
        for seletor in seletores:
            try:
                elementos.extend(await self.page.query_selector_all(seletor))
            except Exception as e:
                logger.debug(f"Erro ao buscar elementos com seletor {seletor}: {str(e)}")
                
        return elementos

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

            is_link_ata, portaria = self._eh_link_ata(titulo)
            if portaria:
                return None

            data = self._extrair_data_documento(titulo)

            return {
                "url": href,
                "titulo": titulo,
                "data": data,
                **({"portaria": portaria} if portaria else {})
            }

        except Exception as e:
            logger.debug(f"Erro ao processar elemento: {str(e)}")
            return None

    def _eh_link_pdf(self, url: str) -> bool:
        """Verifica se o link é realmente um PDF"""

        url_lower = url.lower()

        if url_lower.endswith('.pdf'):
            return True

        if '.pdf' in url_lower:
            partes = url_lower.split('.pdf')
            if len(partes) > 1 and not any(c.isalnum() for c in partes[1][:1]):
                return True
                
        return False

    def _eh_link_ata(self, titulo: str) -> [bool, str]:
        """Verifica link é de uma ata CIG"""

        titulo_lower = titulo.lower()

        if ("resolução" in titulo_lower) or ("governança" in titulo_lower) or ("portaria" in titulo_lower):
            return False, None

        if "portaria" in titulo_lower:
            True, titulo_lower
        return None, None

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
                response = requests.get(url, stream=True)
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

            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Erro ao baixar {url}: {str(e)}")
            except Exception as e:
                logger.error(f"⚠ Ocorreu um erro ao processar {titulo}: {str(e)}")
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
        resultados = await lara.processar_orgaos(limit=1)
        #logger.info("✅ Resultados finais:")
        logger.info(json.dumps(resultados, indent=2, ensure_ascii=False))

        #await lara.upload_pdfs_s3()
        #logger.info("✅ PDFs salvos com sucesso na S3")
    except Exception as e:
        logger.error(f"Erro durante a execução do LARA-I: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())