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

### AGIR-RAG Lite
Camada leve de recuperacao aumentada para consultar o acervo documental, devolver evidencias com fonte e transformar criterios normativos em indicadores auditaveis. O RAG Lite substitui a necessidade de uma pilha pesada como RAGFlow no ciclo atual do projeto: usa SQLite FTS5 para busca textual, Qdrant local para busca semantica, Parquet para bases intermediarias e Gemini como modelo padrao de resposta quando `GEMINI_API_KEY` estiver configurada.

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
- SQLite FTS5 (Base auditavel e busca lexical)
- Qdrant (Indice vetorial local)
- Docker / Docker Compose
- LibreOffice (Conversao DOCX para PDF)
- Playwright (Automacao web)

## Estrutura do Projeto

```
agir-unb/
├── cli/                    # Comandos de linha de comando
│   ├── dani_worker.py      # Worker para execucao em background
│   ├── rag_indexer.py      # CLI da Sprint 5 (base auditavel e indice vetorial)
│   ├── rag_search.py       # CLI da Sprint 6 (recuperacao hibrida e evidencias)
│   ├── rag_classify.py     # CLI da Sprint 7 (classificacao e indicadores)
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
│   ├── services/           # Servicos de documentos e indexacao
│   │   ├── rag_index_service.py
│   │   └── rag_retrieval_service.py
│   └── workers/            # Gerenciadores de workers
├── data/
│   └── dani/
│       ├── docs/
│       │   ├── input/      # PDFs coletados (cig/, pg/, compliance/)
│       │   ├── integridade/# Planos de integridade
│       │   └── output/     # Relatorios gerados
│       └── palavras_chaves.txt
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── .env.example          # Modelo de variáveis de ambiente
└── requirements.txt      # Dependências Python (usado pelo Docker e venv local)
```

## Dependências

### Adicionar ou atualizar pacotes Python

1. Edite o arquivo `requirements.txt` na raiz (inclua versões fixas, por exemplo `pacote==1.2.3`, quando quiser builds reproduzíveis).
2. **Docker:** o `Dockerfile` instala `requirements.txt` e, na mesma etapa, alguns pacotes extras (`pymupdf`, `pdfplumber`, `wordcloud`, `matplotlib`). Se novas dependências substituírem o papel desses pacotes, ajuste também essa linha `RUN pip install ...` no `Dockerfile`.
3. Reconstrua as imagens para aplicar mudanças:
   ```bash
   docker compose build --no-cache
   # ou
   make build-no-cache && make up
   ```

### Ambiente virtual local (sem Docker)

```bash
make setup-venv       # cria `.venv` e instala `requirements.txt`
make install-deps     # reinstala requirements + `playwright install --with-deps chromium`
```

Ou manualmente: `pip install -r requirements.txt` e `playwright install chromium` (ou `playwright install --with-deps chromium` em Linux).

### Dependências de sistema

Para OCR, conversão DOCX→PDF e Playwright, o `Dockerfile` já instala pacotes Debian necessários (Tesseract, LibreOffice, bibliotecas do Chromium, etc.). Em máquina local, use o alvo `make install-deps` ou consulte o `Dockerfile` como referência.

## Variáveis de ambiente

1. Copie o modelo e edite os valores sensíveis:
   ```bash
   cp .env.example .env
   ```
2. O `docker-compose.yml` referencia `env_file: .env` nos serviços `cli`, `dashboard` e `dani-worker`, carregando essas variáveis nos containers.
3. Em execução local com Python, o `python-dotenv` (usado em `core/services/aws_service.py`) tenta carregar um arquivo `.env` no diretório de trabalho ao acessar a AWS.

| Variável | Obrigatória | Descrição |
|----------|-------------|-----------|
| `AWS_ACCESS_KEY_ID` | Sim, para S3 | Credencial de acesso à AWS (upload LARA-I, sync/baixar documentos no DANI, download da lista de órgãos). |
| `AWS_SECRET_ACCESS_KEY` | Sim, para S3 | Chave secreta correspondente. |
| `AWS_DEFAULT_REGION` | Não | Região do bucket (boto3 também pode usar configuração padrão da AWS CLI). |
| `DATA_DIR` | Não | Diretório de dados; nos containers o padrão é `/app/data` (volume `./data`). |
| `KEYWORDS_FILE` | Não | Caminho do `.txt` de palavras-chave do DANI. O compose do `dani-worker` define um padrão em `/app/data/dani/palavras_chaves.txt`. |
| `DANI_BATCH_SIZE` | Não | Tamanho do lote no DANI (padrão `15`). |
| `DANI_MAX_WORKERS` | Não | Workers paralelos no DANI (padrão `2`). |
| `DANI_INPUT_SUBDIR` | Não | Qual subpasta de `docs/input` analisar: `cig`, `pg` ou `compliance` (padrão `cig`). |
| `LARA_TIPOS_COLETA` | Não | Tipos a coletar no LARA-I, separados por vírgula (`cig`, `pg`, `compliance`), se não usar `--tipos` na CLI. |
| `GEMINI_API_KEY` | Não | Ativa Gemini no dashboard RAG. Sem a chave, o RAG continua em modo extrativo com evidências. |
| `GEMINI_MODEL` | Não | Modelo Gemini usado pelo dashboard e pelo teste local. Padrão: `gemini-2.5-flash`. |
| `OLLAMA_BASE_URL` | Não | Endpoint opcional para respostas via Ollama. Padrão: `http://localhost:11434`. |

**Bucket S3:** o nome do bucket está fixo no código como `agir-bucket` (prefixos `dani-docs/`, `lara-config/`). Trocar de bucket exige alteração no código.

Comentários e variáveis opcionais adicionais estão documentados em [`.env.example`](.env.example).

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
cp .env.example .env
# Edite .env (principalmente AWS_ACCESS_KEY_ID e AWS_SECRET_ACCESS_KEY se for usar S3)

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
| `make run-rag-index-local` | Constrói SQLite/Parquet e índice vetorial local da Sprint 5 |
| `make run-rag-search-local` | Executa recuperação híbrida e retorna evidências da Sprint 6 |
| `make run-rag-classify-local` | Classifica evidências e gera indicadores da Sprint 7 |
| `make status` | Status dos containers |
| `make clean` | Remove containers e volumes |

### Acessar o Dashboard

Apos iniciar os servicos:
```
http://localhost:8501
```

## Funcionalidades do Dashboard

- **LARA-I - Coleta**: dispara a coleta e mostra os documentos disponiveis por tipo.
- **DANI - Analise geral**: consolida frequencias de palavras-chave e ocorrencias nos documentos.
- **Analise de Integridade/IMGA**: exibe maturidade, eixos, termos encontrados e auditoria do calculo.
- **Analise com inteligencia artificial**: concentra o AGIR-RAG Lite para perguntas com fonte, busca de evidencias, conformidade por criterio e indicadores comparativos.
- **Eixos Analiticos**: referencia da taxonomia IMGA usada nas analises.

## Sprint 5 - Base Auditavel e Indexacao

O AGIR-RAG Lite agora possui uma etapa dedicada para:

- extrair texto por pagina a partir dos PDFs ja validados;
- segmentar o conteudo em `chunks` auditaveis;
- persistir documentos e chunks em SQLite com FTS5;
- exportar a base intermediaria em Parquet;
- indexar os chunks em Qdrant local com metadados.

Valor para o usuario: a etapa cria uma base consultavel e rastreavel. Cada resposta posterior pode apontar o documento, a pagina, o tipo documental e o trecho usado como evidencia.

Execucao local:

```bash
make run-rag-index-local
```

Com reset e parametros customizados:

```bash
make run-rag-index-local ARGS="--reset --tipos pg compliance integridade --chunk-size 1000 --chunk-overlap 150"
```

A indexacao gera artefatos em `data/rag/`:

- `agir_rag.db`
- `documents.parquet`
- `chunks.parquet`
- `index_manifest.json`
- `qdrant/`

### Sprint 6 - Recuperacao Hibrida e Evidencias

A Sprint 6 combina busca textual em SQLite FTS5 com busca semantica no Qdrant local, funde os rankings e retorna evidencias com trecho, documento, pagina, orgao, tipo documental e score.

Valor para o usuario: perguntas livres deixam de depender de leitura manual de todos os PDFs. O sistema recupera os melhores trechos e mostra o diagnostico da recuperacao; se o indice semantico local estiver indisponivel, a busca textual auditavel continua funcionando.

Consulta livre:

```bash
make run-rag-search-local ARGS='--pergunta "Ha canal de denuncia previsto?" --top-k 3'
```

Teste com pergunta normativa real do checklist:

```bash
make run-rag-search-local ARGS="--usar-criterios --criterio E1-GOV-001 --top-k 3"
```

Teste em lote controlado:

```bash
make run-rag-search-local ARGS="--usar-criterios --max-criterios 5 --tipos pg compliance"
```

### Sprint 7 - Classificacao e Indicadores

A Sprint 7 transforma as evidencias da recuperacao hibrida em conformidade mensuravel. A classificacao automatica usa o checklist normativo, os eixos IMGA, score de recuperacao, termos esperados e sinais de ausencia para produzir:

- classificacao por criterio e orgao (`atende`, `atende_parcialmente`, `nao_atende`, `nao_encontrado`);
- pontuacao ponderada por criterio;
- conformidade por eixo IMGA;
- ranking comparativo por orgao;
- amostra em CSV para validacao manual.

Valor para o usuario: o dashboard passa de consulta pontual para acompanhamento comparativo, permitindo ver quais orgaos possuem evidencias fortes, quais exigem revisao e quais criterios precisam de validacao humana.

Execucao controlada para teste:

```bash
make run-rag-classify-local ARGS="--max-orgaos 2 --max-criterios 5"
```

Processar um orgao e um criterio especificos:

```bash
make run-rag-classify-local ARGS="--orgao SEAGRI --criterio E2-INT-001 --top-k 3"
```

A classificacao gera artefatos em `data/rag/sprint7/`:

- `classificacoes.json`
- `indicadores_orgaos.csv`
- `criterios_orgaos.csv`
- `validacao_manual_amostra.csv`
- `sprint7_report.json`

### Gemini no RAG

O dashboard usa Gemini como modelo atual quando `GEMINI_API_KEY` existe no `.env`. Para testar a configuracao:

```bash
make test-gemini
```

Sem chave Gemini, o RAG permanece utilizavel no modo `Sem LLM`, gerando uma resposta extrativa com os principais trechos recuperados.

## Auditoria de Calculos

O dashboard oferece transparencia total nos calculos IMGA:
- Formula de normalizacao: `I_Ei = min((Soma_Bruta / (Total_Palavras/100)) * 10, 100)`
- Formula do indice global: `IMGA = Soma(I_Ei x Peso_Ei)`
- Detalhamento por eixo com soma bruta, densidade, contribuicao ponderada
- Listagem completa de termos encontrados por eixo

## Documentacao Adicional

- [`Dockerfile`](Dockerfile) — dependências de sistema (Debian) usadas nas imagens.

## Coordenadores

| Nome | Email |
|------|-------|
| Fatima de Souza | ffreire@unb.br |

## Equipe

| Nome | Email | GitLab |
|------|-------|--------|
| Mateus S. Santana | - | @Mateus-SS |
| Vinicius M. Martins | viniciusmendes1019@gmail.com | @yabamiah1 |

image.pngj
