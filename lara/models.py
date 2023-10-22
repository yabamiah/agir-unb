# LARA - Levantador Automático de Recursos Administrativos
#

import pandas as pd
from bs4 import BeautifulSoup
import requests
import matplotlib

class Licitacao:
    """
    Classe para representar um banco de dados sobre as informações das licitações coletadas

    Atributos:
    - n_licitacao (str): Número de licitação.
    - modalidade (str): Modalidade de licitação.
    - situacao (str): Situação da licitação.
    - orgao (str): Órgão responsável pela licitação.
    - tipo (str): Tipo de licitação.
    - titulo (str): Título da licitação.
    - edital_url (str): URL do edital.
    """

    def __init__(self):
        self.n_licitacao = ""
        self.modalidade= ""  
        self.situacao= ""   
        self.orgao= ""
        self.tipo= ""
        self.titulo= ""
        self.edital_url= ""

class Lara:
    """
    Classe principal para o sistema AGIR.

    Atributos:
    - message (str): Mensagem de boas-vindas e informações sobre o sistema.
    - url (str): URL da página de licitações.
    - header (dict): Cabeçalho para evitar detecção como um script.
    - total (int): Total de alguma métrica não especificada.
    - licitacoes (list): Lista de instâncias da classe Licitacao.

    Métodos:
    - __init__(self, args: str): Inicializa uma instância da classe Lara.
    - scrape_data(self): Realiza a raspagem de dados.
    - data_to_excel(self): Converte dados para formato Excel.
    - display_data(self): Exibe dados.
    - trigger_dani(self): Ativa o bot Dani.
    - execute_command(self, command: str): Executa um comando específico.
    """

    message = """NOME:
                AGIR é um sistema de automação para uma Governança Inteligente e Responsável

            USO:
                agir [global options] command [command options] [arguments...]

            VERSÃO:
                0.0.1
            
            COMANDOS:
                lara, l             Ativa o bot Lara que irá raspar as informações públicas do GDF acerca das licitações
                dani, d             Ativa o bot Dani que irá gerar o dashboard com a partir dos argumentos de qualidade
                datadisplay, dd     Exibir dados coletados em planilha
                help, h             Exibe uma lista de comandos

            OPÇÕES GLOBAIS:
                --help, -h          Exibe ajuda
                --version, -v       Imprime a versão
          """
    url = "https://www.transparencia.df.gov.br/#/licitacoes-contratos/licitacoes"
    header = {'user-agent' : 'Mozilla/5.0'} # Header para a página não identificar que é um script
    total = 0
    licitacao = []

    def __init__(self, args: str):
        print("Bem-vindo ao sistema AGIR!")
        print(self.msg)
        input(args)
        self.execute_commands(args)

    def execute_commadns(self, command: str):
        commands = {
            'lara': self.scrape_data, 'l': self.scrape_data,
            'datadisplay': self.display_data, 'dd': self.display_data,
            'dani': self.trigger_dani, 'd': self.trigger_dani
        }

        if command in commands:
            commands[command]()
        else:
            print("Comando não reconhecido.")

    def scrape_data(self):
        print("Scrape data")

    def data_to_excel(self):
        print("Data to excel")

    def display_data(self):
        print("Display data")

    def trigger_dani(self):
        print("Trigger dani")
