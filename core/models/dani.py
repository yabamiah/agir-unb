###################################################################
## DANI - Desenvolvedor e Apresentador de Números e Indicadores ##
##################################################################

import os
from os import listdir
import sys
import io
from os.path import isfile, isdir, join

from unidecode import unidecode

import docx

import re

from core.utils.pdf_handler import PdfReader

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class Dani:
    __docs_path = "/home/yaba/agir-unb/data/dani/docs/input"
    __is_silga = False
    __all_orgaos = ""
    __orgao_name = ""
    __name_docs_read = []
    __read_ratio = 3
    __total_words_read = 0
    __keywords = {}
    __snippets = []
    __output_path = "dani/docs/output/resultados.txt"
    __docx_path = "/home/yaba/agir-unb/data/dani/docs/output/"

    def __init__(self) -> None:
        self.__total_words_read = 0
        self.__keywords = {}
        self.__saved_snippets = []
        self.docx_files = {}
        self.catch_param()

        if (self.__all_orgaos == 's'):
            self.read_all_docs()
        else:
            self.read_docs()

        # Não precisamos mais chamar save_and_close_docs aqui, pois já salvamos após cada leitura
        # Fechamos os documentos que ainda podem estar abertos
        self.close_all_docs()
        self.display_results()

        exit(0)

    def catch_param(self) -> None:
        self.__all_orgaos = input("Você deseja fazer uma pesquisa geral (s/n): ")

        if (self.__all_orgaos == 'n'):
            self.__orgao_name = input("Insira o nome do orgão: ")  # .title()
            acronym = company_acronym(self.__orgao_name.upper())
            if not acronym == "":
                self.__orgao_name = acronym.upper()
            else:
                self.__orgao_name = self.__orgao_name.upper()

            self.__read_ratio = int(input("Insira a quantidade de documentos que serão lidos: "))

        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        tratar___keywords = input("Insira as palavras-chaves(separadas por vírgula): ").strip()
        __keywords = [k.strip() for k in tratar___keywords.split(",") if k.strip()]

        for keyword in __keywords:
            self.__keywords.setdefault(keyword.lower(), 0)

    def read_docs(self) -> None:
        self.__docs_path = f"{self.__docs_path}/{self.__orgao_name}"
        if (self.__read_ratio == 0):
            self.__read_ratio = len(listdir(self.__docs_path))

        pdfs_read = 0
        for file in listdir(self.__docs_path):
            if isfile(join(self.__docs_path, file)):
                # O nome do órgão é obtido diretamente do nome do diretório
                orgao_name = os.path.basename(self.__docs_path)

                self.read_pdf_file(f"{self.__docs_path}/{file}", orgao_name)
                # Salva o resultado após cada leitura
                self.save_docs_for_current_orgao(orgao_name)

                self.__name_docs_read.append(file)
                pdfs_read += 1

                if pdfs_read >= self.__read_ratio:
                    break

    def read_all_docs(self) -> None:
        all_dir = [join(self.__docs_path, d) for d in listdir(self.__docs_path) if isdir(join(self.__docs_path, d))]
        self.__orgao_name = [os.path.basename(d) for d in all_dir]  # Usa o nome do diretório como nome do órgão

        file_atas_dict = {}

        all_files = []

        for dir in all_dir:
            orgao_atual = os.path.basename(dir)  # Obtém o nome do órgão do diretório de entrada
            for file in listdir(dir):
                if isfile(join(dir, file)):
                    self.__name_docs_read.append(file)
                    all_files.append(join(dir, file))
                    file_atas_dict.setdefault(orgao_atual, []).append(join(dir, file))

        for orgao, files in file_atas_dict.items():
            for file in files:
                self.read_pdf_file(file, orgao)
                # Salva o resultado após cada leitura
                self.save_docs_for_current_orgao(orgao)

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calcula a similaridade entre dois textos (0 a 1)."""
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(vectors[0], vectors[1])[0][0]

    def _is_duplicate_snippet(self, new_snippet: str, threshold: float = 0.8) -> bool:
        """Verifica se o snippet já existe (com base na similaridade)."""
        for saved_snippet in self.__saved_snippets:
            similarity = self._calculate_similarity(new_snippet, saved_snippet)
            if similarity >= threshold:
                return True
        return False

    def read_pdf_file(self, file_name: str, orgao_name: str) -> None:
        try:
            pdf_handler = PdfReader()
            pdf_pages_text = pdf_handler.pdf_to_string(file_name)
            words_read = pdf_handler.get_total_words_pdf()
            self.__total_words_read += words_read

            for page_text in pdf_pages_text:
                keyword_in_page = self.count_keywords(page_text)
                if keyword_in_page:
                    for keyword in self.__keywords:
                        if self.__keywords[keyword] != 0:
                            snippets = self.save_text_snippet(page_text, keyword)
                            if snippets is not None:
                                for snippet in snippets:
                                    if not self._is_duplicate_snippet(snippet):
                                        self.write_keyword_docx(snippet, keyword, orgao_name)
                                        self.__saved_snippets.append(snippet)  # Adiciona aos salvos
                                    else:
                                        print(f"[DEBUG] Snippet duplicado ignorado: {snippet[:50]}...")
        except Exception as e:
            print(f"Erro ao ler PDF {file_name}: {e}")

    def display_results(self) -> None:
        print("Os orgãos que tiveram suas atas do CIG lidos foram:")
        print(self.__orgao_name)

        print("Os documentos lidos foram:")
        print(self.__name_docs_read)

        print("Quantidade de vezes que cada palavra chave foi encontrada:")
        for keyword in self.__keywords:
            keyword_count = self.__keywords[keyword]
            percentage = (keyword_count / self.__total_words_read) * 100.0 if self.__total_words_read > 0 else 0
            print(f"{keyword} foi encontrada: {keyword_count}, que representa {percentage:.2f}%")

        print("No diretório \output você pode verificar os pedaços em que o texto foi encontrado")

    def save_text_snippet(self, page_text: str, keyword: str, window_size: int = 210) -> list:
        snipppets = []
        index = 0

        while index < len(page_text):
            found_index = page_text.find(keyword.lower(), index)

            if found_index == -1:
                break

            start_index = max(0, found_index - window_size)
            end_index = min(len(page_text), found_index + len(keyword) + window_size)

            snipppet = page_text[start_index:end_index]
            snipppet = '"' + snipppet + '"'
            snipppets.append(snipppet)
            index = found_index + len(keyword)

        return snipppets

    def create_keyword_docx(self, keyword: str, orgao_name: str) -> docx.Document:
        # Garantir que existe o diretório do órgão
        org_dir = join(self.__docx_path, orgao_name)
        os.makedirs(org_dir, exist_ok=True)

        new___docx_path = join(org_dir, f'output_{orgao_name}_{keyword}.docx')
        if isfile(new___docx_path):
            doc = docx.Document(new___docx_path)
        else:
            doc = docx.Document()
            doc.add_heading('Resultado Dani', 0)
            doc.add_heading(f'Análise atas CIG {orgao_name}', 2)
            doc.add_heading(f'Palavra-chave: {keyword}', 2)
        return doc

    def write_keyword_docx(self, snippet: str, keyword: str, orgao_name: str) -> None:
        key = (orgao_name, keyword)
        if key not in self.docx_files:
            self.docx_files[key] = self.create_keyword_docx(keyword, orgao_name)

        doc = self.docx_files[key]

        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1
        p.paragraph_format.space_after = 0

        valid_chars = ''.join(c for c in snippet if c.isprintable())
        snippet_fixed = ''.join(c if c.isprintable() else ' ' for c in snippet)

        p.add_run(snippet_fixed)
        p.add_run("\n")

    def save_docs_for_current_orgao(self, orgao_name: str) -> None:
        """Salva os documentos relacionados a um órgão específico"""
        # Garante que o diretório do órgão existe
        org_dir = join(self.__docx_path, orgao_name)
        os.makedirs(org_dir, exist_ok=True)

        # Filtra apenas os documentos do órgão atual
        docs_to_save = {k: v for k, v in self.docx_files.items() if k[0] == orgao_name}

        # Salva cada documento docx no diretório do órgão
        for (org, keyword), doc in docs_to_save.items():
            file_path = join(org_dir, f'output_{org}_{keyword}.docx')
            doc.save(file_path)
            print(f"Arquivo salvo: {file_path}")

    def close_all_docs(self) -> None:
        """Fecha todos os documentos docx que ainda estejam abertos na memória"""
        self.docx_files.clear()

    def save_and_close_docs(self) -> None:
        """Método mantido por compatibilidade, mas que agora apenas fecha os documentos"""
        self.close_all_docs()

    def count_keywords(self, text: str) -> bool:
        verif = False
        for keyword in self.__keywords:
            default = re.compile(r'\b' + re.escape(keyword) + r'\w*\b', re.IGNORECASE)
            keyword_count = len(default.findall(text))
            self.__keywords[keyword] += keyword_count

            if keyword_count > 0:
                verif = True

        return verif


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
        'Controladoria-Geral do DF': 'CGDF'
    }

    acronym = company_name in acronyms
    if acronym:
        return acronyms[company_name]
    else:
        return ""