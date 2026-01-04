# Commands Reference

> Back to [CLAUDE.md](../../CLAUDE.md)

A `Makefile` is provided to help centralize commands:

```bash
make  # List available commands
```

## First-time Setup

```bash
make init
```

## Starting the Application

Start background services:

```bash
make start     # Run in foreground with logs
make start-bg  # Run in background
```

Start the app:

```bash
make dev       # Run in foreground with logs
```

Access the app at http://localhost:8000

Start Celery worker (required for background tasks like sync, LLM analysis):

```bash
make celery    # Starts worker + beat with --pool=solo
```

**macOS Celery Warning**: Always use `make celery` or `--pool=solo`. The default `prefork` pool causes **SIGSEGV crashes** on macOS.

## Stopping Services

```bash
make stop
```

## Common Development Commands

```bash
make shell            # Open Python / Django shell
make dbshell          # Open PostgreSQL shell
make manage ARGS='command'  # Run any Django management command
```

## Database

```bash
make migrations       # Create new migrations
make migrate          # Apply migrations
```

## Testing

Tests run with **pytest**. The test suite has ~4900 tests.

```bash
# Basic commands
make test                                     # Run all tests (parallel by default)
make test ARGS='apps.module.tests.test_file'  # Run specific test module
make test ARGS='-k test_name'                 # Run tests matching pattern

# Advanced commands
make test-serial                              # Run tests without parallelization
make test-slow                                # Show 20 slowest tests (--durations)
make test-coverage                            # Run with coverage report
make test-fresh                               # Fresh database (when models change)
make test-django                              # Fallback to Django test runner

# pytest-specific options (always use venv)
.venv/bin/pytest apps/metrics -v                        # Verbose output
.venv/bin/pytest --lf                                   # Run last failed tests only
.venv/bin/pytest -x                                     # Stop on first failure
.venv/bin/pytest -p randomly --randomly-seed=12345      # Reproducible random order
```

**Speed Tips:**
- `make test` runs in parallel by default with `--reuse-db` (~94s for full suite)
- Use `make test-serial` to disable parallelization for debugging
- Use `make test-slow` to identify optimization candidates
- Use `make test-fresh` after adding new migrations

## E2E Testing (Playwright)

E2E tests verify user flows in a real browser. **Requires dev server running.**

```bash
make e2e              # Run all E2E tests
make e2e-smoke        # Run smoke tests only (fast, ~4s)
make e2e-auth         # Authentication tests
make e2e-dashboard    # Dashboard tests
make e2e-ui           # Open Playwright UI for debugging
make e2e-report       # View test report
```

**Test Credentials:** `admin@example.com` / `admin123`

## Code Quality

```bash
make ruff-format      # Format code
make ruff-lint        # Lint and auto-fix
make ruff             # Run both format and lint
```

## Python Package Management

```bash
make uv add '<package>'         # Add a new package
make uv run '<command> <args>'  # Run a Python command
```

## Frontend

```bash
make npm-install      # Install npm packages
make npm-install package-name  # Install specific package
make npm-uninstall package-name  # Uninstall package
make npm-dev          # Run the Vite development server
make npm-build        # Build for production
make npm-type-check   # Run TypeScript type checking
```

Note: Vite runs automatically with hot-reload when using `make dev`.

## Code Generation

```bash
make uv run 'pegasus startapp <app_name> <Model1> <Model2Name>'  # Start a new Django app
```

## AI Detection Tools

```bash
make export-prompts                                        # Generate promptfoo.yaml from templates
.venv/bin/python manage.py run_llm_analysis --limit 50    # Analyze PRs with LLM
.venv/bin/python manage.py backfill_ai_detection          # Backfill regex detection
```

## Demo Data Seeding

```bash
.venv/bin/python manage.py seed_demo_data              # Seed default demo data
.venv/bin/python manage.py seed_demo_data --clear      # Clear and reseed
.venv/bin/python manage.py seed_demo_data --prs 100    # Custom amounts

# Scenario-based seeding (recommended for coherent demo data)
.venv/bin/python manage.py seed_demo_data --scenario ai-success --seed 42
.venv/bin/python manage.py seed_demo_data --list-scenarios  # Show all scenarios
```

See `dev/DEV-ENVIRONMENT.md` for full options including all 4 scenarios.

## Public Report (AI Impact Analysis)

The `public_report/index.html` is a standalone HTML report analyzing AI tool adoption.

```bash
make build-report  # Build public_report/index.html from templates
```

See `public_report/templates/README.md` for template documentation.
