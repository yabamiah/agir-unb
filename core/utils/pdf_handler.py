import pytesseract
from pdf2image import convert_from_path
from PIL import Image


def pdf_to_image(file_path: str) -> list[Image.Image]:
    return convert_from_path(file_path)


def ocr_image_to_string(file_path: str) -> str:
    text = pytesseract.image_to_string(file_path, lang="por")
    return text.lower()


class PdfReader:
    def __init__(self) -> None:
        self._pdf_pages_text = None
        self._qtd_pdf_pages = 0
        self._total_words_pdf = 0

    def pdf_to_string(self, file_path: str) -> list[str]:
        pdf_images = pdf_to_image(file_path)
        self._qtd_pdf_pages = len(pdf_images)
        self._pdf_pages_text = []

        for _, image in enumerate(pdf_images):
            self._pdf_pages_text.append(ocr_image_to_string(image))

        return self._pdf_pages_text

    def get_total_pages_pdf(self) -> int:
        if self._qtd_pdf_pages == 0:
            raise Exception("Nenhum arquivo PDF foi lido")

        return self._qtd_pdf_pages

    def get_total_words_pdf(self) -> int:
        if self._qtd_pdf_pages == 0:
            raise Exception("Nenhum arquivo PDF foi lido")

        for page_text in self._pdf_pages_text:
            self._total_words_pdf += len(page_text)

        return self._total_words_pdf
