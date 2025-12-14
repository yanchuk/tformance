# Dashboard UX Improvements Plan

**Last Updated:** 2024-12-14

## Executive Summary

This plan addresses two critical UX issues:

1. **App Home Page (`/app/`)**: Currently shows a generic "You're Signed In!" template regardless of user state. Needs to differentiate between new users (guide to integrations) and users with data (show quick stats/insights).

2. **Team Dashboard (`/app/metrics/dashboard/team/`)**: Has poor layout (side-by-side chart + table) and limited charts. Needs stacked layout and additional charts per PRD specifications.

**Goal:** Transform the app into a data-driven experience that guides new users and delivers immediate value to existing users.

---

## Current State Analysis

### App Home Page (`/app/`)

**Current behavior:**
- Shows static "You're Signed In!" message with rocket image
- Same content for all users regardless of integration status or data
- No actionable guidance or insights
- Template: `templates/web/app_home.html`
- View: `apps/web/views.py::team_home()`

**Problems:**
- New users see no guidance on next steps
- Users with data see no value on landing
- Missed opportunity for engagement

### Team Dashboard (`/app/metrics/dashboard/team/`)

**Current behavior:**
- Side-by-side layout: Cycle Time Trend (left) + AI Detective Leaderboard (right)
- Only 2 widgets implemented (chart + table)
- Template: `templates/metrics/team_dashboard.html`
- View: `apps/metrics/views/dashboard_views.py::team_dashboard()`

**Problems:**
- Side-by-side layout causes cramped display
- Missing charts from PRD: PR throughput, review distribution, velocity
- No key metrics cards (stats summary)
- Limited insights for team members

### Integration Status

The demo team has:
- GitHub: Connected (36 members, demo-org)
- Jira: Not connected
- Slack: Not connected

---

## Proposed Future State

### App Home Page - Two States

#### State 1: New User (No Integrations)

```
┌─────────────────────────────────────────────────────────────┐
│  Welcome to Tformance!                                       │
│                                                              │
│  Let's get you set up in 3 easy steps:                      │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 1. Connect GitHub  [Required]                    [→]    ││
│  │    Import your team and start tracking PRs              ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 2. Connect Jira    [Optional]                   [Skip]  ││
│  │    Track story points and sprint velocity               ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 3. Connect Slack   [Optional]                   [Skip]  ││
│  │    Enable PR surveys and leaderboards                   ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  Progress: [████░░░░░░] 1/3 steps complete                  │
└─────────────────────────────────────────────────────────────┘
```

#### State 2: User with Data (Has GitHub + Data)

```
┌─────────────────────────────────────────────────────────────┐
│  Good morning! Here's your team's pulse:                     │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 12 PRs   │ │ 4.2 hrs  │ │ 67%      │ │ 2.1/3    │       │
│  │ merged   │ │ avg cycle│ │ AI-assist│ │ quality  │       │
│  │ +3 ↑     │ │ -0.5 ↓   │ │ +5% ↑    │ │ +0.2 ↑   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                              │
│  Quick Actions:                                              │
│  [View Analytics →]  [Check Leaderboard →]                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Recent Activity                                          ││
│  │ • PR #234 merged by @john (AI-assisted)                 ││
│  │ • PR #233 merged by @jane                               ││
│  │ • New survey responses: 3                               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ⚠️ Complete your setup:                                  ││
│  │ Connect Slack to enable PR surveys [Connect →]          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Team Dashboard - Stacked Layout with More Charts

```
┌─────────────────────────────────────────────────────────────┐
│  Team Dashboard                          [7d] [30d] [90d]   │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 12 PRs   │ │ 4.2 hrs  │ │ 67%      │ │ 2.1/3    │       │
│  │ merged   │ │ avg cycle│ │ AI-assist│ │ quality  │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ PR Throughput                                   📈      ││
│  │ [Chart: PRs merged over time - bar/line]               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Cycle Time Trend                                📉      ││
│  │ [Chart: Average cycle time over time - line]           ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Review Distribution                             🍩      ││
│  │ [Chart: Reviews by team member - pie/donut]            ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ AI Detective Leaderboard                        🏆      ││
│  │ [Table: Rankings with accuracy]                        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Recent PRs                                      📋      ││
│  │ [Table: PR title, author, cycle time, AI status]       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: App Home Page Redesign (Priority: High)

**Goal:** Make the home page actionable based on user state

#### 1.1 Backend: Integration Status Detection

Create a service to detect integration status for a team:

```python
# apps/integrations/services/status.py
def get_team_integration_status(team):
    """Return integration status and data counts for a team."""
    return {
        'github': {
            'connected': bool,
            'org_name': str | None,
            'member_count': int,
            'repo_count': int,
        },
        'jira': {
            'connected': bool,
            'site_name': str | None,
            'project_count': int,
        },
        'slack': {
            'connected': bool,
            'workspace_name': str | None,
        },
        'has_data': bool,  # True if PRs exist
        'pr_count': int,
        'survey_count': int,
    }
```

#### 1.2 Backend: Quick Stats Service

```python
# apps/metrics/services/quick_stats.py
def get_team_quick_stats(team, days=7):
    """Return quick stats for dashboard home."""
    return {
        'prs_merged': int,
        'prs_merged_change': float,  # % vs previous period
        'avg_cycle_time_hours': float,
        'cycle_time_change': float,
        'ai_assisted_percent': float,
        'ai_percent_change': float,
        'avg_quality_rating': float,
        'quality_change': float,
        'recent_activity': [
            {'type': 'pr_merged', 'title': str, 'author': str, 'ai_assisted': bool},
            ...
        ]
    }
```

#### 1.3 Frontend: Conditional Home Template

Update `templates/web/app_home.html` with Alpine.js state handling:

- New user state: Setup wizard with progress indicator
- Data state: Stats cards + quick actions + recent activity
- Partial integration state: Show setup prompts for missing integrations

#### 1.4 View Update

```python
# apps/web/views.py
@login_and_team_required
def team_home(request):
    integration_status = get_team_integration_status(request.team)

    context = {
        'team': request.team,
        'active_tab': 'dashboard',
        'integration_status': integration_status,
    }

    if integration_status['has_data']:
        context['quick_stats'] = get_team_quick_stats(request.team)

    return render(request, 'web/app_home.html', context)
```

### Phase 2: Team Dashboard Layout Fix (Priority: High)

**Goal:** Convert side-by-side to stacked layout, add key metrics cards

#### 2.1 Update Template Layout

Change from `grid-cols-2` to single column stacked layout:

```html
<!-- Before -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">

<!-- After -->
<div class="flex flex-col gap-6">
```

#### 2.2 Add Key Metrics Cards

Add stats cards row at the top (reuse from CTO overview):

```html
<div id="key-metrics-container"
     hx-get="{% url 'metrics:cards_metrics' %}?days={{ days }}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <!-- 4 stat cards: PRs, Cycle Time, AI%, Quality -->
</div>
```

### Phase 3: Additional Charts (Priority: Medium)

**Goal:** Add missing charts from PRD

#### 3.1 PR Throughput Chart

- Type: Bar chart with line overlay
- X-axis: Days/weeks
- Y-axis: PR count
- Shows merged PRs over time

```python
# New view
@login_and_team_required
def pr_throughput_chart(request):
    # Query PullRequest.objects.filter(...).annotate(...)
    pass
```

#### 3.2 Review Distribution Chart

- Type: Pie/donut chart
- Shows reviews per team member
- Identifies review load imbalance

```python
@login_and_team_required
def review_distribution_chart(request):
    # Query PRReview.objects.filter(...).values('reviewer').annotate(...)
    pass
```

#### 3.3 Recent PRs Table

- Columns: PR Title (linked), Author, Cycle Time, Quality, AI Status
- Paginated with HTMX
- Shows last 10 PRs

```python
@login_and_team_required
def recent_prs_table(request):
    # Query last 10 merged PRs
    pass
```

### Phase 4: Polish & Testing (Priority: Medium)

- Responsive design testing
- Loading states for all HTMX components
- Empty states for charts with no data
- E2E tests for both user states

---

## Technical Details

### New Files to Create

```
apps/integrations/services/status.py          # Integration status service
apps/metrics/services/quick_stats.py          # Quick stats for home
apps/metrics/views/chart_views.py             # New chart views (if splitting)
templates/web/app_home.html                   # Complete rewrite
templates/web/components/setup_wizard.html    # New user setup component
templates/web/components/quick_stats.html     # Stats cards component
templates/metrics/partials/pr_throughput.html # New chart partial
templates/metrics/partials/review_dist.html   # New chart partial
templates/metrics/partials/recent_prs.html    # New table partial
```

### Files to Modify

```
apps/web/views.py                             # Update team_home view
apps/metrics/views/dashboard_views.py         # Update team_dashboard
apps/metrics/urls.py                          # Add new chart endpoints
templates/metrics/team_dashboard.html         # Layout changes
assets/javascript/dashboard/                  # New chart configs
```

### URL Patterns to Add

```python
# apps/metrics/urls.py
path("charts/pr-throughput/", views.pr_throughput_chart, name="chart_pr_throughput"),
path("charts/review-distribution/", views.review_distribution_chart, name="chart_review_dist"),
path("tables/recent-prs/", views.recent_prs_table, name="table_recent_prs"),
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Performance with many PRs | Medium | High | Use pagination, date limits, caching |
| Chart.js integration issues | Low | Medium | Use existing patterns from cto_overview |
| Empty state confusion | Medium | Medium | Design clear empty states with guidance |
| Mobile responsiveness | Medium | Low | Test on multiple screen sizes |

---

## Success Metrics

1. **New User Conversion**: Users who connect GitHub within first session increases
2. **Time to Value**: Users see relevant data within 30 seconds of login
3. **Engagement**: Dashboard page views per session increases
4. **Setup Completion**: % of teams with all 3 integrations connected

---

## Dependencies

- Existing Chart.js utilities in `assets/javascript/dashboard/`
- HTMX lazy loading patterns from CTO overview
- DaisyUI stat card components
- Integration models and services already exist

---

## Effort Estimates

| Phase | Tasks | Effort | Priority |
|-------|-------|--------|----------|
| Phase 1 | App Home Redesign | L (3-4 days) | High |
| Phase 2 | Dashboard Layout | S (0.5 day) | High |
| Phase 3 | Additional Charts | M (2 days) | Medium |
| Phase 4 | Polish & Testing | M (1-2 days) | Medium |
| **Total** | | **~7-8 days** | |
