.PHONY: help typecheck lint lint-fix audit test test-unit test-component coverage check test-e2e generate-api generate-world budget mantine-styles

# Colors for output
ifeq ($(OS),Windows_NT)
    ESC     := $(shell printf '\e')
    RESET   := $(ESC)[0m
    GREEN   := $(ESC)[32m
    PURPLE  := $(ESC)[35m
    AZURE   := $(ESC)[36m
else
    RESET  := \033[0m
    GREEN  := \033[32m
    PURPLE := \033[35m
    AZURE  := \033[36m
endif

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  ${AZURE}%-15s${RESET} %s\n", $$1, $$2}'

typecheck: ## Type-check sources with tsc
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}tsc${AZURE}' typecheck${RESET}"
	@npm run typecheck

lint: ## Lint sources with oxlint
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}oxlint${AZURE}' lint${RESET}"
	@npm run lint

lint-fix: ## Auto-fix lint issues (oxlint --fix)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}oxlint --fix${AZURE}'${RESET}"
	@npm run lint:fix

test: ## Run all Vitest tests once — unit + component (vitest run)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}vitest${AZURE}' tests${RESET}"
	@npm run test:run

test-unit: ## Run unit tests only (*.test.ts — pure logic)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}vitest${AZURE}' unit tests${RESET}"
	@npm run test:unit

test-component: ## Run component tests only (*.test.tsx — rendered React)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}vitest${AZURE}' component tests${RESET}"
	@npm run test:component

coverage: ## Run tests with coverage report
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}vitest${AZURE}' coverage${RESET}"
	@npm run coverage

generate-api: ## Regenerate src/api/generated from backend/openapi.json (run after make be-openapi-dump)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}openapi-ts${AZURE}' codegen${RESET}"
	@npm run generate:api

generate-world: ## Rebuild src/data/world-countries.topo.json from data/world-countries.geo.json
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}build-world-topology${AZURE}' codegen${RESET}"
	@npm run generate:world

budget: ## Production build + bundle budget check per page (limits — .claude/rules/web/performance.md)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}vite build${AZURE}' + bundle budget${RESET}"
	@npm run budget

mantine-styles: ## Check src/mantineStyles.ts lists exactly the Mantine stylesheets the used components need
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}check-mantine-styles${AZURE}'${RESET}"
	@npm run mantine-styles

audit: ## Scan npm dependencies for known vulnerabilities (high+)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}npm audit${AZURE}' security scan${RESET}"
	@npm audit --audit-level=high

check: lint typecheck mantine-styles audit test ## Run lint + typecheck + Mantine stylesheets + audit + unit/component (fast; the coverage gate is separate: make coverage; e2e: make test-e2e)

# Arguments passed through to playwright: narrow the browser or the test set.
# E.g. E2E_ARGS="--project=chromium -g login": three browsers are overkill for the dev loop.
E2E_ARGS ?=

test-e2e: ## Run Playwright e2e against E2E_BASE_URL (usually started by the root `make test-e2e` / `make test-e2e-dev`)
	@echo "${GREEN}INFO :  ${AZURE}Run '${PURPLE}playwright test $(E2E_ARGS)${AZURE}' e2e${RESET}"
	@npm run e2e -- $(E2E_ARGS)
