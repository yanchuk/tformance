# E2E Testing Plan - Context Document

**Last Updated:** 2025-12-13
**Status:** Planning Complete

---

## Critical Files

### URL Configuration
| File | Purpose |
|------|---------|
| `tformance/urls.py` | Main URL router |
| `apps/web/urls.py` | Web views (surveys, webhooks) |
| `apps/metrics/urls.py` | Dashboard and chart URLs |
| `apps/integrations/urls.py` | Integration setup URLs |
| `apps/teams/urls.py` | Team management URLs |
| `apps/onboarding/urls.py` | Onboarding flow URLs |

### View Files
| File | Purpose |
|------|---------|
| `apps/web/views.py` | Surveys, webhooks, home |
| `apps/metrics/views/dashboard_views.py` | Dashboard pages |
| `apps/metrics/views/chart_views.py` | Chart data endpoints |
| `apps/integrations/views.py` | Integration CRUD |
| `apps/onboarding/views.py` | Onboarding steps |
| `apps/teams/views.py` | Team management |

### Templates
| Directory | Contents |
|-----------|----------|
| `templates/web/` | Home, surveys |
| `templates/metrics/` | Dashboard, charts |
| `templates/integrations/` | Integration setup |
| `templates/onboarding/` | Onboarding steps |
| `templates/teams/` | Team management |
| `templates/allauth/` | Auth pages |

### Test Factories
| File | Factories |
|------|-----------|
| `apps/metrics/factories.py` | TeamFactory, TeamMemberFactory, PullRequestFactory, PRSurveyFactory |
| `apps/integrations/factories.py` | UserFactory, GitHubIntegrationFactory, SlackIntegrationFactory |

---

## Key URLs to Test

### Public URLs (No Auth)
| URL | View | Purpose |
|-----|------|---------|
| `/` | `home` | Homepage |
| `/accounts/login/` | allauth | Login |
| `/accounts/signup/` | allauth | Signup |
| `/health/` | health_check | Health endpoint |
| `/survey/<token>/` | `survey_landing` | Survey access |

### Authenticated URLs
| URL | View | Requires |
|-----|------|----------|
| `/app/` | `app_home` | Login |
| `/onboarding/` | `onboarding_start` | Login, no team |
| `/users/profile/` | `profile` | Login |

### Team-Scoped URLs
| URL Pattern | View | Requires |
|-------------|------|----------|
| `/app/<slug>/` | `team_home` | Team member |
| `/app/<slug>/metrics/dashboard/cto/` | `cto_overview` | Team admin |
| `/app/<slug>/metrics/dashboard/team/` | `team_dashboard` | Team member |
| `/app/<slug>/integrations/` | `integrations_home` | Team member |
| `/app/<slug>/team/` | `manage_team` | Team admin |

---

## Test User Setup

### Option 1: Superuser
```bash
make manage ARGS='createsuperuser'
# Email: test@example.com
# Password: testpass123
```

### Option 2: Seed Demo Data
```bash
python manage.py seed_demo_data
# Creates: Demo Team with members, PRs, surveys
```

### Option 3: Factory in Tests
```python
from apps.integrations.factories import UserFactory
from apps.metrics.factories import TeamFactory

user = UserFactory(email='test@example.com')
user.set_password('testpass123')
user.save()

team = TeamFactory(name='Test Team', slug='test-team')
team.members.add(user, through_defaults={'role': 'admin'})
```

---

## Server Commands

### Start Services
```bash
make start-bg      # PostgreSQL + Redis (Docker)
make dev           # Django + Vite dev servers
```

### Verify Running
```bash
curl -s localhost:8000/health/  # Should return 200
curl -s localhost:8000/         # Should return HTML
```

### Stop Services
```bash
make stop          # Stop Docker services
# Ctrl+C to stop dev server
```

---

## Playwright MCP Tools

### Navigation & Snapshots
```
mcp__playwright__browser_navigate(url="http://localhost:8000/")
mcp__playwright__browser_snapshot()
mcp__playwright__browser_take_screenshot()
```

### Form Interaction
```
mcp__playwright__browser_fill_form(fields=[
    {"name": "Email", "type": "textbox", "ref": "S123", "value": "test@example.com"},
    {"name": "Password", "type": "textbox", "ref": "S124", "value": "testpass123"}
])
mcp__playwright__browser_click(element="Submit button", ref="S125")
```

### Verification
```
mcp__playwright__browser_wait_for(text="Dashboard")
mcp__playwright__browser_console_messages()
mcp__playwright__browser_network_requests()
```

---

## Authentication Flow

### Login Process
1. Navigate to `/accounts/login/`
2. Fill email field
3. Fill password field
4. Click "Sign In" button
5. Wait for redirect to `/app/` or `/onboarding/`

### Session Management
- Django session cookie: `sessionid`
- CSRF token required for POST requests
- Session expires based on `SESSION_COOKIE_AGE` setting

---

## HTMX Considerations

### Lazy Loading
Dashboard charts use HTMX lazy loading:
```html
<div hx-get="/app/slug/metrics/charts/ai-adoption/"
     hx-trigger="load"
     hx-swap="innerHTML">
  Loading...
</div>
```

**Testing Approach:**
1. Navigate to page
2. Wait for initial load
3. Wait for HTMX requests to complete
4. Then take snapshot/screenshot

### Partial Updates
Form submissions often return partial HTML:
```html
<form hx-post="/app/slug/integrations/github/repos/123/toggle/"
      hx-swap="outerHTML">
```

**Testing Approach:**
1. Click toggle button
2. Wait for network request
3. Verify element updated

---

## Known Limitations

### OAuth Testing
- GitHub/Jira/Slack OAuth require external services
- Cannot fully automate OAuth flows
- Use pre-seeded integrations instead

### Rate Limiting
- OAuth callbacks: 10/min per IP
- Webhooks: 100/min per IP
- May need delays between rapid tests

### Team Isolation
- Each team's data is isolated
- Tests must use correct team_slug
- Admin vs member access differs

---

## Environment Variables

Key settings for testing:
```bash
DEBUG=True                    # Enable debug mode
DATABASE_URL=postgresql://... # Test database
REDIS_URL=redis://localhost   # Cache
SECRET_KEY=test-secret-key    # Django secret
```

---

## Existing Test Patterns

### Django TestCase Pattern
```python
from django.test import TestCase, Client
from apps.metrics.factories import TeamFactory

class TestDashboard(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.user = UserFactory()
        self.client = Client()
        self.client.force_login(self.user)

    def test_dashboard_loads(self):
        response = self.client.get(f'/app/{self.team.slug}/metrics/dashboard/team/')
        self.assertEqual(response.status_code, 200)
```

### View Test Pattern
```python
def test_requires_login(self):
    response = self.client.get('/app/')
    self.assertEqual(response.status_code, 302)
    self.assertIn('/accounts/login/', response.url)
```

---

## Dependencies

### Required Services
| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache/Celery |
| Django | 8000 | Backend |
| Vite | 5173 | Frontend assets |

### Python Packages
- `django-allauth` - Authentication
- `factory-boy` - Test data
- `celery` - Background tasks

### JavaScript Packages
- `@playwright/test` - Browser automation
- `htmx.org` - AJAX interactions
- `alpinejs` - Client-side state
- `chart.js` - Data visualization
