##############################################################
## LARA - Levantador Automático de Recursos Administrativos ##
##############################################################


## Bibliotecas para formatação, conversão de arquivos e utilidades básicas
import time
import pandas as pd
import tabula
import json
import os
import weasyprint
import re

## Bibliotecas para lidar com requisições web e web scraping
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By



## Biblioteca para resolver problema de falta de certificado
import ssl
ssl._create_default_https_context = ssl._create_unverified_context


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
    # pdf_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.pdf"
    # data_frame_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.csv"
    list_orgaos_name = "lara/docs/list_orgaos_name.txt"
    dict_company_path = "lara/docs/dict_company_links.json"
    dict_orgao_path = "lara/docs/dict_orgao_links.json"
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
    private_companys = []
    adm_direta = []
    mista_publica = []
    
    def __init__(self) -> None:
        # if not os.path.exists(self.data_frame_path):
        #     self.pdf_to_excel()
        
        # self.scrape_pdf_data()

        if not os.path.exists(self.list_orgaos_name):
            self.scrape_orgaos_name()
            self.save_orgaos_name()
        else:
            self.load_orgaos_name()
        
        self.organ_analysis()

        
        # self.scrape_web_privado_data()
        # self.scrape_web_adm_direta_data()
        # self.scrape_web_pub_mista_data()

        print("Todas as informações já foram armazenadas..")
        
    def pdf_to_excel(self) -> None:
        """
        Converte arquivo .PDF para .EXCEL (Para o arquivo .pdf específico de compliance do governo).

        Retorna None.
        """

        tabula.convert_into(self.pdf_path, self.data_frame_path, output_format="csv", pages="all", lattice=True, stream=True)

        with open(self.data_frame_path, 'r') as file:
            rows = file.readlines()

        rows = rows[1:]

        with open(self.data_frame_path, 'w') as file:
            file.writelines(rows)
    
    def scrape_pdf_data(self) -> None:
        """
        Extrai informações de um arquivo PDF e prepara os dados para posterior web scraping.

        - Extrai informações relevantes (EMPRESA) e as prepara para o web scraping.
        - Realiza algumas manipulações nos nomes das empresas e órgãos contratantes.
        - Armazena as informações em listas (companys) para uso posterior.

        Retorna None.

        Observações:
        - Certifique-se de ter as bibliotecas necessárias instaladas (os, pandas).
        - O caminho do arquivo pdf é definido em data_frame_path.
        """

        data_frame = pd.read_csv(self.data_frame_path).fillna('0')
        #data_frame = data_frame.fillna('0')
        df_list = data_frame[['EMPRESA']].to_dict('records')

        for dict_compay in df_list:
            name = dict_compay['EMPRESA'].replace("\n", " ").replace("LTDA", "").replace("S/A", "").replace("S.A", "").strip().title()
            if (dict_compay['EMPRESA'] == "Empresa") or (dict_compay['EMPRESA'] in self.private_companys or dict_compay['EMPRESA'] == "BANCO DE BRASÍLIA S.A"):
                continue
            self.private_companys.append(name)

        print("As informações do PDF foram extraídas com sucesso...")

    def scrape_orgaos_name(self) -> None:
        self.adm_direta.append("Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal")
        links1 = ['https://www.df.gov.br/secretarias/', 'https://www.df.gov.br/orgaos-especializados/'] # Administração direta
        link2 = ['https://www.df.gov.br/entidades/'] # Empresas públicas e sociedades mistas

        #-------------------- Links 1 --------------------#
        for link in links1:
            time.sleep(4) # [(－－)]..zzZ
            page = requests.get(link, verify=False)
            soup = BeautifulSoup(page.text, 'html.parser')

            format = ""
            for tags in soup.find_all('h3'):
                if ('Palácio do Buriti' in tags.text or any(digit.isdigit() for digit in tags.text)):
                    continue
            
                format = tags.text
                if not format.find("(") == -1:
                    idx = tags.text.find('(') - 1
                    format = tags.text[0:idx]

                if format.upper() == format:
                    format = format.title()

                format = re.sub(r'\s+', ' ', format).strip()   

                print(format)
                self.adm_direta.append(format)

        print("Adm direta: " + str(len(self.adm_direta)))
        lista = self.adm_direta
        self.adm_direta = [elemento for elemento in lista if elemento != ""]

        #-------------------- Link 2 --------------------#
        for link in link2:
            time.sleep(4) # [(－－)]..zzZ
            page = requests.get(link)
            soup = BeautifulSoup(page.text, 'html.parser')

            format = ""
            for tags in soup.find_all('h3'):
                if ('Palácio do Buriti' in tags.text or '24' in tags.text or '21' in tags.text or any(digit.isdigit() for digit in tags.text)):
                    continue
            
                format = tags.text
                if not format.find("(") == -1:
                    idx = tags.text.find('(') - 1
                    format = tags.text[0:idx]

                if format.upper() == format:
                    format = format.title()   
                
                print(format)
                self.mista_publica.append(format)

        print("Adm direta: " + str(len(self.mista_publica)))
        lista = self.mista_publica
        self.mista_publica = [elemento for elemento in lista if elemento != ""]

    def load_orgaos_name(self) -> None:
    
        with open(self.list_orgaos_name, 'r') as file:
            is_mista = 0
            for item in file:
                if ("---" in item):
                    is_mista = 1

                if (not is_mista):
                    self.adm_direta.append(item)
                else:
                    self.mista_publica.append(item)


    def save_orgaos_name(self) -> None:
        with open(self.list_orgaos_name, 'w') as file:
            for orgao in self.adm_direta:
                file.write(orgao + '\n')

            file.write("---\n")

            for orgao in self.mista_publica:
                file.write(orgao + '\n')
        

    def scrape_web_data(self, company: str, type: int) -> None:
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

        if not type == 0 :
            search_param = " plano de integridade"
        else:
            search_param = " código de conduta ética e integridade"

        payload = company + search_param
        
        try:
            source = requests.get(self.url + payload, headers=self.header, verify=False)
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)
    
        soup = BeautifulSoup(source.text, 'html.parser')
        print(f"# Empresa: {company}")
        links = []
        company_format = company.lower()

        max_scrape = 2
        scrape = 0
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
            print("Travou? Esperando....")
            scrape += 1
            if scrape == max_scrape:
                break

            if not company_dict.get(company):
                del company_dict[company]


        self.donwload_company_compliance(company_dict, type)

    def scrape_web_privado_data(self) -> None:
        for company in self.private_companys:
            time.sleep(10)
            self.scrape_web_data(company=company, type=0)

    def scrape_web_adm_direta_data(self) -> None:
        # if os.path.isfile("orgaos_excluidos"):
        print("Scrape web Administração direta")
        orgaos_list = []
        ementa_objs = []
        for name in self.adm_direta:
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
        for name in self.adm_direta:
            if name not in orgaos_filtrados:
                    orgaos_excluidos.append(name)

        file =  open("orgaos_excluidos", 'w')
        for orgao in orgaos_excluidos:
            file.write(orgao+"\n")

        company_dict = {}
        for ementa in ementas:
            company_dict.setdefault(ementa.__orgao_name__, []).append(ementa.__link_arquivo__)
            
        self.donwload_company_compliance(company_dict, 1)

        orgaos_excluidos = [company_acronym(orgao) for orgao in orgaos_excluidos]

        for i, orgao in enumerate(orgaos_excluidos):
            if "DF" not in orgao:
                orgao = orgao + " DF"
                orgaos_excluidos[i] = orgao
            if "/" in orgao:
                orgao = orgao.replace("/", " ")
                orgaos_excluidos[i] = orgao

        for orgao in orgaos_excluidos:
            time.sleep(10)
            self.scrape_web_data(company=orgao, type=1)

        return
        # else:
        #     orgaos_excluidos = []    
        #     with open("orgaos_excluidos") as file:
        #         orgaos_excluidos = [line for line in file]

        #     orgaos_excluidos = [orgao.replace("\n", "") for orgao in orgaos_excluidos]
        #     orgaos_excluidos = [company_acronym(orgao) for orgao in orgaos_excluidos]

        #     for i, orgao in enumerate(orgaos_excluidos):
        #         if "DF" not in orgao:
        #             orgao = orgao + " DF"
        #             orgaos_excluidos[i] = orgao
        #         if "/" in orgao:
        #             orgao = orgao.replace("/", " ")
        #             orgaos_excluidos[i] = orgao

        #     self.scrape_web_data(optional_orgaos=orgaos_excluidos, type=1);
    
    def scrape_web_pub_mista_data(self) -> None:
        #if os.path.isfile("orgaos_excluidos"):
        print("Scrape web Empresas públicas e Socieadades mistas")
        orgaos_list = []
        ementa_objs = []
        for name in self.mista_publica:
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
        for name in self.mista_publica:
            if name not in orgaos_filtrados:
                    orgaos_excluidos.append(name)

        file =  open("orgaos_excluidos", 'w')
        for orgao in orgaos_excluidos:
            file.write(orgao+"\n")

        company_dict = {}
        for ementa in ementas:
            company_dict.setdefault(ementa.__orgao_name__, []).append(ementa.__link_arquivo__)
            
        self.donwload_company_compliance(company_dict, 2)

        orgaos_excluidos = [company_acronym(orgao) for orgao in orgaos_excluidos]

        for i, orgao in enumerate(orgaos_excluidos):
            if "DF" not in orgao:
                orgao = orgao + " DF"
                orgaos_excluidos[i] = orgao
            if "/" in orgao:
                orgao = orgao.replace("/", " ")
                orgaos_excluidos[i] = orgao

        for orgao in orgaos_excluidos:
            time.sleep(10)
            self.scrape_web_data(company=orgao, type=1)

        return
        # else:
        #     orgaos_excluidos = []    
        #     with open("orgaos_excluidos") as file:
        #         orgaos_excluidos = [line for line in file]

        #     orgaos_excluidos = [orgao.replace("\n", "") for orgao in orgaos_excluidos]
        #     orgaos_excluidos = [company_acronym(orgao) for orgao in orgaos_excluidos]

        #     for i, orgao in enumerate(orgaos_excluidos):
        #         if "DF" not in orgao:
        #             orgao = orgao + " DF"
        #             orgaos_excluidos[i] = orgao
        #         if "/" in orgao:
        #             orgao = orgao.replace("/", " ")
        #             orgaos_excluidos[i] = orgao

        #     self.scrape_web_data(optional_orgaos=orgaos_excluidos, type=2);

    def organ_analysis(self) -> None:
        # os.system("clear")
        total_orgaos = len(self.mista_publica) + len(self.adm_direta)
        print(f"A quantidade total de orgãos do Distrito Federal que serão analisados é de: {total_orgaos}")
        print("Sendo dividos em")
        print(f"\tAdministração Direta, Autarqiuas e Fundações Públicas: {len(self.adm_direta)}")
        print(f"\tEmpresas Públicas e Sociedades de Economia Mista: {len(self.mista_publica)}")


        

    def donwload_company_compliance(self, company_links: dict, type: int) -> None:
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
        - type (int): type == 0 : Empresa privada
                      type == 1 : Administração Direta
                      type == 2 : Empresas públicas e Sociedades Mistas


        Retorna None.

        Observações:
        - Usa a biblioteca 'requests' para fazer download dos arquivos a partir das URLs fornecidas.
        - Chama o método 'download_files_by_url' para realizar o download de cada arquivo.
        """

        if type == 0:
            directory_path = "./dani/docs/empresa-priv/"
        elif type == 1:
            directory_path = "./dani/docs/adm-direta/"
        elif type == 2:
            directory_path = "./dani/docs/empresa-pub-e-mista/"


        for company, links in company_links.items():
            print(f"Company : | {company} |")
            print(f"Links: | {links} |")
            time.sleep(10) # [(－－)]..zzZ
            try:
            
                if len(links) == 1:
                    source = requests.get(links[0], headers=self.header, stream=True, verify=False, timeout=70)
                    if source.status_code != 200:
                        print(f"Falha em acessar o {links[0]}")
                    download_files_by_url(company=company, link=links[0], source=source, directory_path=directory_path)             
                else:
                    for i, link in enumerate(links):
                        source = requests.get(link, headers=self.header, stream=True, verify=False, timeout=70)
                        if source.status_code != 200:
                            print(f"Falha em acessar o {link}")
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
        output = f"{directory_path}{company}_Compliance.pdf"
        pdf = weasyprint.HTML(link).write_pdf()
        try:
            open(output, 'wb').write(pdf)
            return 0
        except Exception as err:
            print(err)
            raise
        
        
        # soup = BeautifulSoup(source.text, 'html.parser')
        # try:
        #     with open(f"{directory_path}{company}_Compliance.txt", 'wb') as file:
        #         file.write(soup.get_text('\n', '\n\n').encode())
        #         print(f"Sucecss...{company}")
        #         return 0
        # except Exception as err:
        #     print(err)
        #     raise

def search_companay_by_acronym(acronym: str, orgao_list: list) -> list:
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)

    payloads = [ f"https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=Pol%C3%ADtica+de+Integridade+P%C3%BAblica+{acronym}", f"https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=compliance+{acronym}" ]


    max_scrapes = 5
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

        driver.implicitly_wait(5)
        print(f"{acronym}: {len(orgao_list)}")
        if len(orgao_list) >= max_scrapes:
            break

    driver.quit()    
    return orgao_list

def filtrar_ementas(ementas: list) -> list:
    ementas_filtradas = []
    for ementa in ementas:
        if ("integridade" not in ementa.__ementa_titulo__.lower() and
            "compliance" not in ementa.__ementa_titulo__.lower() and
            "governança" not in ementa.__ementa_titulo__.lower()):
            continue
        ano = int(ementa.__data__.split('/')[2])
        if not ano >= 2022:
            continue
        ementas_filtradas.append(ementa)

    return ementas_filtradas

def company_acronym(company_name: str) -> str:
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
        'Secretaria De Estado De Segurança Pública': 'SSP/DF',
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
        'Corpo de Bombeiros': 'CBMDF',
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
        'Fundação de Apoio à Pesquisa do Distrito Federal': 'FAPDF',
        'Fundação de Ensino e Pesquisa em Ciências da Saúde': 'FEPECS',
        'Fundação Hemocentro de Brasília': 'FHB',
        'Fundação Jardim Zoológico de Brasília': 'FJZB',
        'Fundação Jardim Botânico': 'JBB',
        'Universidade do Distrito Federal': 'UNDF',
        'Escola de Governo': 'EGOV',
        'Junta Comercial, Industrial E Serviços Do Distrito Federal': 'JUCIS-DF',
        'Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal': 'SEPLAD',
    }


    acronym = company_name in acronyms
    if acronym:
        return acronyms[company_name]
    else:
        return ""
        
