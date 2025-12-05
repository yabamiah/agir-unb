.PHONY: help build up down logs restart clean shell cli dash rebuild run-lara run-dani stop-all

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

