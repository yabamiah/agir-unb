##############################################################
## LARA - Levantador Automático de Recursos Administrativos ##
##############################################################

import time
import pandas as pd

import json

from bs4 import BeautifulSoup

import requests

from selenium import webdriver
from selenium.webdriver.common.by import By

import tabula

import os

class Ementa:
    def __init__(self, orgao_name: str, ementa_titulo: str, data: str, link_arquivo: str):
        self.__orgao_name__ = orgao_name
        self.__ementa_titulo__ = ementa_titulo
        self.__data__ = data
        self.__link_arquivo__ = link_arquivo

    def set_ementa_titulo(self, ementa_titulo: str):
        self.__ementa_titulo__ = ementa_titulo

    def set_data(self, data: str):
        self.__data__ = data

    def set_link_arquito(self, link_arquivo: str):
        self.__link_arquivo__ = link_arquivo

    def set_orgao_name(self, orgao_name: str):
        self.__orgao_name__ = orgao_name

    def __repr__(self) -> str:
        return f"Orgão: {self.__orgao_name__}\nTítulo: {self.__ementa_titulo__}\nData: {self.__data__}\nLinks: {self.__link_arquivo__}\n"

class Lara:
    """
    Classe principal para o sistema AGIR.

    Atributos:1
    - url (str): URL da página de licitações.
    - pdf_path (str): Caminho para o arquivo PDF no sistema.
    - data_frame_path (str): Caminho para o arquivo CSV gerado a partir do PDF.
    - dict_company_path (str): Caminho para o arquivo .json das empresas privadas
    - dict_orgao_path (str): Caminho para o arquivo .json das empresas públicas
    - header (dict): Cabeçalho para evitar detecção como um script.
    - companys (list): Lista de nomes de empresas extraídos.
    - orgaos (list): Lista de órgãos contratantes extraídos.
    
    Métodos:
    - pdf_to_excel(self): Realiza a conversão de um arquivo pdf para excel.
    - scrape_web_data(self, optional_orgao): Realiza a raspagem de dados da página de licitações.
    - scrape_web_pub_data(self): Realiza a raspagem de dados de orgãos públicos
    - scrape_pdf_data(self): Realiza a raspagem de dados de um arquivo PDF.
    - donwload_company_compliance(self, companys_links: dict, type: int): Realiza o download de arquivos compliance da internet.
    """

    url = "https://google.com/search?q="
    pdf_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.pdf"
    data_frame_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.csv"
    dict_company_path = "lara/docs/dict_company_links.json"
    dict_orgao_path = "lara/docs/dict_orgao_links.json"
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
    companys = []
    orgaos = []
    
    def __init__(self) -> None:
        if not os.path.exists(self.data_frame_path):
            self.pdf_to_excel()
        
        self.scrape_pdf_data()
        
        self.scrape_web_data([])
        #self.scrape_web_pub_data()

        print("Todas as informações já foram armazenadas..")
        
    def pdf_to_excel(self) -> None:
        tabula.convert_into(self.pdf_path, self.data_frame_path, output_format="csv", pages="all", lattice=True, stream=True)

        # Retirando a primeira linha do .csv que quebrava o arquivo
        with open(self.data_frame_path, 'r') as file:
            rows = file.readlines()

        rows = rows[1:]

        with open(self.data_frame_path, 'w') as file:
            file.writelines(rows)
    
    def scrape_pdf_data(self) -> None:
        """
        Extrai informações de um arquivo PDF e prepara os dados para posterior web scraping.

        - Verifica se o arquivo CSV já existe; se não, converte o PDF para CSV.
        - Remove a primeira linha do CSV, que pode estar quebrada após a conversão.
        - Lê o CSV em um DataFrame pandas e realiza manipulações nos dados.
        - Extrai informações relevantes (EMPRESA e ÓRGÃO CONTRATANTE) e as prepara para o web scraping.
        - Realiza algumas manipulações nos nomes das empresas e órgãos contratantes.
        - Armazena as informações em listas (companys e orgaos) para uso posterior.

        Retorna None.

        Observações:
        - Certifique-se de ter as bibliotecas necessárias instaladas (os, pandas, tabula).
        - O caminho do arquivo CSV é definido em data_frame_path.
        """
        self.orgaos.append("Gabinete do Governador")

        data_frame = pd.read_csv(self.data_frame_path)
        data_frame = data_frame.fillna('0')
        df_list = data_frame[['EMPRESA', 'ÓRGÃO CONTRATANTE']].to_dict('records')
        self.data_frame_dict = df_list

        for dict_compay in df_list:
            name = dict_compay['EMPRESA'].replace("\n", " ").replace("LTDA", "").replace("S/A", "").replace("S.A", "").strip().title()
            if (dict_compay['EMPRESA'] == "Empresa") or (dict_compay['EMPRESA'] in self.companys):
                continue
            self.companys.append(name)

            name = dict_compay['ÓRGÃO CONTRATANTE'].replace("\n", " ").replace("LTDA", "").replace("S/A", "").replace("S.A", "").strip().title()
            if (dict_compay['ÓRGÃO CONTRATANTE'] == "ÓRGÃO CONTRATANTE" or dict_compay['ÓRGÃO CONTRATANTE'] in self.orgaos):
                continue
            self.orgaos.append(name)


        print("As informações do PDF foram extraídas com sucesso...")

    def scrape_web_data(self, optional_orgaos: list) -> None:
        """
        Realiza a raspagem de dados das páginas da web relacionadas à integridade e ética de empresas.

        Itera sobre a lista de empresas (self.companys), realiza uma pesquisa na web para cada empresa,
        analisa os resultados da pesquisa e extrai os links relevantes relacionados a códigos de conduta ética e integridade.

        E quando utiliza do parâmetro 'optional_orgaos' realiza pesquisa de orgãos públicos que não foram achados no médoto scrape_web_pub_data().

        Retorna None.

        Observações:
        - Usa a biblioteca 'requests' para enviar solicitações HTTP às páginas da web.
        - Utiliza a biblioteca 'BeautifulSoup' para analisar o HTML das páginas web.
        - Imprime informações sobre os links encontrados para cada empresa e armazena em um dicionário (company_dict).
        - Chama o método 'donwload_company_compliance' para fazer download dos códigos de conduta com base nos links obtidos.
        """

        company_dict = {}

        if optional_orgaos:
            companys = optional_orgaos
            search_param = " compliance"
        else:
            companys = self.companys
            search_param = " código de conduta ética e integridade"

        for i, company in enumerate(companys, start=1):
            payload = company + " código de conduta ética e integridade"
        
            try:
                source = requests.get(self.url + payload, headers=self.header, verify=False)
            except requests.exceptions.HTTPError as err:
                raise SystemExit(err)
    
            soup = BeautifulSoup(source.text, 'html.parser')
            print(f"# Empresa {i}: {company}")
            links = []
            company_format = company.lower()
            i += 1

            for info in soup.find_all('a', attrs={"jsname": "UWckNb"}):
                title_link = info.get_text('|').replace("|", " ", 1).split("|")[0].lower()
                if company_format in title_link  and ("ética" in title_link or "compliance" in title_link or "integridade" in title_link):
                    print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                    links.append(info['href'])
                elif(company_format.count(" ")):
                    if (company_format.split(" ")[0] in title_link and company_format.split(" ")[1] in title_link) and ("ética" in title_link or "compliance" in title_link or "integridade" in title_link):
                        print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                        links.append(info['href'])

                company_dict[company] = links

                if not company_dict[f'{company}']:
                    del company_dict[f'{company}']

        print(company_dict)
        with open(self.dict_company_path, 'w') as file:
            file.write(json.dumps(company_dict))

        if optional_orgaos:
            self.donwload_company_compliance(company_dict, 1)
        else:
            self.donwload_company_compliance(company_dict, 0)

    def scrape_web_pub_data(self) -> None:
        print("Scrape web pub data")
        print(self.orgaos)
        orgaos_list = []
        ementa_objs = []
        for name in self.orgaos:
            orgaos_list.append([name])

        for orgao in orgaos_list:
            acronym = company_acronym(orgao[0])
            search_companay_by_acronym(acronym, orgao)
        
        for orgao in orgaos_list:
            for i in range(len(orgao)):
                for j in range(len(orgao[1])):
                    ementa_objs.append(Ementa( orgao[0], orgao[1][j], orgao[2][j], orgao[3][j] ))

        orgaos_filtrados = []
        ementas = filtrar_ementas(ementas=ementa_objs)
        for ementa in ementas:
            if ementa.__orgao_name__ in orgaos_filtrados:
                continue
            orgaos_filtrados.append(ementa.__orgao_name__)

        orgaos_excluidos = []
        for name in self.orgaos:
            if name not in orgaos_filtrados:
                    orgaos_excluidos.append(name)

        company_dict = {}
        for ementa in ementas:
            company_dict.setdefault(ementa.__orgao_name__, []).append(ementa.__link_arquivo__)
        
        self.donwload_company_compliance(company_dict, 1)

        print("------------------------------\n\n\n")
        orgaos_excluidos = [company_acronym(orgao) for orgao in orgaos_excluidos]
        self.scrape_web_data(optional_orgaos=orgaos_excluidos);

    def donwload_company_compliance(self, companys_links: dict, type: int) -> None:
        """
        Faz download dos códigos de conduta ética e integridade de empresas com base nos links fornecidos.

        Itera sobre um dicionário onde as chaves são nomes de empresas e os valores são listas de links relacionados.
        Para cada empresa, verifica a quantidade de links disponíveis:
        - Se houver apenas um link, realiza o download diretamente.
        - Se houver vários links, itera sobre eles e realiza o download individualmente.

        Função auxiliar:
        - download_files_by_url(company, link, source): Função para realizar o download de um arquivo a partir de uma URL.

        Parâmetros:
        - companys_links (dict): Dicionário onde as chaves são nomes de empresas e os valores são listas de links.
        - type (int): type == 0 : Empresa privada, type == 1 : Orgão público

        Retorna None.

        Observações:
        - Usa a biblioteca 'requests' para fazer download dos arquivos a partir das URLs fornecidas.
        - Chama o método 'download_files_by_url' para realizar o download de cada arquivo.
        """

        if type:
            directory_path = "./dani/docs/empresa-pub/"
        else:
            directory_path = "./dani/docs/empresa-priv/"

        for company, links in companys_links.items():
            time.sleep(10) # [(－－)]..zzZ
            try:
            
                if len(links) == 1:
                    source = requests.get(links[0], headers=self.header, stream=True, verify=False, timeout=30)
                    download_files_by_url(company=company, link=links[0], source=source, directory_path=directory_path)             
                else:
                    for i, link in enumerate(links):
                        source = requests.get(link, headers=self.header, stream=True, verify=False, timeout=30)
                        download_files_by_url(company=company+str(i), link=link, source=source, directory_path=directory_path)
            except requests.exceptions.ConnectionError:
                print('Erro de conexão')

        print("Documentos baixados com sucesso..")

def download_files_by_url(company: str, link: str, source: str, directory_path: str) -> int:
    """
    Realiza o download de arquivos a partir de uma URL e salva localmente.

    Verifica o tipo de arquivo com base na extensão do link e realiza o download para o diretório especificado.
    Os tipos de arquivo suportados são PDF, DOCX e outros (considerados como texto).

    Parâmetros:
    - company (str): Nome da empresa para compor o nome do arquivo.
    - link (str): URL do arquivo a ser baixado.
    - source (str): Conteúdo da resposta HTTP da URL.
    - directory_path (str): Local onde o arquivo será armazenado.

    Retorna:
    - int: 0 se o download for bem-sucedido, caso contrário, uma exceção é levantada.

    Observações:
    - O nome do arquivo gerado é composto pelo nome da empresa e a extensão do arquivo.
    - Os arquivos são salvos no diretório "./dani/docs/".
    - O tipo de arquivo é determinado pela extensão do link.
    - Caso o link não contenha uma extensão reconhecida, o conteúdo da página HTML é salvo como um arquivo de texto.
    """
    
    company = company.title().replace(" ", "")
    
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

    if "pdf" in link: 
        try:
            with open(f"{directory_path}{company}_Compliance.pdf", 'wb') as file:
                file.write(source.content)
                print(f"Sucecss...{company}")
                return 0
        except Exception as err:
            print(err)
            raise
    elif "docx" in link: 
        try:
            with open(f"{directory_path}{company}_Compliance.docx", 'wb') as file:
                file.write(source.content)
                print(f"Sucecss...{company}")
                return 0
        except Exception as err:
            print(err)
            raise
    else:
        soup = BeautifulSoup(source.text, 'html.parser')
        try:
            with open(f"{directory_path}{company}_Compliance.txt", 'wb') as file:
                file.write(soup.get_text('\n', '\n\n').encode())
                print(f"Sucecss...{company}")
                return 0
        except Exception as err:
            print(err)
            raise

def search_companay_by_acronym(acronym: str, orgao_list: list) -> list:
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)

    payloads = [ f"https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=Pol%C3%ADtica+de+Integridade+P%C3%BAblica+{acronym}", f"https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=compliance+{acronym}" ]

    for payload in payloads:
        driver.get(url=payload)

        quadros = driver.find_elements(By.CSS_SELECTOR, 'div.column.w-90-pc.text-justify.ds_ementa')
        quadros = [quadro.text for quadro in quadros]
        orgao_list.append(quadros)

        datas = driver.find_elements(By.CSS_SELECTOR, 'span.dt_assinatura.dt_assinatura_text')
        datas = [str(data.text).split()[0] for data in datas]
        orgao_list.append(datas)

        links_arquivos = driver.find_elements(By.CLASS_NAME, 'baixarArquivo')
        links_arquivos = [link.get_attribute("href") for link in links_arquivos]
        orgao_list.append(links_arquivos)

        driver.implicitly_wait(10)

    driver.quit()    
    return orgao_list

def filtrar_ementas(ementas: list) -> list:
    ementas_filtradas = []
    for ementa in ementas:
        if ("integridade" not in ementa.__ementa_titulo__.lower() and
            "riscos" not in ementa.__ementa_titulo__.lower() and
            "compliance" not in ementa.__ementa_titulo__.lower() and
            "governança" not in ementa.__ementa_titulo__.lower()):
            continue
        ano = int(ementa.__data__.split('/')[2])
        if not ano >= 2021:
            continue
        ementas_filtradas.append(ementa)

    return ementas_filtradas

def company_acronym(company_name: str) -> str:
    acronyms = {
        'Secretaria De Estado De Educação Do Distrito Federal': 'see',
        'Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal': 'seplad',
        'Instituto De Assistência À Saúde Dos Servidores Do Distrito Federal': 'inas',
        'Secretaria De Estado De Obras E Infraestrutura Do Distrito Federal': 'sodf',
        'Companhia Imobiliária De Brasília' : 'terracap',
        'Companhia De Saneamento Ambiental Do Distrito Federal' : 'caesb',
        'Secretaria De Estado De Economia Do Distrito Federal' : 'seec',
        'Secretaria De Estado De Justiça E Cidadania Do Distrito Federal' : 'sejus df',
        'Companhia Urbanizadora Da Nova Capital Do Brasil' : 'novacap',
        'Departamento De Estradas De Rodagem Do Distrito Federal' : 'der',
        'Corpo De Bombeiros Militar Do Distrito Federal' : 'cbmdf',
        'Polícia Civil Do Distrito Federal' : 'pcdf',
        'Banco De Brasília' : 'brb',
        'Companhia Do Metropolitano Do Distrito Federal' : 'metrô-df',
        'Instituto De Pesquisa E Estatística Do Distrito Federal' : 'ipedf',
        'Serviço De Limpeza Urbana' : 'slu',
        'Gabinete do Governador' : 'gag',
    }

    acronym = company_name in acronyms
    if acronym:
        return acronyms[company_name]
    else:
        return ""
        
