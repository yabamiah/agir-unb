import requests
from bs4 import BeautifulSoup
import re

def verificar_site(url):
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
            # print(link)
            # Verifica se o link contém a palavra "Ata" ou uma data ou ".pdf" no URL
        
            if ('ata' in link.get_text().lower() or 
                data_pattern.search(link.get_text()) or
                ata_reuniao_pattern1.search(link.get_text().lower()) or
                ata_reuniao_pattern2.search(link.get_text().lower()) or
                ata_reuniao_pattern3.search(link.get_text().lower()) or
                ata_reuniao_pattern4.search(link.get_text().lower())):
    
                print(link.get_text())
                print("Link:", link.get('href'))
    
    else:
        print("Falha ao carregar o site.")


verificar_site('https://www.iprev.df.gov.br/atas-das-reunioes-cig-2024/')
