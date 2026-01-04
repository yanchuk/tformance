# Tformance - AI Impact Analytics Platform

## Project Overview

Tformance is SaaS platform helping CTOs understand if AI coding tools are improving team performance. Connects to GitHub, Jira, and Slack to correlate AI usage with delivery metrics.

## Project development concept

**Main concepts**:
- We use localhost:8000 for most of development.
- We use cloudflare tunnel to run localhost on dev.ianchuk.com.
- Dev2.ianchuk.com is our app running in docker in Unraid, not auto updated and required `make dev2` command to build image and some time for Watchtower on Unraid to pull an update.
- If our changes are significant and might interference with other ongoing tasks we use git worktrees and after merge.
- Ongoing tasks and documentation are listed in /dev having /dev/active and /dev/completed tasks descriptions.
- Sometimes in /dev/active might be already completed and not moved to /dev/completed plans.
- We try to use /dev-docs command as often as possible to create new feature or large scope changes so we create proper plans in /dev/active those help to keep context in case of context window compact.
- We use feature flags (django waffle) and for MVP Alpha we rely only on Github data without connecting Jira, Slack, Copilot.
- We use Groq for LLM processing. We try always use Batches in Groq if it makes sense for scheduled tasks or onboarding PR batches processing as it saves costs by 50% and almost real-time.

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

### Testing with Factories

**Always use Factory Boy for test data:**

```python
from apps.metrics.factories import PullRequestFactory, TeamMemberFactory

def test_pr_metrics(self):
    member = TeamMemberFactory(team=self.team)
    pr = PullRequestFactory(team=self.team, author=member)
```

Use `factory.Sequence` for unique fields to avoid constraint violations.

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

## Quick Commands

```bash
make dev              # Start dev server
make test             # Run all tests
make celery           # Start Celery worker
make ruff             # Format and lint
```

Full reference: [COMMANDS-REFERENCE.md](dev/guides/COMMANDS-REFERENCE.md)

## Data Flow

```
GitHub/Jira APIs → Backend → PostgreSQL → Dashboard (Chart.js) → User
                                    ↓
                              Slack Bot (surveys)
```
