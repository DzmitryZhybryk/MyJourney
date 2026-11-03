.PHONY: help format format-check lint typecheck dead-code audit arch check check-ci test coverage test-unit test-integration test-api test-auth test-users test-shared test-journeys test-geo test-health test-media openapi-dump

# Colors for output
ifeq ($(OS),Windows_NT)
    ESC     := $(shell printf '\e')
    RESET   := $(ESC)[0m
    BLACK   := $(ESC)[30m
    RED     := $(ESC)[31m
    GREEN   := $(ESC)[32m
    YELLOW  := $(ESC)[33m
    BLUE    := $(ESC)[34m
    PURPLE  := $(ESC)[35m
    AZURE   := $(ESC)[36m
    WHITE   := $(ESC)[37m
else
    RESET  := \033[0m
    BLACK  := \033[30m
    RED    := \033[31m
    GREEN  := \033[32m
    YELLOW := \033[33m
    BLUE   := \033[34m
    PURPLE := \033[35m
    AZURE  := \033[36m
    WHITE  := \033[37m
endif

# Sources to check
RUFF_SOURCES := app migrations tests devtools

# Docker-окружение для testcontainers (integration-уровень). Применяется к таргету
# test-integration — единственному, который запускает integration-тесты.
#   DOCKER_HOST — куда стучится Python-клиент docker (на нём testcontainers). Берём из
#     активного docker-контекста, если не задан явно: Docker Desktop держит сокет не в
#     /var/run/docker.sock. В CI контекст вернёт дефолтный сокет — работает и там, и локально.
#   SOCKET_OVERRIDE — источник bind-маунта сокета в контейнер-уборщик Ryuk. По умолчанию
#     testcontainers берёт его из DOCKER_HOST (хостовый путь Desktop), а его демон в VM
#     примонтировать не может. Канонический /var/run/docker.sock Desktop маунтит спец-обработкой.
DOCKER_TC_ENV = DOCKER_HOST="$${DOCKER_HOST:-$$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null)}" TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE=/var/run/docker.sock

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${AZURE}%-15s${RESET} %s\n", $$1, $$2}'

format: ## Auto-format python source files
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}ruff${AZURE}' format${RESET}"
	@uv run ruff check --fix --unsafe-fixes $(RUFF_SOURCES)
	@uv run ruff format $(RUFF_SOURCES)

format-check: ## Verify formatting without modifying files (CI-режим format)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}ruff${AZURE}' format --check${RESET}"
	@uv run ruff format --check $(RUFF_SOURCES)

lint: ## Lint python source files with ruff
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}ruff${AZURE}' lint${RESET}"
	@uv run ruff check $(RUFF_SOURCES)

typecheck: ## Type check python source files with ty
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}ty${AZURE}' typecheck${RESET}"
	@uv run ty check $(RUFF_SOURCES)

dead-code: ## Find unused code with vulture
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}vulture${AZURE}' dead code check${RESET}"
	@uv run vulture

audit: ## Scan dependencies for known vulnerabilities (uv audit)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}uv audit${AZURE}' security scan${RESET}"
	@uv audit --preview-features audit-command

arch: ## Enforce DDD layer/import boundaries (tach)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}tach${AZURE}' boundary check${RESET}"
	@uv run tach check --exact

check: format lint typecheck arch dead-code audit test ## Run format + lint + typecheck + arch + dead-code + audit + fast tests (unit+api; integration → test-integration)

check-ci: format-check lint typecheck arch dead-code audit test ## CI-гейт: как check, но format в проверочном режиме (не модифицирует файлы)

test: ## Run fast tests — unit + api (no Docker; integration → make test-integration)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}pytest${AZURE}' unit + api tests${RESET}"
	@uv run pytest -m "unit or api"

coverage: ## Run unit + api tests with coverage report (мерж-гейт: >= 90%)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}pytest${AZURE}' coverage (unit + api)${RESET}"
	@uv run pytest -m "unit or api" --cov=app --cov-report=term-missing --cov-fail-under=90

# Запуск тестов по осям маркеров (авто-маркировка по пути — см. tests/conftest.py).
# `|| [ $$? -eq 5 ]` — не считать "тесты не найдены" (exit 5) ошибкой: пустые группы
# (ещё ненаполненные уровни/домены) не должны валить таргет.
test-unit: ## Run unit-level tests (-m unit)
	@uv run pytest -m unit || [ $$? -eq 5 ]

test-integration: ## Run integration-level tests (-m integration; нужен Docker для testcontainers)
	@$(DOCKER_TC_ENV) uv run pytest -m integration || [ $$? -eq 5 ]

test-api: ## Run api-level tests (-m api)
	@uv run pytest -m api || [ $$? -eq 5 ]

test-auth: ## Run auth-domain tests, any level (-m auth)
	@uv run pytest -m auth || [ $$? -eq 5 ]

test-users: ## Run users-domain tests, any level (-m users)
	@uv run pytest -m users || [ $$? -eq 5 ]

test-shared: ## Run shared-infra tests, any level (-m shared)
	@uv run pytest -m shared || [ $$? -eq 5 ]

test-journeys: ## Run journeys-domain tests, any level (-m journeys)
	@uv run pytest -m journeys || [ $$? -eq 5 ]

test-geo: ## Run geo-domain tests, any level (-m geo)
	@uv run pytest -m geo || [ $$? -eq 5 ]

test-health: ## Run health-domain tests, any level (-m health)
	@uv run pytest -m health || [ $$? -eq 5 ]

test-media: ## Run media-domain tests, any level (-m media)
	@uv run pytest -m media || [ $$? -eq 5 ]

openapi-dump: ## Rewrite backend/openapi.json from the app (drift gate is the snapshot test in make test)
	@echo "${GREEN}INFO :  ${AZURE}Update '${PURPLE}openapi.json${AZURE}' snapshot${RESET}"
	@UPDATE_OPENAPI=1 uv run pytest tests/api/test_openapi_schema.py -q
