.PHONY: help build up down logs restart clean shell cli dash rebuild run-lara run-dani stop-all run-dani-integrity-docker fix-data-permissions run-lara-local run-lara-local-upload run-rag-index-local run-rag-index-pilot run-rag-search-local run-rag-classify-local run-rag-classify-pilot run-rag-pipeline-pilot run-dashboard-local run-dashboard-rag-local test-gemini

# Variáveis
COMPOSE = docker compose
DOCKER = docker
RAG_PYTHON ?= $(shell if [ -x .venv/bin/python ] && .venv/bin/python -c "import loguru" >/dev/null 2>&1; then echo .venv/bin/python; elif [ -x .venv-clean/bin/python ]; then echo .venv-clean/bin/python; else echo python3; fi)
STREAMLIT_PORT ?= 8501
RAG_PILOT_DOCS ?= 5
RAG_PILOT_ORGAOS ?=
RAG_PILOT_TIPOS ?= pg compliance
RAG_PILOT_CRITERIOS ?= 10
RAG_PILOT_TOP_K ?= 5
RAG_MAX_PAGES_PER_DOC ?= 40

# Comando padrão
.DEFAULT_GOAL := help

help: ## Mostra esta mensagem de ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Constrói as imagens Docker
	$(COMPOSE) build

build-no-cache: ## Constrói as imagens Docker sem usar cache
	$(COMPOSE) build --no-cache

up: ## Inicia todos os serviços
	$(COMPOSE) up -d

up-build: ## Constrói e inicia os serviços
	$(COMPOSE) up -d --build

down: ## Para e remove os containers
	$(COMPOSE) down

logs: ## Mostra logs de todos os serviços
	$(COMPOSE) logs -f

clean: ## Remove containers, volumes e imagens não utilizadas
	$(COMPOSE) down -v --rmi local --remove-orphans
	$(DOCKER) system prune -f

rebuild: clean build up ## Remove tudo, reconstrói e inicia

rebuild-no-cache: clean build-no-cache up ## Reconstrução completa sem cache

run-lara: ## Executa o trigger para iniciar LARA-I
	@mkdir -p data/triggers
	@touch data/triggers/run_lara.trigger
	@echo "Trigger LARA-I criado"

run-dani: ## Executa o trigger para iniciar DANI
	@mkdir -p data/triggers
	@touch data/triggers/run_dani.trigger
	@echo "Trigger DANI criado"

run-dani-integrity-trigger: ## Cria trigger para DANI integridade (via Docker)
	@mkdir -p data/triggers
	@touch data/triggers/run_dani_integrity.trigger
	@echo "📊 Trigger DANI Integridade criado"

fix-data-permissions: ## Corrige permissoes locais de data/ criadas por containers Docker
	@echo "🔧 Ajustando permissões de data/ para o usuário local..."
	$(COMPOSE) run --rm --user root cli sh -c "mkdir -p /app/data/triggers /app/data/dani/docs/output /app/data/dani/docs/result_pdf/output && for path in /app/data/triggers /app/data/dani/docs/output /app/data/dani/docs/result_pdf /app/data/dani/docs/summary_results.json; do if [ -e \"$$path\" ]; then chown -R $(shell id -u):$(shell id -g) \"$$path\" && chmod -R u+rwX,g+rwX \"$$path\"; fi; done"
	@echo "✅ Permissões de data/triggers e resultados DANI ajustadas."

status: ## Mostra status dos containers
	$(COMPOSE) ps
	@echo "\n--- Logs recentes ---"
	$(COMPOSE) logs --tail=20

stop-all: down ## Para todos os containers

start-all: up ## Inicia todos os containers

install-deps: ## Instala dependências localmente
	pip install -r requirements.txt
	playwright install --with-deps chromium

setup-venv: ## Cria e configura ambiente virtual
	@echo "🔧 Criando ambiente virtual..."
	python3 -m venv .venv
	@echo "📦 Instalando dependências..."
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Ambiente configurado! Ative com: source .venv/bin/activate"

install-venv-deps: ## Instala dependências no venv existente
	@echo "📦 Instalando dependências no venv..."
	.venv/bin/pip install -r requirements.txt
	@echo "✅ Dependências instaladas!"

install-all: install-venv-deps ## Instala todas as dependências (alias)
	@echo "✅ Todas as dependências instaladas!"

# ============================================
# LARA-I - Execução Local
# ============================================
# Opcional: argumentos extra (ex.: make run-lara-local ARGS='--tipos pg --limite 2')

run-lara-local: ## Executa LARA-I localmente (coleta PDFs, sem upload S3)
	@echo "🚀 Iniciando LARA-I (sem upload S3)..."
	.venv/bin/python -m core.models.lara_i $(ARGS)

run-lara-local-upload: ## Executa LARA-I localmente e envia PDFs para a S3 após a coleta
	@echo "🚀 Iniciando LARA-I (com upload S3)..."
	.venv-clean/bin/python -m core.models.lara_i --upload-s3 $(ARGS)

# ============================================
# DANI - Execução Local
# ============================================

run-dani-local: ## Executa DANI localmente (todos os órgãos)
	@echo "🚀 Iniciando DANI (todos os órgãos)..."
	.venv/bin/python -c "from core.models.dani import Dani; d = Dani(all_orgaos=True); d.run()"

run-dani-integrity: ## Executa DANI para planos de integridade (modo IMGA)
	@echo "🚀 Iniciando DANI (planos de integridade - IMGA)..."
	.venv/bin/python -c "from core.models.dani import Dani; d = Dani(only_integrity_plans=True, all_orgaos=True); d.run()"

run-dani-orgao: ## Executa DANI para órgão específico (ORGAO=nome)
	@if [ -z "$(ORGAO)" ]; then \
		echo "❌ Erro: Especifique o órgão com ORGAO=nome"; \
		echo "   Exemplo: make run-dani-orgao ORGAO=SEMA"; \
		exit 1; \
	fi
	@echo "🚀 Iniciando DANI para órgão: $(ORGAO)..."
	.venv/bin/python -c "from core.models.dani import Dani; d = Dani(orgao_name='$(ORGAO)'); d.run()"

run-dani-convert-pdf: ## Converte DOCX para PDF (todos os órgãos)
	@echo "📄 Iniciando conversão DOCX → PDF..."
	.venv/bin/python -c "from core.models.dani import Dani; d = Dani(); d.run_with_pdf_conversion()"

run-rag-index-local: ## Executa a Sprint 5: base auditavel + SQLite/Parquet + Qdrant local
	@echo "🧭 Construindo base auditavel e indice vetorial local..."
	$(RAG_PYTHON) -m cli.rag_indexer $(ARGS)

run-rag-index-pilot: ## Indexa amostra pequena do RAG (ajuste RAG_PILOT_DOCS/RAG_PILOT_ORGAOS/RAG_PILOT_TIPOS)
	@echo "🧭 Construindo amostra RAG com até $(RAG_PILOT_DOCS) documento(s)..."
	$(RAG_PYTHON) -m cli.rag_indexer --reset --tipos $(RAG_PILOT_TIPOS) $(if $(RAG_PILOT_ORGAOS),--orgaos $(RAG_PILOT_ORGAOS),) --max-documents $(RAG_PILOT_DOCS) --max-pages-per-document $(RAG_MAX_PAGES_PER_DOC)

run-rag-search-local: ## Executa a Sprint 6: recuperacao hibrida + evidencias
	@echo "🔎 Buscando evidencias com recuperacao hibrida..."
	$(RAG_PYTHON) -m cli.rag_search $(ARGS)

run-rag-classify-local: ## Executa a Sprint 7: classificacao + indicadores IMGA
	@echo "📐 Classificando evidencias e calculando indicadores..."
	$(RAG_PYTHON) -m cli.rag_classify $(ARGS)

run-rag-classify-pilot: ## Calcula conformidade em amostra pequena do RAG
	@echo "📐 Calculando conformidade documental da amostra..."
	$(RAG_PYTHON) -m cli.rag_classify --max-orgaos 3 --max-criterios $(RAG_PILOT_CRITERIOS) --top-k $(RAG_PILOT_TOP_K)

run-rag-pipeline-pilot: run-rag-index-pilot run-rag-classify-pilot ## Executa pipeline RAG piloto: indexacao pequena + conformidade
	@echo "✅ Pipeline RAG piloto concluido."

test-gemini: ## Testa GEMINI_API_KEY do .env com uma chamada curta
	@echo "🧪 Testando Gemini..."
	$(RAG_PYTHON) -m cli.gemini_test

# ============================================
# Docker - Comandos DANI
# ============================================

run-dani-docker: ## Executa DANI via Docker (todos os órgãos)
	@echo "🚀 Executando DANI via Docker..."
	$(COMPOSE) exec dani-worker python -c "from cli.dani_worker import run_dani_normal; run_dani_normal()"

run-dani-integrity-docker: ## Executa DANI integridade via Docker (IMGA)
	@echo "📊 Executando DANI Integridade via Docker..."
	$(COMPOSE) exec dani-worker python -c "from cli.dani_worker import run_dani_integrity; run_dani_integrity()"

logs-dani-worker: ## Mostra logs do worker DANI
	$(COMPOSE) logs -f dani-worker

restart-dani-worker: ## Reinicia o worker DANI
	$(COMPOSE) restart dani-worker

# ============================================
# Dashboard - Atalhos
# ============================================

run-dashboard: up ## Inicia dashboard (alias para up)
	@echo "📊 Dashboard disponível em http://localhost:8501"

run-dashboard-local: ## Inicia dashboard local carregando .env
	@echo "📊 Dashboard local em http://localhost:$(STREAMLIT_PORT)"
	@mkdir -p /tmp/matplotlib-cache /tmp/agir-pycache
	@set -a; [ -f .env ] && . ./.env; set +a; \
	MPLCONFIGDIR=/tmp/matplotlib-cache PYTHONPYCACHEPREFIX=/tmp/agir-pycache STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
	$(RAG_PYTHON) -m streamlit run core/dashboard/app.py --server.port $(STREAMLIT_PORT) --server.headless true --browser.gatherUsageStats false

run-dashboard-rag-local: run-rag-pipeline-pilot run-dashboard-local ## Executa amostra RAG e abre dashboard local

open-dashboard: ## Abre dashboard no navegador
	@echo "🌐 Abrindo dashboard..."
	@xdg-open http://localhost:8501 2>/dev/null || open http://localhost:8501 2>/dev/null || echo "Acesse: http://localhost:8501"
