###########################################################################
## LARA-I : Levantador Automático de Recursos Administrativos Interativo ##
###########################################################################
import asyncio
import re
import json
from playwright.async_api import async_playwright, ElementHandle
from typing import Tuple, List, Optional


async def verificar_resultados(orgaos_gdf_links: dict[str, dict[str, str]],
                               resultado: dict[str, list[str]]) -> dict[str, str]:

    verificacao = {}
    for sigla, links in resultado.items():
        possui_atas = orgaos_gdf_links[sigla].get("possui_atas").lower() == "true"
        tem_links = links is not None and len(links) > 0

        if (possui_atas and not tem_links) or (not possui_atas and tem_links):
            verificacao[sigla] = "❌ Erro: inconsistência"
        else:
            verificacao[sigla] = "✅ OK"

    return verificacao



async def processar_links_orgaos(orgaos_gdf_links: dict[str, dict[str, str]], limit: int | None = None) -> dict[
    str, list[str]]:
    resultados = {}
    for i, (sigla, dados_orgao) in enumerate(orgaos_gdf_links.items()):
        if limit is not None and i >= limit:
            break

        url = dados_orgao.get("link")
        if not url:
            print(f"⚠️ URL não encontrada para {sigla}")
            continue

        print(f"\n--- Processando {sigla} ({i + 1}/{len(orgaos_gdf_links)}) ---")
        links_atas = await buscar_links_atas_cig(url)
        resultados[sigla] = links_atas

    return resultados

def carregar_orgaos_sites(caminho: str = None):
    arquivo = caminho or "/home/yaba/agir-unb/data/lara/orgaos_gdf_links.json"
    try:
        with open(arquivo, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados
    except FileNotFoundError:
        print(f"Arquivo não encontrado: {arquivo}")
    except json.JSONDecodeError:
        print(f"Erro ao decodificar o JSON do arquivo: {arquivo}")
    return {}

async def buscar_links_atas_cig(link_orgao: str, timeout_config: dict = None) -> List[str] | None:
    timeout = timeout_config or {
        'navigation': 15000,
        'selector': 1000,
        'fill': 5000,
        'press': 5000
    }
    termos_de_pesquisa = ["cig atas", "Comitê Interno de Governança", "cigp", "Reuniões: Atas",
                          "Relatórios de Reuniões de Governança"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-gpu", "--single-process", "--ignore-certificate-errors"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        try:
            await page.goto(url=link_orgao, timeout=timeout['navigation'])
            links_coletados = []

            for termo in termos_de_pesquisa:
                try:
                    await page.fill("input[name='s']", termo, timeout=timeout['fill'])
                    await page.press("input[name='s']", "Enter", timeout=timeout['press'])
                    await page.wait_for_selector("li h3 a.title, li p", timeout=timeout['selector'])

                    resultados_titulos = await page.query_selector_all("li h3 a.title, li h4 a.title")
                    resultados_paragrafos = await page.query_selector_all("li p")

                    # Verifica títulos
                    titulo_valido, link_titulo, tem_ano = await verifica_selectors_cig_titulo(resultados_titulos)
                    if titulo_valido:
                        if tem_ano:
                            # Se tem ano, coleta todos os links de anos
                            links_anos = await coletar_links_por_ano(page)
                            links_coletados.extend(links_anos)
                            return links_coletados
                        else:
                            return [link_titulo]

                    # Verifica parágrafos
                    paragrafo_valido, link_paragrafo = await verifica_selectors_cig_paragrafos(resultados_paragrafos)
                    if paragrafo_valido:
                        return [link_paragrafo]

                    await page.goto(url=link_orgao, timeout=timeout['navigation'])
                except Exception as e:
                    print(f"Erro ao processar termo '{termo}': {str(e)}")
                    await page.goto(url=link_orgao, timeout=timeout['navigation'])
                    continue

            return links_coletados if links_coletados else None
        finally:
            await browser.close()


async def verifica_selectors_cig_titulo(resultados_titulos: list[ElementHandle]) -> Tuple[bool, Optional[str], bool]:
    for resultado in resultados_titulos:
        titulo = await resultado.inner_text()
        titulo_lower = titulo.lower()

        if "comitê interno de governança" in titulo_lower or "atas das reuniões" in titulo_lower:
            link_valido = await resultado.get_attribute("href")
            # Verifica se tem ano no título (ex: "2023", "2024")
            tem_ano = bool(re.search(r'\b(20\d{2})\b', titulo))
            return True, link_valido, tem_ano
    return False, None, False


async def verifica_selectors_cig_paragrafos(resultados_paragrafos: list[ElementHandle]) -> Tuple[bool, Optional[str]]:
    for resultado in resultados_paragrafos:
        paragrafo = await resultado.inner_text()
        paragrafo_lower = paragrafo.lower()

        if "comitê interno de governança" in paragrafo_lower:
            link_element = await resultado.query_selector(
                "xpath=./preceding-sibling::h3/a | ./preceding-sibling::h4/a | ./parent::a")

            if link_element:
                link = await link_element.get_attribute("href")
                return True, link
    return False, None


async def coletar_links_por_ano(page) -> List[str]:
    """Coleta todos os links que contêm anos no título"""
    links_anos = []

    # Encontra todos os elementos de título que podem conter anos
    elementos_titulos = await page.query_selector_all("li h3 a.title, li h4 a, [class*='title'] a")

    for elemento in elementos_titulos:
        titulo = await elemento.inner_text()
        if re.search(r'\b(20\d{2})\b', titulo):  # Verifica se tem um ano (2000-2099)
            link = await elemento.get_attribute("href")
            if link:
                links_anos.append(link)

    # Remove duplicados mantendo a ordem
    seen = set()
    return [x for x in links_anos if not (x in seen or seen.add(x))]

# def verifica_pagina_cig(sigla_orgao: str, link_orgao: str):

if __name__ == "__main__":
    links_orgaos_sites = carregar_orgaos_sites()
    resultados = asyncio.run(processar_links_orgaos(links_orgaos_sites, limit=25))
    verificacao = asyncio.run(verificar_resultados(links_orgaos_sites, resultados))
    print(resultados)
    print(verificacao)
