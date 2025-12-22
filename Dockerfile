FROM python:3.11-slim

WORKDIR /app

# Instala dependências do sistema
# Necessárias para conversão de documentos (pypandoc, libreoffice)
RUN apt-get update && apt-get install -y \
    pandoc \
    # LibreOffice para conversão DOCX → PDF (DANI)
    libreoffice-common \
    libreoffice-writer \
    # Para conversão de PDF em imagens (pdf2image)
    poppler-utils \
    # Para OCR (pytesseract)
    tesseract-ocr \
    tesseract-ocr-por \
    # Fontes básicas
    fonts-liberation \
    # Bibliotecas mínimas necessárias para Playwright/Chromium
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    # Bibliotecas para PyMuPDF (PDF otimizado)
    libmupdf-dev \
    # SSL/certificados
    ca-certificates \
    # Utilitários
    wget \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir pymupdf pdfplumber wordcloud matplotlib

# Instala navegadores do Playwright sem dependências do sistema
RUN playwright install chromium

COPY . .

CMD ["python", "-m", "cli.orchestrator"]