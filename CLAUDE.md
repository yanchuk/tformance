# Tformance - AI Impact Analytics Platform

## Project Overview

Tformance is a SaaS platform helping CTOs understand if AI coding tools are improving team performance. Connects to GitHub, Jira, and Slack to correlate AI usage with delivery metrics.

**Built on [Pegasus SaaS](https://www.saaspegasus.com/)** Django boilerplate.

## Tech Stack

- **Django 5.2.9 with Python 3.12** with django-allauth for auth
- **HTMX + Alpine.js** for SPA-like experience
- **Tailwind v4 + DaisyUI** for styling
- **Celery + Redis** for background jobs
- **PostgreSQL** database
- **Vite** for frontend bundling via django-vite

## Development Setup

- Local dev: `localhost:8000`
- Cloudflare tunnel: `http://dev.ianchuk.com`
- Docker staging: `https://dev2.ianchuk.com` (requires `make dev2`)
- Feature flags via Django Waffle
- LLM processing via Groq (with batch mode for 50% cost savings)

## Quick Commands

```bash
make dev              # Start dev server
make test             # Run all tests (parallel)
make celery           # Start Celery worker (macOS-safe)
make ruff             # Format and lint
make e2e              # E2E tests (requires dev server)
```

Full reference: [dev/guides/COMMANDS-REFERENCE.md](dev/guides/COMMANDS-REFERENCE.md)

## Critical Rules (Will Cause Bugs If Violated)

### Python Virtual Environment
Always use `.venv/bin/` prefix:
- `.venv/bin/python manage.py <command>`
- `.venv/bin/pytest apps/myapp/tests/`

### Team Isolation (TEAM001) - Security Critical
All `BaseTeamModel` queries MUST filter by team:
```python
# Safe
Model.for_team.filter(...)

# Unsafe - data leak risk
Model.objects.filter(state='merged')  # Missing team!
```
Suppress when intentional: `# noqa: TEAM001 - reason`

### Async Pattern
Never use `asyncio.run()` in Django - use `async_to_sync()` instead.
Applies to: Celery tasks, views, signals, middleware.

### Celery on macOS
Always use `make celery` or `--pool=solo`. Default prefork causes SIGSEGV.

### Prompt Changes Require Approval
Before modifying `apps/metrics/prompts/templates/*`:
1. Explain change and show diff
2. **Wait for user approval**
3. Bump `PROMPT_VERSION` in `apps/metrics/prompts/constants.py`

### LLM Data Priority
Always use `effective_*` properties on PullRequest (not raw fields).
See [AI-DETECTION-TESTING.md](prd/AI-DETECTION-TESTING.md#llm-data-priority-rule).

## Key Decisions (Do Not Change Without Discussion)

| Decision | Choice | Why |
|----------|--------|-----|
| Hosting | Heroku (Docker) | Full platform: dynos, Postgres, Redis |
| Client data | Single DB (team-isolated) | Faster MVP, lower friction |
| Dashboards | Native (Chart.js + HTMX) | Full design control |
| Sync frequency | Daily | Simpler than real-time |
| AI detection | PR patterns + LLM | No extra setup required |

## Django Apps

| App | Purpose |
|-----|---------|
| `apps/integrations` | GitHub, Jira, Slack connections |
| `apps/metrics` | Core metrics models & services |
| `apps/dashboard` | Dashboard views |
| `apps/teams` | Multi-tenancy |
| `apps/users` | User management |
| `apps/insights` | AI-powered insights |
| `apps/pullrequests` | PR-specific features |
| `apps/subscriptions` | Billing & plans |
| `apps/onboarding` | User onboarding flow |

## Anti-Patterns to Avoid

- Class-based views → use function-based (except DRF)
- `objects.filter(team=team)` → use `for_team` manager
- Business logic in views → extract to services
- N+1 queries → use `select_related`/`prefetch_related`
- Files over 300 lines → split into modules
- Inline `<script>` in HTMX partials → use Alpine.js

## Documentation

**Product Requirements** (`prd/`):
- [PRD-MVP.md](prd/PRD-MVP.md) - Product spec
- [ARCHITECTURE.md](prd/ARCHITECTURE.md) - Technical architecture
- [DATA-MODEL.md](prd/DATA-MODEL.md) - Database schema
- [AI-DETECTION-TESTING.md](prd/AI-DETECTION-TESTING.md) - AI detection & LLM processing

**Development Guides** (`dev/guides/`):
- [COMMANDS-REFERENCE.md](dev/guides/COMMANDS-REFERENCE.md) - All make/pytest/npm commands
- [TESTING-GUIDE.md](dev/guides/TESTING-GUIDE.md) - TDD, factories, E2E testing
- [FRONTEND-PATTERNS.md](dev/guides/FRONTEND-PATTERNS.md) - HTMX, Alpine.js, charts
- [DESIGN-SYSTEM.md](dev/guides/DESIGN-SYSTEM.md) - Colors, DaisyUI, components
- [EXTERNAL-INTEGRATIONS.md](dev/guides/EXTERNAL-INTEGRATIONS.md) - GitHub, Jira, Slack APIs
- [COPILOT-DEVELOPMENT.md](dev/guides/COPILOT-DEVELOPMENT.md) - Mock data for Copilot features

**Active Development**: Check `dev/active/` for ongoing tasks and context.

## TDD Requirement

All new features use Red-Green-Refactor cycle. See [TESTING-GUIDE.md](dev/guides/TESTING-GUIDE.md).

## Data Flow

```
GitHub/Jira APIs → Backend → PostgreSQL → Dashboard (Chart.js) → User
                                    ↓
                              Slack Bot (surveys)
```
