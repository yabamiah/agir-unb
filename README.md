# AGIR - Automacao para uma Governanca Inteligente e Responsavel no DF

## Sobre o Projeto

AGIR e um projeto de Engenharia de Software da Universidade de Brasilia (UnB), desenvolvido no ambito do Programa Institucional de Bolsas de Iniciacao em Desenvolvimento Tecnologico e Inovacao (PIBITI).

O objetivo principal e automatizar a analise de documentos de governanca e integridade do Distrito Federal, utilizando tecnicas de Processamento de Linguagem Natural (NLP) e automacao de coleta de dados.

## Arquitetura

O sistema e composto por tres componentes principais:

### LARA-I (Robo de Coleta)
Responsavel pela coleta automatizada de documentos do portal de transparencia do DF.

### DANI (Analisador de Documentos)
Realiza duas funcoes principais:
- **Analise Geral**: Busca por palavras-chave em documentos e gera relatorios
- **Analise de Integridade (IMGA)**: Calcula o Indice de Maturidade da Governanca Algoritmica para planos de integridade

### Dashboard Web
Interface para visualizacao de resultados, execucao de processos e auditoria dos calculos IMGA.

## Indice de Maturidade da Governanca Algoritmica (IMGA)

O IMGA avalia planos de integridade em 8 eixos analiticos:

| Eixo | Nome | Peso |
|------|------|------|
| E1 | Estrutura de Governanca e Lideranca | 10% |
| E2 | Cultura de Integridade | 10% |
| E3 | Ambiente de Compliance | 15% |
| E4 | Due Diligence e Terceiros | 20% |
| E5 | Comunicacao, Treinamento e Monitoramento | 10% |
| E6 | Gestao de Riscos e Controles Internos | 15% |
| E7 | Transparencia, Accountability e Evidenciacao | 10% |
| E8 | Efetividade e Maturidade do Programa | 10% |

### Faixas de Maturidade
- **Incipiente** (0-25): Programa em fase inicial
- **Basica** (26-50): Estruturas basicas estabelecidas
- **Intermediaria** (51-75): Programa consolidado
- **Avancada** (76-100): Excelencia em governanca

## Tecnologias Utilizadas

- Python 3.11
- Streamlit (Dashboard)
- PyMuPDF / pdfplumber (Extracao de PDF)
- Tesseract OCR
- Docker / Docker Compose
- LibreOffice (Conversao DOCX para PDF)
- Playwright (Automacao web)

## Estrutura do Projeto

```
agir-unb/
├── cli/                    # Comandos de linha de comando
│   ├── dani_worker.py      # Worker para execucao em background
│   └── orchestrator.py     # Orquestrador de processos
├── core/
│   ├── dashboard/          # Interface web Streamlit
│   ├── models/
│   │   └── dani.py         # Classe principal DANI
│   ├── motor_nlp/          # Motor de NLP para IMGA
│   │   ├── classificador_eixos.py
│   │   ├── pontuador_maturidade.py
│   │   ├── calculador_imga.py
│   │   └── dicionario.json
│   ├── processors/         # Processadores de documentos
│   │   ├── pdf_processor.py
│   │   └── docx_converter.py
│   └── workers/            # Gerenciadores de workers
├── data/
│   └── dani/
│       ├── docs/
│       │   ├── input/      # Atas CIG (entrada)
│       │   ├── integridade/# Planos de integridade
│       │   └── output/     # Relatorios gerados
│       └── palavras_chaves.txt
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

## Instalacao e Uso

### Pre-requisitos
- Docker
- Docker Compose
- Make (opcional)

### Configuracao Inicial

```bash
# Clonar o repositorio
git clone <repository-url>
cd agir-unb

# Configurar variaveis de ambiente
cp env.example .env

# Construir e iniciar
make up-build
```

### Comandos Principais

| Comando | Descricao |
|---------|-----------|
| `make up` | Inicia todos os servicos |
| `make up-build` | Reconstroi e inicia servicos |
| `make down` | Para todos os containers |
| `make logs` | Mostra logs de todos os servicos |
| `make logs-dani-worker` | Logs do worker DANI |
| `make run-dani-integrity-trigger` | Dispara analise IMGA |
| `make status` | Status dos containers |
| `make clean` | Remove containers e volumes |

### Acessar o Dashboard

Apos iniciar os servicos:
```
http://localhost:8501
```

## Funcionalidades do Dashboard

- **Resultados**: Metricas gerais e resultados IMGA com detalhamento por eixo
- **Eixos Analiticos**: Referencia da taxonomia IMGA
- **Documentos**: Visualizador de PDFs (inputs e outputs)
- **Painel de Controle**: Execucao de processos e configuracao de palavras-chave

## Auditoria de Calculos

O dashboard oferece transparencia total nos calculos IMGA:
- Formula de normalizacao: `I_Ei = min((Soma_Bruta / (Total_Palavras/100)) * 10, 100)`
- Formula do indice global: `IMGA = Soma(I_Ei x Peso_Ei)`
- Detalhamento por eixo com soma bruta, densidade, contribuicao ponderada
- Listagem completa de termos encontrados por eixo

## Documentacao Adicional

- [DEPENDENCIES.md](DEPENDENCIES.md) - Dependencias do sistema

## Coordenadores

| Nome | Email |
|------|-------|
| Fatima de Souza | ffreire@unb.br |

## Equipe

| Nome | Email | GitLab |
|------|-------|--------|
| Mateus S. Santana | - | @Mateus-SS |
| Vinicius M. Martins | viniciusmendes1019@gmail.com | @yabamiah1 |
