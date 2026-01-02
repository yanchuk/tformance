# Tformance - AI Impact Analytics Platform

## Project Overview

Tformance is a SaaS platform helping CTOs understand if AI coding tools are actually improving their team's performance. Connects to GitHub, Jira, and Slack to correlate AI usage with delivery metrics.

## Documentation

All product requirements are in `/prd/`:
- [PRD-MVP.md](prd/PRD-MVP.md) - Main product spec
- [IMPLEMENTATION-PLAN.md](prd/IMPLEMENTATION-PLAN.md) - Build phases & order
- [ARCHITECTURE.md](prd/ARCHITECTURE.md) - Technical architecture
- [DATA-MODEL.md](prd/DATA-MODEL.md) - Database schema
- [SLACK-BOT.md](prd/SLACK-BOT.md) - Bot specification
- [DASHBOARDS.md](prd/DASHBOARDS.md) - Dashboard views
- [ONBOARDING.md](prd/ONBOARDING.md) - User flow
- [AI-DETECTION-TESTING.md](prd/AI-DETECTION-TESTING.md) - AI detection testing tools & workflow
- [PROMPT-ENGINEERING.md](prd/PROMPT-ENGINEERING.md) - LLM prompt best practices (Anthropic guidelines)

Development guides in `/dev/guides/`:
- [HEROKU-DEPLOYMENT.md](dev/guides/HEROKU-DEPLOYMENT.md) - Heroku Docker deployment (staging & production)
- [AUTHENTICATION-FLOWS.md](dev/guides/AUTHENTICATION-FLOWS.md) - OAuth and auth patterns
- [REAL-WORLD-TESTING.md](dev/guides/REAL-WORLD-TESTING.md) - Testing with real integrations

**Read these before implementing features.**

## Key Decisions (Do Not Change Without Discussion)

| Decision | Choice | Why |
|----------|--------|-----|
| **Hosting** | Heroku (Docker) | Full platform: dynos, Postgres, Redis. Docker for portability |
| Client data storage | Single DB (team-isolated) | Faster MVP, lower onboarding friction. BYOS deferred to Phase 12 if demand exists |
| Dashboards | Native (Chart.js + HTMX) | Already integrated, full design control |
| Sync frequency | Daily | Simpler than real-time |
| AI data source | Surveys + Copilot API (MVP) | Surveys for all, Copilot for teams with 5+ licenses |
| User discovery | GitHub org import | Auto-populate team |

## Implementation Order

Follow phases in [IMPLEMENTATION-PLAN.md](prd/IMPLEMENTATION-PLAN.md):
1. Foundation (auth, secrets, encrypted storage)
2. GitHub integration
3. Jira integration
4. Basic dashboard
5. Slack bot + surveys
6. AI correlation views
7. Leaderboard
8. Copilot metrics
9. Billing

**MVP checkpoint = Phase 8 complete (includes Copilot metrics).**

## Integrations

| Service | Auth | Scope |
|---------|------|-------|
| GitHub | OAuth | `read:org`, `repo`, `read:user` |
| Jira | OAuth (Atlassian) | `read:jira-work`, `read:jira-user` |
| Slack | OAuth | `chat:write`, `users:read`, `users:read.email` |
| Copilot | Via GitHub OAuth | `manage_billing:copilot` |

## AI Detection System

Detects AI tool usage in PRs via regex patterns and LLM analysis.

> **Full documentation:** See [AI-DETECTION-TESTING.md](prd/AI-DETECTION-TESTING.md) for workflows, testing tools, and implementation details.

### LLM Data Priority Rule

**IMPORTANT: Always prioritize LLM-detected data over pattern/regex detection.**

Use `effective_*` model properties that implement this priority:

| Property | LLM Source | Fallback |
|----------|------------|----------|
| `pr.effective_tech_categories` | `llm_summary.tech.categories` | `PRFile.file_category` aggregation |
| `pr.effective_is_ai_assisted` | `llm_summary.ai.is_assisted` (confidence ≥0.5) | `is_ai_assisted` field |
| `pr.effective_ai_tools` | `llm_summary.ai.tools` | `ai_tools_detected` field |

### Pattern Versioning

When adding new regex patterns:
1. Update `AI_SIGNATURE_PATTERNS` in `apps/metrics/services/ai_patterns.py`
2. Increment `PATTERNS_VERSION` (e.g., 1.5.0 → 1.6.0)
3. Run `python manage.py backfill_ai_detection` to update historical PRs

### Prompt Template Changes (REQUIRE APPROVAL)

Before modifying any prompt template (`apps/metrics/prompts/templates/*`):
1. **Explain the change** and show the diff
2. **Wait for user approval** - templates affect all PR analysis
3. **Bump version** - Update `PROMPT_VERSION` in `llm_prompts.py`
4. **Test** - Run `make export-prompts && npx promptfoo eval`

### Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/ai_patterns.py` | Regex patterns + `PATTERNS_VERSION` |
| `apps/metrics/services/llm_prompts.py` | `PROMPT_VERSION` + user prompt builder |
| `apps/metrics/prompts/templates/` | Jinja2 prompt templates (source of truth) |
| `apps/metrics/prompts/golden_tests.py` | 29 test cases for LLM evaluation |
| `apps/integrations/services/groq_batch.py` | LLM batch processing via Groq |

## Data Flow

GitHub/Jira APIs → Our Backend → PostgreSQL → Dashboard (Chart.js) → User ↓ Slack Bot (surveys)

We store: OAuth tokens (encrypted), accounts, billing, all metrics/surveys (team-isolated)

## PostHog Analytics

We use PostHog for product analytics. Events are tracked both server-side (Python) and client-side (JavaScript).

### Key Files

| File | Purpose |
|------|---------|
| `apps/utils/analytics.py` | Server-side tracking helpers |
| `apps/utils/middleware.py` | Error tracking middleware |
| `assets/javascript/analytics.js` | Client-side tracking module |
| `templates/web/components/posthog_init.html` | PostHog JS SDK initialization |

### Server-Side Events (Python)

Use helpers from `apps/utils/analytics`:

```python
from apps.utils.analytics import track_event, identify_user, update_user_properties

# Track an event
track_event(user, "pr_list_exported", {"format": "csv", "team_slug": team.slug})

# Update user properties (lightweight, no defaults)
update_user_properties(user, {"has_connected_github": True})
```

### Client-Side Events (JavaScript)

Use the global `TformanceAnalytics` object:

```javascript
// Track custom event
TformanceAnalytics.trackEvent('custom_action', { property: 'value' });

// Track chart interaction (auto-attached to Chart.js instances)
TformanceAnalytics.trackChartInteraction('cycle-time-chart', 'click', { label: 'Week 1', value: 24 });
```

### Event Catalog

| Event | Trigger | Key Properties |
|-------|---------|----------------|
| `integration_connected` | OAuth callback success | `provider`, `team_slug`, `is_reconnect` |
| `integration_disconnected` | User disconnects | `provider`, `team_slug` |
| `team_member_invited` | Invite sent | `team_slug`, `inviter_role` |
| `team_member_joined` | Invite accepted | `team_slug`, `invite_age_days` |
| `analytics_viewed` | Dashboard page view | `tab`, `date_range`, `team_slug` |
| `pr_list_filtered` | Filter applied | `filter_type`, `active_filters_count` |
| `pr_list_exported` | CSV export | `format`, `row_count`, `has_filters` |
| `insight_viewed` | Insight summary/Q&A | `insight_type`, `team_slug` |
| `feedback_submitted` | Feedback form | `category`, `has_text` |
| `repo_filter_applied` | Repo filter used | `tab`, `repo_name` |
| `error_occurred` | 500 errors (middleware) | `error_type`, `path`, `status_code` |
| `chart_interaction` | Chart click (frontend) | `chart_type`, `action`, `data_label` |
| `navigation` | Sidebar click (frontend) | `from_page`, `to_page` |
| `theme_switched` | Theme toggle (frontend) | `new_theme`, `previous_theme` |

### Adding New Events

1. **Backend**: Use `track_event()` from `apps/utils/analytics.py`
2. **Frontend**: Use `TformanceAnalytics.trackEvent()` from `analytics.js`
3. **Always include** `team_slug` for team-scoped events
4. **Document** new events in this table

# Codebase Guidelines

## Architecture

- This is a Django project built on Python 3.12.
- User authentication uses `django-allauth`.
- The front end is mostly standard Django views and templates.
- HTMX and Alpine.js are used to provide single-page-app user experience with Django templates.
  HTMX is used for interactions which require accessing the backend, and Alpine.js is used for
  browser-only interactions.
- JavaScript files are kept in the `/assets/` folder and built by vite.
  JavaScript code is typically loaded via the static files framework inside Django templates using `django-vite`.
- APIs use Django Rest Framework, and JavaScript code that interacts with APIs uses an
  auto-generated OpenAPI-schema-baesd client.
- The front end uses Tailwind (Version 4) and DaisyUI.
- The main database is Postgres.
- Celery is used for background jobs and scheduled tasks.
- Redis is used as the default cache, and the message broker for Celery (if enabled).

## Design System

The visual design follows the **"Easy Eyes Dashboard"** direction - inspired by the [Easy Eyes VS Code theme](https://github.com/vvhg1/easyeyes) for reduced eye strain.

**⚠️ DO NOT CHANGE THEME COLORS WITHOUT EXPLICIT USER APPROVAL ⚠️**

**Design Resources:**
- Design tokens & CSS classes: `assets/styles/app/tailwind/design-system.css`
- Theme definitions: `assets/styles/site-tailwind.css`
- Tailwind config: `tailwind.config.js`

### Color System Architecture

**IMPORTANT: Always use semantic DaisyUI colors, never hardcoded Tailwind colors.**

Colors are managed at three levels:
1. **DaisyUI Themes** (`site-tailwind.css`) - Define `tformance` (dark) and `tformance-light` themes
2. **Semantic Classes** (`design-system.css`) - App-specific `app-*` classes for common patterns
3. **Light Theme Overrides** (`site-tailwind.css`) - WCAG AA contrast fixes for light theme

### Color Usage Rules

| Use Case | Correct Class | Avoid |
|----------|--------------|-------|
| Primary text | `text-base-content` | `text-white`, `text-stone-*` |
| Secondary text | `text-base-content/80` | `text-gray-400`, `text-stone-400` |
| Muted text | `text-base-content/70` | `text-gray-500` |
| Backgrounds | `bg-base-100`, `bg-base-200` | `bg-deep`, `bg-surface`, `bg-neutral-*` |
| Borders | `border-base-300` | `border-elevated`, `border-neutral-*` |
| Success/positive | `text-success`, `app-status-connected` | `text-emerald-*`, `text-green-*` |
| Error/negative | `text-error` | `text-red-*` |
| Warning | `text-warning` | `text-amber-*` |
| Primary accent | `text-primary`, `bg-primary` | `text-orange-*`, `bg-accent-primary` |

### DaisyUI Theme Tokens (Easy Eyes Inspired)

| Token | Dark (`tformance`) | Light (`tformance-light`) |
|-------|-------------------|--------------------------|
| `base-100` | `#1e1e1e` (soft dark) | `#FAFAF8` |
| `base-200` | `#2a2a28` (warm elevated) | `#FFFFFF` |
| `base-300` | `#3c3c3a` (warm borders) | `#E5E7EB` |
| `base-content` | `#ccc9c0` (Easy Eyes text) | `#1F2937` |
| `primary` | `#F97316` (coral orange) | `#C2410C` |
| `secondary` | `#ffe96e` (golden amber) | `#FDA4AF` |
| `accent` | `#5a9997` (Easy Eyes teal) | `#10B981` |

### Typography

- **DM Sans** - UI text, headings
- **JetBrains Mono** - Code, metrics, data values

### Design Principles

1. **Easy on the eyes** - Soft dark backgrounds, warm text colors (inspired by Easy Eyes VS Code theme)
2. **Warm over cold** - Use coral/orange accents instead of typical blue/purple
2. **WCAG AA compliant** - All color combinations meet 4.5:1+ contrast ratio
3. **Semantic colors** - Use DaisyUI tokens that adapt to theme
4. **Terminal aesthetic** - Monospace fonts for data, dark backgrounds

### CSS Classes

Use the `app-*` prefixed utility classes from `design-system.css`:

```html
<!-- Cards -->
<div class="app-card">...</div>
<div class="app-card-interactive">...</div>

<!-- Buttons -->
<button class="app-btn-primary">Primary</button>
<button class="app-btn-secondary">Secondary</button>

<!-- Stats -->
<div class="app-stat-value app-stat-value-positive">+12%</div>
<div class="app-stat-value app-stat-value-negative">-5%</div>

<!-- Badges -->
<span class="app-badge app-badge-success">Active</span>

<!-- Status indicators -->
<span class="app-status-connected">Connected</span>
<span class="app-status-disconnected">Disconnected</span>
<span class="app-status-error">Error</span>
```

## Commands you can run

The following commands can be used for various tools and workflows.
A `Makefile` is provided to help centralize commands:

```bash
make  # List available commands
```

### First-time Setup

```bash
make init
```

### Starting the Application

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

**Important for Claude Code sessions**: After completing each implementation phase, verify the dev server is running:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/  # Should return 200
```
If not running, restart with `make dev` or `DEBUG=True .venv/bin/python manage.py runserver &`

### Stopping Services

Stop background services:

```bash
make stop
```

## Common Commands

### Development

```bash
make shell            # Open Python / Django shell
make dbshell          # Open PostgreSQL shell
make manage ARGS='command'  # Run any Django management command
```

### Database

```bash
make migrations       # Create new migrations
make migrate          # Apply migrations
```

### Testing

Tests run with **pytest** and **pytest-django**. The test suite has ~2000 tests.

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

# pytest-specific options
pytest apps/metrics -v                        # Verbose output
pytest --lf                                   # Run last failed tests only
pytest -x                                     # Stop on first failure
pytest -p randomly --randomly-seed=12345      # Reproducible random order
```

**Speed Tips:**
- `make test` runs in parallel by default with `--reuse-db` (~94s for full suite)
- Use `make test-serial` to disable parallelization for debugging
- Use `make test-slow` to identify optimization candidates
- Use `make test-fresh` after adding new migrations

### E2E Testing (Playwright)

E2E tests verify user flows in a real browser. **Requires dev server running.**

```bash
# Run all E2E tests
make e2e

# Run smoke tests only (fast, ~4s)
make e2e-smoke

# Run specific test suites
make e2e-auth           # Authentication tests
make e2e-dashboard      # Dashboard tests

# Interactive mode
make e2e-ui             # Open Playwright UI for debugging

# View test report
make e2e-report
```

**Test Files:** `tests/e2e/`
- `smoke.spec.ts` - Basic page loads, health checks
- `auth.spec.ts` - Login, logout, access control
- `dashboard.spec.ts` - CTO dashboard, navigation
- `integrations.spec.ts` - Integration status pages

**When to Run E2E Tests:**
- After changing views, templates, or URL patterns
- After modifying authentication or access control
- Before major releases
- When debugging user-reported issues

**Test Credentials:** `admin@example.com` / `admin123`

### Python Code Quality

```bash
make ruff-format      # Format code
make ruff-lint        # Lint and auto-fix
make ruff             # Run both format and lint
```
### Python

```bash
make uv add '<package>'         # Add a new package
make uv run '<command> <args>'  # Run a Python command
```

### Frontend

```bash
make npm-install      # Install npm packages
make npm-install package-name  # Install specific package
make npm-uninstall package-name  # Uninstall package
make npm-dev          # Run the Vite development server
make npm-build        # Build for production
make npm-type-check   # Run TypeScript type checking
```

Note: Vite runs automatically with hot-reload when using `make dev`.

### Code generation

```bash
make uv run 'pegasus startapp <app_name> <Model1> <Model2Name>'  # Start a new Django app (models are optional)
```

### AI Detection Tools

```bash
make export-prompts                         # Generate promptfoo.yaml from templates
python manage.py run_llm_analysis --limit 50  # Analyze PRs with LLM
python manage.py backfill_ai_detection      # Backfill regex detection
```

### Demo Data Seeding

```bash
python manage.py seed_demo_data              # Seed default demo data
python manage.py seed_demo_data --clear      # Clear and reseed
python manage.py seed_demo_data --prs 100    # Custom amounts

# Scenario-based seeding (recommended for coherent demo data)
python manage.py seed_demo_data --scenario ai-success --seed 42
python manage.py seed_demo_data --list-scenarios  # Show all scenarios
```

See `dev/DEV-ENVIRONMENT.md` for full options including all 4 scenarios.

### Public Report (AI Impact Analysis)

The `public_report/index.html` is a standalone HTML report analyzing AI tool adoption across 100 OSS companies. It's built from Jinja2 templates with data from CSV exports.

```bash
make build-report  # Build public_report/index.html from templates
```

**Template Structure** (in `public_report/templates/`):
| File | Purpose |
|------|---------|
| `base.html.j2` | HTML skeleton, `<head>`, script/style includes |
| `content.html.j2` | All HTML sections (nav, header, 17 content sections, footer) |
| `scripts.js.j2` | Theme toggle, 13 Chart.js charts, Alpine.js table, UI interactions |
| `styles.css.j2` | All CSS including dark/light theme variables |

**Data Flow**:
1. CSV files in `public_report/data/` (exported via `public_report/scripts/export_report_data.py`)
2. `build_report.py` loads CSVs into Python dicts
3. Jinja2 renders templates with data context
4. Output: `public_report/index.html` (186 KB standalone file)

**Key Variables** (available in templates):
- `data.team_summary` - Team-level metrics (74 teams with 500+ PRs)
- `data.tool_trends` - Monthly tool usage by month
- `data.overall_stats` - Aggregate statistics

**When Editing Templates**:
- Charts use `teamData` and `toolTrends` (injected in `base.html.j2`)
- Theme colors come from `getColors()` function
- Alpine.js components (like sortable table) need functions defined before Alpine loads

See `public_report/templates/README.md` for detailed documentation.

## Test-Driven Development (TDD)

**IMPORTANT: This project follows strict TDD practices. All new features MUST be implemented using the Red-Green-Refactor cycle.**

### Before Starting Any Implementation

1. **Run existing tests first**: `make test` to ensure the codebase is in a passing state
2. **Identify what tests exist**: Check `apps/<app>/tests/` for related test files
3. **Never break existing tests**: If your changes cause test failures, fix them before proceeding

### TDD Workflow (Red-Green-Refactor)

When implementing new features, follow this strict cycle:

#### 🔴 RED Phase - Write Failing Test First
- Write a test that describes the expected behavior
- Run the test and confirm it **fails** (this proves the test is valid)
- Do NOT write any implementation code yet

#### 🟢 GREEN Phase - Make It Pass
- Write the **minimum** code needed to make the test pass
- No extra features, no "nice to haves"
- Run the test and confirm it **passes**

#### 🔵 REFACTOR Phase - Improve
- Clean up the implementation while keeping tests green
- Extract reusable code, improve naming, remove duplication
- Run tests after each change to ensure they still pass

### Test File Conventions

```bash
# Test location pattern
apps/<app_name>/tests/test_<feature>.py

# Running specific tests with pytest
pytest apps/myapp/tests/test_feature.py                              # Run file
pytest apps/myapp/tests/test_feature.py::TestClassName               # Run class
pytest apps/myapp/tests/test_feature.py::TestClassName::test_method  # Run method
pytest -k "test_feature and not slow"                                # Pattern match
```

### Test Structure (Django TestCase with Factories)

Use Factory Boy factories for creating test data. Factories are in `apps/<app>/factories.py`.

```python
from django.test import TestCase

from apps.metrics.factories import TeamMemberFactory, PullRequestFactory
from apps.teams.factories import TeamFactory


class TestFeatureName(TestCase):
    """Tests for <feature description>."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_describes_expected_behavior(self):
        """Test that <specific behavior> works correctly."""
        # Arrange - use factories for test data
        pr = PullRequestFactory(team=self.team, author=self.member)

        # Act - perform the action
        # Assert - verify the outcome
        self.assertEqual(pr.author, self.member)
```

### Factory Guidelines

- **Always use factories** for creating test data instead of manual model creation
- Factories are located in `apps/<app>/factories.py`
- Use `Factory.build()` for unit tests (doesn't save to DB)
- Use `Factory.create()` or `Factory()` for integration tests (saves to DB)
- Use `Factory.create_batch(n)` to create multiple instances
- Override specific attributes: `TeamMemberFactory(role="lead", display_name="John")`
- **Use `factory.Sequence`** for unique fields to avoid constraint violations:
  ```python
  email = factory.Sequence(lambda n: f"user{n}@example.com")
  github_id = factory.Sequence(lambda n: str(10000 + n))
  ```

Available factories in `apps/metrics/factories.py`:
- `TeamFactory`, `TeamMemberFactory`
- `PullRequestFactory`, `PRReviewFactory`, `CommitFactory`
- `JiraIssueFactory`, `AIUsageDailyFactory`
- `PRSurveyFactory`, `PRSurveyReviewFactory`
- `WeeklyMetricsFactory`

### TDD Skill Activation

This project has Claude Code skills configured to enforce TDD. When you request a new feature implementation, the TDD skill will automatically:

1. Delegate to `tdd-test-writer` agent for RED phase
2. Delegate to `tdd-implementer` agent for GREEN phase
3. Delegate to `tdd-refactorer` agent for REFACTOR phase

**Trigger phrases**: "implement", "add feature", "build", "create functionality"

**Does NOT trigger for**: bug fixes, documentation, configuration changes

## General Coding Preferences

- **ALWAYS run tests before committing**: Run `make test` before every commit to catch regressions early. A pre-push hook enforces this automatically (skip with `git push --no-verify` if needed).
- Always prefer simple solutions.
- Avoid duplication of code whenever possible, which means checking for other areas of the codebase that might already have similar code and functionality.
- You are careful to only make changes that are requested or you are confident are well understood and related to the change being requested.
- When fixing an issue or bug, do not introduce a new pattern or technology without first exhausting all options for the existing implementation. And if you finally do this, make sure to remove the old implementation afterwards so we don’t have duplicate logic.
- Keep the codebase clean and organized.
- Avoid writing scripts in files if possible, especially if the script is likely only to be run once.
- Try to avoid having files over 200-300 lines of code. Refactor at that point.
- **Large file splitting convention**: When a file exceeds limits, split into a directory with focused submodules:
  - `models.py` (if >500 lines) → `models/` directory with domain files (e.g., `github.py`, `jira.py`)
  - `views.py` (if >500 lines) → `views/` directory with feature files (e.g., `github.py`, `slack.py`)
  - `test_*.py` (if >1000 lines) → `tests/<feature>/` subdirectory with focused test files
  - Always include `__init__.py` with re-exports for backward compatibility
  - Example: `from apps.metrics.models import PullRequest` continues to work after splitting
- Don't ever add mock data to functions. Only add mocks to tests or utilities that are only used by tests.
- Always think about what other areas of code might be affected by any changes made.
- Never overwrite my .env file without first asking and confirming.

## External API Integration Guidelines

**IMPORTANT: Always prefer official SDKs/libraries over direct API calls.**

### Library Selection Hierarchy

When integrating with external services, follow this preference order:

1. **Official SDK/library** - Published and maintained by the service provider
2. **Well-maintained 3rd party library** - Popular, actively maintained, with good documentation
3. **Direct API calls** - Only as a last resort when no suitable library exists

### Required Libraries for This Project

| Service | Library | PyPI Package | Notes |
|---------|---------|--------------|-------|
| GitHub | PyGithub | `PyGithub` | Official community library, most popular |
| Jira | jira-python | `jira` | Most popular, well-maintained |
| Slack | slack-sdk | `slack-sdk` | Official Slack SDK |
| Atlassian (generic) | atlassian-python-api | `atlassian-python-api` | Alternative for Jira/Confluence |

### Documentation Lookup with Context7

**ALWAYS use the Context7 MCP server to get up-to-date documentation** before implementing integrations:

1. First, resolve the library ID:
   ```
   mcp__context7__resolve-library-id(libraryName="PyGithub")
   ```

2. Then fetch relevant documentation:
   ```
   mcp__context7__get-library-docs(context7CompatibleLibraryID="/...", topic="pull requests")
   ```

This ensures you're using current API methods and best practices, not outdated patterns from training data.

### Why Libraries Over Direct API

- **Pagination handling** - Libraries handle cursor-based and offset pagination automatically
- **Rate limiting** - Built-in retry logic and rate limit respect
- **Authentication** - Proper token refresh, OAuth flows handled
- **Error handling** - Typed exceptions, clear error messages
- **Type safety** - Many libraries have type hints or stubs available
- **Testing** - Easier to mock library objects than raw HTTP responses

### Integration Code Organization

- Integration-specific code lives in `apps/integrations/`
- Service clients should be instantiated with tokens from the team's connected accounts
- Use dependency injection patterns to make integrations testable
- Wrap library calls in service classes that handle our domain logic

## Python Code Guidelines

### Code Style

- Follow PEP 8 with 120 character line limit.
- Use double quotes for Python strings (ruff enforced).
- Sort imports with isort (via ruff).
- Try to use type hints in new code. However, strict type-checking is not enforced and you can leave them out if it's burdensome.
  There is no need to add type hints to existing code if it does not already use them.

### Preferred Practices

- Use Django signals sparingly and document them well.
- Always use the Django ORM if possible. Use best practices like lazily evaluating querysets
  and selecting or prefetching related objects when necessary.
- Use function-based views by default, unless using a framework that relies on class-based views (e.g. Django Rest Framework).
- Always validate user input server-side.
- Handle errors explicitly, avoid silent failures.

#### Django models

- All Django models should extend `apps.utils.models.BaseModel` (which adds `created_at` and `updated_at` fields) or `apps.teams.models.BaseTeamModel` (which also adds a `team`) if owned by a team.
- Models that extend `BaseTeamModel` should use the `for_team` model manager for queries that require team filtering. This will apply the team filter automatically based on the global team context. See `apps.teams.context.get_current_team`.
- The project's user model is `apps.users.models.CustomUser` and should be imported directly.
- The `Team` model is like a virtual tenant and most data access / functionality happens within
  the context of a `Team`.

#### Team Isolation Linting (TEAM001)

A custom linter enforces safe query patterns on `BaseTeamModel` subclasses to prevent tenant data leakage:

```bash
make lint-team-isolation        # Check production code
make lint-team-isolation-all    # Include test files
```

**Safe patterns:**
```python
Model.objects.filter(team=team)      # Explicit team filter
Model.for_team.filter(...)           # Team-scoped manager
Model.objects.filter(related__in=team_scoped_qs)  # Filtering through relations
```

**Unsafe pattern (flagged):**
```python
Model.objects.filter(state='merged')  # TEAM001: Missing team filter
```

**Suppression:** When intentional unscoped access is needed (webhooks, Celery tasks with IDs from trusted sources):
```python
Model.objects.get(id=id)  # noqa: TEAM001 - ID from Celery task queue
```

#### Django URLs, Views and Teams

- Many apps have a `urls.py` with a `urlpatterns` and a `team_urlpatterns` value.
  The `urlpatterns` are for views that happen outside the context of a `Team` model.
  `team_urlpatterns` are for views that happen within the context of a `Team`.
- Anything in `team_urlpatterns` will have URLs of the format `/a/<team_slug>/<app_path>/<pattern>/`.
- Any view referenced by `team_urlpatterns` must contain `team_slug` as the first argument.
- For team-based views, the `@login_and_team_required` and `@team_admin_required` decorators
  can be used to ensure the user is logged in and can access the associated team.
- If not specified, assume that a given url/view belongs within the context of a team
  (and follows the above guidance)

## Django Template Coding Guidelines for HTML files

- Indent templates with two spaces.
- Use standard Django template syntax.
- JavaScript and CSS files built with vite should be included with the `{% vite_asset %}` template tag provided by `django-vite` (must have `{% load django_vite %}` at the top of the template)
- Any react components also need `{% vite_react_refresh %}` for Vite + React's HMR functionality, from the same `django_vite` template library)
- Use the Django `{% static %}` tag for loading images and external JavaScript / CSS files not managed by vite.
- Prefer using alpine.js for page-level JavaScript, and avoid inline `<script>` tags where possible.
- Break re-usable template components into separate templates with `{% include %}` statements.
  These normally go into a `components` folder.
- Use DaisyUI styling markup for available components. When not available, fall back to standard TailwindCSS classes.
- Stick with the DaisyUI color palette whenever possible.

## JavaScript Code Guidelines

### Code Style

- Use ES6+ syntax for JavaScript code.
- Use 2 spaces for indentation in JavaScript, JSX, and HTML files.
- Use single quotes for JavaScript strings.
- End statements with semicolons.
- Use camelCase for variable and function names.
- Use PascalCase for component names (React).
- For React components, use functional components with hooks rather than class components.
- Use explicit type annotations in TypeScript files.
- Use ES6 import/export syntax for module management.

### Preferred Practices
- React components should be kept small and focused on a single responsibility.
- Store state at an appropriate level; avoid prop drilling by using context when necessary.
- Where possible, use TypeScript for React components to leverage type safety.
- When using HTMX, follow progressive enhancement patterns.
- Use Alpine.js for client-side interactivity that doesn't require server interaction.
- Avoid inline `<script>` tags wherever posisble.
- Use the generated OpenAPI client for API calls instead of raw fetch or axios calls.
- Validate user input on both client and server side.
- Handle errors explicitly in promise chains and async functions.

### Build System

- Code is bundled using vite and served with `django-vite`.
- Before pushing, always run:
  .venv/bin/pre-commit run --all-files  # Lint check
  make test                              # Unit tests

## HTMX + Alpine.js Integration Patterns

This project uses HTMX for server-driven partial page updates and Alpine.js for client-side reactivity. Follow these patterns to avoid common pitfalls.

### Critical Rules

1. **NEVER use inline `<script>` tags in HTMX partials** - They won't execute after HTMX swaps content
2. **Use Alpine.store() for state that must persist** across HTMX navigation
3. **Use ChartManager for all chart initialization** - Prevents duplicate instances

### Alpine.js Stores

Use `Alpine.store()` for state that needs to survive HTMX content swaps:

```javascript
// In assets/javascript/alpine.js
Alpine.store('dateRange', {
  days: 30,
  preset: '',
  setDays(d) { this.days = d; this.preset = ''; },
  setPreset(p) { this.preset = p; this.days = 0; },
  isActive(d) { return this.days === d && !this.preset; }
});

// In templates - access via $store
<button @click="$store.dateRange.setDays(7)"
        :class="{'btn-primary': $store.dateRange.isActive(7)}">
  7d
</button>
```

**Available stores:**
- `$store.dateRange` - Time range selection (days, preset, granularity)
- `$store.metrics` - Selected metrics for comparison views

### Alpine Component Registration

Extract reusable components to JS modules instead of inline scripts:

```javascript
// In assets/javascript/components/my-component.js
export function registerMyComponent() {
  Alpine.data('myComponent', () => ({
    open: false,
    toggle() { this.open = !this.open; }
  }));
}

// In alpine.js - register during alpine:init
import { registerMyComponent } from './components/my-component.js';
document.addEventListener('alpine:init', () => {
  registerMyComponent();
});
```

### ChartManager Usage

All charts should be registered with ChartManager for proper lifecycle management:

```javascript
// Register a chart factory
chartManager.register('my-chart', (canvas, data) => {
  if (!data) return null;
  return new Chart(canvas.getContext('2d'), { /* config */ });
}, { dataId: 'my-chart-data' });

// Charts auto-initialize on htmx:afterSwap via chartManager.initAll()
```

**Registered charts:** ai-adoption-chart, cycle-time-chart, review-time-chart, copilot-trend-chart, pr-type-chart, tech-chart, trend-chart

### HTMX Event Handlers

Key handlers in `assets/javascript/htmx.js`:

```javascript
// Error handling - shows user-friendly message on 4xx/5xx
htmx.on('htmx:afterRequest', (evt) => {
  if (evt.detail.failed) {
    // Display error in target element
  }
});

// Alpine re-initialization after content swap
htmx.on('htmx:afterSwap', (evt) => {
  if (window.Alpine) {
    Alpine.initTree(evt.detail.target);
  }
});
```

### Template Best Practices

```html
<!-- DO: Use data attributes for chart config -->
<canvas id="my-chart"
        data-chart-type="stacked-bar"
        data-chart-data-id="my-chart-data">
</canvas>
{{ chart_data|json_script:"my-chart-data" }}

<!-- DO: Use Alpine store for persistent state -->
<div x-data>
  <button @click="$store.dateRange.setDays(30)">30d</button>
</div>

<!-- DON'T: Inline scripts in partials -->
<script>
  // This won't execute after HTMX swap!
  new Chart(...)
</script>
```

### Testing HTMX Flows

E2E tests for HTMX integration are in `tests/e2e/`:
- `htmx-error-handling.spec.ts` - Error display
- `htmx-navigation.spec.ts` - State persistence
- `alpine-htmx-integration.spec.ts` - Store + component behavior

Run with: `npx playwright test tests/e2e/htmx --reporter=list`