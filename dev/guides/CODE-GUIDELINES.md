# Code Guidelines

> Back to [CLAUDE.md](../../CLAUDE.md)

## Python Code Style

- Follow PEP 8 with 120 character line limit
- Use double quotes for strings (ruff enforced)
- Sort imports with isort (via ruff)
- Use type hints in new code (not strictly enforced)

## Python Preferred Practices

- Use Django signals sparingly and document them well
- Always use Django ORM if possible. Use lazy querysets, `select_related`, `prefetch_related`
- Use function-based views by default (class-based for DRF)
- Always validate user input server-side
- Handle errors explicitly, avoid silent failures

## Django Models

- All models extend `apps.utils.models.BaseModel` (adds `created_at`, `updated_at`)
- Team-owned models extend `apps.teams.models.BaseTeamModel` (also adds `team`)
- Use `for_team` manager for team-filtered queries: `Model.for_team.filter(...)`
- User model is `apps.users.models.CustomUser`
- `Team` model is like a virtual tenant - most data access happens within Team context

## Team Isolation Linting (TEAM001)

Custom linter enforces safe query patterns to prevent tenant data leakage:

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

**Suppression (when intentional):**
```python
Model.objects.get(id=id)  # noqa: TEAM001 - ID from Celery task queue
```

## Django URLs, Views and Teams

- Apps have `urlpatterns` (outside Team context) and `team_urlpatterns` (within Team)
- `team_urlpatterns` URLs: `/a/<team_slug>/<app_path>/<pattern>/`
- Team-based views must have `team_slug` as first argument
- Use `@login_and_team_required` and `@team_admin_required` decorators
- Assume views belong within team context unless specified otherwise

## JavaScript Code Style

- Use ES6+ syntax
- 2 spaces for indentation in JS, JSX, HTML
- Use single quotes for strings
- End statements with semicolons
- Use camelCase for variables/functions, PascalCase for components
- Prefer functional React components with hooks
- Use explicit TypeScript annotations
- Use ES6 import/export

## JavaScript Preferred Practices

- Keep React components small and focused
- Store state appropriately; use context to avoid prop drilling
- Use TypeScript for React components where possible
- Follow progressive enhancement patterns with HTMX
- Use Alpine.js for client-side interactivity without server interaction
- Avoid inline `<script>` tags
- Use generated OpenAPI client for API calls (not raw fetch/axios)
- Validate user input on client and server side
- Handle errors explicitly in promises/async functions

## File Splitting Convention

When files exceed 200-300 lines, split into directories:

- `models.py` (>500 lines) → `models/` with domain files
- `views.py` (>500 lines) → `views/` with feature files
- `services/large_service.py` (>500 lines) → `services/large_service/` package

**Requirements:**
- Always include `__init__.py` with re-exports for backward compatibility
- Original file can become a facade that re-exports from the package
- Test files should also be granular when possible

**Example:** `github_sync.py` was split into:
```
apps/integrations/services/github_sync/
├── __init__.py      # Re-exports all public functions
├── client.py        # GitHub API client functions
├── converters.py    # Data conversion utilities
├── processors.py    # Per-entity sync operations
├── metrics.py       # Metrics calculations
└── sync.py          # Sync orchestration
```

## Build System

Code is bundled with Vite and served with `django-vite`.

Before pushing:
```bash
.venv/bin/pre-commit run --all-files  # Lint check
make test                              # Unit tests
```
