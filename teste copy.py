from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import requests
import time
from bs4 import BeautifulSoup
import pandas as pd

import re
from unidecode import unidecode


def ler_dados_excel(nome_arquivo):
    df = pd.read_excel(nome_arquivo, header=None)

    header_row_index = df[df.iloc[:, 0] == 'Empresa/Órgão'].index[0]

    df = pd.read_excel(nome_arquivo, header=header_row_index)

    dados = {}

    for index, row in df.iterrows():
        orgao = company_acronym(row['Empresa/Órgão'])
        atas_cig = row['Atas do CIG']
        
        if 'sim' in str(atas_cig).lower():
            dados[orgao] = True
        elif 'não' in str(atas_cig).lower():
            dados[orgao] = False
        else: 
            dados[orgao] = False

    return dados

def comparar_mapas(mapa_dados, mapa_links):
    resultados = {}
    total = 0
    acertos = 0
    
    for orgao, tem_atas in mapa_dados.items():
        if tem_atas:
            total += 1
            if orgao in mapa_links and len(mapa_links[orgao]) > 0:
                # print(mapa_links[orgao])
                resultados[orgao] = True
                acertos += 1
            else:
                resultados[orgao] = False
        else:
            resultados[orgao] = None

    return resultados, acertos, total

def verifica_palavras_chaves(link, palavras_chave):
    palavras_chave = palavras_chave.split()
    for palavra_chave in palavras_chave:
        if len(palavra_chave) <= 2:
            continue
        palavra_chave = unidecode(palavra_chave)
        padrao = re.compile(palavra_chave, re.IGNORECASE)
        if padrao.search(link):
            return True
    return False

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

def load_orgaos_name(adm_direta: list, mista_publica: list) -> None:
    
    with open(list_orgaos_name, 'r') as file:
        is_mista = 0
        for item in file:
            if ("---" in item):
                is_mista = 1
                continue

            if (not is_mista):
                adm_direta.append(item.strip())
            else:
                mista_publica.append(item.strip())

def search_link_cig(acronym: str, orgao: str, param: str, link_base: str, header: dict) -> dict:
    orgao_name_params = [acronym + " df", orgao]

    for orgao_name_param in orgao_name_params:
        search_param = link_base + orgao_name_param + param
        print("Orgão: " + orgao_name_param)

        link_orgao_dict = {}
        source = requests.get(search_param, header, verify=False)

        if source.status_code != 200:
            print("Erro ao acessar a página")

        soup = BeautifulSoup(source.text, 'lxml')
        for g in soup.find_all('div',  {'class':'Gx5Zad'}):
            links = g.find_all('a')
            for link in links:

                link_addrs = str(link['href'])
                if ("comitê interno de governança" in link.get_text().lower() or "governança" in link.get_text().lower() or "atas" in link.get_text().lower()):
                    if (("comite" in link_addrs and "interno" in link_addrs and "governanca" in link_addrs and acronym.lower() in link_addrs) or
                        ("comite" in link_addrs and "interno" in link_addrs and "governanca" in link_addrs and verifica_palavras_chaves(link_addrs, orgao)) or
                        (("comite" in link_addrs or "interno" in link_addrs or "governanca" in link_addrs or "atas" in link_addrs or "cig" in link_addrs) and acronym.lower() in link_addrs) or
                        (("comite" in link_addrs or "interno" in link_addrs or "governanca" in link_addrs or "atas" in link_addrs or "cig" in link_addrs) and verifica_palavras_chaves(link_addrs, orgao))):
                        
                        link_orgao_dict.setdefault(acronym, []).append(link_addrs.split("&")[0])
                        # print("if 1: " + str(link_orgao_dict))
                        # print("\n")

                elif (("gestão" in link.get_text().lower() and "risco" in link.get_text().lower()) or 
                    ("gestão" in link.get_text().lower() and "governança" in link.get_text().lower())):
                    
                    if (acronym.lower() in link_addrs or verifica_palavras_chaves(link_addrs, orgao)):
                        link_orgao_dict.setdefault(acronym, []).append(link_addrs.split("&")[0])
                        # print("if 2: " + str(link_orgao_dict))
                        # print("\n")
                    
                # link_addrs = str(link['href'])
                # link_addrs = link_addrs.split("&")[0]
                # print(f"Título: {link.get_text()}, link: {link_addrs}")   
        if link_orgao_dict.get(acronym) != None:
            break
        

    return link_orgao_dict

def search_link_cig2(acronym: str, orgao: str, param: str, link_base: str, header: dict, link_orgao_dict: dict) -> dict:
    orgao_name_params = [acronym + " df", orgao]

    for orgao_name_param in orgao_name_params:
        search_param = link_base + orgao_name_param + param
        # print("Orgão: " + orgao_name_param)
        links_count = 0
        source = requests.get(search_param, header, verify=False)

        if source.status_code != 200:
            print("Erro ao acessar a página")

        soup = BeautifulSoup(source.text, 'lxml')
        for g in soup.find_all('div',  {'class':'Gx5Zad'}):
            links = g.find_all('a')
            for link in links:
                link_addrs = str(link['href'])
                
                if ("comitê interno de governança" in link.get_text().lower() or "governança" in link.get_text().lower() or "atas" in link.get_text().lower()):
                    if ((acronym.lower() in link_addrs and "df" in link_addrs) or (verifica_palavras_chaves(link_addrs, orgao) and "df" in link_addrs)):
                        link_orgao_dict.setdefault(acronym, []).append(link_addrs.split("&")[0])
                        # print("if 1: " + str(link_orgao_dict))
                        # print("\n")
                        links_count += 1
                        if links_count >= 6:
                            return link_orgao_dict

                elif (("gestão" in link.get_text().lower() and "risco" in link.get_text().lower()) or 
                    ("gestão" in link.get_text().lower() and "governança" in link.get_text().lower())):
                    
                    if ((acronym.lower() in link_addrs and "df" in link_addrs) or (verifica_palavras_chaves(link_addrs, orgao) and "df" in link_addrs)):
                        link_orgao_dict.setdefault(acronym, []).append(link_addrs.split("&")[0])
                        # print("if 2: " + str(link_orgao_dict))
                        # print("\n")
                        links_count += 1
                        if links_count >= 6:
                            return link_orgao_dict

        if link_orgao_dict.get(acronym) != None:
            break
        

    return link_orgao_dict


def filter_webpage_type1(url: str, orgao: str) -> bool:
    # Esse função vai realizar uma filtragem pela estrutura html do site
    # A filtragem vai servir para pegar somente os sites sejam nosso objetivo
    # Retornar webpage_atas_1 (para acessar as atas é preciso acessar uma página)
    # Faz a requisição para o site
    response = requests.get(url, verify=False)
    
    # Verifica se a requisição foi bem-sucedida
    if response.status_code == 200:
        # Analisa o conteúdo HTML da página
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Encontra todos os links na página
        links = soup.find_all('a')
        
        data_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
        ata_reuniao_pattern1 = re.compile(r'ata da \d+ª reunião')
        ata_reuniao_pattern2 = re.compile(r'ata \d+ª reunião')
        ata_reuniao_pattern3 = re.compile(r'\d+ª reunião')
        ata_reuniao_pattern4 = re.compile(r'ata da reunião extraordinária Nº \d')


        # Percorre os links encontrados
        for link in links:
            if ('ata' in link.get_text().lower() or 
                data_pattern.search(link.get_text()) or
                ata_reuniao_pattern1.search(link.get_text().lower()) or
                ata_reuniao_pattern2.search(link.get_text().lower()) or
                ata_reuniao_pattern3.search(link.get_text().lower()) or
                ata_reuniao_pattern4.search(link.get_text().lower())):
    
                print(link.get_text())
                print("Link:", link.get('href'))
                return True
            
        return False
    else:
        print("Falha ao carregar o site.")
        return False
    
def filter_webpage_type2(url: str, orgao: str) -> bool:
    # Esse função vai realizar uma filtragem pela estrutura html do site
    # A filtragem vai servir para pegar somente os sites sejam nosso objetivo
    # Retornar webpage_atas_2 (para acessar as atas é preciso acessar duas páginas)
    response = requests.get(url, verify=False)
    
    # Verifica se a requisição foi bem-sucedida
    if response.status_code == 200:
        # Analisa o conteúdo HTML da página
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Encontra todos os links na página
        links = soup.find_all('a')
        
        year_pattern = re.compile(r'\d{4}')

        # Percorre os links encontrados
        for link in links:        
            if ('ata' in link.get_text().lower() or 
                year_pattern.search(link.get_text())):

                print(link.get_text())
                print("Link:", link.get('href'))
                return True
            
        return False
    else:
        print("Falha ao carregar o site.")
        return False


excel = "FAPDF-Segmentoseitensintegridade(versão20.04.Completo)_corrigido.xlsx"
dados = ler_dados_excel(excel)

url_google = "https://google.com/search?q="
header= {'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}
param = " atas comitê interno de governança"

url = "http://www.ibram.df.gov.br/comite-interno-de-governanca/"
list_orgaos_name = "lara/docs/list_orgaos_name.txt"

adm_direta = []
mista_publica = []

load_orgaos_name(adm_direta, mista_publica)

dict_lol = {}
for orgao in adm_direta:
    search_link_cig2(company_acronym(orgao), orgao, param, url_google, header, dict_lol)
    time.sleep(7)

resul, acertos, total = comparar_mapas(dados, dict_lol)

print("Total: " + str(total))
print("Quantidade de Acertos: " + str(acertos))
print("Porcentagem de Acertos: " + str((acertos/total)*100))
for orgoao, tem_atas in resul.items():
    print(f"{orgoao}: {tem_atas}")

dict_1 = {}
dict_2 = {}
dict_excluidos = {}

for key, value in dict_lol.items():
    for link in value:
        if (filter_webpage_type1(link, key)):
            dict_1.setdefault(key, []).append(link)
        elif (filter_webpage_type2(link, key)):
            dict_2.setdefault(key, []).append(link)
        else:
            dict_excluidos.setdefault(key, []).append(link)

print("\n\n\n\n\n")
print(dict_lol)