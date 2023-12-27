##############################################################
## LARA - Levantador Automático de Recursos Administrativos ##
##############################################################

import pandas as pd

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By

import tabula

import os
import math

from colorama import Fore, Style

class Empresa:
    """
    Classe para representar um banco de dados sobre as informações da Empresa coletada

    Atributos:
    - nome_empresa (str): Nome da Empresa.
    - orgao_contratante (str): Nome do Órgao Contratante.
    - orgao (str): Órgão responsável pela licitação.
    - cnpj (str): Valor do CNPJ da empresa.
    - data_prog (str): Data de Apresentação do Programa.
    - data_aval (str): Data da avaliação
    """

    def __init__(self):
        self.nome_empresa = ""
        self.orgao_contratante = ""  
        self.cnpj = ""
        self.data_prog = ""
        self.data_aval = ""

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

    url = "https://www.cg.df.gov.br/programa-de-integridade/"
    pdf_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.pdf"
    header = {'user-agent' : 'Mozilla/5.0'}
    total = 0
    empresas = []
    args = ""
    message = f"""
            NOME:
                {Fore.BLUE}AGIR - Automação para uma Governança Inteligente e Responsável{Style.RESET_ALL}

            USO:
                agir [global options] command [command options] [arguments...]

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
                --help, -h          Exibe ajuda
                --version, -v       Imprime a versão
          """
    
    def __init__(self):
        print("Bem-vindo ao sistema AGIR!")
        print(self.message)
        self.args = input("Digite aqui: ") 
        self.execute_commands(self.args)
    
    def __help__(self):
        print(self.message)

    def __quit__(self):
        os._exit(0)

    def execute_commands(self, command: str):
        commands = {
            'lara': self.scrape_data, 'l': self.scrape_data,
            'readpdf': self.scrape_pdf_data, 'r': self.scrape_pdf_data,
            'datadisplay': self.display_data, 'dd': self.display_data,
            'dani': self.trigger_dani, 'd': self.trigger_dani,
            'help': self.__help__, 'h': self.__help__,
            'quit': self.__quit__, 'q': self.__quit__
        }

        if command in commands:
            commands[command]()
        else:
            print("Comando não reconhecido.")
            commands['help']()

    def scrape_pdf_data(self):
        print("Scrape pdf data")

        # Gerando o arquivo .csv   
        data_frama_path = "lara/docs/Empresas_Programa_Integridade_2023_05.10.2023.csv"
        if not os.path.exists(data_frama_path):
            tabula.convert_into(self.pdf_path, data_frama_path, output_format="csv", pages="all")
        else:
            print("The file already exists")

        data_frame = pd.read_csv(data_frama_path)
        data_frame = data_frame.fillna('0')

        qtd_rows = len(data_frame.index)

        empresas_data_frame_list = []
        for i in range(qtd_rows):
            empresas_data_frame_list.append(data_frame.loc[[i], ['Cadastro de Empresas que adotam Programa de Integridade']]) 

        empresas_list = []
        for i in range(len(empresas_data_frame_list)):
            formata_nome = (str(empresas_data_frame_list[i]))
            formata_nome = formata_nome.split("\n")[1]
            formata_nome = formata_nome.split(maxsplit=1)[1].strip()
            if formata_nome != '0':
                empresas_list.append(formata_nome)
                print(formata_nome)

    def scrape_data(self):
        print("Scrape data")
        browser_driver = webdriver.Firefox()
        browser_driver.get(self.url)
        soup = BeautifulSoup(browser_driver.page_source, 'html.parser')

        # <-----------------> Procurando o botão de pesquisa <-----------------> #
        search_button = browser_driver.find_element(By.XPATH, "/html/body/main/section[2]/div/div[1]/form/div[8]/input")
        search_button.click()

        # <-----------------> Iterando pelas tabela de licitações para coletar a quantidade de licitações que há <----------------->
        rows_qtd = 0
        bidding_table = browser_driver.find_element(By.ID, 'etable')
        for row in bidding_table.find_elements(By.CSS_SELECTOR, 'tr'):
            rows_qtd = rows_qtd + 1
        
        # <-----------------> Criando uma lista para mepear as licitações em andamento <----------------->
        rows_list = list((range(rows_qtd)))
        print(rows_qtd)
        for i in range(rows_qtd):
            rows_list[i] = 0

        # <-----------------> Mapeando a lista <----------------->
        count = 0
        for row in bidding_table.find_elements(By.CSS_SELECTOR, 'tr'):
            count = count + 1
            for cell in row.find_elements(By.TAG_NAME, 'TD'):
                if (cell.find_elements(By.CLASS_NAME, "icon-hammer2")):
                    span_elements = cell.find_elements(By.CLASS_NAME, "icon-hammer2")
                    for span in span_elements:
                        if (not span.get_attribute("disabled")):
                            rows_list[count-1] = 1

        print(rows_list)

        links = []
        count = 0
        for row in bidding_table.find_elements(By.CSS_SELECTOR, 'tr'):
            count = count + 1
            for cell in row.find_elements(By.TAG_NAME, 'TD'):
                if (rows_list[count-1] == 1):
                    print(cell.find_elements(By.XPATH, "/html/body/main/section[2]/div/div[2]/div/div/div/table/tbody/tr[8]/td[1]/a"))
        

    def data_to_excel(self):
        print("Data to excel")

    def display_data(self):
        print("Display data")

    def trigger_dani(self):
        print("Trigger dani")
