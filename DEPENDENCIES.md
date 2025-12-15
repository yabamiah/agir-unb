# Dependências do Projeto AGIR-UNB

Este documento explica as dependências do sistema necessárias para executar o projeto.

## Dependências do Sistema (Apt)

### 1. Conversão de Documentos (DOCX → PDF)

**Pacotes necessários:**
- `pandoc` - Ferramenta de conversão de documentos
- `texlive-xetex` - Engine XeLaTeX para compilação de PDFs
- `texlive-luatex` - Engine LuaLaTeX como alternativa
- `texlive-binaries` - Binários do TeX

**Uso no projeto:**
- Usado em `core/models/dani.py` para converter documentos DOCX gerados em PDF
- A classe `Dani` usa `pypandoc` com engines `xelatex`, `pdflatex` e `lualatex`

### 2. Conversão de PDF em Imagens

**Pacotes necessários:**
- `poppler-utils` - Conjunto de ferramentas para manipular PDFs

**Uso no projeto:**
- Usado por `pdf2image` para converter PDFs em imagens PNG
- Utilizado em `core/utils/pdf_handler.py` para OCR de PDFs

### 3. OCR (Optical Character Recognition)

**Pacotes necessários:**
- `tesseract-ocr` - Motor de OCR
- `tesseract-ocr-por` - Pacote de idioma Português

**Uso no projeto:**
- Usado por `pytesseract` para extrair texto de imagens
- Utilizado para processar PDFs escaneados sem texto extraível

### 4. Navegação Web (Playwright)

**Pacotes necessários:**
Bibliotecas mínimas para o Chromium funcionar headless:
- `libnss3`, `libnspr4` - Segurança e criptografia
- `libatk1.0-0`, `libatk-bridge2.0-0` - Acessibilidade
- `libdrm2` - Gerenciamento de dispositivos
- `libxkbcommon0` - Teclado
- `libxcomposite1`, `libxdamage1`, `libxrandr2` - Composição de janelas
- `libgbm1` - Buffer management
- `libgtk-3-0` - Interface gráfica
- `libasound2` - Áudio
- `libpango-1.0-0`, `libcairo2` - Renderização de texto/gráficos
- `libatspi2.0-0` - Acessibilidade

**Uso no projeto:**
- Usado por `playwright` em `core/models/lara_i.py` para navegação web automatizada
- Necessário para coletar documentos dos portais do GDF

### 5. Fontes

**Pacotes necessários:**
- `fonts-liberation` - Fontes básicas

**Uso no projeto:**
- Necessário para renderização adequada de textos em documentos

### 6. Utilitários

**Pacotes necessários:**
- `ca-certificates` - Certificados SSL/TLS
- `wget` - Download de arquivos

## Dependências Python

Principais bibliotecas Python e seus usos:

| Biblioteca | Uso |
|------------|-----|
| `playwright` | Automação de navegação web (LARA-I) |
| `pdf2image` | Conversão de PDFs em imagens |
| `pytesseract` | OCR para extrair texto de imagens |
| `pypandoc` | Conversão de documentos (DOCX → PDF) |
| `boto3` | Interação com AWS S3 |
| `pandas` | Manipulação de dados |
| `scikit-learn` | Análise de similaridade de textos |
| `requests` | Requisições HTTP |
| `python-docx` | Manipulação de documentos DOCX |
| `streamlit` | Dashboard web |
| `loguru` | Sistema de logs |

## Tamanho da Imagem Docker

O Dockerfile otimizado inclui apenas as dependências essenciais. O tamanho estimado é:
- Base: Python 3.11-slim (~120MB)
- Dependências do sistema: ~400MB
- Python packages: ~300MB
- **Total estimado: ~800-900MB**

## Otimizações Aplicadas

1. **Remoção de cache:** `rm -rf /var/lib/apt/lists/*` remove cache do apt após instalação
2. **Combinação de RUN:** Comandos combinados reduzem camadas da imagem
3. **Instalação específica:** Apenas `playwright install chromium` (não todos os browsers)
4. **Dependências mínimas:** Apenas bibliotecas essenciais para Playwright/Chromium

## Verificação de Dependências

Para verificar se todas as dependências estão instaladas dentro do container:

```bash
# Verificar pandoc
docker-compose exec cli pandoc --version

# Verificar tesseract
docker-compose exec cli tesseract --version

# Verificar pdf2image
docker-compose exec cli pdfinfo --version

# Verificar playwright
docker-compose exec cli playwright --version
```

