include custom.mk

setup-env:
	@[ ! -f ./.env ] && cp ./.env.example ./.env || echo ".env file already exists."

start: ## Start the docker containers
	@echo "Starting the docker containers"
	@docker compose up

stop: ## Stop Containers
	@docker compose down

restart: stop start ## Restart Containers

start-bg:  ## Run containers in the background
	@docker compose up -d

dev: ## Start Django and npm dev servers
	@./scripts/dev.sh

healthcheck: ## Check if all dev services are running
	@./scripts/healthcheck.sh

django: ## Run Django dev server
	@uv run manage.py runserver

celery: ## Start Celery and celery beat
	@uv run celery -A tformance worker -l INFO --beat --pool=solo

manage: ## Run any manage.py command. E.g. `make manage ARGS='createsuperuser'`
	@uv run manage.py ${ARGS}

migrations: ## Create DB migrations in the container
	@uv run manage.py makemigrations

migrate: ## Run DB migrations in the container
	@echo "Waiting for database to be ready..."
	@until docker compose exec db pg_isready -d tformance -U postgres >/dev/null 2>&1; do echo "Database not ready, waiting..."; sleep 2; done
	@echo "Database is ready, running migrations..."
	@uv run manage.py migrate

shell: ## Get a Django shell
	@uv run manage.py shell

dbshell: ## Get a Database shell
	@docker compose exec db psql -U postgres tformance

test: ## Run Django tests
	@uv run manage.py test ${ARGS}

test-parallel: ## Run Django tests in parallel (faster but may have intermittent failures)
	@uv run manage.py test --parallel ${ARGS}

init: setup-env start-bg migrations migrate npm-install-all bootstrap_content install-hooks  ## Quickly get up and running (start containers and bootstrap DB)

install-hooks: ## Install git hooks (pre-push runs tests)
	@echo "Installing git hooks..."
	@cp scripts/hooks/pre-push .git/hooks/pre-push
	@chmod +x .git/hooks/pre-push
	@echo "✅ Git hooks installed"

uv: ## Run a uv command
	@uv $(filter-out $@,$(MAKECMDGOALS))

uv-sync: ## Sync dependencies
	@uv sync --frozen

ruff-format: ## Runs ruff formatter on the codebase
	@uv run ruff format .

ruff-lint:  ## Runs ruff linter on the codebase
	@uv run ruff check --fix .

ruff: ruff-format ruff-lint ## Formatting and linting using Ruff

lint-team-isolation: ## Check for unsafe .objects. usage on team models
	@uv run python scripts/lint_team_isolation.py apps/ --exclude-tests

lint-team-isolation-all: ## Check all files including tests for team isolation
	@uv run python scripts/lint_team_isolation.py apps/

lint-colors: ## Check templates for hardcoded colors (use semantic DaisyUI classes)
	@uv run python scripts/lint_colors.py templates/

lint-colors-fix: ## Check templates for hardcoded colors with fix suggestions
	@uv run python scripts/lint_colors.py templates/ --fix-suggestions

lint: ruff lint-team-isolation lint-colors ## Run all linters (ruff + team isolation + colors)

e2e: ## Run all E2E tests (requires dev server running)
	@npx playwright test

e2e-smoke: ## Run smoke E2E tests only (fast, for pre-commit)
	@npx playwright test --grep @smoke

e2e-auth: ## Run authentication E2E tests
	@npx playwright test auth.spec.ts

e2e-dashboard: ## Run dashboard E2E tests
	@npx playwright test dashboard.spec.ts

e2e-ui: ## Run E2E tests with UI mode (interactive)
	@npx playwright test --ui

e2e-report: ## Show last E2E test report
	@npx playwright show-report

npm-install-all: ## Runs npm install
	@npm install

npm-install: ## Runs npm install (optionally accepting package names)
	@npm install $(filter-out $@,$(MAKECMDGOALS))

npm-uninstall: ## Runs npm uninstall (takes package name(s))
	@npm uninstall $(filter-out $@,$(MAKECMDGOALS))

npm-build: ## Runs npm build (for production assets)
	@npm run build

npm-dev: ## Runs npm dev
	@npm run dev

npm-type-check: ## Runs the type checker on the front end TypeScript code
	@npm run type-check

bootstrap_content:  ## Initializes your Wagtail content with some example pages and blog posts
	@uv run manage.py bootstrap_content

upgrade: migrations migrate npm-install npm-dev  ## Run after a Pegasus upgrade to update requirements, migrate the database, and rebuild the front end

build-api-client:  ## Update the JavaScript API client code.
	@cp ./api-client/package.json ./package.json.api-client
	@rm -rf ./api-client
	@mkdir -p ./api-client
	@mv ./package.json.api-client ./api-client/package.json
	@docker run --rm --network host \
		-v ./api-client:/local \
		--user $(MY_UID):$(MY_GID) \
		openapitools/openapi-generator-cli:v7.9.0 generate \
		-i http://localhost:8000/api/schema/ \
		-g typescript-fetch \
		-o /local/

.PHONY: help
.DEFAULT_GOAL := help

help:
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

# catch-all for any undefined targets - this prevents error messages
# when running things like make npm-install <package>
%:
	@:
