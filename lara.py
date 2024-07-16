import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from unidecode import unidecode

def read_excel_data(filename: str) -> dict[str, bool] | None:
    """Reads data from an Excel file and returns a dictionary with the CIG minutes status for each organization.
    
    Args:
        filename (str): Name of the Excel file.

    Returns:
        dict[str, bool] | None: Dictionary with organization acronyms as keys and a boolean value indicating
        if they have CIG minutes, or None if there is an error reading the file.
    """
    
    df = pd.DataFrame()

    try:
        df = pd.read_excel(filename, header=None)
    except Exception as e:
        print(e)
        return None

    header_row_index = df[df.iloc[:, 0] == 'Empresa/Órgão'].index[0]

    df = pd.read_excel(filename, header=header_row_index)

    dados = {}

    for _, row in df.iterrows():
        orgao = company_acronym(row['Empresa/Órgão'])
        atas_cig = row['Atas do CIG']

        if 'sim' in str(atas_cig).lower():
            dados[orgao] = True
        elif 'não' in str(atas_cig).lower():
            dados[orgao] = False
        else:
            dados[orgao] = False

    return dados

def comparar_mapas(data_map, links_map) -> tuple[dict[str, bool], int, int]:
    """Compares two maps (dictionaries) of data and links to verify the presence of minutes.

    Args:
        data_map (dict): Dictionary with the data of the organizations and presence of minutes.
        links_map (dict): Dictionary with the links found for the organizations.

    Returns:
        tuple[dict[str, bool], int, int]: Tuple containing a dictionary with the comparison results,
        the number of matches, and the total number of organizations with minutes.
    """
    
    results = {}
    total = 0
    matches = 0

    for org, has_minutes in data_map.items():
        if has_minutes:
            total += 1
            if org in links_map and len(links_map[org]) > 0:
                results[org] = True
                matches += 1
            else:
                results[org] = False
        else:
            results[org] = None

    return results, matches, total

def verifica_palavras_chaves(link, keywords) -> bool:
    """Checks if a link contains any of the specified keywords.

    Args:
        link (str): URL of the link to be checked.
        keywords (str): Keywords to be checked, separated by spaces.

    Returns:
        bool: True if the link contains any of the keywords, False otherwise.
    """
    
    keywords = keywords.split()

    for keyword in keywords:
        if len(keyword) <= 2:
            continue
        keyword = unidecode(keyword)
        pattern = re.compile(keyword, re.IGNORECASE)
        if pattern.search(link):
            return True
    return False


def company_acronym(company_name: str) -> str:
    """Returns the acronym of the company/organization from the full name.

    Args:
        company_name (str): Full name of the company/organization.

    Returns:
        str: Acronym corresponding to the company/organization name or an error message if not found.
    """
    
    acronyms = {
        'Secretaria De Estado Da Agricultura, Abastecimento E Desenvolvimento Rural': 'SEAGRI',
        'Secretaria De Estado De Atendimento À Comunidade': 'SEAC',
        'Casa Civil': 'CACI',
        'Casa Militar': 'CM',
        'Secretaria De Estado De Comunicação': 'SECOM',
        'Secretaria De Estado De Cultura E Economia Criativa': 'SECEC',
        'Secretaria De Estado De Ciência, Tecnologia E Inovação': 'SECTI',
        'Secretaria De Desenvolvimento Social': 'SEDES',
        'Secretaria De Estado De Educação': 'SEE',
        'Secretaria De Estado De Esporte E Lazer Do Distrito Federal': 'SELDF',
        'Secretaria De Estado De Economia': 'SEEC',
        'Secretaria De Desenvolvimento Urbano E Habitação': 'SEDUH',
        'Secretaria De Estado De Justiça E Cidadania': 'SEJUS',
        'Secretaria De Estado Do Meio Ambiente E Proteção Animal': 'SEMA',
        'Secretaria De Estado Da Mulher': 'SMDF',
        'Secretaria De Estado De Obras E Infraestrutura': 'SODF',
        'Secretaria De Estado De Família E Juventude': 'SEJUV',
        'Secretaria De Estado De Projetos Especiais': 'SEPE',
        'Secretaria De Estado De Relações Institucionais': 'SERINS',
        'Secretaria De Estado De Saúde': 'SES',
        'Secretaria De Estado De Segurança Pública': 'SSP',
        'Secretaria De Estado De Desenvolvimento Econômico, Trabalho E Renda': 'SEDET',
        'Secretaria De Estado De Transporte E Mobilidade': 'SEMOB',
        'Secretaria De Estado De Turismo': 'SETUR',
        'Secretaria De Estado De Governo': 'SEGOV',
        'Secretaria De Estado De Proteção Da Ordem Urbanística – Df Legal': 'DF LEGAL',
        'Secretaria De Estado De Administração Penitenciária – Seape': 'SEAPE',
        'Secretaria Da Pessoa Com Deficiência Do Distrito Federal': 'SEPD',
        'Secretaria De Estado De Assuntos Internacionais': 'SERINTER',
        'Controladoria-Geral do DF': 'CGDF',
        'Procuradoria Geral do DF': 'PGDF',
        'Polícia Civil': 'PCDF',
        'Polícia Militar': 'PMDF',
        'Corpo de Bombeiros': 'CBM',
        'Arquivo Público Do Distrito Federal': 'ARPDF',
        'Agência Reguladora de Águas e Saneamento do DF': 'ADASA',
        'Departamento de Estradas de Rodagem do DF': 'DER',
        'Departamento de Trânsito do DF': 'DETRAN-DF',
        'Instituto de Assistência à Saúde dos Servidores do DF': 'INAS',
        'Instituto de Defesa do Consumidor do DF': 'PROCON-DF',
        'Instituto de Previdência dos Servidores do DF': 'IPREV',
        'Instituto Brasília Ambiental': 'IBRAM',
        'Serviço de Limpeza Urbana do DF': 'SLU',
        'Centrais de Abastecimento do Distrito Federal': 'CEASA',
        'Companhia de Desenvolvimento Habitacional': 'CODHAB-DF',
        'Companhia Imobiliária de Brasília': 'TERRACAP',
        'Instituto de Pesquisa e Estatística do Distrito Federal': 'IPEDF',
        'Companhia de Saneamento Ambiental do DF': 'CAESB',
        'Companhia Urbanizadora da Nova Capital do Brasil': 'NOVACAP',
        'Empresa de Assistência Técnica e Extensão Rural': 'EMATER',
        'Companhia do Metropolitano do Distrito Federal': 'METRÔ-DF',
        'Sociedade de Transportes Coletivos de Brasília': 'TCB',
        'Banco de Brasília': 'BRB',
        'Companhia Energética de Brasília': 'CEB',
        'Fundação de Amparo ao Trabalhador Preso do Distrito Federal': 'FUNAP',
        'Fundação de Apoio à Pesquisa do Distrito Federal': 'FAP',
        'Fundação de Ensino e Pesquisa em Ciências da Saúde': 'FEPECS',
        'Fundação Hemocentro de Brasília': 'FHB',
        'Fundação Jardim Zoológico de Brasília': 'FJZB',
        'Fundação Jardim Botânico': 'JBB',
        'Universidade do Distrito Federal': 'UNDF',
        'Escola de Governo': 'EGOV',
        'Junta Comercial, Industrial E Serviços Do Distrito Federal': 'JUCIS-DF',
        'Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal': 'SEPLAD',
    }

    company_name = company_name.strip()
    acronym = company_name in acronyms
    if acronym:
        return acronyms[company_name]
    else:
        return f"Not found: {company_name}"


def load_orgaos_name(adm_direta: list, mista_publica: list) -> int:
    """Loads the names of organizations from a text file into separate lists for direct and mixed public administration.

    Args:
        direct_admin (list): List to store the names of direct administration organizations.
        mixed_public (list): List to store the names of mixed public administration organizations.

    Returns:
        int: 0 if successful, 1 if there is an error opening the file.
    """

    try:
        file = open("list_orgaos_name.txt", 'r')
    except Exception as e:
        print(e)
        return 1

    is_mista = 0
    for line in file:
        if ("---" in line):
            is_mista = 1
            continue

        if (not is_mista):
            adm_direta.append(line.strip())
        else:
            mista_publica.append(line.strip())

    file.close()
    return 0

def search_link_cig2(acronym: str, org: str, param: str, base_link: str, header: dict, limit: int) -> dict:
    """Performs a search for links related to the Internal Governance Committee (CIG) for a specific organization.

    Args:
        acronym (str): Acronym of the organization.
        org (str): Name of the organization.
        param (str): Additional search parameters.
        base_link (str): Base URL for the search.
        header (dict): HTTP header for the request.
        limit (int): Limit of links to be returned.

    Returns:
        dict: Dictionary with the acronyms of the organizations as keys and lists of links as values.
    """
    org_name_params = [acronym + " df", org]
    org_link_dict = {}
    
    try:
        for org_name_param in org_name_params:
            search_param = f"{base_link}{org_name_param}{param}"
            source = requests.get(search_param, header, verify=False)

            if source.status_code != 200:
                print("Erro ao acessar a página")
                continue

            soup = BeautifulSoup(source.text, 'lxml')
            links_count = 0

            for g in soup.find_all('div',  {'class': 'Gx5Zad'}):
                links = g.find_all('a')
                links = links[:limit]

                for link in links:
                    link_addrs = str(link['href'])
                    link_text = link.get_text().lower()

                    if (("comitê interno de governança" in link_text) or ("governança" in link_text) or (("atas" in link_text) and "cig" in link_text)):
                        if (acronym.lower() in link_addrs and "df" in link_addrs) or ((verifica_palavras_chaves(link_addrs, orgao) and "df" in link_addrs)):
                            if link_addrs.split("&")[0] not in org_link_dict.get(acronym, []):
                                org_link_dict.setdefault(acronym, []).append(
                                    link_addrs.split("&")[0])
                    elif (("gestão" in link_text and "risco" in link_text) or
                          ("gestão" in link_text and "governança" in link_text)):
                        if ((acronym.lower() in link_addrs and "df" in link_addrs) or (verifica_palavras_chaves(link_addrs, orgao) and "df" in link_addrs)):
                            if link_addrs.split("&")[0] not in org_link_dict.get(acronym, []):
                                org_link_dict.setdefault(acronym, []).append(
                                    link_addrs.split("&")[0])
            
            if org_link_dict.get(acronym) != None:
                break
    
    except requests.RequestException as e:
        print(f"Erro na requisição HTTP: {e}")
    except Exception as e:
        print(f"Erro inesperado: {e}")

    return org_link_dict

def filter_webpage_type1(url: str) -> tuple[bool, None] | tuple[bool, str]:
    """Filters web pages to check for the presence of meeting minutes and updates.

    Args:
        url (str): URL of the page to be checked.

    Returns:
        tuple[bool, None] | tuple[bool, str]: Tuple indicating if the minutes are present and the update date,
        or None in case of failure.
    """

    try:
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}
        response = requests.get(url, headers=header, verify=False)

        data_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
        update_site_pattern = re.compile(
            r'Atualizado em \d{1,2}/\d{1,2}/\d{2,4} às ([01]?[0-9]|2[0-3])h[0-5][0-9]', re.IGNORECASE)

        meeting_minutes_patterns = [
            re.compile(r'ata da \d+ª reunião', re.IGNORECASE),
            re.compile(r'ata \d+ª reunião', re.IGNORECASE),
            re.compile(r'\d+ª reunião', re.IGNORECASE),
            re.compile(r'ata da reunião extraordinária Nº \d', re.IGNORECASE),
        ]

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            page_text = soup.get_text().lower()
            match = update_site_pattern.search(page_text)

            links = soup.find_all('a')

        for link in links:
            link_text = link.get_text().lower()
            link_href = link.get('href')
            if ('ata' in link_text or
                data_pattern.search(link_text) or
                    any(pattern.search(link_text) for pattern in meeting_minutes_patterns)):

                print(link_text)
                print("Link:", link_href)

                if match:
                    return True, match.group()
                return True, None

            if match:
                return False, match.group()
            return False, None
        else:
            print("Falha ao carregar o site.")
            return False, None
        
    except requests.RequestException as e:
        print(f"Erro na requisição HTTP: {e}")
        return False, None

    except Exception as e:
        print(f"Erro inesperado: {e}")
        return False, None


def filter_webpage_type2(url: str) -> tuple[bool, None] | tuple[bool, str]:
    """Filters web pages to check for the presence of meeting minutes and updates.

    Args:
        url (str): URL of the page to be checked.

    Returns:
        tuple[bool, None] | tuple[bool, str]: Tuple indicating if the minutes are present and the update date,
        or None in case of failure.
    """

    try:
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}
        response = requests.get(url, headers=header, verify=False)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            data_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}')
            update_site_pattern = re.compile(
                r'Atualizado em \d{1,2}/\d{1,2}/\d{2,4} às ([01]?[0-9]|2[0-3])h[0-5][0-9]', re.IGNORECASE)
            target_text1 = "decreto n° 39.736, de 28 de março de 2019".lower()
            target_text2 = "comitê interno de governança".lower()
            target_text3 = "atas das reuniões".lower()

            page_text = soup.get_text().lower()
            match = update_site_pattern.search(page_text)

            if (target_text1 in page_text and
                target_text2 in page_text and
                    target_text3 in page_text):

                links = soup.find_all('a')

                for link in links:
                    if (target_text3 in link.get_text().lower() or
                            data_pattern.search(link)):
                        print(link.get_text())
                        print("Link:", link.get('href'))

                        if match:
                            return True, match.group()

                        return True, None

                if match:
                    return False, match.group()
                return False, None
        else:
            print("Falha ao carregar o site.")
            return False, None

    except requests.RequestException as e:
        print(f"Erro na requisção: {e}")
        return False, None
    except Exception as e:
        print(f"Erro inesperado: {e}")
        return False, None
