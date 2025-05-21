###########################################################################
## LARA-I : Levantador Automático de Recursos Administrativos Interativo ##
###########################################################################
import asyncio
import re
import json
from loguru import logger
from playwright.async_api import async_playwright, ElementHandle, Locator
from typing import Tuple, List, Optional, Dict

logger.add("lara-i_logs.log", rotation="1 MB", retention="7 days", level="INFO", encoding="utf-8")
logger.info("🚀 Iniciando LARA-I...")

async def verificar_resultados(orgaos_gdf_links: dict[str, dict[str, str]],
                               resultado: dict[str, list[str]]) -> dict[str, str]:

    verificacao = {}
    for sigla, links in resultado.items():
        possui_atas = orgaos_gdf_links[sigla].get("possui_atas")
        possui_repositorio = orgaos_gdf_links[sigla].get("possui_repositorio")
        tem_links = links is not None and len(links) > 0

        if (possui_atas and not tem_links and not possui_repositorio) or (not possui_atas and tem_links and not possui_repositorio):
            verificacao[sigla] = "❌ Erro: inconsistência"
        else:
            verificacao[sigla] = "✅ OK"

    return verificacao


async def processar_links_orgaos(orgaos_gdf_links: dict[str, dict[str, str]], limit: int | None = None) -> dict[str, list[str]]:
    resultados = {}
    for i, (sigla, dados_orgao) in enumerate(orgaos_gdf_links.items()):
        if limit is not None and i >= limit:
            break

        url = dados_orgao.get("link")
        possui_atas = dados_orgao.get("possui_atas")
        possui_repositorio = dados_orgao.get("possui_repositorio")

        if (not url or
            not possui_atas or
            possui_repositorio):
            logger.warning(f"⚠️ Não foi possível extrair atas: {sigla}")
            resultados[sigla] = None
            continue

        logger.info(f"--- Processando {sigla} ({i + 1}/{len(orgaos_gdf_links)}) ---")
        links_atas = await buscar_links_atas_cig(url)
        if not links_atas:
            logger.warning(f"Nenhum link encontrado para {sigla}")
        resultados[sigla] = links_atas

    return resultados


def carregar_orgaos_sites(caminho: str = None):
    arquivo = caminho or "/home/yaba/agir-unb/data/lara/orgaos_gdf_links.json"
    try:
        with open(arquivo, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados
    except FileNotFoundError:
        logger.error(f"Arquivo não encontrado: {arquivo}")
    except json.JSONDecodeError:
        logger.error(f"Erro ao decodificar o JSON do arquivo: {arquivo}")
    return {}


async def buscar_links_atas_cig(link_orgao: str, timeout_config: dict = None) -> List[str] | None:
    timeout = timeout_config or {
        'navigation': 220_000,
        'selector': 180_000,
        'fill': 180_000,
        'press': 180_000,
        'load_state': 180_000,
    }
    termos_de_pesquisa = ["cig atas", "Comitê Interno de Governança", "cigp", "Reuniões: Atas",
                          "Relatórios de Reuniões de Governança"]
    inputs = ["s", "q", "searchword"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-gpu", "--single-process", "--ignore-certificate-errors"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        try:
            await page.goto(url=link_orgao, timeout=timeout['navigation'])
            links_coletados = []

            input_name = None
            for input_candidate in inputs:
                if await page.query_selector(f"input[name='{input_candidate}']"):
                    input_name = input_candidate
                    break

            if not input_name:
                logger.warning("Nenhum input de pesquisa encontrado")
                return None

            for termo in termos_de_pesquisa:
                logger.info(f"Pesquisando por '{termo}'...")
                try:
                    await page.fill(f"input[name='{input_name}']", termo, timeout=timeout['fill'])
                    await page.press(f"input[name='{input_name}']", "Enter", timeout=timeout['press'])
                    await page.wait_for_load_state('networkidle', timeout=timeout['load_state'])

                    links = await page.query_selector_all("li h3 a, li h4 a, div.row div.col div.col a")
                    paragrafos = await page.query_selector_all("li p, div.row div.col div.col span")

                    all_elements_links = []
                    for link, paragrafo in zip(links, paragrafos):
                        all_elements_links.append(await get_element_data(link, paragrafo))

                    link_valido, link_titulo, tem_ano = await verifica_selectors_cig_titulo(all_elements_links)
                    if link_valido:
                        if tem_ano:
                            links_anos = await coletar_links_por_ano(page)
                            links_coletados.extend(links_anos)
                            return links_coletados
                        else:
                            return [link_titulo]

                    await page.goto(url=link_orgao, timeout=timeout['navigation'])
                except Exception as e:
                    logger.error(f"Erro ao processar termo '{termo}': {str(e)}")
                    continue

            if not links_coletados:
                logger.warning(f"Nenhum link de atas encontrado para URL: {link_orgao}")
            return links_coletados if links_coletados else None
        finally:
            await browser.close()

async def get_element_data(link: ElementHandle, paragrafo: ElementHandle) -> dict:
    return {
        'text': (await link.text_content() or "").strip().lower(),
        'paragraph': (await paragrafo.text_content() or "").strip().lower(),
        'href': await link.get_attribute('href') or "",
    }

async def verifica_selectors_cig_titulo(elements: list[dict]) -> Tuple[bool, Optional[str], bool]:
    for element in elements:
        link = element['href']
        titulo = element['text']
        paragrafo = element['paragraph']

        termos_busca = ["comitê interno de governança",
                        "comitê de governança",
                        "atas",
                        "atas das reuniões",
                        "atas de reuniões",
                        "governança pública"]

        if (any(termo in titulo for termo in termos_busca) or
            any(termo in paragrafo for termo in termos_busca)):
            link_valido = link
            tem_ano = bool(re.search(r'\b(20\d{2})\b', titulo))
            return True, link_valido, tem_ano

    return False, None, False

async def coletar_links_por_ano(page) -> List[str]:
    links_anos = []

    # TODO: Revisar essa parte e adicionar logs
    elementos_titulos = await page.query_selector_all("li h3 a.title, li h4 a, [class*='title'] a, div.row div.col div.col a")

    for elemento in elementos_titulos:
        titulo = await elemento.inner_text()
        if re.search(r'\b(20\d{2})\b', titulo):
            link = await elemento.get_attribute("href")
            if link:
                links_anos.append(link)

    seen = set()
    return [x for x in links_anos if not (x in seen or seen.add(x))]


if __name__ == "__main__":
    links_orgaos_sites = carregar_orgaos_sites()
    resultados = asyncio.run(processar_links_orgaos(links_orgaos_sites))
    verificacao = asyncio.run(verificar_resultados(links_orgaos_sites, resultados))
    logger.info("✅ Resultados finais:")
    logger.info(resultados)
    logger.info(verificacao)