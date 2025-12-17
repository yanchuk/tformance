# AI Impact Analytics Platform

## Project Overview

A SaaS platform helping CTOs understand if AI coding tools are actually improving their team's performance. Connects to GitHub, Jira, and Slack to correlate AI usage with delivery metrics.

## Documentation

All product requirements are in `/prd/`:
- [PRD-MVP.md](prd/PRD-MVP.md) - Main product spec
- [IMPLEMENTATION-PLAN.md](prd/IMPLEMENTATION-PLAN.md) - Build phases & order
- [ARCHITECTURE.md](prd/ARCHITECTURE.md) - Technical architecture
- [DATA-MODEL.md](prd/DATA-MODEL.md) - Database schema
- [SLACK-BOT.md](prd/SLACK-BOT.md) - Bot specification
- [DASHBOARDS.md](prd/DASHBOARDS.md) - Dashboard views
- [ONBOARDING.md](prd/ONBOARDING.md) - User flow

**Read these before implementing features.**

## Key Decisions (Do Not Change Without Discussion)

| Decision | Choice | Why |
|----------|--------|-----|
| Client data storage | Single DB (team-isolated) | Faster MVP, lower onboarding friction. BYOS deferred to Phase 12 if demand exists |
| Dashboards | Native (Chart.js + HTMX) | Already integrated, full design control |
| Sync frequency | Daily | Simpler than real-time |
| AI data source | Self-reported surveys (MVP) | Cursor API is Enterprise-only |
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

**MVP checkpoint = Phase 5 complete.**

## Integrations

| Service | Auth | Scope |
|---------|------|-------|
| GitHub | OAuth | `read:org`, `repo`, `read:user` |
| Jira | OAuth (Atlassian) | `read:jira-work`, `read:jira-user` |
| Slack | OAuth | `chat:write`, `users:read`, `users:read.email` |
| Copilot | Via GitHub OAuth | `manage_billing:copilot` |

## Data Flow

GitHub/Jira APIs → Our Backend → PostgreSQL → Dashboard (Chart.js) → User ↓ Slack Bot (surveys)

We store: OAuth tokens (encrypted), accounts, billing, all metrics/surveys (team-isolated)

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

```bash
make test                              # Run all Django unit tests
make test ARGS='apps.module.tests.test_file'  # Run specific test
make test ARGS='path.to.test --keepdb'        # Run with options
```

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

### Demo Data Seeding

```bash
python manage.py seed_demo_data              # Seed default demo data
python manage.py seed_demo_data --clear      # Clear and reseed
python manage.py seed_demo_data --prs 100    # Custom amounts
```

See `dev/DEV-ENVIRONMENT.md` for full options.

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

# Running specific tests
make test ARGS='apps.myapp.tests.test_feature'
make test ARGS='apps.myapp.tests.test_feature::TestClassName'
make test ARGS='apps.myapp.tests.test_feature::TestClassName::test_method'
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

- **ALWAYS run tests before committing**: Run `make test ARGS='--keepdb'` before every commit to catch regressions early. Never commit without verifying tests pass.
- Always prefer simple solutions.
- Avoid duplication of code whenever possible, which means checking for other areas of the codebase that might already have similar code and functionality.
- You are careful to only make changes that are requested or you are confident are well understood and related to the change being requested.
- When fixing an issue or bug, do not introduce a new pattern or technology without first exhausting all options for the existing implementation. And if you finally do this, make sure to remove the old implementation afterwards so we don’t have duplicate logic.
- Keep the codebase clean and organized.
- Avoid writing scripts in files if possible, especially if the script is likely only to be run once.
- Try to avoid having files over 200-300 lines of code. Refactor at that point.
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