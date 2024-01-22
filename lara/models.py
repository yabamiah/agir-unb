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

from dani.models import Dani

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
    - pdf_path (str): Caminho para o arquivo PDF no sistema.
    - data_frame_path (str): Caminho para o arquivo CSV gerado a partir do PDF.
    - header (dict): Cabeçalho para evitar detecção como um script.
    - total (int): Total de alguma métrica não especificada.
    - companys (list): Lista de nomes de empresas extraídos.
    - orgaos (list): Lista de órgãos contratantes extraídos.
    - args (str): Argumentos fornecidos na inicialização.
    
    Métodos:
    - __init__(self): Inicializa uma instância da classe Lara.
    - __help__(self): Exibe uma mensagem de ajuda e lista de comandos disponíveis.
    - __quit__(self): Encerra a execução do AGIR.
    - __version__(self): Exibe a versão atual do AGIR.
    - execute_commands(self): Executa os comandos com base nos argumentos fornecidos.
    - scrape_web_data(self): Realiza a raspagem de dados da página de licitações.
    - scrape_pdf_data(self): Realiza a raspagem de dados de um arquivo PDF.
    - data_to_excel(self): Converte dados para formato Excel.
    - display_data(self): Exibe dados coletados.
    - trigger_dani(self): Ativa o bot Dani.
    """

    url = "https://google.com/search?q="
    pdf_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.pdf"
    data_frame_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.csv"
    header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}
    total = 0
    companys = []
    orgaos = [] 
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
    
    def scrape_pdf_data(self) -> list:
        """
        Extrai informações de um arquivo PDF e prepara os dados para posterior web scraping.

        - Verifica se o arquivo CSV já existe; se não, converte o PDF para CSV.
        - Remove a primeira linha do CSV, que pode estar quebrada após a conversão.
        - Lê o CSV em um DataFrame pandas e realiza manipulações nos dados.
        - Extrai informações relevantes (EMPRESA e ÓRGÃO CONTRATANTE) e as prepara para o web scraping.
        - Realiza algumas manipulações nos nomes das empresas e órgãos contratantes.
        - Armazena as informações em listas (companys e orgaos) para uso posterior.

        Atributos:
        - self.pdf_path (str): Caminho do arquivo PDF a ser extraído
        - self.data_frame_path (str): Caminho do arquivo excel a ser criado
        - self.companys (list): Lista de nomes de empresas extraídos do pdf.
        - self.orgaos (list): Lista de nomes de orgãos extraídos do pdf.

        Retorna Lista.

        Observações:
        - Certifique-se de ter as bibliotecas necessárias instaladas (os, pandas, tabula).
        - O caminho do arquivo CSV é definido em data_frame_path.
        """

        if not os.path.exists(self.data_frame_path):
            tabula.convert_into(self.pdf_path, self.data_frame_path, output_format="csv", pages="all", lattice=True, stream=True)

            # Retirando a primeira linha do .csv que quebrava o arquivo
            with open(self.data_frame_path, 'r') as file:
                rows = file.readlines()

            rows = rows[1:]

            with open(self.data_frame_path, 'w') as file:
                file.writelines(rows)
        else:
            print("O arquivo já existe")

        data_frame = pd.read_csv(self.data_frame_path)
        data_frame = data_frame.fillna('0')
        df_list = data_frame[['EMPRESA', 'ÓRGÃO CONTRATANTE']].to_dict('records')
        self.data_frame_dict = df_list

        for name in df_list:
            name['EMPRESA'] = name['EMPRESA'].replace("\n", " ").replace("LTDA", "").replace("S/A", "").replace("S.A", "").strip().title()
            if name['EMPRESA'] == "Empresa": 
                continue
            self.companys.append(name['EMPRESA'])

            name['ÓRGÃO CONTRATANTE'] = name['ÓRGÃO CONTRATANTE'].replace("\n", " ").replace("LTDA", "").replace("S/A", "").replace("S.A", "").strip().title()
            self.orgaos.append(name['ÓRGÃO CONTRATANTE'])

        print("As informações do PDF foram extraídas com sucesso...")
        print(self.orgaos)

        if (self.args == 'dani' or self.args == 'd'):
            return df_list
        
        self.scrape_web_data()

    def scrape_web_data(self):
        """
        Realiza a raspagem de dados das páginas da web relacionadas à integridade e ética de empresas.

        Itera sobre a lista de empresas (self.companys), realiza uma pesquisa na web para cada empresa,
        analisa os resultados da pesquisa e extrai os links relevantes relacionados a códigos de conduta ética e integridade.

        Atributos:
        - self.companys (list): Lista de nomes de empresas a serem pesquisados.
        - self.url (str): URL base para a pesquisa web.
        - self.header (dict): Cabeçalho para evitar detecção como um script.

        Método:
        - donwload_company_compliance(company_dict): Método para fazer download dos códigos de conduta com base nos links obtidos.

        Retorna None.

        Observações:
        - Usa a biblioteca 'requests' para enviar solicitações HTTP às páginas da web.
        - Utiliza a biblioteca 'BeautifulSoup' para analisar o HTML das páginas web.
        - Imprime informações sobre os links encontrados para cada empresa e armazena em um dicionário (company_dict).
        - Chama o método 'donwload_company_compliance' para fazer download dos códigos de conduta com base nos links obtidos.
        """

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
            #print(soup.prettify())
            for info in soup.find_all('a', attrs={"jsname": "UWckNb"}):
                title_link = info.get_text('|').replace("|", " ", 1).split("|")[0].lower()
                if company_format in title_link  and ("ética" in title_link or "compliance" in title_link or "integridade" in title_link):
                    print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                    links.append(info['href'])
                elif (company_format.split(" ")[0] in title_link and company_format.split(" ")[1] in title_link) and ("ética" in title_link or "compliance" in title_link or "integridade" in title_link):
                    print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                    links.append(info['href'])
                
                company_dict[company] = links

                if not company_dict[f'{company}']:
                    del company_dict[f'{company}']

        self.donwload_company_compliance(company_dict, 0)

        orgao_dict = {}
        for i, orgao in enumerate(self.orgaos, start=1):
            payload = orgao + " Política de Governança, Gestão de Riscos e Compliance"
        
            try:
                source = requests.get(self.url + payload, headers=self.header)
            except requests.exceptions.HTTPError as err:
                raise SystemExit(err)
    
            soup = BeautifulSoup(source.text, 'html.parser')
            print(f"# Orgão {i}: {orgao}")
            links = []
            orgao_format = orgao.lower()
            i += 1
            #print(soup.prettify())
            for info in soup.find_all('a', attrs={"jsname": "UWckNb"}):
                title_link = info.get_text('|').replace("|", " ", 1).split("|")[0].lower()
                if ("governança" in title_link or "compliance" in title_link or "integridade" in title_link or "riscos" in title_link):
                    print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                    links.append(info['href'])
                elif (orgao_format.split(" ")[0] in title_link and company_format.split(" ")[1] in title_link) and ("governança" in title_link or "compliance" in title_link or "integridade" in title_link):
                    print(f"- Found the URL: {info['href']}\n- Title: {title_link}")
                    links.append(info['href']) 
                
                orgao_dict[orgao] = links

                if not orgao_dict[f'{orgao}']:
                    del orgao_dict[f'{orgao}']

        self.donwload_company_compliance(orgao_dict, 1)

    def donwload_company_compliance(self, companys_links: dict, type: int) -> None:
        """
        Faz download dos códigos de conduta ética e integridade de empresas com base nos links fornecidos.

        Itera sobre um dicionário onde as chaves são nomes de empresas e os valores são listas de links relacionados.
        Para cada empresa, verifica a quantidade de links disponíveis:
        - Se houver apenas um link, realiza o download diretamente.
        - Se houver vários links, itera sobre eles e realiza o download individualmente.

        Atributos:
        - self.header (dict): Cabeçalho para evitar detecção como um script.

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
            if len(links) == 1:
                source = requests.get(links[0], headers=self.header, stream=True)
                download_files_by_url(company=company, link=links[0], source=source, directory_path=directory_path)             
            else:
                for i, link in enumerate(links):
                    source = requests.get(link, headers=self.header, stream=True, verify=False)
                    download_files_by_url(company=company+str(i), link=link, source=source, directory_path=directory_path)

        print("Documentos baixados com sucesso, iniciando a Dani...")

    def display_data(self):
        print("Display data")

    def data_to_excel(self):
        print("Data to excel")

    def trigger_dani(self) -> Dani:
        df_list = self.scrape_pdf_data()
        dani_bot = Dani(df_list)
        while 1:
            dani_bot.app.run()
        

def download_files_by_url(company: str, link: str, source: str, directory_path: str) -> int:
    """
    Realiza o download de arquivos a partir de uma URL e salva localmente.

    Verifica o tipo de arquivo com base na extensão do link e realiza o download para o diretório especificado.
    Os tipos de arquivo suportados são PDF, DOCX e outros (considerados como texto).

    Parâmetros:
    - company (str): Nome da empresa para compor o nome do arquivo.
    - link (str): URL do arquivo a ser baixado.
    - source (str): Conteúdo da resposta HTTP da URL.

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
        print(os.getcwd())

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