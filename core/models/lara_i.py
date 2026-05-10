###########################################################################
## LARA-I : Levantador Automático de Recursos Administrativos Interativo ##
###########################################################################
import argparse
import asyncio
import os
import os.path
import re
import json
from collections import deque
from dataclasses import dataclass
from typing import Tuple, List, Optional, Dict, Any, FrozenSet, Literal, Callable, Awaitable, TypeVar
from urllib.parse import urljoin, urlparse, unquote

from loguru import logger
from playwright.async_api import (
    async_playwright,
    ElementHandle,
    Page,
    BrowserContext,
    APIRequestContext,
)

from core.services.aws_service import S3Service

# Subpastas em data/dani/docs/input/ para separar PDFs por tipo de documento coletado
TIPOS_DOCUMENTO_INPUT = ("cig", "pg", "compliance")
_TIPOS_DOCUMENTO_SET = frozenset(TIPOS_DOCUMENTO_INPUT)

T = TypeVar("T")


def pasta_downloads_orgao_tem_arquivos(
    output_files: str, sigla: str, tipo_documento: str
) -> bool:
    """True se já existem arquivos em output_files/{tipo}/{SIGLA}/."""
    pasta = os.path.join(output_files, tipo_documento, sigla.upper())
    if not os.path.isdir(pasta):
        return False
    return any(
        os.path.isfile(os.path.join(pasta, nome))
        for nome in os.listdir(pasta)
    )


def _user_agent_string() -> str:
    """UA alinhado a Chromium recente (mesma família do Playwright)."""
    return (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )


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
    # None = coletar cig, pg e compliance; senão subconjunto de TIPOS_DOCUMENTO_INPUT
    tipos_coleta: Optional[FrozenSet[str]] = None
    # Paralelismo: quantos órgãos processar ao mesmo tempo (máx. 1 = sequencial).
    concorrencia_orgaos: int = 4
    max_tentativas_rede: int = 3
    backoff_base_ms: int = 1000
    bfs_habilitado: bool = True
    bfs_max_paginas: int = 35
    bfs_max_profundidade: int = 2
    bfs_max_hubs_retorno: int = 5

    def __post_init__(self):
        if self.tipos_coleta is None:
            self.tipos_coleta = _TIPOS_DOCUMENTO_SET
        else:
            tipos_invalidos = self.tipos_coleta - _TIPOS_DOCUMENTO_SET
            if tipos_invalidos:
                raise ValueError(
                    f"tipos_coleta contém tipos desconhecidos: {sorted(tipos_invalidos)}. "
                    f"Use um ou mais de: {', '.join(TIPOS_DOCUMENTO_INPUT)}"
                )
            if not self.tipos_coleta:
                raise ValueError("tipos_coleta não pode ser vazio")

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


def _verificar_resultado(
    possui_atas: bool,
    links: Optional[List[str]],
    possui_repositorio: bool,
) -> str:
    tem_links = links is not None and len(links) > 0

    if possui_repositorio:
        return "✅ OK" if tem_links else "❌ Erro: nenhum link encontrado no repositório"

    if (possui_atas and not tem_links) or (not possui_atas and tem_links):
        return "❌ Erro: inconsistência"
    return "✅ OK"


class LaraISession:
    """Uma sessão Playwright (contexto + página) para processar um órgão."""

    def __init__(
        self,
        config: ConfiguracaoLara,
        output_files: str,
        page: Page,
        context: BrowserContext,
    ):
        self.config = config
        self.output_files = output_files
        self.page = page
        self.context = context
        self.site_domain = ""

    def _deve_coletar(self, tipo: str) -> bool:
        return tipo in self.config.tipos_coleta

    def _pasta_downloads_nao_vazia(self, sigla: str, tipo_documento: str) -> bool:
        """True se já existem arquivos em output/{tipo}/{SIGLA} (evita re-download e re-extração)."""
        return pasta_downloads_orgao_tem_arquivos(self.output_files, sigla, tipo_documento)

    async def _retry_async(
        self,
        factory: Callable[[], Awaitable[T]],
        operation_name: str,
    ) -> T:
        last_exc: Optional[BaseException] = None
        n = max(1, self.config.max_tentativas_rede)
        for attempt in range(n):
            try:
                return await factory()
            except Exception as e:
                last_exc = e
                if attempt < n - 1:
                    delay_s = (self.config.backoff_base_ms / 1000.0) * (2 ** attempt)
                    logger.warning(
                        f"{operation_name} falhou (tentativa {attempt + 1}/{n}): {e}; "
                        f"nova tentativa em {delay_s:.1f}s"
                    )
                    await asyncio.sleep(delay_s)
        assert last_exc is not None
        raise last_exc

    async def _wait_after_navigation(self) -> None:
        """Dom + load; networkidle só como reforço curto; depois tenta resultados de busca."""
        to = self.config.timeout_load_state
        await self.page.wait_for_load_state("domcontentloaded", timeout=to)
        try:
            await self.page.wait_for_load_state("load", timeout=min(90_000, to))
        except Exception:
            pass
        try:
            await self.page.wait_for_load_state("networkidle", timeout=15_000)
        except Exception:
            pass
        for sel in ("li h3 a", "h2.genericItemTitle a", "li h4 a"):
            try:
                await self.page.wait_for_selector(sel, timeout=8_000)
                break
            except Exception:
                continue

    async def _goto(self, url: str) -> None:
        async def _go() -> None:
            await self.page.goto(url=url, timeout=self.config.timeout_navegacao)
            await self._wait_after_navigation()

        await self._retry_async(_go, f"goto({url[:96]!r})")

    def _normalizar_url_interna(self, url: str, origin: str) -> str:
        u = (url or "").strip().split("#")[0]
        if not u:
            return ""
        if u.startswith("//"):
            return f"https:{u}"
        if u.startswith("/"):
            return origin.rstrip("/") + u
        return u

    async def _bfs_coletar_hubs(
        self,
        start_url: str,
        tipo: Literal["cig", "pg", "compliance"],
    ) -> List[str]:
        """
        Varredura em largura limitada na mesma origem; retorna URLs de páginas candidatas
        (hubs com vários PDFs ou caminho alinhado ao tipo). Ver documentação em docs/.
        """
        if not self.config.bfs_habilitado:
            return []

        parsed = urlparse(start_url)
        if not parsed.scheme or not parsed.netloc:
            return []
        origin = f"{parsed.scheme}://{parsed.netloc}"

        path_keywords = {
            "cig": (
                "cig", "governanca", "governança", "ata", "atas", "transparencia",
                "transparência", "acervo", "documento", "comite", "comitê",
                "reuniao", "reunião", "colegiado",
            ),
            "pg": (
                "integridade", "programa", "compliance", "transparencia", "transparência",
            ),
            "compliance": (
                "compliance", "integridade", "plano", "transparencia", "transparência",
            ),
        }[tipo]

        visited: set[str] = set()
        queue: deque[Tuple[str, int]] = deque([(start_url, 0)])
        hubs: List[str] = []
        pages_visited = 0
        max_p = self.config.bfs_max_paginas
        max_d = self.config.bfs_max_profundidade

        while queue and pages_visited < max_p:
            current, depth = queue.popleft()
            norm = self._normalizar_url_interna(current, origin)
            if not norm.startswith("http") or norm in visited:
                continue
            if not norm.startswith(origin):
                continue
            visited.add(norm)

            try:
                await self._goto(norm)
            except Exception as e:
                logger.debug(f"BFS ignorando {norm}: {e}")
                continue

            pages_visited += 1
            path_l = urlparse(norm).path.lower()
            keyword_hit = any(k in path_l for k in path_keywords)

            pdf_score = 0
            links_out: List[str] = []
            anchors = await self.page.query_selector_all("a[href]")
            for a in anchors[:300]:
                try:
                    href = await a.get_attribute("href")
                    if not href or href.startswith("#"):
                        continue
                    text = (await a.inner_text() or "").strip()
                    abs_url = urljoin(norm, href)
                    if not abs_url.startswith(("http://", "https://")):
                        continue
                    p2 = urlparse(abs_url)
                    same = f"{p2.scheme}://{p2.netloc}" == origin
                    if self._e_provavel_pdf(abs_url, text, tipo):
                        pdf_score += 1
                    if same and depth < max_d:
                        clean = abs_url.split("#")[0]
                        if clean not in visited:
                            links_out.append(clean)
                except Exception:
                    continue

            if keyword_hit or pdf_score >= 2:
                hubs.append(norm)

            for link_u in links_out[:40]:
                if link_u not in visited:
                    queue.append((link_u, depth + 1))

        return hubs[: self.config.bfs_max_hubs_retorno]

    async def executar_orgao(
        self,
        sigla: str,
        dados: Dict[str, Any],
        indice: int,
        total: int,
    ) -> Tuple[str, Dict[str, Any]]:
        """Processa um órgão; retorna (sigla, bloco de resultados para merge)."""

        resultado_vazio = {
            "resultados": None,
            "links_detalhados": None,
            "verificacao": "❌ Erro: falha no processamento",
            "programas_de_integridade": None,
            "programas_integridade_links": None,
            "planos_compliance": None,
        }

        url = dados.get("link")
        if not url:
            logger.warning(f"⚠️ URL não encontrada para: {sigla}")
            return sigla, {
                **resultado_vazio,
                "verificacao": "❌ Erro: URL ausente",
                "resultados": None,
                "links_detalhados": None,
            }

        self.site_domain = url.rstrip("/")
        possui_atas = dados.get("possui_atas")
        possui_repositorio = dados.get("possui_repositorio")

        resultados: Any = None
        links_detalhados: Any = None
        programas_de_integridade: Any = None
        programas_integridade_links: Any = None
        planos_compliance: Any = None

        logger.info(f"--- Processando {sigla} ({indice}/{total}) ---")

        try:
            if possui_repositorio:
                link_repo = dados.get("link_repo")

                logger.info(f"Órgão {sigla} possui repositório. Extraindo links diretamente...")

                await self._goto(url)
                resultados = "não foi preciso."
                if self._deve_coletar("cig"):
                    if self._pasta_downloads_nao_vazia(sigla, "cig"):
                        logger.info(
                            f"Pulando CIG para {sigla}: diretório de destino já contém arquivos."
                        )
                        links_detalhados = None
                    else:
                        links_detalhados = await self.extrair_links_cig(link_repo, "cig")
                        if links_detalhados:
                            logger.info(f"Baixando PDFs para {sigla}...")
                            await self._baixar_pdfs(links_detalhados, sigla, "cig")
                else:
                    links_detalhados = None

                if self._deve_coletar("pg"):
                    programas_de_integridade = await self.possui_programa_integridade(url)
                else:
                    programas_de_integridade = None

                if self._deve_coletar("pg"):
                    if self._pasta_downloads_nao_vazia(sigla, "pg"):
                        logger.info(
                            f"Pulando Programa de Integridade para {sigla}: "
                            "diretório de destino já contém arquivos."
                        )
                        programas_integridade_links = None
                    else:
                        links_pg = await self.buscar_links_programa_integridade(url)
                        programas_integridade_links = links_pg
                        if links_pg:
                            logger.info(
                                f"Extraindo links detalhados de Programa de Integridade para {sigla}..."
                            )
                            links_pg_detalhados = await self.extrair_links_cig(links_pg, "pg")
                            if links_pg_detalhados:
                                logger.info(f"Baixando PDFs de Programa de Integridade para {sigla}...")
                                await self._baixar_pdfs(links_pg_detalhados, sigla, "pg")
                else:
                    programas_integridade_links = None

                if self._deve_coletar("compliance"):
                    if self._pasta_downloads_nao_vazia(sigla, "compliance"):
                        logger.info(
                            f"Pulando Plano de Compliance para {sigla}: "
                            "diretório de destino já contém arquivos."
                        )
                        planos_compliance = None
                    else:
                        links_compliance = await self.buscar_links_plano_compliance(url)
                        planos_compliance = links_compliance
                        if links_compliance:
                            logger.info(
                                f"Extraindo links detalhados de Plano de Compliance para {sigla}..."
                            )
                            links_compliance_detalhados = await self.extrair_links_cig(
                                links_compliance, "compliance"
                            )
                            if links_compliance_detalhados:
                                logger.info(f"Baixando PDFs de Plano de Compliance para {sigla}...")
                                await self._baixar_pdfs(links_compliance_detalhados, sigla, "compliance")
                else:
                    planos_compliance = None
            else:
                if not possui_atas:
                    logger.warning(f"⚠️ Órgão {sigla} não possui atas")
                    resultados = None
                    links_detalhados = None
                    programas_de_integridade = None
                elif self._deve_coletar("cig"):
                    if self._pasta_downloads_nao_vazia(sigla, "cig"):
                        logger.info(
                            f"Pulando CIG para {sigla}: diretório de destino já contém arquivos."
                        )
                        resultados = (
                            "Coleta CIG omitida: PDFs já presentes em "
                            f"{os.path.join(self.output_files, 'cig', sigla.upper())}."
                        )
                        links_detalhados = None
                    else:
                        links = await self.buscar_links_atas_cig(url)
                        resultados = links

                        if links:
                            logger.info(f"Extraindo links detalhados para {sigla}...")
                            links_detalhados = await self.extrair_links_cig(links, "cig")
                            logger.debug(f"Links detalhados {sigla}: {links_detalhados!r}")

                            if links_detalhados:
                                logger.info(f"Baixando PDFs para {sigla}...")
                                await self._baixar_pdfs(links_detalhados, sigla, "cig")
                        else:
                            links_detalhados = None
                else:
                    resultados = None
                    links_detalhados = None

                if self._deve_coletar("pg"):
                    programas_de_integridade = await self.possui_programa_integridade(url)
                    if self._pasta_downloads_nao_vazia(sigla, "pg"):
                        logger.info(
                            f"Pulando Programa de Integridade para {sigla}: "
                            "diretório de destino já contém arquivos."
                        )
                        programas_integridade_links = None
                    else:
                        links_pg = await self.buscar_links_programa_integridade(url)
                        programas_integridade_links = links_pg
                        if links_pg:
                            logger.info(
                                f"Extraindo links detalhados de Programa de Integridade para {sigla}..."
                            )
                            links_pg_detalhados = await self.extrair_links_cig(links_pg, "pg")
                            if links_pg_detalhados:
                                logger.info(f"Baixando PDFs de Programa de Integridade para {sigla}...")
                                await self._baixar_pdfs(links_pg_detalhados, sigla, "pg")
                else:
                    programas_integridade_links = None

                if self._deve_coletar("compliance"):
                    if self._pasta_downloads_nao_vazia(sigla, "compliance"):
                        logger.info(
                            f"Pulando Plano de Compliance para {sigla}: "
                            "diretório de destino já contém arquivos."
                        )
                        planos_compliance = None
                    else:
                        links_compliance = await self.buscar_links_plano_compliance(url)
                        planos_compliance = links_compliance
                        if links_compliance:
                            logger.info(
                                f"Extraindo links detalhados de Plano de Compliance para {sigla}..."
                            )
                            links_compliance_detalhados = await self.extrair_links_cig(
                                links_compliance, "compliance"
                            )
                            if links_compliance_detalhados:
                                logger.info(f"Baixando PDFs de Plano de Compliance para {sigla}...")
                                await self._baixar_pdfs(links_compliance_detalhados, sigla, "compliance")
                else:
                    planos_compliance = None

            verificacao = _verificar_resultado(possui_atas, resultados, possui_repositorio)

        except Exception as e:
            logger.error(f"Erro ao processar {sigla}: {str(e)}")
            return sigla, resultado_vazio

        return sigla, {
            "resultados": resultados,
            "links_detalhados": links_detalhados,
            "verificacao": verificacao,
            "programas_de_integridade": programas_de_integridade,
            "programas_integridade_links": programas_integridade_links,
            "planos_compliance": planos_compliance,
        }

    async def buscar_links_atas_cig(self, url: str) -> Optional[List[str]]:
        """Busca links de atas em uma URL específica"""
        await self._goto(url)
        links_coletados: List[str] = []

        input_name = await self._encontrar_input_pesquisa()
        if not input_name:
            logger.warning(f"Nenhum input de pesquisa encontrado em {url}")
            hubs = await self._bfs_coletar_hubs(url, "cig")
            if hubs:
                logger.info(f"BFS (cig): {len(hubs)} página(s) candidata(s) sem busca no site")
            return hubs if hubs else None

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

                await self._goto(url)
            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de atas encontrado para URL: {url}")
            hubs = await self._bfs_coletar_hubs(url, "cig")
            if hubs:
                logger.info(f"BFS (cig): fallback com {len(hubs)} página(s) candidata(s)")
            return hubs if hubs else None
        return links_coletados

    async def possui_programa_integridade(self, url: str) -> Optional[bool]:
        """Verifica se o órgão possui programa de integridade"""

        await self._goto(url)

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

        logger.warning(f"Nenhum resultado de programa de integridade em: {url}")
        return False

    async def buscar_links_programa_integridade(self, url: str) -> Optional[List[str]]:
        """Busca links de Programa de Integridade em uma URL específica"""
        await self._goto(url)
        links_coletados: List[str] = []

        input_name = await self._encontrar_input_pesquisa()
        if not input_name:
            logger.warning(f"Nenhum input de pesquisa encontrado em {url}")
            hubs = await self._bfs_coletar_hubs(url, "pg")
            return hubs if hubs else None

        for termo in self.config.termos_pesquisa.get("pg"):
            logger.info(f"Pesquisando Programa de Integridade por '{termo}'...")
            try:
                all_elements_links = await self._buscar_elementos_por_input(input_name, termo)

                link_valido, link_titulo, tem_ano = await self._verificar_titulos_programa_integridade(
                    all_elements_links
                )
                if link_valido:
                    if tem_ano:
                        links_anos = await self._coletar_links_por_ano()
                        links_coletados.extend(links_anos)
                        return links_coletados
                    else:
                        return [link_titulo]

                await self._goto(url)
            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de Programa de Integridade encontrado para URL: {url}")
            hubs = await self._bfs_coletar_hubs(url, "pg")
            if hubs:
                logger.info(f"BFS (pg): fallback com {len(hubs)} página(s) candidata(s)")
            return hubs if hubs else None
        return links_coletados

    async def buscar_links_plano_compliance(self, url: str) -> Optional[List[str]]:
        """Busca links de Plano de Compliance em uma URL específica"""
        await self._goto(url)
        links_coletados: List[str] = []

        input_name = await self._encontrar_input_pesquisa()
        if not input_name:
            logger.warning(f"Nenhum input de pesquisa encontrado em {url}")
            hubs = await self._bfs_coletar_hubs(url, "compliance")
            return hubs if hubs else None

        for termo in self.config.termos_pesquisa.get("compliance"):
            logger.info(f"Pesquisando Plano de Compliance por '{termo}'...")
            try:
                all_elements_links = await self._buscar_elementos_por_input(input_name, termo)

                link_valido, link_titulo, tem_ano = await self._verificar_titulos_plano_compliance(
                    all_elements_links
                )
                if link_valido:
                    if tem_ano:
                        links_anos = await self._coletar_links_por_ano()
                        links_coletados.extend(links_anos)
                        return links_coletados
                    else:
                        return [link_titulo]

                await self._goto(url)
            except Exception as e:
                logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                continue

        if not links_coletados:
            logger.warning(f"Nenhum link de Plano de Compliance encontrado para URL: {url}")
            hubs = await self._bfs_coletar_hubs(url, "compliance")
            if hubs:
                logger.info(f"BFS (compliance): fallback com {len(hubs)} página(s) candidata(s)")
            return hubs if hubs else None
        return links_coletados

    async def _buscar_elementos_por_input(self, input_name: str, termo: str):
        """Busca links e paragrafos da página e retorna elementos tratados"""

        await self.page.fill(f"input[name='{input_name}']", termo, timeout=self.config.timeout_preenchimento)
        await self.page.press(f"input[name='{input_name}']", "Enter", timeout=self.config.timeout_press)
        await self._wait_after_navigation()

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

    async def extrair_links_cig(
        self,
        links_atas: List[str] | str,
        tipo_documento: Literal["cig", "pg", "compliance"] = "cig",
    ) -> List[Dict[str, str]]:
        """Extrai links de PDFs das páginas indicadas (CIG, programa de integridade ou compliance)."""

        if isinstance(links_atas, str):
            links_atas = [links_atas]

        links_extraidos = []

        for page_url in links_atas:
            try:
                page_url_norm = self._normalizar_url(page_url)
                await self._goto(page_url_norm)

                elementos = await self._extrair_elementos_pdf_avancado(tipo_documento)

                for elemento in elementos:
                    if link_info := await self._processar_elemento_pdf(elemento):
                        links_extraidos.append(link_info)

            except Exception as e:
                logger.error(f"Erro ao processar página {page_url}: {str(e)}")
                continue

        return self._filtrar_links_duplicados(links_extraidos)

    async def _extrair_elementos_pdf_avancado(
        self,
        tipo_documento: Literal["cig", "pg", "compliance"] = "cig",
    ) -> List[ElementHandle]:
        """Versão mais robusta que também verifica o conteúdo e contexto dos links"""

        elementos = []

        todos_links = await self.page.query_selector_all("a[href]")

        for link in todos_links:
            try:
                href = await link.get_attribute("href")
                texto = await link.inner_text()

                if self._e_provavel_pdf(href, texto, tipo_documento):
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

    def _e_provavel_pdf(
        self,
        href: str,
        texto: str,
        tipo_documento: Literal["cig", "pg", "compliance"] = "cig",
    ) -> bool:
        """Determina se um link provavelmente aponta para um PDF.

        Para ``pg`` e ``compliance``, URLs típicas de PDF (``.pdf``, sufixo Liferay ``-pdf``,
        ``/documents/...``) não são descartadas por heurísticas de texto pensadas para filtrar
        atas CIG — onde a palavra "plano" no rótulo do link é comum ruído.
        """

        if not href:
            return False

        href_lower = href.lower()
        texto_lower = (texto or "").lower()

        if tipo_documento in ("pg", "compliance"):
            path_sem_q = href_lower.split("?")[0].split("#")[0].rstrip("/")
            ultimo_seg = path_sem_q.split("/")[-1] if path_sem_q else ""
            tem_marca_pdf = (
                path_sem_q.endswith(".pdf")
                or path_sem_q.endswith("-pdf")
                or path_sem_q.endswith("_pdf")
                or ".pdf" in href_lower
                or ultimo_seg.endswith("-pdf")
                or ultimo_seg.endswith("_pdf")
            )
            if tem_marca_pdf:
                return True
            if "/documents/" in href_lower and any(
                frag in href_lower
                for frag in ("compliance", "integridade", "programa", "compactado")
            ):
                return True

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
            'instrução' in texto_lower,
            'portaria' in texto_lower,
            'resolução' in texto_lower,
            'apresentação' in texto_lower,
            'decreto' in texto_lower,
            'certificado' in texto_lower,
            'retificação' in texto_lower,
            'organograma' in texto_lower,
            'pesquisa' in texto_lower,
            'cartilhas' in texto_lower,
            'guia' in texto_lower,
            'certidão' in texto_lower,
            'manual' in texto_lower,
        ]

        if tipo_documento == "cig":
            contra_criterios_texto.extend(
                [
                    'plano' in texto_lower,
                    'política' in texto_lower,
                ]
            )

        if any(contra_criterios_texto):
            return False

        return any(criterios_url) or any(criterios_texto)

    async def _processar_elemento_pdf(self, elemento: ElementHandle) -> Optional[Dict[str, str]]:
        """Processa um elemento de link e extrai informações do PDF"""

        try:
            href = await elemento.get_attribute("href")
            texto_bruto = await elemento.text_content()
            titulo = (texto_bruto or "").strip()

            if not href:
                return None

            href = self._normalizar_url(href)

            if not self._eh_link_pdf(href):
                return None

            if not titulo:
                path_last = unquote(urlparse(href).path.rstrip("/").split("/")[-1] or "")
                titulo = (
                    path_last.replace("-", " ").replace("_", " ").strip() or "documento"
                )

            data = self._extrair_data_documento(titulo)

            return {
                "url": href,
                "titulo": titulo,
                "data": ""
            }

        except Exception as e:
            logger.debug(f"Erro ao processar elemento: {str(e)}")
            return None

    def _eh_link_pdf(self, url: str) -> bool:
        """Verifica se o link é realmente um PDF"""

        if not url:
            return False

        url_lower = url.lower()
        path_part = url_lower.split("?")[0].split("#")[0].rstrip("/")

        if path_part.endswith('.pdf'):
            return True

        if '.pdf' in path_part:
            partes = path_part.split('.pdf')
            if len(partes) > 1 and not any(c.isalnum() for c in partes[1][:1]):
                return True

        if path_part.endswith('-pdf') or path_part.endswith('_pdf'):
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
            if any(path_part.endswith(term) for term in terminacoes_documento):
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

        # Já é absoluta
        if url.startswith(("http://", "https://")):
            return url

        if url.startswith("//"):
            return f"https:{url}"

        # Caminhos relativos (com ou sem "/") devem usar a origem do órgão atual.
        base = (self.site_domain or "").rstrip("/") + "/"
        if base != "/" and not url.startswith(("mailto:", "tel:", "javascript:")):
            return urljoin(base, url)

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

    async def _baixar_pdfs(
        self,
        links: List[Dict[str, str]],
        sigla: str,
        tipo_documento: str,
    ) -> None:
        """
        Baixa PDFs via APIRequestContext do Playwright (mesma sessão/cookies do browser).
        Ver documentação em docs/lara-i-downloads-e-bfs.md.
        """
        if tipo_documento not in TIPOS_DOCUMENTO_INPUT:
            raise ValueError(f"tipo_documento deve ser um de {TIPOS_DOCUMENTO_INPUT}, recebido: {tipo_documento}")

        if self._pasta_downloads_nao_vazia(sigla, tipo_documento):
            dest = os.path.join(self.output_files, tipo_documento, sigla.upper())
            logger.info(
                f"Pulando download de PDFs ({tipo_documento}) para {sigla}: "
                f"diretório já contém arquivos ({dest})."
            )
            return

        req: APIRequestContext = self.context.request
        timeout_ms = min(120_000, self.config.timeout_navegacao)
        tentativas = max(1, self.config.max_tentativas_rede)

        for link in links:
            of_tratado = os.path.join(self.output_files, tipo_documento, sigla.upper())
            if not os.path.exists(of_tratado):
                os.makedirs(of_tratado)
                logger.info(f"📂 Diretório '{of_tratado}' criado.")

            url = link['url']
            titulo = link['titulo']
            data = link['data']

            if not url:
                logger.warning(f"⚠ URL não encontrada para: {titulo}. Pulando...")
                continue

            logger.info(f"📂 Baixando PDF: {url}")

            nome_arquivo_tratado = "".join(
                c if c.isalnum() or c in (' ', '.', '_') else '_' for c in titulo
            )
            if data:
                nome_arquivo = f"{data.replace('/', '-')}_{nome_arquivo_tratado}.pdf"
            else:
                nome_arquivo = f"{nome_arquivo_tratado}.pdf"

            caminho_completo = os.path.join(of_tratado, nome_arquivo)

            ultimo_erro: Optional[BaseException] = None
            for attempt in range(tentativas):
                try:
                    response = await req.get(url, timeout=timeout_ms)
                    if response.status >= 400:
                        raise RuntimeError(f"HTTP {response.status}")

                    body = await response.body()
                    if body and not body.startswith(b"%PDF"):
                        ct = (response.headers.get("content-type") or "").lower()
                        if "pdf" not in ct:
                            logger.warning(
                                f"Resposta de {url[:80]} não parece PDF (magic bytes); "
                                f"content-type={ct!r}. Salvando mesmo assim."
                            )

                    with open(caminho_completo, 'wb') as f:
                        f.write(body)

                    logger.info(f"'{nome_arquivo}' salvo em '{of_tratado}'")
                    ultimo_erro = None
                    break
                except Exception as e:
                    ultimo_erro = e
                    if attempt < tentativas - 1:
                        delay_s = (self.config.backoff_base_ms / 1000.0) * (2 ** attempt)
                        logger.warning(
                            f"Download falhou (tentativa {attempt + 1}/{tentativas}) {url[:80]}: {e}; "
                            f"nova tentativa em {delay_s:.1f}s"
                        )
                        await asyncio.sleep(delay_s)
                    else:
                        logger.error(
                            f"⚠ Erro ao baixar {url} após {tentativas} tentativas: {ultimo_erro}. "
                            "Continuando com próximo..."
                        )


class LaraI:
    """Orquestração do LARA-I: browser compartilhado e processamento paralelo por órgão."""

    def __init__(self, config: Optional[ConfiguracaoLara] = None):
        self.config = config or ConfiguracaoLara()
        self._setup_logger()

        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))
        self.output_files = os.path.join(base_dir, 'data', 'dani', 'docs', 'input')
        os.makedirs(self.output_files, exist_ok=True)
        for tipo in TIPOS_DOCUMENTO_INPUT:
            os.makedirs(os.path.join(self.output_files, tipo), exist_ok=True)

    def _setup_logger(self):
        """Configura o logger do sistema"""

        def _candidate_log_paths() -> list[str]:
            env_path = (os.environ.get("LARA_LOG_PATH") or "").strip()
            if env_path:
                return [env_path]

            base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
            return [
                os.path.join(base_dir, "logs", "lara-i_logs.log"),
                os.path.join("/tmp", "agir-unb", "logs", "lara-i_logs.log"),
            ]

        last_exc: Optional[BaseException] = None
        for log_path in _candidate_log_paths():
            try:
                log_dir = os.path.dirname(log_path) or "."
                os.makedirs(log_dir, exist_ok=True)
                if not os.access(log_dir, os.W_OK):
                    raise PermissionError(f"Diretório sem permissão de escrita: {log_dir}")

                logger.add(
                    log_path,
                    rotation="1 MB",
                    retention="7 days",
                    level="INFO",
                    encoding="utf-8",
                )
                logger.info(f"📝 Log em arquivo habilitado: {log_path}")
                last_exc = None
                break
            except Exception as e:
                last_exc = e

        if last_exc is not None:
            logger.warning(
                "⚠ Não foi possível habilitar log em arquivo; seguindo com logs no console. "
                f"Último erro: {last_exc}"
            )

        logger.info("🚀 Iniciando LARA-I...")

    def _carregar_orgaos(self) -> Dict[str, Dict[str, Any]]:
        """Carrega os dados dos órgãos do arquivo JSON"""

        try:
            with open(self.config.arquivo_orgaos, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Erro ao carregar arquivo de órgãos: {str(e)}")
            return {}

    def _resolver_concorrencia(self) -> int:
        raw = os.environ.get("LARA_CONCORRENCIA_ORGAOS", "").strip()
        if raw.isdigit():
            return max(1, int(raw))
        return max(1, int(self.config.concorrencia_orgaos))

    def _coleta_cig_aplicavel(self, dados: Dict[str, Any]) -> bool:
        """CIG só é coletado com repositório ou com possui_atas (alinhado a executar_orgao)."""
        return bool(dados.get("possui_repositorio")) or bool(dados.get("possui_atas"))

    def _tipo_tem_coleta_pendente(self, sigla: str, tipo: str, dados: Dict[str, Any]) -> bool:
        """Pasta do tipo vazia e, para CIG, metadados permitem coleta."""
        if pasta_downloads_orgao_tem_arquivos(self.output_files, sigla, tipo):
            return False
        if tipo == "cig" and not self._coleta_cig_aplicavel(dados):
            return False
        return True

    def _orgao_precisa_scraping(self, sigla: str, dados: Dict[str, Any]) -> bool:
        return any(
            self._tipo_tem_coleta_pendente(sigla, t, dados)
            for t in self.config.tipos_coleta
        )

    async def processar_orgaos(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Processa todos os órgãos (paralelo entre órgãos) e retorna os resultados."""

        orgaos = self._carregar_orgaos()
        all_items = list(orgaos.items())
        if limit is not None:
            all_items = all_items[:limit]

        items: List[Tuple[str, Dict[str, Any]]] = []
        pulados: List[Tuple[str, Dict[str, Any]]] = []
        for s, d in all_items:
            if self._orgao_precisa_scraping(s, d):
                items.append((s, d))
            else:
                pulados.append((s, d))

        total = len(items)
        conc = self._resolver_concorrencia()

        logger.info(
            "Tipos de documento nesta execução: "
            f"{', '.join(sorted(self.config.tipos_coleta))}"
        )
        logger.info(
            f"Candidatos no JSON (após --limite): {len(all_items)}; "
            f"com coleta pendente: {total}; concorrência: {conc}"
        )
        if pulados:
            logger.info(
                "Órgãos sem scraping (pastas já preenchidas ou sem CIG aplicável, ex. possui_atas=false "
                "sem repositório): "
                f"{', '.join(sorted(s for s, _ in pulados))}"
            )
        if items:
            logger.info(f"Órgãos que serão raspados: {', '.join(sorted(s for s, _ in items))}")
        else:
            logger.info("Nenhum órgão com coleta pendente; scraping não será iniciado.")

        resultados: Dict[str, Any] = {}
        verificacao: Dict[str, Any] = {}
        links_detalhados: Dict[str, Any] = {}
        programas_de_integridade: Dict[str, Any] = {}
        planos_compliance: Dict[str, Any] = {}
        programas_integridade_links: Dict[str, Any] = {}

        if total == 0:
            return {
                "resultados": resultados,
                "verificacao": verificacao,
                "links_detalhados": links_detalhados,
                "programas_de_integridade": programas_de_integridade,
                "programas_integridade_links": programas_integridade_links,
                "planos_compliance": planos_compliance,
            }

        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            # "--single-process" costuma gerar crashes intermitentes em alguns ambientes Linux.
            # Preferimos flags mais robustas para execução headless em CI/containers.
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--ignore-certificate-errors",
            ],
        )
        sem = asyncio.Semaphore(conc)
        ua = _user_agent_string()

        async def run_one(entry: Tuple[int, Tuple[str, Dict[str, Any]]]) -> Any:
            idx, (sigla, dados) = entry
            async with sem:
                context = await browser.new_context(
                    ignore_https_errors=True,
                    extra_http_headers={"User-Agent": ua},
                )
                page = await context.new_page()
                session = LaraISession(self.config, self.output_files, page, context)
                try:
                    return await session.executar_orgao(sigla, dados, idx, total)
                finally:
                    await page.close()
                    await context.close()

        try:
            tasks = [run_one((i + 1, t)) for i, t in enumerate(items)]
            resolved = await asyncio.gather(*tasks, return_exceptions=True)

            for item in resolved:
                if isinstance(item, BaseException):
                    logger.error(f"Falha em tarefa de órgão: {item}")
                    continue
                sigla, blob = item
                resultados[sigla] = blob["resultados"]
                verificacao[sigla] = blob["verificacao"]
                links_detalhados[sigla] = blob["links_detalhados"]
                programas_de_integridade[sigla] = blob["programas_de_integridade"]
                programas_integridade_links[sigla] = blob["programas_integridade_links"]
                planos_compliance[sigla] = blob["planos_compliance"]
        finally:
            await browser.close()
            await playwright.stop()

        return {
            "resultados": resultados,
            "verificacao": verificacao,
            "links_detalhados": links_detalhados,
            "programas_de_integridade": programas_de_integridade,
            "programas_integridade_links": programas_integridade_links,
            "planos_compliance": planos_compliance,
        }

    async def upload_pdfs_s3(self):
        """Envia PDFs para S3 (prefixo dani-docs/{tipo}/{sigla}/)."""

        pdfs_path = self.output_files
        logger.debug(f"📂 Caminho de saída: {pdfs_path}")

        os.makedirs(pdfs_path, exist_ok=True)
        if not os.path.exists(pdfs_path):
            logger.error("❌ Falha ao enviar pdfs para o S3. PDFs não encontrados.")
            return False

        for tipo in TIPOS_DOCUMENTO_INPUT:
            tipo_path = os.path.join(pdfs_path, tipo)
            if not os.path.isdir(tipo_path):
                continue
            for sigla in os.listdir(tipo_path):
                orgao_path = os.path.join(tipo_path, sigla)
                if not os.path.isdir(orgao_path):
                    continue
                logger.debug(f"📁 Diretório de órgão encontrado: {tipo}/{sigla}")
                for pdf in os.listdir(orgao_path):
                    file_path = os.path.join(orgao_path, pdf)
                    if not os.path.isfile(file_path):
                        continue
                    object_name = f'dani-docs/{tipo}/{sigla}/{pdf}'

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


def _resolver_tipos_coleta(argv_tipos: Optional[List[str]]) -> Optional[FrozenSet[str]]:
    """CLI --tipos tem prioridade; senão usa LARA_TIPOS_COLETA (vírgula); None = todos os tipos."""
    if argv_tipos:
        return frozenset(argv_tipos)
    raw = os.environ.get("LARA_TIPOS_COLETA", "").strip()
    if not raw:
        return None
    partes = [p.strip().lower() for p in raw.split(",") if p.strip()]
    return frozenset(partes) if partes else None


async def main():
    """Função principal para execução do LARA-I"""
    parser = argparse.ArgumentParser(
        description="LARA-I — coleta de PDFs (CIG, programa de integridade, plano de compliance)."
    )
    parser.add_argument(
        "--tipos",
        nargs="+",
        choices=list(TIPOS_DOCUMENTO_INPUT),
        metavar="TIPO",
        help=(
            "Quais tipos coletar: cig, pg, compliance (pode combinar). "
            "Padrão: todos. Ex.: --tipos pg  |  --tipos cig pg"
        ),
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=None,
        metavar="N",
        help="Processar no máximo N órgãos (útil para testes).",
    )
    parser.add_argument(
        "--concorrencia",
        type=int,
        default=None,
        metavar="N",
        help="Órgãos em paralelo (padrão: config ou env LARA_CONCORRENCIA_ORGAOS).",
    )
    parser.add_argument(
        "--upload-s3",
        action="store_true",
        help="Após a coleta, envia os PDFs locais para a S3 (bucket agir-bucket).",
    )
    args = parser.parse_args()
    tipos = _resolver_tipos_coleta(args.tipos)
    config = ConfiguracaoLara(tipos_coleta=tipos)
    if args.concorrencia is not None:
        config.concorrencia_orgaos = max(1, args.concorrencia)
    logger.success("Iniciando LARA-I...")
    lara = LaraI(config)

    try:
        resultados = await lara.processar_orgaos(limit=args.limite)
        logger.info(json.dumps(resultados, indent=2, ensure_ascii=False))

        if args.upload_s3:
            ok = await lara.upload_pdfs_s3()
            if ok:
                logger.info("✅ Upload de PDFs para a S3 concluído.")
            else:
                logger.warning("⚠ Upload S3 finalizado com falhas ou sem arquivos; veja os logs acima.")
    except Exception as e:
        logger.error(f"Erro durante a execução do LARA-I: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
