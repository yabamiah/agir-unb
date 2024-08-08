# import requests
# from bs4 import BeautifulSoup
# import pandas as pd
# import re
# from unidecode import unidecode
import urllib3
import time

from core.models.lara import Lara

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Função que ler os dados de uma planilha excel e estabele quais órgãos possuem atas do cig


# def ler_dados_excel(nome_arquivo: str) -> dict[str, bool] | None:
#     """_summary_

#     Args:
#         nome_arquivo (str): _description_

#     Returns:
#         dict[str, bool] | None: _description_
#     """
#     df = pd.DataFrame()

#     try:
#         df = pd.read_excel(nome_arquivo, header=None)
#     except Exception as e:
#         print(e)
#         return None

#     header_row_index = df[df.iloc[:, 0] == 'Empresa/Órgão'].index[0]

#     df = pd.read_excel(nome_arquivo, header=header_row_index)

#     dados = {}

#     for _, row in df.iterrows():
#         orgao = company_acronym(row['Empresa/Órgão'])
#         atas_cig = row['Atas do CIG']

#         if 'sim' in str(atas_cig).lower():
#             dados[orgao] = True
#         elif 'não' in str(atas_cig).lower():
#             dados[orgao] = False
#         else:
#             dados[orgao] = False

#     return dados

# # Função que verificar se a Lara encontrou os links das atas do cig dos órgãos


# def comparar_mapas(mapa_dados, mapa_links) -> tuple[dict[str, bool], int, int]:
#     """_summary_

#     Args:
#         mapa_dados (_type_): _description_
#         mapa_links (_type_): _description_

#     Returns:
#         tuple[dict[str, bool], int, int]: _description_
#     """
#     resultados = {}
#     total = 0
#     acertos = 0
    
#     for orgao, tem_atas in mapa_dados.items():
#         if tem_atas:
#             total += 1
#             if orgao in mapa_links and len(mapa_links[orgao]) > 0:
#                 resultados[orgao] = True
#                 acertos += 1
#             else:
#                 resultados[orgao] = False
#         else:
#             resultados[orgao] = None
            
    
#     # for orgao, links in mapa_links.items():
#     #     if orgao not in mapa_dados.keys():
#     #         print(f"Este ogão não está na planilha: {orgao}")
#     #         print(f"Orgão links: {links}")
            
#     # return resultados, acertos, total

# # Função que verificar se o link passado possui as palavras-chaves


# def verifica_palavras_chaves(link, palavras_chave) -> bool:
#     palavras_chave = palavras_chave.split()

#     for palavra_chave in palavras_chave:
#         if len(palavra_chave) <= 2:
#             continue
#         palavra_chave = unidecode(palavra_chave)
#         padrao = re.compile(palavra_chave, re.IGNORECASE)
#         if padrao.search(link):
#             return True
#     return False


# def company_acronym(company_name: str) -> str:
#     """_summary_

#     Args:
#         company_name (str): _description_

#     Returns:
#         str: _description_
#     """
#     acronyms = {
#         'Secretaria De Estado Da Agricultura, Abastecimento E Desenvolvimento Rural': 'SEAGRI',
#         'Secretaria De Estado De Atendimento À Comunidade': 'SEAC',
#         'Casa Civil': 'CACI',
#         'Casa Militar': 'CM',
#         'Secretaria De Estado De Comunicação': 'SECOM',
#         'Secretaria De Estado De Cultura E Economia Criativa': 'SECEC',
#         'Secretaria De Estado De Ciência, Tecnologia E Inovação': 'SECTI',
#         'Secretaria De Desenvolvimento Social': 'SEDES',
#         'Secretaria De Estado De Educação': 'SEE',
#         'Secretaria De Estado De Esporte E Lazer Do Distrito Federal': 'SELDF',
#         'Secretaria De Estado De Economia': 'SEEC',
#         'Secretaria De Desenvolvimento Urbano E Habitação': 'SEDUH',
#         'Secretaria De Estado De Justiça E Cidadania': 'SEJUS',
#         'Secretaria De Estado Do Meio Ambiente E Proteção Animal': 'SEMA',
#         'Secretaria De Estado Da Mulher': 'SMDF',
#         'Secretaria De Estado De Obras E Infraestrutura': 'SODF',
#         'Secretaria De Estado De Família E Juventude': 'SEJUV',
#         'Secretaria De Estado De Projetos Especiais': 'SEPE',
#         'Secretaria De Estado De Relações Institucionais': 'SERINS',
#         'Secretaria De Estado De Saúde': 'SES',
#         'Secretaria De Estado De Segurança Pública': 'SSP',
#         'Secretaria De Estado De Desenvolvimento Econômico, Trabalho E Renda': 'SEDET',
#         'Secretaria De Estado De Transporte E Mobilidade': 'SEMOB',
#         'Secretaria De Estado De Turismo': 'SETUR',
#         'Secretaria De Estado De Governo': 'SEGOV',
#         'Secretaria De Estado De Proteção Da Ordem Urbanística – Df Legal': 'DF LEGAL',
#         'Secretaria De Estado De Administração Penitenciária – Seape': 'SEAPE',
#         'Secretaria Da Pessoa Com Deficiência Do Distrito Federal': 'SEPD',
#         'Secretaria De Estado De Assuntos Internacionais': 'SERINTER',
#         'Controladoria-Geral do DF': 'CGDF',
#         'Procuradoria Geral do DF': 'PGDF',
#         'Polícia Civil': 'PCDF',
#         'Polícia Militar': 'PMDF',
#         'Corpo de Bombeiros': 'CBM',
#         'Arquivo Público Do Distrito Federal': 'ARPDF',
#         'Agência Reguladora de Águas e Saneamento do DF': 'ADASA',
#         'Departamento de Estradas de Rodagem do DF': 'DER',
#         'Departamento de Trânsito do DF': 'DETRAN-DF',
#         'Instituto de Assistência à Saúde dos Servidores do DF': 'INAS',
#         'Instituto de Defesa do Consumidor do DF': 'PROCON-DF',
#         'Instituto de Previdência dos Servidores do DF': 'IPREV',
#         'Instituto Brasília Ambiental': 'IBRAM',
#         'Serviço de Limpeza Urbana do DF': 'SLU',
#         'Centrais de Abastecimento do Distrito Federal': 'CEASA',
#         'Companhia de Desenvolvimento Habitacional': 'CODHAB-DF',
#         'Companhia Imobiliária de Brasília': 'TERRACAP',
#         'Instituto de Pesquisa e Estatística do Distrito Federal': 'IPEDF',
#         'Companhia de Saneamento Ambiental do DF': 'CAESB',
#         'Companhia Urbanizadora da Nova Capital do Brasil': 'NOVACAP',
#         'Empresa de Assistência Técnica e Extensão Rural': 'EMATER',
#         'Companhia do Metropolitano do Distrito Federal': 'METRÔ-DF',
#         'Sociedade de Transportes Coletivos de Brasília': 'TCB',
#         'Banco de Brasília': 'BRB',
#         'Companhia Energética de Brasília': 'CEB',
#         'Fundação de Amparo ao Trabalhador Preso do Distrito Federal': 'FUNAP',
#         'Fundação de Apoio à Pesquisa do Distrito Federal': 'FAP',
#         'Fundação de Ensino e Pesquisa em Ciências da Saúde': 'FEPECS',
#         'Fundação Hemocentro de Brasília': 'FHB',
#         'Fundação Jardim Zoológico de Brasília': 'FJZB',
#         'Fundação Jardim Botânico': 'JBB',
#         'Universidade do Distrito Federal': 'UNDF',
#         'Escola de Governo': 'EGOV',
#         'Junta Comercial, Industrial E Serviços Do Distrito Federal': 'JUCIS-DF',
#         'Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal': 'SEPLAD',
#     }

#     company_name = company_name.strip()
#     acronym = company_name in acronyms
#     if acronym:
#         return acronyms[company_name]
#     else:
#         return f"Not found: {company_name}"


# def load_orgaos_name(adm_direta: list, mista_publica: list) -> int:
#     """_summary_

#     Args:
#         adm_direta (list): _description_
#         mista_publica (list): _description_

#     Returns:
#         int: _description_
#     """

#     try:
#         file = open(list_orgaos_name, 'r')
#     except Exception as e:
#         print(e)
#         return 1

#     is_mista = 0
#     for line in file:
#         if ("---" in line):
#             is_mista = 1
#             continue

#         if (not is_mista):
#             adm_direta.append(line.strip())
#         else:
#             mista_publica.append(line.strip())

#     file.close()

#     return 0


# def search_link_cig2(acronym: str, orgao: str, param: str, link_base: str, header: dict, limite: int) -> dict:
#     """_summary_

#     Args:
#         acronym (str): _description_
#         orgao (str): _description_
#         param (str): _description_
#         link_base (str): _description_
#         header (dict): _description_
#         limite (int): _description_

#     Returns:
#         dict: _description_
#     """
#     orgao_name_params = [acronym + " df", orgao]
#     link_orgao_dict = {}
#     try:
#         for orgao_name_param in orgao_name_params:
#             search_param = f"{link_base}{orgao_name_param}{param}"

#             source = requests.get(search_param, header, verify=False)

#             if source.status_code != 200:
#                 print("Erro ao acessar a página")
#                 continue

#             soup = BeautifulSoup(source.text, 'lxml')
#             links_count = 0

#             for g in soup.find_all('div',  {'class': 'Gx5Zad'}):
#                 links = g.find_all('a')
#                 links = links[:limite]

#                 for link in links:
#                     link_addrs = str(link['href'])
#                     link_text = link.get_text().lower()

#                     if (("comitê interno de governança" in link_text) or ("governança" in link_text) or (("atas" in link_text) and "cig" in link_text)):
#                         if (acronym.lower() in link_addrs and "df" in link_addrs) or ((verifica_palavras_chaves(link_addrs, orgao) and "df" in link_addrs)):
#                             if (link_addrs.split("&")[0] not in link_orgao_dict.get(acronym, [])):
#                                 link_orgao_dict.setdefault(acronym, []).append(
#                                     link_addrs.split("&")[0])
#                     elif (("gestão" in link_text and "risco" in link_text) or
#                           ("gestão" in link_text and "governança" in link_text)):
#                         if ((acronym.lower() in link_addrs and "df" in link_addrs) or (verifica_palavras_chaves(link_addrs, orgao) and "df" in link_addrs)):
#                             if (link_addrs.split("&")[0] not in link_orgao_dict.get(acronym, [])):
#                                 link_orgao_dict.setdefault(acronym, []).append(
#                                     link_addrs.split("&")[0])
#             links_count += 1
#             if links_count >= limite:
#                 return link_orgao_dict

#             if link_orgao_dict.get(acronym) != None:
#                 break

#     except requests.RequestException as e:
#         print(f"search_link_cig2. Erro na requisição HTTP: {e}")
#     except Exception as e:
#         print(f"search_link_cig2. Erro inesperado: {e}")

#     return link_orgao_dict


# # Verificar se é a página com os links para acessar as atas
# def filter_webpage_type1(url: str, orgao: str) -> tuple[bool, None] | tuple[bool, str]:
#     """_summary_

#     Args:
#         url (str): _description_
#         orgao (str): _description_

#     Returns:
#         tuple[bool, None] | tuple[bool, str]: _description_
#     """
#     # Esse função vai realizar uma filtragem pela estrutura html do site
#     # A filtragem vai servir para pegar somente os sites sejam nosso objetivo
#     # Retornar webpage_atas_1 (para acessar as atas é preciso acessar uma página)
#     # Faz a requisição para o site
#     try:
#         header = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}
#         response = requests.get(url, headers=header, verify=False, timeout=5)

#         data_pattern = re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4})|(\d{4})')
#         update_site_pattern = re.compile(
#             r'Atualizado em \d{1,2}/\d{1,2}/\d{2,4} às ([01]?[0-9]|2[0-3])h[0-5][0-9]', re.IGNORECASE)

#         ata_reuniao_patterns = [
#             re.compile(r'ata da \d+ª reunião', re.IGNORECASE),
#             re.compile(r'ata \d+ª reunião', re.IGNORECASE),
#             re.compile(r'\d+ª reunião', re.IGNORECASE),
#             re.compile(r'ata da reunião extraordinária Nº \d{1,2}', re.IGNORECASE),
#             re.compile(r'ata reunião ordinária Nº \d{1,2}', re.IGNORECASE),
#             re.compile(r'Ata de reunião \d{1,2}', re.IGNORECASE),
#             re.compile(r'atas das reuniões cig', re.IGNORECASE)

#         ]

#         if response.status_code == 200:
#             soup = BeautifulSoup(response.text, 'html.parser')

#             page_text = soup.get_text().lower()
#             match = update_site_pattern.search(page_text)

#             links = soup.find_all('a')

#             for link in links:
#                 link_text = link.get_text().lower()
#                 link_href = str(link.get('href')).lower()

#                 if (any(pattern.search(link_text) for pattern in ata_reuniao_patterns)):
#                     if ("reuniao" in link_href and "cig" in link_href and ".pdf" in link_href):
#                         if match:
#                             return True, match.group()
#                         return True, None
#                 elif (data_pattern.search(link_text)):
#                     if (("ata" in link_href and "cig" in link_href) and ".pdf" in link_href):
#                         if match:
#                             return True, match.group()
#                         return True, None

#             if match:
#                 return False, match.group()
#             return False, None

#         else:
#             print(f"Falha ao carregar o site: {url}")
#             return False, None
#     except requests.RequestException as e:
#         print(f"filter_webpage_type1. Erro na requisição HTTP: {e}")
#         return False, None

#     except Exception as e:
#         print(f"filter_webpage_type1. Erro inesperado: {e}")
#         return False, None

# # Verificar se um portal do comite de inteterno de governança


# def filter_webpage_type2(url: str, orgao: str) -> tuple[bool, bool, None] | tuple[bool, bool, str]:
#     """_summary_

#     Args:
#         url (str): _description_
#         orgao (str): _description_

#     Returns:
#         tuple[bool, bool, None] | tuple[bool, bool, str]: _description_
#     """
#     # Esse função vai realizar uma filtragem pela estrutura html do site
#     # A filtragem vai servir para pegar somente os sites sejam nosso objetivo
#     # Retornar webpage_atas_2 (para acessar as atas é preciso acessar duas páginas)
#     try:
#         header = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}
#         response = requests.get(url, headers=header, verify=False)
#         # Verifica se a requisição foi bem-sucedida
#         if response.status_code == 200:
#             # Analisa o conteúdo HTML da página
#             soup = BeautifulSoup(response.text, 'html.parser')

#             data_pattern = re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}')
#             year_pattern = re.compile(r'\d{4}')
            
#             update_site_pattern = re.compile(
#                 r'Atualizado em \d{1,2}/\d{1,2}/\d{2,4} às ([01]?[0-9]|2[0-3])h[0-5][0-9]', re.IGNORECASE)
#             decreto_pattern1 = re.compile(
#                 r"decreto\s+n[°º]\s*39\.736(?:,?\s*de\s*28\s*de\s*março\s*de\s*2019)?|decreto\s+n[°º]\s*39\.736/?2019", re.IGNORECASE)
#             decreto_pattern2 = re.compile(
#                 r"decreto\s+n[°º]\s*37\.297(?:,?\s*de\s*29\s*de\s*abril\s*de\s*2016)?|decreto\s+n[°º]\s*37\.297/?2016", re.IGNORECASE)

#             target_text1 = "comitê interno de governança".lower()
#             target_text1_1 = "comitê de governança e estratégia".lower()
#             target_text2 = "atas das reuniões".lower()
#             target_text2_1 = "atas de memórias de reuniões".lower()
#             target_text2_2 = "atas".lower()
#             target_text3 = "portaria".lower()

#             page_text = soup.get_text().lower()
#             match = update_site_pattern.search(page_text)

#             if (((decreto_pattern1.search(page_text) or decreto_pattern2.search(page_text)) and
#                 (target_text1 in page_text) or (target_text1_1 in page_text) or
#                 ((target_text3 in page_text) and (target_text1 in page_text)) or
#                 ((target_text3 in page_text) and (target_text1_1 in page_text)) or
#                     (target_text2 in page_text))):

#                 links = soup.find_all('a')

#                 for link in links:
#                     link_text = link.get_text().lower()
#                     link_href = str(link.get('href')).lower()

#                     if (target_text2 in link_text or target_text2_2 in link_text or data_pattern.search(str(link_text))):
#                         if match:
#                             return True, True, match.group()

#                         return True, True, None
#                     elif (year_pattern.search(str(link_text)) and ("atas" in str(link_href) or "cig" in str(link_href))):
#                         if match:
#                             return True, True, match.group()

#                         return True, True, None
#                 if match:
#                     return True, False, match.group()

#                 return True, False, None

#             elif ((target_text1 in page_text and target_text2 in page_text) or (target_text1_1 in page_text and target_text2 in page_text) or
#                     (target_text1 in page_text and target_text2_1) or (target_text1_1 in page_text and target_text2_1) or
#                     (target_text1 in page_text and target_text2_2) or (target_text1_1 in page_text and target_text2_2)):
            
#                 links = soup.find_all('a')
                
#                 for link in links:
#                     link_text = link.get_text().lower()
#                     link_href = str(link.get('href')).lower()
                    
#                     is_ata_cig = (verifica_palavras_chaves(link_href, "comite") and verifica_palavras_chaves(
#                         link_href, "interno") and verifica_palavras_chaves(link_href, "governanca"))
                    
#                     if (year_pattern.search(str(link_text)) and is_ata_cig) or (year_pattern.search(str(link_text)) and "cig" in link_text):
#                         if match:
#                             return True, True, match.group()

#                         return True, True, None
                    
#                     elif (data_pattern.search(str(link_text)) and is_ata_cig) or (data_pattern.search(str(link_text)) and "cig" in link_text):
#                         if match:
#                             return True, True, match.group()

#                         return True, True, None 
                    
#                 if match:
#                     return False, False, match.group()

#                 return False, False, None 
#             else:
#                 return False, False, None
#         else:
#             print(f"Falha ao carregar o site: {url}")
#             return False, False, None

#     except requests.RequestException as e:
#         print(f"filter_webpage_type2. Erro na requisção: {e}")
#         return False, False, None
#     except Exception as e:
#         print(f"filter_webpage_type2. Erro inesperado: {e}")
#         return False, False, None
    
lara = Lara()

excel = "FAPDF-Segmentoseitensintegridade(versão20.04.Completo)_corrigido(1).xlsx"
# dados = ler_dados_excel(excel)
dados = lara.read_excel_data(excel)
if dados == None:
    print(f"Erro ao ler o arquivo: {excel}")

url_google = "https://google.com/search?q="
header = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}

param = " atas comitê interno de governança"

url = "http://www.ibram.df.gov.br/comite-interno-de-governanca/"
list_orgaos_name = "data/lara/docs/list_orgaos_name.txt"

adm_direta = []
mista_publica = []

if lara.load_orgaos_name(adm_direta, mista_publica) == 1:
    print("Erro ao carregar os nomes dos órgões")    
# if load_orgaos_name(adm_direta, mista_publica) == 1:
#     print("Erro ao carregar os nomes dos órgões")

# orgao = ""
# for nome in adm_direta:
#     if "Instituto de Previdência dos Servidores do DF" == nome:
#         orgao = nome

dict_general = {}
for orgao in adm_direta:
    dict_general.update(lara.search_link_cig(lara.company_acronym(orgao), orgao,
                     param, url_google, header, 6))
    time.sleep(7)

resul, acertos, total = lara.compare_maps(dados, dict_general)
# resul, acertos, total = comparar_mapas(dados, dict_general)

print("Total: " + str(total))
print("Quantidade de Acertos: " + str(acertos))
print("Porcentagem de Acertos: " + str((acertos/total)*100))
for orgoao, tem_atas in resul.items():
    print(f"{orgoao}: {tem_atas}")

exit(0)

for orgao in adm_direta:
    dict_lol = search_link_cig2(company_acronym(orgao), orgao,
                                param, url_google, header, 6)
    time.sleep(7)
    for key, value in dict_lol.items():
        for link in value:
            link = link.split("=", 1)[1]

            link = "https://fap.df.gov.br/atas-cig-2022/"
            # ft1, _ = filter_webpage_type1(link, key)        
            ft2, tem_ata, data = filter_webpage_type2(link, key)
    
            # if (ft1):
            #     print(f"Página das atas: {link}")
            if (ft2):
                print(f"Portal CIG: {link}")
                if (tem_ata):
                    print("Portal CIG com atas acessíveis")
            else:
                print(f"Não é portal CIG: {link}")
            exit(0)
            # if (not ft1 and not ft2):
            #     print(f"Não é nenhum dos dois: {link}")

# for orgao in adm_direta:
#     dict_lol = search_link_cig2(company_acronym(orgao), orgao,
#                      param, url_google, header, 6)
#     time.sleep(7)

# print(dict_lol)
# resul, acertos, total = comparar_mapas(dados, dict_lol)

# print("Total: " + str(total))
# print("Quantidade de Acertos: " + str(acertos))
# print("Porcentagem de Acertos: " + str((acertos/total)*100))
# for orgoao, tem_atas in resul.items():
#     print(f"{orgoao}: {tem_atas}")

exit(0)
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


# Usar esse código depois
# source = requests.get(url)

# soup = BeautifulSoup(source.text, 'html.parser')

# links_ata_por_ano = []
#
# for link in soup.find_all('a'):
#     if ("atas" in str(link.get('href')) and "reunioes" in str(link.get('href'))):
#         links_ata_por_ano.append(link.get('href'))

# for links in links_ata_por_ano:
#     source = requests.get(links)
#     soup = BeautifulSoup(source.text, 'html.parser')

#     for link in soup.find_all('a'):
#         if ("facebook" in str(link.get('href')).lower() or "twitter" in str(link.get('href')).lower()):
#             continue

#         if ("ata" in str(link.get('href')).lower() or (".pdf" in str(link.get('href')).lower()) or "reuniao" in str(link.get('href')).lower()):
#             print(link.get('href'))


# class Ementa:
#     def __init__(self, orgao_name: str, ementa_titulo: str, data: str, link_arquivo: str):
#         self.__orgao_name__ = orgao_name
#         self.__ementa_titulo__ = ementa_titulo
#         self.__data__ = data
#         self.__link_arquivo__ = link_arquivo

#     def set_ementa_titulo(self, ementa_titulo: str):
#         self.__ementa_titulo__ = ementa_titulo

#     def set_data(self, data: str):
#         self.__data__ = data

#     def set_link_arquito(self, link_arquivo: str):
#         self.__link_arquivo__ = link_arquivo

#     def set_orgao_name(self, orgao_name: str):
#         self.__orgao_name__ = orgao_name

#     def __repr__(self) -> str:
#         return f"Orgão: {self.__orgao_name__}\nTítulo: {self.__ementa_titulo__}\nData: {self.__data__}\nLinks: {self.__link_arquivo__}\n"

# # Função para encontrar a sigla do orgão do distrito federal


# # Função para raspar as informações das ementas: título, data e link da ementa
# def search_companay_by_acronym(acronym: str, orgao_list: list) -> list:
#     options = webdriver.FirefoxOptions()
#     options.add_argument("-headless")
#     driver = webdriver.Firefox(options=options)
#     print(acronym)
#     driver.get(f"https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=Pol%C3%ADtica+de+Integridade+P%C3%BAblica+{acronym}")

#     quadros = driver.find_elements(By.CSS_SELECTOR, 'div.column.w-90-pc.text-justify.ds_ementa')
#     quadros = [quadro.text for quadro in quadros]
#     orgao_list.append(quadros)

#     datas = driver.find_elements(By.CSS_SELECTOR, 'span.dt_assinatura.dt_assinatura_text')
#     datas = [str(data.text).split()[0] for data in datas]
#     orgao_list.append(datas)

#     links_arquivos = driver.find_elements(By.CLASS_NAME, 'baixarArquivo')
#     links_arquivos = [link.get_attribute("href") for link in links_arquivos]
#     orgao_list.append(links_arquivos)


#     driver.implicitly_wait(100)
#     driver.quit()
#     return orgao_list

# def filtrar_ementas(ementas: list) -> list:
#     ementas_filtradas = []
#     print(ementas)
#     for ementa in ementas:
#         if ("Política de Integridade Pública" not in ementa.__ementa_titulo__ and "Política de Gestão de Riscos" not in ementa.__ementa_titulo__):
#             continue
#         ano = int(ementa.__data__.split('/')[2])
#         if not ano >= 2022:
#             continue
#         ementas_filtradas.append(ementa)

#     return ementas_filtradas

# # Criando um exemplo de lista de orgãos
# orgaos = [ ["Secretaria De Estado De Educação Do Distrito Federal"], ["Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal"], ["Instituto De Assistência À Saúde Dos Servidores Do Distrito Federal"] ]
# # Lista que vai conter todos os objetos Ementa
# ementa_objs = []

# # Raspa as informações da web e vai criar uma lista encadeada das informações das ementas de cada orgão
# for orgao_list in orgaos:
#     acronym = company_acronym(orgao_list[0])
#     search_companay_by_acronym(acronym=acronym, orgao_list=orgao_list)
#     # driver.get("https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=Pol%C3%ADtica+de+Integridade+P%C3%BAblica+{acronym}")

#     # quadros = driver.find_elements(By.CSS_SELECTOR, 'div.column.w-90-pc.text-justify.ds_ementa')
#     # orgao_list.append(quadros
#     #                   )
#     # datas = driver.find_elements(By.CSS_SELECTOR, 'span.dt_assinatura.dt_assinatura_text')
#     # orgao_list.append(datas)

#     # links_arquivos = driver.find_elements(By.CLASS_NAME, 'baixarArquivo')
#     # orgao_list.append(links_arquivos)

# print("---------------------\n\n")

# # Instâncianeo os objetos com as informações coletadas e armazenadas na orgao
# for orgao_list in orgaos:
#     for i in range(len(orgao_list)):
#         for j in range(len(orgao_list[1])):
#             ementa_objs.append(Ementa( orgao_list[0], orgao_list[1][j], orgao_list[2][j], orgao_list[3][j] ))

# ementas = filtrar_ementas(ementa_objs)
# company_dict = {}
# for ementa in ementas:
#     company_dict.setdefault(ementa.__orgao_name__, []).append(ementa.__link_arquivo__)


# link = company_dict['Secretaria De Estado De Educação Do Distrito Federal'][0]
# source = requests.get(link, stream=True)
# soup = BeautifulSoup(source.text, 'html.parser')

# with open("ementa_teste.txt", 'wb') as file:
#     file.write(soup.get_text('\n', '\n').encode())

# print(company_dict)
