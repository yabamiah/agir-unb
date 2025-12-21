.PHONY: help build up down logs restart clean shell cli dash rebuild run-lara run-dani stop-all run-dani-integrity-docker

# Variáveis
COMPOSE = docker-compose
DOCKER = docker

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

down-volumes: ## Para e remove containers e volumes
	$(COMPOSE) down -v

logs: ## Mostra logs de todos os serviços
	$(COMPOSE) logs -f

logs-cli: ## Mostra logs do serviço CLI
	$(COMPOSE) logs -f cli

logs-dash: ## Mostra logs do dashboard
	$(COMPOSE) logs -f dashboard

logs-tail: ## Mostra últimas 100 linhas dos logs
	$(COMPOSE) logs --tail=100

ps: ## Lista containers em execução
	$(COMPOSE) ps

restart: ## Reinicia todos os serviços
	$(COMPOSE) restart

restart-cli: ## Reinicia o serviço CLI
	$(COMPOSE) restart cli

restart-dash: ## Reinicia o dashboard
	$(COMPOSE) restart dashboard

clean: ## Remove containers, volumes e imagens não utilizadas
	$(COMPOSE) down -v --rmi local --remove-orphans
	$(DOCKER) system prune -f

shell-cli: ## Abre shell interativo no container CLI
	$(COMPOSE) exec cli /bin/bash

shell-dash: ## Abre shell interativo no container dashboard
	$(COMPOSE) exec dashboard /bin/bash

cli: shell-cli ## Alias para shell-cli

dash: shell-dash ## Alias para shell-dash

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

status: ## Mostra status dos containers
	$(COMPOSE) ps
	@echo "\n--- Logs recentes ---"
	$(COMPOSE) logs --tail=20

stop-all: down ## Para todos os containers

start-all: up ## Inicia todos os containers

update: ## Atualiza imagens e reconstrói
	$(COMPOSE) pull
	$(COMPOSE) up -d --build

follow-logs: logs ## Alias para logs

# Comandos de desenvolvimento
test: ## Executa testes
	$(COMPOSE) exec cli python -m pytest

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

# Informações do sistema
info: ## Mostra informações do Docker
	@echo "=== Docker Info ==="
	$(DOCKER) --version
	@echo "\n=== Docker Compose Info ==="
	$(COMPOSE) --version
	@echo "\n=== Containers ==="
	$(COMPOSE) ps
	@echo "\n=== Imagens ==="
	$(DOCKER) images | grep agir-unb

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

dani-help: ## Mostra ajuda específica do DANI
	@echo ""
	@echo "════════════════════════════════════════════════════"
	@echo "  DANI - Desenvolvedor e Apresentador de Números"
	@echo "════════════════════════════════════════════════════"
	@echo ""
	@echo "Comandos disponíveis:"
	@echo "  make run-dani-local        - Processar todos os órgãos"
	@echo "  make run-dani-integrity    - Processar planos de integridade (IMGA)"
	@echo "  make run-dani-orgao ORGAO=X - Processar órgão específico"
	@echo "  make run-dani-convert-pdf  - Converter DOCX para PDF"
	@echo ""

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

open-dashboard: ## Abre dashboard no navegador
	@echo "🌐 Abrindo dashboard..."
	@xdg-open http://localhost:8501 2>/dev/null || open http://localhost:8501 2>/dev/null || echo "Acesse: http://localhost:8501"
