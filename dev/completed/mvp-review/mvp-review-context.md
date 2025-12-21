# MVP Review Context

**Last Updated:** 2025-12-13 (Session 2)

## Current Implementation State

### Session Progress
- **Test Suite**: All 1071 tests PASS ✅
- **Demo Data**: Seeded with `seed_demo_data --clear`
- **Test User**: `test@example.com` / `testpass123` (superuser, admin of Demo Team 1)

### Pages Reviewed
| Page | URL | Status | Issues |
|------|-----|--------|--------|
| App Home | `/app/` | ✅ Works | Placeholder content (should redirect to Analytics) |
| CTO Dashboard | `/app/metrics/dashboard/cto/` | ✅ Works | Page title generic |
| Team Dashboard | `/app/metrics/dashboard/team/` | ❌ **BUG** | HTMX target inheritance destroys page |
| Integrations | `/app/integrations/` | ✅ Works | Clean card layout |
| GitHub Members | `/app/integrations/github/members/` | ✅ Works | Table displays correctly |

### Screenshots Captured
All in `.playwright-mcp/`:
- `mvp-review-01-app-home.png` - App home with rocket illustration
- `mvp-review-02-cto-dashboard.png` - Full CTO dashboard with charts
- `mvp-review-04-team-dashboard-full.png` - Team dashboard (shows bug)
- `mvp-review-05-team-dashboard-partial.png` - Just leaderboard table (bug visible)
- `mvp-review-06-integrations.png` - Integrations page
- `mvp-review-07-github-members.png` - GitHub members table

---

## CRITICAL BUG FOUND

### Team Dashboard HTMX Target Inheritance Bug

**File**: `templates/metrics/team_dashboard.html`

**Problem**: Line 8 has `hx-target="#page-content"` on the outer wrapper:
```html
<div id="page-content" hx-target="#page-content">
```

This causes HTMX requests from child elements (chart containers) to target and REPLACE the entire `#page-content` div instead of just their own containers.

**Symptoms**:
- Page loads with header + charts initially
- After HTMX requests complete, only the LAST loaded partial remains
- Header "Team Dashboard" and time filter disappear
- Either only the chart OR only the leaderboard table shows

**Root Cause**: HTMX `hx-target` inheritance - children without explicit `hx-target` inherit from parent.

**Fix Required**: Add `hx-target="this"` to each chart container:
```html
<div id="cycle-time-container"
     hx-get="{% url 'metrics:chart_cycle_time' %}?days={{ days }}"
     hx-trigger="load"
     hx-swap="innerHTML"
     hx-target="this">  <!-- ADD THIS -->
```

Or remove `hx-target="#page-content"` from line 8.

---

## Key Files

### URL Configuration
- `tformance/urls.py` - Main URL routing (uses `/app/` prefix for team URLs)
- `apps/metrics/urls.py` - Dashboard URLs (cto_overview, team_dashboard, chart partials)
- `apps/integrations/urls.py` - Integration management URLs
- `apps/onboarding/urls.py` - Onboarding wizard URLs
- `apps/teams/urls.py` - Team management URLs

### Views
- `apps/metrics/views.py` - Dashboard views
- `apps/metrics/views/chart_views.py` - HTMX chart partial views
- `apps/integrations/views.py` - Integration OAuth and management
- `apps/onboarding/views.py` - Onboarding wizard steps
- `apps/teams/views/manage_team_views.py` - Team settings

### Templates (Bug Related)
- `templates/metrics/team_dashboard.html` - **HAS BUG** (line 8)
- `templates/metrics/cto_overview.html` - May have same issue, needs check
- `templates/metrics/partials/cycle_time_chart.html` - Partial (no issues)
- `templates/metrics/partials/leaderboard_table.html` - Partial (no issues)

### Services
- `apps/metrics/services/dashboard_service.py` - Dashboard data aggregation
- `apps/metrics/services/chart_formatters.py` - Chart.js data formatting
- `apps/metrics/services/survey_service.py` - PR survey logic
- `apps/integrations/services/github_sync.py` - GitHub data sync
- `apps/integrations/services/jira_sync.py` - Jira data sync
- `apps/integrations/services/slack_*.py` - Slack bot services

### Models
- `apps/metrics/models.py` - TeamMember, PullRequest, JiraIssue, PRSurvey, WeeklyMetrics
- `apps/integrations/models.py` - IntegrationCredential, GitHubRepo, SlackIntegration
- `apps/teams/models.py` - Team, Membership, Invitation

### JavaScript
- `assets/javascript/dashboard/dashboard-charts.js` - Chart.js utilities
- `assets/javascript/app.js` - HTMX event handlers

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| URL structure | `/app/` prefix (no team slug) | Simplified for single-team users |
| Dashboard charts | Chart.js + HTMX lazy loading | Already integrated, fast rendering |
| Styling | DaisyUI + TailwindCSS | Consistent components |
| AI data source | Self-reported surveys | Cursor API unavailable |
| Sync frequency | Daily via Celery Beat | Simple, reliable |
| Permissions | Admin vs Member roles | CTO overview vs Team dashboard |

---

## Dependencies

### External Services
- **GitHub OAuth App** - For repository access
- **Atlassian OAuth App** - For Jira access
- **Slack App** - For bot messaging

### Environment Variables Required
```bash
# GitHub
GITHUB_CLIENT_ID
GITHUB_CLIENT_SECRET
GITHUB_WEBHOOK_SECRET

# Jira
JIRA_CLIENT_ID
JIRA_CLIENT_SECRET

# Slack
SLACK_CLIENT_ID
SLACK_CLIENT_SECRET
SLACK_SIGNING_SECRET
```

### Services Required
- PostgreSQL database
- Redis (for Celery broker)
- Celery worker + beat

---

## Test Files

| Area | Test File | Tests |
|------|-----------|-------|
| Dashboard Service | `apps/metrics/tests/test_dashboard_service.py` | ~30 |
| Dashboard Views | `apps/metrics/tests/test_dashboard_views.py` | ~20 |
| Chart Views | `apps/metrics/tests/test_chart_views.py` | ~60 |
| GitHub Sync | `apps/integrations/tests/test_github_sync.py` | ~40 |
| Jira Sync | `apps/integrations/tests/test_jira_sync.py` | ~20 |
| Jira Views | `apps/integrations/tests/test_jira_views_projects.py` | ~20 |
| Slack Views | `apps/integrations/tests/test_slack_views.py` | ~50 |
| Slack Leaderboard | `apps/integrations/tests/test_slack_leaderboard.py` | ~15 |
| Survey Service | `apps/metrics/tests/test_survey_service.py` | ~30 |

**Total: ~1071 tests**

---

## UI Review Observations

### CTO Dashboard (Works Well)
- Key metrics cards prominent (30 PRs, 40.0h cycle time, 2.3 quality, 40% AI)
- AI Adoption Trend chart renders
- Quality by AI Status shows comparison (2.6 AI vs 1.7 Non-AI)
- Cycle Time Trend chart shows data
- Team breakdown table with avatars formatted well
- Time range filter (7d/30d/90d) visible

### Team Dashboard (Has Bug)
- Cycle Time chart data looks good when visible
- Leaderboard table beautifully rendered with:
  - Medal emojis for top 3 (🥇🥈🥉)
  - Avatar initials
  - Progress bars for accuracy
- BUT: Header and filters disappear due to HTMX bug

### Integrations Page (Excellent)
- Clean card layout for GitHub, Jira, Slack
- GitHub shows "Connected" with green badge
- Jira/Slack show "Not connected" with Connect buttons
- GitHub card has org info, Members (34), Repositories links
- Disconnect button properly styled in red

### GitHub Members (Excellent)
- Back navigation works
- Sync Now button present
- Table with Name, GitHub Username, Email, Status, Actions
- 34 members displayed with avatar initials
- Active status badges
- Deactivate buttons per row

---

## Common Commands

```bash
# Run tests
make test ARGS='--keepdb'

# Run specific test file
make test ARGS='apps.metrics.tests.test_dashboard_views --keepdb'

# Seed demo data
.venv/bin/python manage.py seed_demo_data --clear

# Start dev server
make dev

# Check dev server running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

---

## Known Issues

1. **CRITICAL: Team Dashboard HTMX Bug** - `hx-target="#page-content"` inheritance breaks page
2. **Chart HTMX timing** - Charts may initialize before data loads; handled by `htmx:afterSwap` event
3. **Page title generic** - Shows "The most amazing SaaS application..." instead of proper title
4. **App home placeholder** - Shows rocket illustration instead of redirecting to Analytics
5. **Date filter** - Default is 30 days; ensure seed data has recent dates
6. **Slack surveys** - Require real Slack workspace for full testing

---

## Next Steps (Priority Order)

1. **FIX**: Team Dashboard HTMX bug (templates/metrics/team_dashboard.html line 8)
2. **CHECK**: CTO Dashboard for same HTMX issue
3. **REVIEW**: Team Settings page
4. **REVIEW**: Landing page
5. **REVIEW**: Onboarding flow (skip OAuth since no prod credentials)
6. **FIX**: Page titles
7. **CONSIDER**: App home redirect to Analytics

---

## Review Checklist Reference

### Per-Page Checklist
- [ ] Page loads without errors
- [ ] Console shows no JS errors
- [ ] HTMX requests complete
- [ ] Data displays correctly
- [ ] Mobile responsive
- [ ] Styling consistent with DaisyUI
- [ ] Loading states visible
- [ ] Error states handled

### Per-Form Checklist
- [ ] Validation works
- [ ] Success redirects correctly
- [ ] Error messages display
- [ ] Submit button disabled during request
