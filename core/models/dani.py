###################################################################
## DANI - Desenvolvedor e Apresentador de Números e Indicadores ##
##################################################################
import os
from os import listdir
from os.path import isfile, isdir, join
import re
import sys
import io

import docx

from core.utils.pdf_handler import PdfReader

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from loguru import logger
from typing import List, Dict

from core.services.aws_service import S3Service

class Dani:
    """
    DANI - Desenvolvedor e Apresentador de Números e Indicadores
    Classe para leitura, análise e extração de informações de documentos PDF e DOCX.
    """
    def __init__(self,
                 docs_path: str = None,
                 output_path: str = None,
                 docx_path: str = None):

        base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

        self.s3_service = S3Service(logger=logger)
        self.docs_path = docs_path or os.path.join(base_dir, 'data', 'dani', 'docs', 'input')

        if not os.path.exists(self.docs_path):
            os.makedirs(self.docs_path)

        if len(os.listdir(self.docs_path)) == 0:
            diretorios = self.s3_service.listar_diretorios(bucket='agir-bucket', prefixo='dani-docs/')
            if not diretorios:
                logger.warning(f"Não foi encontrar os diretorios na S3 para {self.docs_path}")
                exit(0)

            for diretorio in diretorios:
                sucesso = self.s3_service.download_object_by_directory(
                    bucket='agir-bucket',
                    directory='dani-docs/',
                    file_path=os.path.join(self.docs_path, diretorio))
                if not sucesso:
                    logger.warning(f"Não foi possível baixar os arquivos do bucket da S3")
                    exit(0)

        self.output_path = output_path or os.path.join(base_dir, 'data', 'dani', 'docs', 'output', 'resultados.txt')
        self.docx_path = docx_path or os.path.join(base_dir, 'data', 'dani', 'docs', 'output')

        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        os.makedirs(self.docx_path, exist_ok=True)
        
        self.orgao_name = ""
        self.all_orgaos = False
        self.read_ratio = 3
        self.total_words_read = 0
        self.keywords: Dict[str, int] = {}
        self.saved_snippets: List[str] = []
        self.name_docs_read: List[str] = []
        self.docx_files = {}
        self.file_atas_dict = {}
        self.logger = logger
        self._setup_logger()

    def _setup_logger(self):
        self.logger.add("dani_logs.log", rotation="1 MB", retention="7 days", level="INFO", encoding="utf-8")
        self.logger.info("🚀 Iniciando DANI...")

    def _carregar_pelo_terminal(self):
        """Função interna para carregar keywords digitadas no terminal."""
        print("-" * 50)
        tratar_keywords = input("Digite as palavras-chave separadas por vírgula: ").strip()

        return [k.strip() for k in tratar_keywords.split(',') if k.strip()]

    def _carregar_por_arquivo(self):
        """Função interna para carregar keywords de um arquivo .txt."""
        print("-" * 50)
        caminho_do_arquivo = input("Digite o caminho para o arquivo .txt com as palavras-chave: ").strip()

        try:
            with open(caminho_do_arquivo, 'r', encoding='utf-8') as arquivo:
                return [linha.strip() for linha in arquivo if linha.strip()]
        except FileNotFoundError:
            print(f"🚨 Erro: O arquivo '{caminho_do_arquivo}' não foi encontrado.")
            return []  # Retorna uma lista vazia em caso de erro
        except Exception as e:
            print(f"🚨 Ocorreu um erro inesperado ao ler o arquivo: {e}")
            return []

    def obter_keywords(self):
        """
        Função principal que oferece ao usuário a escolha de como
        fornecer as palavras-chave.
        """
        keywords_carregadas = []
        while True:
            print("\nComo você deseja fornecer as palavras-chave?")
            print("1 - Digitar diretamente no terminal")
            print("2 - Fornecer um caminho de arquivo (.txt)")

            escolha = input("Digite sua escolha (1 ou 2): ").strip()

            if escolha == '1':
                keywords_carregadas = self._carregar_pelo_terminal()
                break
            elif escolha == '2':
                keywords_carregadas = self._carregar_por_arquivo()
                break
            else:
                print("🚨 Escolha inválida. Por favor, digite 1 ou 2.")

        if keywords_carregadas:
            self.keywords = {k.lower(): 0 for k in keywords_carregadas}
            print("\n✅ Palavras-chave carregadas com sucesso!")
            print(f"   Keywords: {list(self.keywords.keys())}")
        else:
            print("\n⚠️ Nenhuma palavra-chave foi carregada.")
            self.keywords = {}

    def run(self):
        """Método principal para execução da análise"""

        self.catch_param()
        if self.all_orgaos:
            self.read_all_docs()
        else:
            self.read_docs()
        self.upload_docx_s3()
        self.close_all_docs()
        self.display_results()

    def catch_param(self) -> None:
        """Coleta parâmetros do usuário para a análise"""

        all_orgaos_input = input("Você deseja fazer uma pesquisa geral (s/n): ").strip().lower()
        self.all_orgaos = (all_orgaos_input == 's')

        if not self.all_orgaos:
            self.orgao_name = input("Insira o nome do orgão: ").strip()
            acronym = company_acronym(self.orgao_name.upper())
            self.orgao_name = acronym if acronym else self.orgao_name.upper()
            self.read_ratio = int(input("Insira a quantidade de documentos que serão lidos: "))

        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        self.obter_keywords()
        self.logger.info(f"Palavras-chave: {list(self.keywords.keys())}")

    def read_docs(self) -> None:
        """Lê documentos de um órgão específico"""

        docs_path = os.path.join(self.docs_path, self.orgao_name)
        if self.read_ratio == 0:
            self.read_ratio = len(listdir(docs_path))
        pdfs_read = 0
        for file in listdir(docs_path):
            if isfile(join(docs_path, file)):
                self.read_pdf_file(join(docs_path, file), self.orgao_name)
                self.save_docs_for_current_orgao(self.orgao_name)
                self.name_docs_read.append(file)
                pdfs_read += 1
                if pdfs_read >= self.read_ratio:
                    break

    def read_all_docs(self) -> None:
        """Lê documentos de todos os órgãos disponíveis"""

        all_dir = [join(self.docs_path, d) for d in listdir(self.docs_path) if isdir(join(self.docs_path, d))]
        read_orgaos = [os.path.basename(d) for d in listdir(self.docx_path) if isdir(join(self.docx_path, d))]
        orgaos_to_read = [orgao for orgao in all_dir if os.path.basename(orgao) not in read_orgaos]
        self.logger.info(f"Órgãos a serem lidos: {orgaos_to_read}")
        for dir in orgaos_to_read:
            orgao_atual = os.path.basename(dir)
            for file in listdir(dir):
                if isfile(join(dir, file)):
                    self.name_docs_read.append(file)
                    self.read_pdf_file(join(dir, file), orgao_atual)
                    self.save_docs_for_current_orgao(orgao_atual)

    def read_pdf_file(self, file_name: str, orgao_name: str) -> None:
        """Lê e processa um arquivo PDF"""

        try:
            pdf_handler = PdfReader()
            pdf_pages_text = pdf_handler.pdf_to_string(file_name)
            words_read = pdf_handler.get_total_words_pdf()
            self.total_words_read += words_read
            for page_text in pdf_pages_text:
                if self.count_keywords(page_text):
                    for keyword in self.keywords:
                        if self.keywords[keyword] != 0:
                            snippets = self.save_text_snippet(page_text, keyword)
                            if snippets is not None:
                                for snippet in snippets:
                                    if not self._is_duplicate_snippet(snippet):
                                        self.write_keyword_docx(snippet, keyword, orgao_name)
                                        self.saved_snippets.append(snippet)
                                    else:
                                        self.logger.debug(f"Snippet duplicado ignorado: {snippet[:50]}...")
        except Exception as e:
            self.logger.error(f"Erro ao ler PDF {file_name}: {e}")

    def count_keywords(self, text: str) -> bool:
        """Conta as palavras-chave no texto e atualiza o dicionário de contagem"""

        verif = False
        for keyword in self.keywords:
            default = re.compile(r'\b' + re.escape(keyword) + r'\w*\b', re.IGNORECASE)
            keyword_count = len(default.findall(text))
            self.keywords[keyword] += keyword_count
            if keyword_count > 0:
                verif = True
        return verif

    def save_text_snippet(self, page_text: str, keyword: str, window_size: int = 210) -> List[str]:
        """Salva trechos do texto ao redor da palavra-chave"""

        snippets = []
        index = 0
        while index < len(page_text):
            found_index = page_text.find(keyword.lower(), index)
            if found_index == -1:
                break
            start_index = max(0, found_index - window_size)
            end_index = min(len(page_text), found_index + len(keyword) + window_size)
            snippet = page_text[start_index:end_index]
            snippet = '"' + snippet + '"'
            snippets.append(snippet)
            index = found_index + len(keyword)
        return snippets

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        vectorizer = TfidfVectorizer()
        vectors = vectorizer.fit_transform([text1, text2])
        return cosine_similarity(vectors[0], vectors[1])[0][0]

    def _is_duplicate_snippet(self, new_snippet: str, threshold: float = 0.8) -> bool:
        for saved_snippet in self.saved_snippets:
            similarity = self._calculate_similarity(new_snippet, saved_snippet)
            if similarity >= threshold:
                return True
        return False

    def create_keyword_docx(self, keyword: str, orgao_name: str) -> docx.Document:
        org_dir = join(self.docx_path, orgao_name)
        os.makedirs(org_dir, exist_ok=True)
        new_docx_path = join(org_dir, f'output_{orgao_name}_{keyword}.docx')
        if isfile(new_docx_path):
            doc = docx.Document(new_docx_path)
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
        snippet_fixed = ''.join(c if c.isprintable() else ' ' for c in snippet)
        p.add_run(snippet_fixed)
        p.add_run("\n")

    def save_docs_for_current_orgao(self, orgao_name: str) -> None:
        org_dir = join(self.docx_path, orgao_name)
        os.makedirs(org_dir, exist_ok=True)
        docs_to_save = {k: v for k, v in self.docx_files.items() if k[0] == orgao_name}
        for (org, keyword), doc in docs_to_save.items():
            file_path = join(org_dir, f'output_{org}_{keyword}.docx')
            doc.save(file_path)
            self.logger.info(f"Arquivo salvo: {file_path}")

    def upload_docx_s3(self):
        docx_path = self.docx_path
        logger.debug(f"📂 Caminho de saída: {docx_path}")

        os.makedirs(docx_path, exist_ok=True)
        if not os.path.exists(docx_path):
            logger.error("❌ Falha ao enviar docxs para o S3. DOCX não encontrados.")
            return False

        entries = os.listdir(docx_path)
        for entry in entries:
            logger.debug(f"📁 Diretório de órgão encontrado: {entry}")
            orgao_path = os.path.join(docx_path, entry)
            if os.path.isdir(orgao_path):
                docxs = os.listdir(orgao_path)
                for docx in docxs:
                    file_path = os.path.join(orgao_path, docx)
                    object_name = f'dani-docs/{entry}/{docx}'

                    if self.s3_service.object_exists(
                            bucket='agir-bucket',
                            object_name=object_name
                    ):
                        logger.warning(f"⚠ Arquivo já existe na S3 e será ignorado: {object_name}")
                        continue

                    logger.debug(f"📄 Enviando DOCX: {docx}")
                    self.s3_service.upload_object(
                        bucket='agir-bucket',
                        object_name=object_name,
                        file_path=file_path
                    )
        return True

    def close_all_docs(self) -> None:
        self.docx_files.clear()

    def display_results(self) -> None:
        self.logger.info("\n--- Resultados DANI ---")
        self.logger.info(f"Órgão(s) analisado(s): {self.orgao_name if not self.all_orgaos else 'Todos'}")
        self.logger.info(f"Documentos lidos: {self.name_docs_read}")
        self.logger.info("Quantidade de vezes que cada palavra-chave foi encontrada:")
        for keyword in self.keywords:
            keyword_count = self.keywords[keyword]
            percentage = (keyword_count / self.total_words_read) * 100.0 if self.total_words_read > 0 else 0
            self.logger.info(f"{keyword} foi encontrada: {keyword_count}, que representa {percentage:.2f}%")
        self.logger.info("No diretório de output você pode verificar os pedaços em que o texto foi encontrado")


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
    return acronyms.get(company_name, "")

if __name__ == "__main__":
    d = Dani()
    d.run()