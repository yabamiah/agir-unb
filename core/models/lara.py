##############################################################
## LARA - Levantador Automático de Recursos Administrativos ##
##############################################################

from core.utils.orgao import Orgao

from services.document_service import DocumentService

import time
import subprocess, os, platform
from os import makedirs, rmdir
from os.path import getsize, exists
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bs4 import BeautifulSoup
import pandas as pd
from unidecode import unidecode
import json

class Lara:
    def __init__(self) -> None:
        self.header = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}
        self.path_docx_report = ""
        self.path_pdf_report = ""
        pass

    def read_excel_data(self, filename: str) -> dict[str, bool] | None:
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
            orgao = self.company_acronym(row['Empresa/Órgão'])
            atas_cig = row['Atas do CIG']

            if 'sim' in str(atas_cig).lower():
                dados[orgao] = True
            elif 'não' in str(atas_cig).lower():
                dados[orgao] = False
            else:
                dados[orgao] = False

        return dados

    def compare_maps(self, data_map: dict[str, bool], links_map: dict[str, list[str]]) -> tuple[dict[str, bool], int, int, int]:
        """Compares two maps (dictionaries) of data and links to verify the presence of minutes.

        Args:
            data_map (dict[str, bool]): Dictionary with the data of the organizations and presence of minutes.
            links_map (dict[str, list[str]]): Dictionary with the links found for the organizations.

        Returns:
            tuple[dict[str, bool], int, int]: Tuple containing a dictionary with the comparison results,
            the number of matches, and the total number of organizations with minutes.
        """

        results = {}
        total_with_minutes = 0
        total_without_minutes = 0
        matches = 0

        for org, has_minutes in data_map.items():
            if has_minutes:
                total_with_minutes += 1
                if org in links_map and len(links_map[org]) > 0:
                    results[org] = True
                    matches += 1
                else:
                    results[org] = False
            else:
                total_without_minutes += 1
                results[org] = None
            
        return results, matches, total_with_minutes, total_without_minutes

    def check_keywords(self, link: str, keywords: str) -> bool:
        """Checks if a link contains any of the specified keywords.

        Args:
            link (str): URL of the link to be checked.
            keywords (str): Keywords to be checked, separated by spaces.

        Returns:
            bool: True if the link contains any of the keywords, False otherwise.
        """

        keywords = set(keywords.split())

        for keyword in keywords:
            if len(keyword) <= 2:
                continue
            keyword = unidecode(keyword)
            if re.search(keyword, link, re.IGNORECASE):
                return True
        return False

    def company_acronym(self, company_name: str) -> str:
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

    def load_orgaos_name(self, adm_direta: list, mista_publica: list) -> int:
        """Loads the names of organizations from a text file into separate lists for direct and mixed public administration.

        Args:
            direct_admin (list): List to store the names of direct administration organizations.
            mixed_public (list): List to store the names of mixed public administration organizations.

        Returns:
            int: 0 if successful, 1 if there is an error opening the file.
        """

        try:
            file = open("data/lara/list_orgaos_name.txt", 'r')
        except Exception as e:
            print(e)
            return 1

        is_mista = 0
        for line in file:
            if "---" in line:
                is_mista = 1
                continue

            if not is_mista:
                adm_direta.append(line.strip())
            else:
                mista_publica.append(line.strip())

        file.close()
        return 0

    def search_link_cig(self, acronym: str, org: str, param: str, base_link: str, limit: int) -> dict[str, list[str]]:
        """Performs a search for links related to the Internal Governance Committee (CIG) for a specific organization.

        Args:
            acronym (str): Acronym of the organization.
            org (str): Name of the organization.
            param (str): Additional search parameters.
            base_link (str): Base URL for the search.
            header (dict): HTTP header for the request.
            limit (int): Limit of links to be returned.

        Returns:
            dict[str, list[str]]: Dictionary with the acronyms of the organizations as keys and lists of links as values.
        """
        
        org_name_params = [acronym + " df", org]
        org_link_dict = {}

        try:
            for org_name_param in org_name_params:
                search_param = f"{base_link}{org_name_param}{param}"
                source = requests.get(search_param, self.header, verify=False)

                if source.status_code != 200:
                    print("Erro ao acessar a página")
                    continue

                soup = BeautifulSoup(source.text, 'lxml')
                links = self.extract_links(soup, acronym, org, limit)
                
                for link in links:
                    link_addrs = link['href']
                    if link_addrs not in org_link_dict.get(acronym, []):
                        org_link_dict.setdefault(acronym, []).append(link_addrs.split("=")[1].split('&')[0])

        except requests.RequestException as e:
            print(f"search_link_cig. Erro na requisição HTTP: {e}")
        except Exception as e:
            print(f"search_link_cig. Erro inesperado: {e}")

        return org_link_dict
    
    def extract_links(self, soup: BeautifulSoup, acronym: str, org: str, limit: int):
        """
        Extracts relevant links from a web page based on specific keywords in the link text and URL.

        Args:
            soup (BeautifulSoup): BeautifulSoup object representing the parsed HTML page.
            acronym (str): Acronym of the organization used to filter links by checking the acronym in the URL.
            org (str): Name of the organization, used for filtering based on relevant keywords in the link.
            limit (int): Maximum number of links to extract from each section of the page.

        Returns:
            list: A list of link elements (`<a>`), containing the `href` and associated text, that match the search criteria.
        """
    
        links = []
        for g in soup.find_all('div',  {'class': 'Gx5Zad'}):
            found_links = g.find_all('a')[:limit]
            for link in found_links:
                link_text = link.get_text().lower()
                link_href = str(link['href'])
                
                if ("comitê interno de governança" in link_text or 
                    "atas" in link_text and "cig" in link_text or
                    "gestão" in link_text and "risco" in link_text):
                    if acronym.lower() in link_href and "df" in link_href or self.check_keywords(link_href, org):
                        links.append(link)
                        
        return links
    
    def save_links_to_json(self, links_dict: dict[str, list[str]], filename: str) -> None:
        """Saves the processed links to a JSON file.
        
        Args:
            links_dict (dict[str, list[str]]): Dictionare of links by organizatoin.
            filename (str): Name of the file.
            
        Return:
            None.
        """
        
        with open(filename, 'w') as json_file:
            json.dump(links_dict, json_file, indent=4)

    def load_links_from_json(self, filename: str) -> dict[str, list[str]]:
        """Loads the processed links from a JSON file.
        
        Args:
            filename (str): Name of the file.
            
        Return:
            None.
        """
        
        try:
            with open(filename, 'r') as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return {}

    def filter_cig_minutes_webpage(self, url: str) -> tuple[bool, None] | tuple[bool, str]:
        """Filters web pages to check for the presence of meeting minutes and updates.

        Args:
            url (str): URL of the page to be checked.

        Returns:
            tuple[bool, None] | tuple[bool, str]: Tuple indicating if the minutes are present and the update date,
            or None in case of failure.
        """
        
        data_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4})|(\d{4})')
        update_site_pattern = re.compile(
            r'Atualizado em \d{1,2}/\d{1,2}/\d{2,4} às ([01]?[0-9]|2[0-3])h[0-5][0-9]', re.IGNORECASE)
        meeting_minutes_patterns = [
            re.compile(r'ata da \d+ª reunião', re.IGNORECASE),
            re.compile(r'ata \d+ª reunião', re.IGNORECASE),
            re.compile(r'\d+ª reunião', re.IGNORECASE),
            re.compile(
                r'ata da reunião extraordinária Nº \d{1,2}', re.IGNORECASE),
            re.compile(r'ata reunião ordinária Nº \d{1,2}', re.IGNORECASE),
            re.compile(r'Ata de reunião \d{1,2}', re.IGNORECASE),
            re.compile(r'atas das reuniões cig', re.IGNORECASE)
        ]
            
        if ".pdf" in url:
            return False, None
        
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        try:
            response = session.get(url, headers=self.header, verify=False, timeout=10)
            response.raise_for_status()

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                page_text = soup.get_text().lower()
                match = update_site_pattern.search(page_text)

                links = soup.find_all('a')

                for link in links:
                    link_text = link.get_text().lower()
                    link_href = str(link.get('href')).lower()

                    if (any(pattern.search(link_text) for pattern in meeting_minutes_patterns)):
                        if ("reuniao" in link_href and "cig" in link_href and ".pdf" in link_href):
                            if match:
                                return True, match.group()
                            return True, None
                    elif (data_pattern.search(link_text)):
                        if (("ata" in link_href and "cig" in link_href) and
                                ".pdf" in link_href):
                            if match:
                                return True, match.group()
                            return False, None
                if match:
                    return False, match.group()
                return False, None
            else:
                print(f"filter_cig_minutes_webpage. Falha ao carregar o site: {url}")
                return False, None

        except requests.RequestException as e:
            print(f"filter_cig_minutes_webpage. Erro na requisição HTTP: {e}")
            return False, None

        except Exception as e:
            print(f"filter_cig_minutes_webpage. Erro inesperado: {e}")
            return False, None

    def filter_portal_webpage(self, url: str) -> tuple[bool, bool, None] | tuple[bool, bool, str]:
        """Filters web pages to check for the presence of meeting minutes and updates.

        Args:
            url (str): URL of the page to be checked.

        Returns:
            tuple[bool, bool, None] | tuple[bool, bool, str]: Tuple indicating if the minutes are present and the update date,
            or None in case of failure.
        """
        
        if ".pdf" in url:
            return False, False, None

        try:
            response = requests.get(url, headers=self.header, verify=False)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                data_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}')
                year_pattern = re.compile(r'\d{4}')

                update_site_pattern = re.compile(
                    r'Atualizado em \d{1,2}/\d{1,2}/\d{2,4} às ([01]?[0-9]|2[0-3])h[0-5][0-9]', re.IGNORECASE)
                decreto_pattern1 = re.compile(
                    r'decreto\s+n[°º]\s*39\.736(?:,?\s*de\s*28\s*de\s*março\s*de\s*2019)?|decreto\s+n[°º]\s*39\.736/?2019', re.IGNORECASE)
                decreto_pattern2 = re.compile(
                    r'decreto\s+n[°º]\s*37\.297(?:,?\s*de\s*29\s*de\s*abril\s*de\s*2016)?|decreto\s+n[°º]\s*37\.297/?2016', re.IGNORECASE)

                target_text1 = "comitê interno de governança".lower()
                target_text1_1 = "comitê de governança e estratégia".lower()
                target_text2 = "atas das reuniões".lower()
                target_text2_1 = "atas de memórias de reuniões".lower()
                target_text2_2 = "atas".lower()
                target_text3 = "portaria".lower()

                page_text = soup.get_text().lower()
                match = update_site_pattern.search(page_text)

                if (((decreto_pattern1.search(page_text) or decreto_pattern2.search(page_text)) and
                         (target_text1 in page_text) or (target_text1_1 in page_text) or
                        ((target_text3 in page_text) and (target_text1 in page_text)) or
                        ((target_text3 in page_text) and (target_text1_1 in page_text)) or
                        (target_text2 in page_text))):

                    links = soup.find_all('a')

                    for link in links:
                        link_text = link.get_text().lower()
                        link_href = str(link.get('href')).lower()

                        if (target_text2 in link_text or target_text2_2 in link_text or data_pattern.search(str(link_text))):
                            if match:
                                return True, True, match.group()

                            return True, True, None
                        elif (year_pattern.search(str(link_text)) and 
                              ("atas" in str(link_href) or "cig" in str(link_href))):
                            if match:
                                return True, True, match.group()
                            return True, True, None
                    if match:
                        return True, False, match.group()
                    return True, False, None
                elif ((target_text1 in page_text and target_text2 in page_text) or (target_text1_1 in page_text and target_text2 in page_text) or
                        (target_text1 in page_text and target_text2_1) or (target_text1_1 in page_text and target_text2_1) or
                        (target_text1 in page_text and target_text2_2) or (target_text1_1 in page_text and target_text2_2)):
                    
                    links = soup.find_all_next('a')
                    
                    for link in links:
                        link_text = link.get_text().lower()
                        link_href = str(link.get('href')).lower()
                        
                        is_ata_cig = (self.check_keywords(link_href, "comite") and self.check_keywords(
                            link_href, "interno") and self.check_keywords(link_href, "governanca"))
                        
                        if (year_pattern.search(str(link_text)) and is_ata_cig) or (year_pattern.search(str(link_text)) and "cig" in link_text):
                            if match:
                                return True, True, match.group()

                            return True, True, None
                    
                        elif (data_pattern.search(str(link_text)) and is_ata_cig) or (data_pattern.search(str(link_text)) and "cig" in link_text):
                            if match:
                                return True, True, match.group()

                            return True, True, None 
                    
                    if match:
                        return True, False, match.group()
                    return True, False, None
                else:
                    return False, False, None
            else:   
                print(f"filter_portal_webpage. Falha ao carregar o site: {url}")
                return False, False, None

        except requests.RequestException as e:
            print(f"filter_portal_webpage. Erro na requisção: {e}")        
            return False, False, None
        except Exception as e:
            print(f"filter_portal_webpage. Erro inesperado: {e}")
            return False, False, None

    def filter_dict_orgaos(self, dict_orgao_links: dict[str, list[str]]) -> list[Orgao]:
        """Filter links to catch CIG sites.

        Args:
            dict_orgao_links (dict[str, list[str]]): Dictionary with the name of the organizations as keys and lists of links as values.

        Returns:
            list[Orgao]: A list with Orgao object containing informations about organizations links filtered.
        """       
         
        list_ogaos = []
        for orgao_name, links in dict_orgao_links.items():
            orgao = Orgao(orgao_name, links, transparency_active=False)
            processed_links = set()
            
            for link in links:            
                base_link = link.split('&')[0]
                
                if base_link in processed_links:
                    continue
                
                processed_links.add(base_link)
                
                is_cig_page, last_page_updt = self.filter_cig_minutes_webpage(base_link)
                time.sleep(3)
                if is_cig_page:
                    orgao.add_link_cig(base_link, last_page_updt)
                    orgao.add_transparency_active(True)
                
                is_portal_page, has_minutes, last_page_updt = self.filter_portal_webpage(base_link)
                time.sleep(3)
                if is_portal_page: 
                    orgao.add_link_portal(base_link, last_page_updt)
                    if has_minutes:
                        orgao.add_portalPage_has_minutes(True)
                        orgao.add_transparency_active(True)
                        
            list_ogaos.append(orgao)
            
        return list_ogaos
    
    def generate_docx_report(self, content: str) -> None:
        """Generate a report with the collected links by organizations and the number os the results.
    
        Args:
            content (str): Content of the report.
            
        Return:
            None.    
        """       
        
        service = DocumentService()
        self.path_docx_report = service.create_document(
            title="Relatório de Mineração de Dados - LARA",
            content=content,
            footer="LARA - Levantador Automático de Recursos Administrativos",
            file_name="realtorio_lara.docx"
        )
        print(f"Documento criado: {self.path_docx_report}")
        
    def generate_pdf_report(self) -> None:
        """
        Converts a Word document (.docx) report into a PDF format.

        Behavior:
            - Utilizes the `convert_docx_to_pdf` method from `DocumentService` 
            to convert the report specified by `self.path_docx_report` into a PDF.

        Precondition:
            - The `self.path_docx_report` attribute must contain a valid path 
            to the existing Word document (.docx) report.

        Postcondition:
            - A PDF version of the report is generated in the same directory or 
            specified by the `convert_docx_to_pdf` implementation.

        Args:
            None

        Returns:
            None
        """

        DocumentService.convert_docx_to_pdf(input=self.path_docx_report)
            
    def execute(self) -> None:
        """Execute Lara bot.
    
        Args:
            None.
            
        Return:
            None.    
        """       
        
        url_google = "https://google.com/search?q="
        param = " atas comitê interno de governança"
        
        excel = "FAPDF-Segmentoseitensintegridade(versão20.04.Completo)_corrigido(1).xlsx"
        dados = self.read_excel_data(excel)
        if dados == None:
            print(f"Erro ao ler o arquivo: {excel}")
            
        adm_direta = []
        mista_publica = []
        if self.load_orgaos_name(adm_direta, mista_publica) == 1:
            print("Erro ao carregar os nomes dos órgões")    

        dict_general = {}
        links_json = self.load_links_from_json('data/lara/json_map_links.json')
        
        if not links_json:
            for orgao in adm_direta:
                dict_general.update(self.search_link_cig(self.company_acronym(orgao), orgao,
                            param, url_google, 6))
                time.sleep(3)
                
            self.save_links_to_json(dict_general, 'data/lara/json_map_links.json')
        else:
            dict_general = links_json    
        
        resul, acertos, total_com_ata, total_sem_ata = self.compare_maps(dados, dict_general)
                
        report_content = (
            f"Quantidade de órgãos do Distrito Federal minerados: {len(dados.keys())}\n"
            f"Total de órgãos que possuem atas: {total_com_ata}\n"
            f"Total de órgãos que não possuem atas: {total_sem_ata}\n"
            f"Quantidade de acertos da Lara: {acertos}\n"
            f"Porcentagem de acertos da Lara: {((acertos / total_com_ata) * 100):.2f}%\n\n"
            "Detalhamento por órgão:\n"
        )
                           
        orgao_details = "\n".join(f"{orgao}: {'Sim' if tem_atas else 'Não'}" for orgao, tem_atas in resul.items())
        report_content += orgao_details
        
        list_orgaos = self.filter_dict_orgaos(dict_general)
            
        for orgao in list_orgaos:
            time.sleep(3)
            self.donwload_minutes(orgao)
            
        self.generate_docx_report(report_content)
            
    def get_pdf_links(self, url: str) -> list[str] | None:
        """
        Extracts a list of PDF links related to meeting minutes from a given URL.

        Args:
            url (str): The URL of the webpage to scrape for PDF links.

        Returns:
            list[str] | None: A list of URLs corresponding to the PDF meeting minutes or None if no valid links are found.

        Exceptions:
            - Prints an error message if the request fails or an unexpected error occurs.

        Details:
            - Uses a set of regular expressions to match text patterns associated with meeting minutes.
            - Extracts the `href` attribute from `<a>` tags on the page.
            - Filters links based on text content and predefined patterns.
            """
            
        try:
            response = requests.get(url.split('&')[0], headers=self.header, verify=False)
            links_list = []
            
            meeting_minutes_patterns = [
                re.compile(r'ata(?:s)? da (?:\d+ª )?reunião (?:ordinária|extraordinária)?(?: nº? \d{1,2})?', re.IGNORECASE),
                re.compile(r'ata \d+ª reunião', re.IGNORECASE),
                re.compile(r'ata \d+ª reunião', re.IGNORECASE),
                re.compile(r'https?://[\w\-\.]+/[\w\-\.]+/[\w\-\.]+/[\w\-\.]+/.*(ATA|Ata|ata)[\w\-_]*(_Reuniao|_reuniao|_REUNIAO)?[\w\-_]*\.pdf'),
                re.compile(r'\d+ª reunião', re.IGNORECASE),
                re.compile(r'Ata de reunião \d{1,2}', re.IGNORECASE),
                re.compile(r'atas das reuniões cig', re.IGNORECASE)
            ]

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a')
                
                for link in links:
                    link_url = link.get('href')
                    link_text = link.get_text().lower()

                    if link_url:
                        for pattern in meeting_minutes_patterns:
                            if pattern.match(link_text):
                                href = link_url.split('&')[0]
                                links_list.append(href)

                return links_list
            else:
                print(f"donwload_pdf_by_link. Erro ao acessar link: {url}. status: {response.status_code} - {response.reason}.")
                return None
        
        except requests.RequestException as e:
            print(f"get_pdf_links. Erro na requisição: {e}")
            return None
        except Exception as e:
            print(f"get_pdf_links. Erro inesperado: {e}")
            return None

    def donwload_minutes(self, orgao: Orgao ) -> None:
        """
        Downloads all meeting minutes PDF files related to a specific organization.

        Args:
            orgao (Orgao): An object representing the organization, which contains its name and links.

        Returns:
            None

        Exceptions:
            - Prints an error message if the PDF links or downloads fail.

        Details:
            - Calls `get_pdf_links` to retrieve PDF links for each URL associated with the organization.
            - Creates a directory for the organization's documents if it doesn't already exist.
            - Iteratively downloads PDFs and saves them with a sequential naming pattern in the directory.
        """ 

        try:
            links = orgao.get_links()      
            if not links:
                return
            
            diretorio = f'data/lara/docs/{orgao._name}'
            if not exists(diretorio):
                makedirs(diretorio)
                
            file_counter = 0
            for link in links:
                minutes_links = self.get_pdf_links(link)    
                
                if not minutes_links:
                    continue
                
                for pdf_link in minutes_links:
                    file_name = diretorio + f"/{orgao._name}_ata{file_counter}.pdf"
                    success = self.donwload_pdf_by_link(pdf_link, file_name)
                    
                    if success:
                        print(f"Downloaded: {file_name}")
                        file_counter += 1
                    else:
                        print(f"Failed to download: {pdf_link}")
        except Exception as e:
            print(f"Um erro inesperado ocorreu: {e}")
            

    def donwload_pdf_by_link(self, url: str, file_name: str) -> bool:
        """
        Downloads a PDF file from a given URL and saves it to a specified file name.

        Args:
            url (str): The URL of the PDF file to download.
            file_name (str): The name and path where the downloaded file will be saved.

        Returns:
            bool: True if the file is successfully downloaded and valid, False otherwise.

        Exceptions:
            - Prints an error message if the download fails or an unexpected error occurs.

        Details:
            - Performs a streaming download to avoid memory issues with large files.
            - Checks the file size after download to verify integrity.
            - Logs success or failure messages.
        """
        
        try:
            response = requests.get(url, stream=True, headers=self.header, verify=False)
            
            if response.status_code == 200:
                with open(file_name, 'wb') as fd:
                    for chunk in response.iter_content(chunk_size=8192):
                        fd.write(chunk)
                    
                file_size = getsize(file_name)
                if file_size > 0:
                    print("Download realizado com sucesso")
                    return True
                else:
                    print("Download falhou")
                    rmdir(file_name)
                    return False
            else:
                print(f"donwload_pdf_by_link. Erro ao acessar link: {url}. status: {response.status_code} - {response.reason}.")
                return False
                
        except requests.RequestException as e:
            print(f"donwload_pdf_by_link. Erro na requisção: {e}") 
            return False
        except Exception as e:
            print(f"donwload_pdf_by_link. Erro na requisção: {e}") 
            return False
        
    def get_docx_report(self):
        """
        Opens the generated Word document report (.docx) in the default application 
        for the current operating system.

        Behavior:
            - On macOS (Darwin): Uses the 'open' command to launch the file.
            - On Windows: Uses 'os.startfile' to open the file.
            - On Linux/Unix: Uses the 'xdg-open' command to open the file.

        Precondition:
            - The `self.path_docx_report` attribute must contain a valid path to the .docx report.

        Raises:
            - No specific exceptions are handled in this method, but subprocess errors 
            or missing files may lead to runtime exceptions.
        """
        
        if self.path_docx_report:
            if platform.system() == 'Darwin': 
                subprocess.call(('open', self.path_docx_report))
            elif platform.system() == 'Windows':
                os.startfile(self.path_docx_report)
            else:
                subprocess.call(('xdg-open', self.path_docx_report))
                
    def get_pdf_report(self):
        """
        Opens the generated PDF report (.pdf) in the default application 
        for the current operating system.

        Behavior:
            - On macOS (Darwin): Uses the 'open' command to launch the file.
            - On Windows: Uses 'os.startfile' to open the file.
            - On Linux/Unix: Uses the 'xdg-open' command to open the file.

        Precondition:
            - The `self.path_pdf_report` attribute must contain a valid path to the .pdf report.

        Raises:
            - No specific exceptions are handled in this method, but subprocess errors 
            or missing files may lead to runtime exceptions.
        """
        
        if self.path_pdf_report:
            if platform.system() == 'Darwin':   
                subprocess.call(('open', self.path_pdf_report))
            elif platform.system() == 'Windows':
                os.startfile(self.path_pdf_report)
            else:                               
                subprocess.call(('xdg-open', self.path_pdf_report))
            