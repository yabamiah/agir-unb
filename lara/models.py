##############################################################
## LARA - Levantador Automático de Recursos Administrativos ##
##############################################################

import pandas as pd

from bs4 import BeautifulSoup

import requests
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# from selenium.webdriver.common.keys import Keys

import tabula

import os

from colorama import Fore, Style

class company:
    """
    Classe para representar um objeto de dados sobre as informações da company coletada

    Atributos:
    - nome_company (str): Nome da company.
    - orgao_contratante (str): Nome do Órgao Contratante..
    """

    def __init__(self):
        self.nome_company = ""
        self.orgao_contratante = ""  

class Lara:
    """
    Classe principal para o sistema AGIR.

    Atributos:
    - message (str): Mensagem de boas-vindas e informações sobre o sistema.
    - url (str): URL da página de licitações.
    - pdf (str): Caminho para o pdf no sistema
    - header (dict): Cabeçalho para evitar detecção como um script.
    - total (int): Total de alguma métrica não especificada.
    - licitacoes (list): Lista de instâncias da classe Licitacao.

    Métodos:
    - __init__(self, args: str): Inicializa uma instância da classe Lara.
    - execute_command(self, command: str): Executa um comando específico.
    - scrape_data(self): Realiza a raspagem de dados.
    - scrape_pdf_data(self): Realiza a raspagem de dados de um arquivo pdf.
    - data_to_excel(self): Converte dados para formato Excel.
    - display_data(self): Exibe dados.
    - trigger_dani(self): Ativa o bot Dani.
    """

    url = "https://google.com/search?q="
    pdf_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.pdf"
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
    total = 0
    companys = []
    args = ""
    message = f"""
            NOME:
                {Fore.BLUE}AGIR - Automação para uma Governança Inteligente e Responsável{Style.RESET_ALL}

            USO:
                agir [comando]

            VERSÃO:
                {Fore.BLUE}0.0.1{Style.RESET_ALL}
            
            COMANDOS:
                {Fore.BLUE}lara, l{Style.RESET_ALL}           Ativa o bot Lara que irá raspar as informações públicas do GDF acerca dos planos de integridade
                {Fore.BLUE}dani, d{Style.RESET_ALL}           Ativa o bot Dani que irá gerar o dashboard com a partir dos parâmetros de qualidade
                {Fore.BLUE}readpdf, r{Style.RESET_ALL}        Ativa o bot Lara que irá ler as informações do pdf
                {Fore.BLUE}datadisplay, dd{Style.RESET_ALL}   Exibir dados coletados em planilha
                {Fore.BLUE}help, h{Style.RESET_ALL}           Exibe uma lista de comandos
                {Fore.BLUE}quit, q{Style.RESET_ALL}           Sair do AGIR

            OPÇÕES GLOBAIS:
                help, h          Exibe comandos
                version, v       Imprime a versão
          """
    
    def __init__(self):
        print("Bem-vindo ao sistema AGIR!")
        print(self.message)
        self.args = input("Digite aqui: ") 
        self.execute_commands()
    
    def __help__(self):
        print(self.message)

    def __quit__(self):
        os._exit(0)

    def __version__(self):
        print(f"{Fore.BLUE}0.0.1{Style.RESET_ALL}")

    def execute_commands(self):
        commands = {
            'lara': self.scrape_web_data, 'l': self.scrape_web_data,
            'readpdf': self.scrape_pdf_data, 'r': self.scrape_pdf_data,
            'datadisplay': self.display_data, 'dd': self.display_data,
            'dani': self.trigger_dani, 'd': self.trigger_dani,
            'help': self.__help__, 'h': self.__help__,
            'quit': self.__quit__, 'q': self.__quit__,
            'version': self.__version__, 'v':self.__version__
        }

        if self.args in commands:
            commands[self.args]()
        else:
            print("Comando não reconhecido.")
            commands['help']()
    
    def scrape_pdf_data(self):
        
        data_frame_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.csv"
        if not os.path.exists(data_frame_path):
            tabula.convert_into(self.pdf_path, data_frame_path, output_format="csv", pages="all", lattice=True, stream=True)

            # Retirando a primeira linha do .csv que quebrava o arquivo
            with open(data_frame_path, 'r') as file:
                rows = file.readlines()

            rows = rows[1:]

            with open(data_frame_path, 'w') as file:
                file.writelines(rows)
        else:
            print("O arquivo já existe")

        data_frame = pd.read_csv(data_frame_path)
        data_frame = data_frame.fillna('0')
        qtd_rows = len(data_frame.index)

        ################### Extraindo companys ###################

        companys_data_frame_list = []
        for i in range(qtd_rows):
            companys_data_frame_list.append(data_frame.loc[[i], ['EMPRESA']]) 

        for i in range(len(companys_data_frame_list)):
            format_name = (str(companys_data_frame_list[i]))
            format_name = format_name.split("\n")[1]
            format_name = format_name.split(maxsplit=1)[1].strip()
            format_name = format_name.replace("LTDA", "").replace("S/A", "").replace("S.A", "").replace(r"\n", " ")
            if format_name == "EMPRESA": 
                continue
            if format_name not in self.companys:
                self.companys.append(format_name)

        ################### Extraindo orgãos contratantes ###################

        orgaos_data_frame_list = []
        for i in range(qtd_rows):
            orgaos_data_frame_list.append(data_frame.loc[[i], ['ÓRGÃO CONTRATANTE']])
        
        orgaos_list = []
        for i in range(len(orgaos_data_frame_list)):
            format_name = (str(orgaos_data_frame_list[i]))
            format_name = format_name.split("\n")[1]
            format_name = format_name.split(maxsplit=1)[1].strip()
            format_name = format_name.replace("LTDA", "").replace("S/A", "").replace("S.A", "").replace(r"\n", " ")
            if format_name not in orgaos_list:
                orgaos_list.append(format_name)

        print("As informações do PDF foram extraídas com sucesso...")

        self.scrape_web_data()

    def scrape_web_data(self):

        company_dict = {}
        for i, company in enumerate(self.companys, start=1):
            payload = company + " código de conduta ética e integridade"
        
            try:
                source = requests.get(self.url + payload, headers=self.header)
            except requests.exceptions.HTTPError as err:
                raise SystemExit(err)
    
            soup = BeautifulSoup(source.text, 'html.parser')
            print(f"# Empresa {i}: {company}")
            links = []
            company_format = company.lower()
            i += 1
            print(soup.prettify())
            for info in soup.find_all('a', attrs={"data-ved": "2ahUKEwjVmqieqsyDAxUxD7kGHTWtAzYQFnoECAkQAw"}):
                title_link = info.get_text('|').replace("|", " ", 1).split("|")[0].lower()
                print(f"assss")
                if company_format in title_link  and ("ética" in title_link or "compliance" in title_link or "integridade" in title_link):
                    print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                    links.append(info['href'])
                elif (company_format.split(" ")[0] in title_link and company_format.split(" ")[1] in title_link) and ("ética" in title_link or "compliance" in title_link or "integridade" in title_link):
                    print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                    links.append(info['href'])
                
                company_dict[company] = links

                if not company_dict[f'{company}']:
                    del company_dict[f'{company}']

        print(company_dict)
        self.donwload_company_compliance(company_dict)

    def donwload_company_compliance(self, companys_links: dict):
        # Se a company tiver só um link, trabalha com este
        # Senão, dar preferência para links com .pdf
        for company, links in companys_links.items():
            if len(links) == 1:
                source = requests.get(links[0], headers=self.header, stream=True)
                download_files_by_url(company=company, link=links[0], source=source)             
            else:
                for i, link in enumerate(links):
                    source = requests.get(link, headers=self.header, stream=True)
                    download_files_by_url(company=company+str(i), link=link, source=source)

    def display_data(self):
        print("Display data")

    def data_to_excel(self):
        print("Data to excel")

    def trigger_dani(self):
        print("Trigger dani")

def download_files_by_url(company: str, link: str, source: str) -> int:
    company = company.title().replace(" ", "")
    if "pdf" in link: 
        with open(f"../dani/docs/{company}_Compliance.pdf", 'a+') as file:
            file.write(source.content)
            return 0
    elif "docx" in link: 
        with open(f"../dani/docs/{company}_Compliance.docx", 'a+') as file:
            file.write(source.content)
            return 0
    else:
        soup = BeautifulSoup(source.text)
        with open(f"../dani/docs/{company}_Compliance.txt", "a+") as file:
            file.write(soup.get_text('\n', '\n\n'))
            return 0
