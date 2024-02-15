from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

import requests

from bs4 import BeautifulSoup

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
    
# Função para encontrar a sigla do orgão do distrito federal
def company_acronym(company_name: str) -> str:
    acronyms = {
        'Secretaria De Estado De Educação Do Distrito Federal': 'see',
        'Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal': 'seplad',
        'Instituto De Assistência À Saúde Dos Servidores Do Distrito Federal': 'inas',
        'Secretaria De Estado De Obras E Infraestrutura Do Distrito Federal': 'sodf',
        'Companhia Imobiliária De Brasília' : 'terracap',
        'Companhia De Saneamento Ambiental Do Distrito Federal' : 'caesb',
        'Secretaria De Estado De Economia Do Distrito Federal' : 'seec',
        'Secretaria De Estado De Justiça E Cidadania Do Distrito Federal' : 'sejus',
        'Companhia Urbanizadora Da Nova Capital Do Brasil' : 'novacap',
        'Departamento De Estradas De Rodagem Do Distrito Federal' : 'der',
        'Corpo De Bombeiros Militar Do Distrito Federal' : 'cbmdf',
        'Polícia Civil Do Distrito Federal' : 'pcdf',
        'Banco De Brasília' : 'brb',
        'Companhia Do Metropolitano Do Distrito Federal' : 'metrô-df',
        'Instituto De Pesquisa E Estatística Do Distrito Federal' : 'ipedf',
        'Serviço De Limpeza Urbana' : 'slu',
    }

    acronym = company_name in acronyms
    if acronym:
        return acronyms[company_name]
    else:
        return ""
    
# Função para raspar as informações das ementas: título, data e link da ementa
def search_companay_by_acronym(acronym: str, orgao_list: list) -> list:
    options = webdriver.FirefoxOptions()
    options.add_argument("-headless")
    driver = webdriver.Firefox(options=options)
    print(acronym)
    driver.get(f"https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=Pol%C3%ADtica+de+Integridade+P%C3%BAblica+{acronym}")

    quadros = driver.find_elements(By.CSS_SELECTOR, 'div.column.w-90-pc.text-justify.ds_ementa')
    quadros = [quadro.text for quadro in quadros]
    orgao_list.append(quadros)

    datas = driver.find_elements(By.CSS_SELECTOR, 'span.dt_assinatura.dt_assinatura_text')
    datas = [str(data.text).split()[0] for data in datas]
    orgao_list.append(datas)

    links_arquivos = driver.find_elements(By.CLASS_NAME, 'baixarArquivo')
    links_arquivos = [link.get_attribute("href") for link in links_arquivos]
    orgao_list.append(links_arquivos)


    driver.implicitly_wait(100)
    driver.quit()
    return orgao_list

def filtrar_ementas(ementas: list) -> list:
    ementas_filtradas = []
    print(ementas)
    for ementa in ementas:
        if ("Política de Integridade Pública" not in ementa.__ementa_titulo__ and "Política de Gestão de Riscos" not in ementa.__ementa_titulo__):
            continue
        ano = int(ementa.__data__.split('/')[2])
        if not ano >= 2022:
            continue
        ementas_filtradas.append(ementa)

    return ementas_filtradas

# Criando um exemplo de lista de orgãos
orgaos = [ ["Secretaria De Estado De Educação Do Distrito Federal"], ["Secretaria De Estado De Planejamento, Orçamento E Administração Do Distrito Federal"], ["Instituto De Assistência À Saúde Dos Servidores Do Distrito Federal"] ]
# Lista que vai conter todos os objetos Ementa
ementa_objs = []

# Raspa as informações da web e vai criar uma lista encadeada das informações das ementas de cada orgão
for orgao_list in orgaos:
    acronym = company_acronym(orgao_list[0])
    search_companay_by_acronym(acronym=acronym, orgao_list=orgao_list)
    # driver.get("https://www.sinj.df.gov.br/sinj/ResultadoDePesquisa?tipo_pesquisa=geral&all=Pol%C3%ADtica+de+Integridade+P%C3%BAblica+{acronym}")

    # quadros = driver.find_elements(By.CSS_SELECTOR, 'div.column.w-90-pc.text-justify.ds_ementa')
    # orgao_list.append(quadros
    #                   )
    # datas = driver.find_elements(By.CSS_SELECTOR, 'span.dt_assinatura.dt_assinatura_text')
    # orgao_list.append(datas)

    # links_arquivos = driver.find_elements(By.CLASS_NAME, 'baixarArquivo')
    # orgao_list.append(links_arquivos)

print("---------------------\n\n")

# Instâncianeo os objetos com as informações coletadas e armazenadas na orgao
for orgao_list in orgaos:
    for i in range(len(orgao_list)):
        for j in range(len(orgao_list[1])):
            ementa_objs.append(Ementa( orgao_list[0], orgao_list[1][j], orgao_list[2][j], orgao_list[3][j] ))

ementas = filtrar_ementas(ementa_objs)
company_dict = {}
for ementa in ementas:
    company_dict.setdefault(ementa.__orgao_name__, []).append(ementa.__link_arquivo__)


link = company_dict['Secretaria De Estado De Educação Do Distrito Federal'][0]
source = requests.get(link, stream=True)
soup = BeautifulSoup(source.text, 'html.parser')

with open("ementa_teste.txt", 'wb') as file:
    file.write(soup.get_text('\n', '\n').encode())

print(company_dict)    
