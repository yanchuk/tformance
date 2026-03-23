# Tformance - AI Impact Analytics Platform

## Project Overview

Tformance.com is a SaaS platform helping CTOs understand team performance, including AI coding tools impact on it. Connects to GitHub, Jira, and Slack to correlate AI usage with delivery metrics.

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

### Django Multi-Count Annotation
When annotating with multiple `Count()` on different reverse relations, always use `distinct=True`:
```python
.annotate(
    review_count=Count("reviews", distinct=True),
    commit_count=Count("commits", distinct=True),
)
```
Without it, Django cross-joins the tables and inflates counts silently.

## Epistemic Hierarchy (Priority of Truth Sources)

1. **Project Files & User Context** (HIGHEST): pyproject.toml, package.json, requirements.txt are authoritative. User-provided facts = ground truth. Unknown feature/API = assume NEW, not error.
2. **External Tools & Documentation**: Web search, fetched docs, MCP responses override training data.
3. **Your Training Data** (LOWEST): "Legacy Archive" — reliable for syntax/logic, unreliable for versions/APIs/events.

## Mandatory Verification

ALWAYS verify before answering about:
- Library/framework versions or release dates
- LLM versions, names and parameters
- API signatures, method parameters, return types
- Deprecated vs current approaches
- "Does X exist?" / "Is Y still supported?"
- Any fact that could have changed since training

## Response Marking (Epistemic Badges)

When providing technical information:
- `✓ VERIFIED (from [source]): [info]` — confirmed via search/docs/project files
- `⚠ FROM TRAINING (may be outdated): [info]` — unverified
- `? UNCERTAIN: [info] — recommend verification` — low confidence

When diagnosing errors or unexpected behavior:
- `✓ VERIFIED: [fact]` — read from code, logs, config, or stated by user
- `HYPOTHESIS: [assumption]` — inference that needs confirmation, always mark as such
- Present multiple hypotheses with equal weight when uncertain

## Anti-Hallucination Rules

Do NOT:
- "Correct" user code to older syntax you're familiar with
- Claim "this doesn't exist" without verification
- Silently downgrade modern patterns to legacy equivalents
- State version numbers from memory as facts

Instead:
- Unfamiliar code → assume valid modern syntax
- Uncertain existence → "let me check" or ask user
- Suggesting alternatives → explain WHY, confirm user's version first
- Stating versions → mark as "from training, verify current"

## Version Handling

1. Check project files (pyproject.toml, package.json) FIRST
2. Version specified → use THAT version's API
3. No version info → ASK user
4. User states version → trust it, even if unfamiliar

## Permission to Say "I Don't Know"

You are explicitly encouraged to say:
- "I'm not certain about the current API — let me check"
- "This might have changed since my training"
- "I don't recognize this, but assuming it's valid modern syntax"

Admitting uncertainty is BETTER than confident hallucination.

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
- `{% trans "..." %}` in templates → use plain strings (i18n disabled)
- `gettext_lazy`/`_()` in Python → use plain strings
- `Count("relation")` without `distinct=True` in multi-relation annotate → inflated counts
- Mocking external services without verifying method names exist → tests pass, production crashes
- `isinstance()` guards for MagicMock in production code → fix the test mock instead

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

## gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

Available skills:
- `/office-hours` — brainstorm and strategize
- `/plan-ceo-review` — CEO-level plan review
- `/plan-eng-review` — engineering plan review
- `/plan-design-review` — design plan review
- `/design-consultation` — design system guidance
- `/review` — code review before merge
- `/ship` — create PR / deploy
- `/land-and-deploy` — production deployment
- `/canary` — canary deployment
- `/benchmark` — performance benchmarking
- `/browse` — headless browser (use for all web browsing)
- `/qa` — QA testing
- `/qa-only` — QA without code changes
- `/design-review` — visual design audit
- `/setup-browser-cookies` — configure browser auth
- `/setup-deploy` — configure deployment
- `/retro` — retrospective
- `/investigate` — debug errors
- `/document-release` — post-ship docs
- `/codex` — cross-model code review
- `/careful` — production safety mode
- `/freeze` — scope edits to one module
- `/guard` — maximum safety mode
- `/unfreeze` — remove edit restrictions
- `/gstack-upgrade` — upgrade gstack
