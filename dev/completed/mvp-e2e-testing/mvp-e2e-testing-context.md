# MVP E2E Testing - Context Document

**Last Updated: 2025-12-18**
**Status: PLANNING**

## Key Files Reference

### Existing E2E Test Files

| File | Path | Purpose |
|------|------|---------|
| Smoke Tests | `tests/e2e/smoke.spec.ts` | Basic health checks (6 tests) |
| Auth Tests | `tests/e2e/auth.spec.ts` | Authentication flows (6 tests) |
| Dashboard Tests | `tests/e2e/dashboard.spec.ts` | Dashboard functionality (62 tests) |
| Accessibility Tests | `tests/e2e/accessibility.spec.ts` | WCAG 2.1 AA compliance (6 tests) |
| Integration Tests | `tests/e2e/integrations.spec.ts` | Integration hub (4 tests) |

### Configuration Files

| File | Path | Purpose |
|------|------|---------|
| Playwright Config | `playwright.config.ts` | Test runner configuration |
| Package.json | `package.json` | Test scripts and dependencies |
| TypeScript Config | `tsconfig.json` | TypeScript settings for tests |

### Seed Data System

| File | Path | Purpose |
|------|------|---------|
| Seed Command | `apps/metrics/management/commands/seed_demo_data.py` | Generate demo data |
| Metrics Factories | `apps/metrics/factories.py` | Factory Boy factories for metrics models |
| Integration Factories | `apps/integrations/factories.py` | Factory Boy factories for integrations |
| Dev Docs | `dev/DEV-ENVIRONMENT.md` | Seeding documentation |

### Key Django Views (Test Targets)

| Feature | View File | URL Pattern |
|---------|-----------|-------------|
| App Home | `apps/web/views.py` | `/app/` |
| Team Dashboard | `apps/metrics/views/dashboard_views.py` | `/app/metrics/dashboard/team/` |
| CTO Dashboard | `apps/metrics/views/dashboard_views.py` | `/app/metrics/dashboard/cto/` |
| Integrations Hub | `apps/integrations/views.py` | `/app/integrations/` |
| GitHub Integration | `apps/integrations/views.py` | `/app/integrations/github/*` |
| Jira Integration | `apps/integrations/views.py` | `/app/integrations/jira/*` |
| Slack Integration | `apps/integrations/views.py` | `/app/integrations/slack/*` |
| Surveys | `apps/web/views.py` | `/survey/<token>/` |
| Team Settings | `apps/teams/views.py` | `/app/team/*` |

### Template Files (UI Reference)

| Component | Template Path |
|-----------|---------------|
| App Home | `templates/web/app_home.html` |
| Team Dashboard | `templates/metrics/dashboard_team.html` |
| CTO Dashboard | `templates/metrics/dashboard_cto.html` |
| Integrations Hub | `templates/integrations/integrations_home.html` |
| Survey Author | `templates/web/survey_author.html` |
| Survey Reviewer | `templates/web/survey_reviewer.html` |

## Test User Credentials

| User | Email | Password | Role | Use Case |
|------|-------|----------|------|----------|
| Admin | `admin@example.com` | `admin123` | Team Admin | CTO dashboard, full access |
| (Future) Lead | `lead@example.com` | `lead123` | Team Lead | Team dashboard, limited admin |
| (Future) Dev | `dev@example.com` | `dev123` | Developer | Basic access, own metrics |

**Note:** Currently only admin user exists. Lead/dev users need to be added to seed_demo_data.

## Seed Data Summary

### Default Seed (`python manage.py seed_demo_data`)

| Model | Count | Notes |
|-------|-------|-------|
| Teams | 1 | `demo-team-1` |
| Team Members | 5 | 1 lead + 4 developers |
| Pull Requests | 50 | 60% merged, realistic cycle times |
| PR Reviews | ~75 | 1-3 per PR |
| Commits | ~300 | 1-5 per PR + standalones |
| Jira Issues | 40 | 8 per member |
| AI Usage Daily | ~150 | 30 days of data |
| PR Surveys | ~30 | 60% of merged PRs |
| PR Survey Reviews | ~60 | 1-2 per survey |
| Weekly Metrics | 40 | 8 weeks × 5 members |

### Seed Commands

```bash
# Default seed
python manage.py seed_demo_data

# Custom amounts
python manage.py seed_demo_data --teams 2 --members 10 --prs 100

# Clear and reseed
python manage.py seed_demo_data --clear

# Seed existing team
python manage.py seed_demo_data --team-slug demo-team
```

## Key Decisions

### 1. Test Isolation Strategy

**Decision:** Use shared seed data across tests (not per-test seeding)

**Rationale:**
- Seed command takes 5-10 seconds
- Running per test would add 10+ minutes to test suite
- Shared data is acceptable for read-only tests
- Destructive tests should be isolated/skipped or run last

**Implementation:**
- Global setup verifies seed data exists
- Tests are read-only (don't modify seed data)
- Destructive tests use unique identifiers

### 2. OAuth Flow Testing

**Decision:** Skip actual OAuth redirects, test UI state only

**Rationale:**
- OAuth flows require real credentials
- External services (GitHub, Jira, Slack) can't be controlled in tests
- Focus on UI state changes based on integration status

**Implementation:**
- Test "Connect" buttons appear when not connected
- Test integration status cards show correct state
- Test member/repo lists appear when connected
- Mock OAuth callback responses if needed

### 3. Browser Coverage

**Decision:** Primary Chrome, secondary Firefox

**Rationale:**
- Chrome represents ~65% of users
- Firefox catches most cross-browser issues
- Safari/WebKit has limited Playwright support
- Keep test suite fast (<5 min)

**Implementation:**
- Default tests run Chrome only
- CI runs Chrome + Firefox
- Manual Safari testing for releases

### 4. HTMX Handling

**Decision:** Use explicit waits for HTMX content

**Rationale:**
- HTMX loads content asynchronously
- Default Playwright waits may not catch HTMX swaps
- Need to wait for specific content, not just network idle

**Implementation:**
```typescript
// Wait for HTMX content to load
await page.waitForSelector('[hx-get].htmx-loaded');
// Or wait for specific content
await page.waitForSelector('.metrics-card');
```

### 5. Test Data Validation

**Decision:** Spot-check key metrics, not exhaustive validation

**Rationale:**
- Full data validation duplicates unit tests
- E2E should focus on UI correctness
- Spot checks catch display bugs

**Implementation:**
- Verify card values are numbers (not NaN)
- Verify charts have data points
- Verify tables have rows
- Don't validate exact calculated values

## Dependencies

### External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `@playwright/test` | ^1.57.0 | Test framework |
| `@axe-core/playwright` | ^4.11.0 | Accessibility testing |

### Internal Dependencies

| Component | Dependency | Notes |
|-----------|------------|-------|
| All tests | Dev server | Must run `make dev` first |
| Auth tests | Admin user | Created by migrations |
| Dashboard tests | Seed data | Run `seed_demo_data` |
| Integration tests | Connected integrations | Seed creates mock connections |

### Environment Requirements

| Requirement | Value | Notes |
|-------------|-------|-------|
| Node.js | 18+ | For Playwright |
| Python | 3.12 | For Django |
| PostgreSQL | Running | Via Docker |
| Redis | Running | For Celery (optional) |
| Dev server | http://localhost:8000 | `make dev` |

## URL Patterns to Test

### Public Pages (No Auth)

| Page | URL | Expected |
|------|-----|----------|
| Landing | `/` | Marketing page or redirect if logged in |
| Login | `/accounts/login/` | Login form |
| Signup | `/accounts/signup/` | Registration form |
| Health | `/health/` | 200 OK or 500 with details |
| 404 | `/nonexistent/` | 404 page |

### Authenticated Pages

| Page | URL | Role Required |
|------|-----|---------------|
| App Home | `/app/` | Any authenticated |
| Team Dashboard | `/app/metrics/dashboard/team/` | Any team member |
| CTO Dashboard | `/app/metrics/dashboard/cto/` | Admin only |
| Integrations | `/app/integrations/` | Any team member |
| GitHub Members | `/app/integrations/github/members/` | Admin |
| GitHub Repos | `/app/integrations/github/repos/` | Admin |
| Jira Projects | `/app/integrations/jira/projects/` | Admin |
| Team Settings | `/app/team/` | Admin |
| Profile | `/accounts/profile/` | Any authenticated |

### Survey Pages (Token Auth)

| Page | URL | Auth |
|------|-----|------|
| Survey Landing | `/survey/<token>/` | Token |
| Author Survey | `/survey/<token>/author/` | Token + author |
| Reviewer Survey | `/survey/<token>/reviewer/` | Token + reviewer |
| Survey Complete | `/survey/<token>/complete/` | Token |

## HTMX Endpoints (Partial Content)

### Dashboard Charts

| Endpoint | URL | Content |
|----------|-----|---------|
| Cycle Time Chart | `/app/metrics/charts/cycle-time/` | Line chart |
| Review Time Chart | `/app/metrics/charts/review-time/` | Line chart |
| PR Size Chart | `/app/metrics/charts/pr-size/` | Bar chart |
| Review Distribution | `/app/metrics/charts/review-distribution/` | Pie chart |
| AI Adoption | `/app/metrics/charts/ai-adoption/` | Line chart |
| AI Quality | `/app/metrics/charts/ai-quality/` | Grouped bar |
| Copilot Trend | `/app/metrics/charts/copilot-trend/` | Line chart |

### Dashboard Cards

| Endpoint | URL | Content |
|----------|-----|---------|
| Metrics Cards | `/app/metrics/cards/metrics/` | 4 stat cards |
| Copilot Cards | `/app/metrics/cards/copilot/` | 4 Copilot stats |

### Dashboard Tables

| Endpoint | URL | Content |
|----------|-----|---------|
| Team Breakdown | `/app/metrics/tables/breakdown/` | Team comparison |
| Leaderboard | `/app/metrics/tables/leaderboard/` | AI Detective |
| Copilot Members | `/app/metrics/tables/copilot-members/` | Per-user Copilot |

## Test Tags

| Tag | Purpose | Usage |
|-----|---------|-------|
| `@smoke` | Critical path checks | Pre-deploy validation |
| `@auth` | Authentication tests | Login/logout flows |
| `@dashboard` | Dashboard tests | UI rendering |
| `@integrations` | Integration tests | Connection flows |
| `@surveys` | Survey tests | Response flows |
| `@interactive` | Click tests | Button/form interactions |
| `@slow` | Long-running tests | Skip in quick runs |
| `@destructive` | Data-modifying tests | Run in isolation |

## Related Documentation

- `CLAUDE.md` - Project guidelines and testing section
- `prd/PRD-MVP.md` - MVP feature requirements
- `prd/DASHBOARDS.md` - Dashboard specifications
- `prd/IMPLEMENTATION-PLAN.md` - Phase completion status
- `dev/DEV-ENVIRONMENT.md` - Development setup
