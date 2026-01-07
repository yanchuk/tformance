# Tformance - AI Impact Analytics Platform

## Project Overview

Tformance is SaaS platform helping CTOs understand if AI coding tools are improving team performance. Connects to GitHub, Jira, and Slack to correlate AI usage with delivery metrics.

## Project development concept

**Main concepts**:
- We use localhost:8000 for most of development.
- We use cloudflare tunnel to run localhost on http://dev.ianchuk.com.
- https://Dev2.ianchuk.com is our app running in docker in Unraid, not auto updated and required `make dev2` command to build image and some time for Watchtower on Unraid to pull an update.
- If our changes are significant and might interference with other ongoing tasks we use git worktrees and after merge.
- Ongoing tasks and documentation are listed in /dev having /dev/active and /dev/completed tasks descriptions.
- Sometimes in /dev/active might be already completed and not moved to /dev/completed plans.
- We try to use /dev-docs command as often as possible to create new feature or large scope changes so we create proper plans in /dev/active those help to keep context in case of context window compact.
- We use feature flags (django waffle) and for MVP Alpha we rely only on Github data without connecting Jira, Slack, Copilot.
- We use Groq for LLM processing. We try always use Batches in Groq if it makes sense for scheduled tasks or onboarding PR batches processing as it saves costs by 50% and almost real-time.
- Always prioritize "Django way" of doing things and appreciate framework capabilities and best practices.
- We are following TDD (test-driven development) style.
- Always try to fix a root cause, not just manually fix something right now (more related to data issues).
- Behave as as senior engineer when you investigate issues. Make sure that you have needed logs (if not - suggest to add), do debug and look at the issue from different angles. 

## Documentation

**Product Requirements** (`/prd/`):
- [PRD-MVP.md](prd/PRD-MVP.md) - Main product spec
- [ARCHITECTURE.md](prd/ARCHITECTURE.md) - Technical architecture
- [DATA-MODEL.md](prd/DATA-MODEL.md) - Database schema
- [AI-DETECTION-TESTING.md](prd/AI-DETECTION-TESTING.md) - AI detection workflows

**Development Guides** (`/dev/guides/`):
- [COMMANDS-REFERENCE.md](dev/guides/COMMANDS-REFERENCE.md) - All make/pytest/npm commands
- [CODE-GUIDELINES.md](dev/guides/CODE-GUIDELINES.md) - Python, JS, Django patterns
- [TESTING-GUIDE.md](dev/guides/TESTING-GUIDE.md) - TDD, factories, E2E testing
- [DESIGN-SYSTEM.md](dev/guides/DESIGN-SYSTEM.md) - Colors, DaisyUI, CSS classes
- [FRONTEND-PATTERNS.md](dev/guides/FRONTEND-PATTERNS.md) - HTMX, Alpine.js, charts
- [EXTERNAL-INTEGRATIONS.md](dev/guides/EXTERNAL-INTEGRATIONS.md) - PyGithub, Jira, Slack
- [POSTHOG-ANALYTICS.md](dev/guides/POSTHOG-ANALYTICS.md) - Event tracking
- [HEROKU-DEPLOYMENT.md](dev/guides/HEROKU-DEPLOYMENT.md) - Docker deployment
- [AUTHENTICATION-FLOWS.md](dev/guides/AUTHENTICATION-FLOWS.md) - OAuth patterns

## Key Decisions (Do Not Change Without Discussion)

| Decision | Choice | Why |
|----------|--------|-----|
| **Hosting** | Heroku (Docker) | Full platform: dynos, Postgres, Redis |
| Client data | Single DB (team-isolated) | Faster MVP, lower friction |
| Dashboards | Native (Chart.js + HTMX) | Full design control |
| Sync frequency | Daily | Simpler than real-time |
| AI data source | Detection from PRs by keyword patterns, LLM processing. Later with Surveys and Copilot data | PR analytics doesn't require actions, Copilot for 5+ licenses, Surveys will help |

## Integrations

| Service | Auth | Scope |
|---------|------|-------|
| GitHub | OAuth (But planned to move to Github App for more refined access) | `read:org`, `repo`, `read:user` |
| Jira | OAuth (Atlassian) | `read:jira-work`, `read:jira-user` |
| Slack | OAuth | `chat:write`, `users:read`, `users:read.email` |
| Copilot | Via GitHub OAuth | `manage_billing:copilot` |

## Copilot Mock Data System

GitHub requires 5+ Copilot licenses to access the metrics API. For development and testing without real Copilot access, use the mock data system.

### Quick Start

```bash
# Seed demo Copilot data for a team
.venv/bin/python manage.py seed_copilot_demo --team=my-team --scenario=growth --weeks=8

# With PR correlation (marks PRs as AI-assisted based on Copilot usage)
.venv/bin/python manage.py seed_copilot_demo --team=my-team --scenario=mixed_usage --correlate-prs

# Clear existing and reseed
.venv/bin/python manage.py seed_copilot_demo --team=my-team --scenario=high_adoption --clear-existing
```

### Enable Mock Mode for API Calls

Add to `.env` or Django settings to make `fetch_copilot_metrics()` return mock data instead of real API calls:

```bash
COPILOT_USE_MOCK_DATA=True
COPILOT_MOCK_SEED=42           # For reproducible data
COPILOT_MOCK_SCENARIO=mixed_usage
```

### Available Scenarios

| Scenario | Acceptance Rate | Description |
|----------|-----------------|-------------|
| `high_adoption` | 40-55% | Power users, high acceptance |
| `low_adoption` | 15-30% | Struggling team, low acceptance |
| `growth` | 20% → 50% | Improving adoption over time |
| `decline` | 50% → 20% | Declining usage over time |
| `mixed_usage` | Variable | Realistic mix of user types (default) |
| `inactive_licenses` | Some 0% | Users with licenses but no usage |

### Key Files

| File | Purpose |
|------|---------|
| `apps/integrations/services/copilot_mock_data.py` | `CopilotMockDataGenerator` class |
| `apps/integrations/services/copilot_metrics.py` | API client with mock mode toggle |
| `apps/integrations/services/copilot_pr_correlation.py` | Correlate PRs with Copilot usage |
| `apps/integrations/services/copilot_metrics_prompt.py` | Aggregate metrics for LLM prompts |
| `apps/metrics/management/commands/seed_copilot_demo.py` | Management command |
| `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2` | LLM prompt template |

### Using in Code

```python
# Generate mock data directly
from apps.integrations.services.copilot_mock_data import CopilotMockDataGenerator

generator = CopilotMockDataGenerator(seed=42)
data = generator.generate(since="2025-01-01", until="2025-01-31", scenario="growth")

# Fetch metrics (respects COPILOT_USE_MOCK_DATA setting)
from apps.integrations.services.copilot_metrics import fetch_copilot_metrics

metrics = fetch_copilot_metrics(access_token, org_slug, since="2025-01-01")

# Correlate PRs with Copilot usage
from apps.integrations.services.copilot_pr_correlation import correlate_prs_with_copilot_usage

count = correlate_prs_with_copilot_usage(team, min_suggestions=1)

# Get metrics for LLM prompts
from apps.integrations.services.copilot_metrics_prompt import get_copilot_metrics_for_prompt

prompt_data = get_copilot_metrics_for_prompt(team, start_date, end_date)
```

### Generated Data Format

Mock data matches the exact GitHub Copilot Metrics API schema:

```json
{
  "date": "2025-01-06",
  "total_active_users": 15,
  "total_engaged_users": 12,
  "copilot_ide_code_completions": {
    "total_completions": 2500,
    "total_acceptances": 875,
    "total_lines_suggested": 4200,
    "total_lines_accepted": 1470,
    "languages": [...],
    "editors": [...]
  },
  "copilot_ide_chat": { "total_chats": 45 },
  "copilot_dotcom_chat": { "total_chats": 12 },
  "copilot_dotcom_pull_requests": { "total_prs": 5 }
}
```

## AI Detection System

> Full details: [AI-DETECTION-TESTING.md](prd/AI-DETECTION-TESTING.md)

### LLM Data Priority Rule

**Always prioritize LLM-detected data over pattern/regex detection.** Use `effective_*` properties:

| Property | LLM Source | Fallback |
|----------|------------|----------|
| `pr.effective_is_ai_assisted` | `llm_summary.ai.is_assisted` (≥0.5) | `is_ai_assisted` |
| `pr.effective_ai_tools` | `llm_summary.ai.tools` | `ai_tools_detected` |
| `pr.effective_tech_categories` | `llm_summary.tech.categories` | `PRFile.file_category` |

### Pattern Versioning

When adding regex patterns:
1. Update `AI_SIGNATURE_PATTERNS` in `apps/metrics/services/ai_patterns.py`
2. Increment `PATTERNS_VERSION`
3. Run `.venv/bin/python manage.py backfill_ai_detection`

### Prompt Changes (REQUIRE APPROVAL)

Before modifying `apps/metrics/prompts/templates/*`:
1. Explain change and show diff
2. **Wait for user approval**
3. Bump `PROMPT_VERSION` in `llm_prompts.py`
4. Run `make export-prompts && npx promptfoo eval`

## Django Apps Overview

| App | Purpose |
|-----|---------|
| `apps/integrations` | GitHub, Jira, Slack integrations |
| `apps/metrics` | Core metrics models & services |
| `apps/dashboard` | Dashboard views |
| `apps/onboarding` | User onboarding flow |
| `apps/teams` | Multi-tenancy |
| `apps/users` | User management |
| `apps/insights` | AI-powered insights |
| `apps/pullrequests` | PR-specific features |
| `apps/subscriptions` | Billing & plans |
| `apps/api` | OpenAPI/REST framework |

## Architecture

- **Django 3.12** with `django-allauth` for auth
- **HTMX + Alpine.js** for SPA-like experience with Django templates
- **Tailwind v4 + DaisyUI** for styling
- **Celery + Redis** for background jobs
- **PostgreSQL** as main database
- **Vite** for frontend bundling via `django-vite`

## Critical Rules

### Python Virtual Environment

**Always use `.venv/bin/` for Python commands:**

| Instead of | Use |
|------------|-----|
| `python` | `.venv/bin/python` |
| `pytest` | `.venv/bin/pytest` |
| `celery` | `.venv/bin/celery` |

```bash
.venv/bin/python manage.py <command>
.venv/bin/pytest apps/myapp/tests/
```

### Async Pattern Warning

**Never use `asyncio.run()` in Django contexts - use `async_to_sync()` instead.**

```python
# WRONG - breaks thread-local DB connections
result = asyncio.run(async_function())

# CORRECT
from asgiref.sync import async_to_sync
result = async_to_sync(async_function)()
```

Applies to: Celery tasks, sync views, signal handlers, middleware.

### Team Isolation (TEAM001)

All `BaseTeamModel` queries must include team filtering:

```python
# Safe
Model.objects.filter(team=team)
Model.for_team.filter(...)

# Unsafe - flagged by linter
Model.objects.filter(state='merged')  # Missing team!
```

Suppress when intentional: `# noqa: TEAM001 - ID from Celery task`

### Celery on macOS

Always use `make celery` or `--pool=solo`. Default `prefork` pool causes SIGSEGV crashes.

### TDD Requirement

All new features use Red-Green-Refactor cycle. See [TESTING-GUIDE.md](dev/guides/TESTING-GUIDE.md).

## Django Development Rules

### Models

**Always extend the correct base class:**

```python
# Team-owned data (most common) - includes team field
from apps.teams.models import BaseTeamModel

class PullRequest(BaseTeamModel):
    title = models.CharField(max_length=255)

# Global data (rare) - no team field
from apps.utils.models import BaseModel

class GlobalConfig(BaseModel):
    key = models.CharField(max_length=100)
```

### Views

**Use function-based views with proper decorators:**

```python
from apps.teams.decorators import login_and_team_required, team_admin_required

@login_and_team_required
def dashboard(request, team_slug):
    team = request.team  # Set by decorator
    data = MyModel.for_team.filter(...)
    return render(request, "app/dashboard.html", {"data": data})

@team_admin_required  # Admin-only access
def settings(request, team_slug):
    pass
```

### URLs

```python
# apps/myapp/urls.py
urlpatterns = []  # Non-team URLs (rare)

# Team-scoped → /a/<team_slug>/myapp/...
team_urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
```

### Queries

```python
# Always use for_team manager for team-scoped data
items = MyModel.for_team.filter(state="active")

# Optimize with select_related/prefetch_related
prs = PullRequest.for_team.select_related("author").prefetch_related("reviews")
```

### Anti-Patterns to Avoid

- ❌ Class-based views (use function-based, except DRF)
- ❌ `objects.filter(team=team)` → use `for_team` manager
- ❌ Business logic in views → extract to services
- ❌ N+1 queries → use `select_related`/`prefetch_related`
- ❌ Files over 200-300 lines → split into modules

## Frontend Rules

### HTMX Partials

**Never use inline `<script>` tags in HTMX partials** - they won't execute after swaps. Use Alpine.js components or ChartManager instead.

### DaisyUI Colors

**Always use semantic DaisyUI colors, never hardcoded Tailwind:**

| Use | Avoid |
|-----|-------|
| `text-base-content` | `text-white`, `text-gray-*` |
| `bg-base-100`, `bg-base-200` | `bg-gray-800`, `bg-neutral-*` |
| `text-success`, `text-error` | `text-green-*`, `text-red-*` |
| `border-base-300` | `border-gray-*` |

## Code Style

### Python

- Follow PEP 8 with **120 character line limit**
- Use **double quotes** for strings (ruff enforced)
- Sort imports with isort (via ruff)
- Use type hints in new code (not strictly enforced)
- Use Django signals sparingly and document them well
- Always validate user input server-side
- Handle errors explicitly, avoid silent failures

### JavaScript

- Use ES6+ syntax with **2 spaces** for indentation
- Use **single quotes** for strings
- End statements with semicolons
- Use camelCase for variables/functions, PascalCase for components
- Use generated OpenAPI client for API calls (not raw fetch/axios)
- Handle errors explicitly in promises/async functions

## TDD Workflow

**All new features MUST use Red-Green-Refactor cycle.**

### Before Starting Any Implementation

1. Run existing tests first: `make test` to ensure passing state
2. Check `apps/<app>/tests/` for related test files
3. Never break existing tests

### RED Phase - Write Failing Test First
- Write test describing expected behavior
- Run test and confirm it **fails** (proves test is valid)
- Do NOT write implementation code yet

### GREEN Phase - Make It Pass
- Write **minimum** code needed to pass
- No extra features, no "nice to haves"
- Run test and confirm it **passes**

### REFACTOR Phase - Improve
- Clean up while keeping tests green
- Extract reusable code, improve naming
- Run tests after each change

## Factory Guidelines

**Always use Factory Boy for test data:**

```python
from apps.metrics.factories import PullRequestFactory, TeamMemberFactory

def test_pr_metrics(self):
    member = TeamMemberFactory(team=self.team)
    pr = PullRequestFactory(team=self.team, author=member)
```

- `Factory.build()` for unit tests (doesn't save to DB)
- `Factory.create()` or `Factory()` for integration tests (saves to DB)
- `Factory.create_batch(n)` to create multiple instances
- Use `factory.Sequence` for unique fields to avoid constraint violations

**Available Factories:**
- `apps/metrics/factories.py`: TeamFactory, TeamMemberFactory, PullRequestFactory, PRReviewFactory, CommitFactory
- `apps/feedback/factories.py`, `apps/integrations/factories.py`, `apps/notes/factories.py`

## Design System

> **DO NOT CHANGE THEME COLORS WITHOUT EXPLICIT USER APPROVAL**

### Color Usage (DaisyUI Semantic Colors Only)

| Use Case | Correct Class | Avoid |
|----------|--------------|-------|
| Primary text | `text-base-content` | `text-white`, `text-stone-*` |
| Secondary text | `text-base-content/80` | `text-gray-400` |
| Backgrounds | `bg-base-100`, `bg-base-200` | `bg-deep`, `bg-neutral-*` |
| Borders | `border-base-300` | `border-elevated`, `border-neutral-*` |
| Success | `text-success`, `app-status-connected` | `text-emerald-*`, `text-green-*` |
| Error | `text-error` | `text-red-*` |
| Primary accent | `text-primary`, `bg-primary` | `text-orange-*` |

### CSS Utility Classes

Use `app-*` prefixed classes from `design-system.css`:
- Cards: `app-card`, `app-card-interactive`
- Buttons: `app-btn-primary`, `app-btn-secondary`
- Stats: `app-stat-value`, `app-stat-value-positive`, `app-stat-value-negative`
- Status: `app-status-connected`, `app-status-disconnected`, `app-status-error`

### Fonts
- **DM Sans** - UI text, headings
- **JetBrains Mono** - Code, metrics, data values

## HTMX + Alpine.js Patterns

### Critical Rules

1. **NEVER use inline `<script>` tags in HTMX partials** - They won't execute after swaps
2. Use `Alpine.store()` for state that must persist across HTMX navigation
3. Use `ChartManager` for all chart initialization

### Alpine Stores

```javascript
// Access in templates via $store
<button @click="$store.dateRange.setDays(7)"
        :class="{'btn-primary': $store.dateRange.isActive(7)}">7d</button>
```

Available: `$store.dateRange`, `$store.metrics`

### Template Best Practices

```html
<!-- DO: Use data attributes for chart config -->
<canvas id="my-chart" data-chart-data-id="my-chart-data"></canvas>
{{ chart_data|json_script:"my-chart-data" }}

<!-- DON'T: Inline scripts in partials -->
<script>new Chart(...)</script>  <!-- Won't execute after HTMX swap! -->
```

## General Coding Preferences

- **Run tests before committing**: `make test`
- Prefer simple solutions
- Avoid code duplication - check for existing patterns
- Only make changes that are requested or clearly necessary
- Keep files under 200-300 lines; refactor when exceeded
- Don't add mock data to production functions (tests only)
- Never overwrite `.env` without asking
- When fixing bugs, don't introduce new patterns - exhaust existing options first

### File Splitting Convention

When files exceed limits, split into directories:
- `models.py` (>500 lines) → `models/` with domain files
- `views.py` (>500 lines) → `views/` with feature files
- Always include `__init__.py` with re-exports for backward compatibility
- Make sure test files are also granular and avoid having huge files if there is an option to make atomic ones and it makes sense

## External Integrations

### Library Selection Hierarchy

**Always prefer official SDKs/libraries over direct API calls:**

1. **Official SDK/library** - Published and maintained by service provider
2. **Well-maintained 3rd party library** - Popular, actively maintained, good docs
3. **Direct API calls** - Last resort when no suitable library exists

| Service | Library | Package | Notes |
|---------|---------|---------|-------|
| GitHub | PyGithub (REST), gql (GraphQL) | `PyGithub`, `gql` | REST for simple ops, GraphQL for bulk |
| Jira | jira-python | `jira` | Most popular, well-maintained |
| Slack | slack-sdk | `slack-sdk` | Official Slack SDK |

### Why Libraries Over Direct API

- **Pagination handling** - Automatic cursor-based pagination
- **Rate limiting** - Built-in retry logic and rate limit respect
- **Authentication** - Token refresh, OAuth flows handled
- **Error handling** - Typed exceptions, clear error messages
- **Testing** - Easier to mock library objects than raw HTTP

### GitHub GraphQL API

**Use GraphQL for bulk operations** (PRs, commits, files). REST for single-item operations.

```python
# GraphQL client location
from apps.integrations.services.github_graphql import GitHubGraphQLClient

# Main sync functions
from apps.integrations.services.github_graphql_sync import (
    sync_repository_history_graphql,      # Full historical sync
    sync_repository_history_by_search,    # Date-filtered sync
    sync_repository_incremental_graphql,  # Since last sync
    fetch_pr_complete_data_graphql,       # Single PR
    sync_github_members_graphql,          # Org members
)
```

**GraphQL Best Practices:**
- Use `first: 10-25` for queries with nested connections
- Include `rateLimit { remaining resetAt }` in all queries
- Handle `GitHubGraphQLRateLimitError` (5000 points/hour limit)
- Use exponential backoff for timeouts

### Context7 for Documentation

Use Context7 MCP server for up-to-date library documentation:
```
mcp__context7__resolve-library-id(libraryName="PyGithub")
mcp__context7__query-docs(libraryId="/...", query="pull requests")
```

## Testing

### Command Reference

```bash
make test                                    # Run all tests (parallel)
make test ARGS='apps.module.tests.test_file' # Run specific module
make test ARGS='-k test_name'                # Run tests matching pattern
make test-serial                             # Without parallelization
make test-slow                               # Show 20 slowest tests
make test-coverage                           # With coverage report
make test-fresh                              # Fresh database

# pytest-specific
.venv/bin/pytest apps/metrics -v             # Verbose output
.venv/bin/pytest --lf                        # Run last failed only
.venv/bin/pytest -x                          # Stop on first failure
```

### E2E Testing (Playwright)

**Requires dev server running.** Test credentials: `admin@example.com` / `admin123`

```bash
make e2e              # Run all E2E tests
make e2e-smoke        # Smoke tests only (~4s)
make e2e-ui           # Open Playwright UI
```

Key test suites in `tests/e2e/`:
- `smoke.spec.ts`, `auth.spec.ts`, `dashboard.spec.ts`
- `htmx-error-handling.spec.ts`, `htmx-navigation.spec.ts`

### Visual Verification with Playwright MCP

```python
# 1. Navigate to page
mcp__playwright__browser_navigate(url="http://localhost:8000/...")
# 2. Capture state
mcp__playwright__browser_snapshot()
# 3. Screenshot for visual confirmation
mcp__playwright__browser_take_screenshot()
```

## Quick Commands

```bash
make dev              # Start dev server
make test             # Run all tests
make celery           # Start Celery worker
make ruff             # Format and lint
make e2e              # E2E tests
make lint-team-isolation  # Check team isolation
```

Full reference: [COMMANDS-REFERENCE.md](dev/guides/COMMANDS-REFERENCE.md)

## Data Flow

```
GitHub/Jira APIs → Backend → PostgreSQL → Dashboard (Chart.js) → User
                                    ↓
                              Slack Bot (surveys)
```
