# Analytics Restructure Plan

**Last Updated:** 2025-12-23
**Status:** Planning
**Priority:** High - Core Product Improvement

---

## Executive Summary

Restructure the monolithic CTO Overview dashboard into focused, question-answering analytics pages. The current implementation has 22+ widgets on a single page, creating information overload. The new structure will provide 6 focused pages that answer specific CTO questions, with a Pull Requests page serving as the data exploration foundation.

### Core Principle
> Data is a compass - showing numbers doesn't help, showing trends and comparisons does.
> Minimum period: weekly. Recommended: monthly for better trend visibility.

### Key Deliverables
1. **Pull Requests Page** - Data explorer with comprehensive filters
2. **Overview (Health Check)** - Quick morning status view
3. **AI Adoption** - Core product differentiator page
4. **Delivery Metrics** - Productivity and velocity trends
5. **Quality & Reviews** - Code quality and review bottlenecks
6. **Team Performance** - Individual metrics with comparisons

---

## Current State Analysis

### Existing Implementation
- **Location:** `templates/metrics/cto_overview.html` (507 lines)
- **Views:** `apps/metrics/views/dashboard_views.py`, `apps/metrics/views/chart_views.py`
- **Services:** `apps/metrics/services/dashboard_service.py`

### Current Page Structure
The `cto_overview.html` contains 22+ widgets in a single scrolling page:
1. Key Metrics Cards (PRs, cycle time, quality, AI %)
2. AI Adoption Trend + Quality by AI Status
3. GitHub Copilot section (4 widgets)
4. AI Detection section (3 widgets)
5. Survey Analytics section (3 widgets)
6. Cycle Time + Review Time trends
7. PR Size Distribution + Quality Indicators
8. AI Feedback Issues
9. Iteration Metrics
10. CI/CD + Deployments
11. File Category Breakdown
12. Team Breakdown Table
13. Reviewer Workload
14. Reviewer Correlations
15. PRs Missing Jira Links

### Problems Identified
1. **Information overload** - Too many widgets competing for attention
2. **No narrative flow** - Just numbers, not answers to questions
3. **Missing trend focus** - Week-over-week comparisons are implicit
4. **No drill-down path** - Can't easily go from summary to detail
5. **Single page load** - Heavy even with HTMX lazy loading

### Data Models Available
All required data is already in the database:
- `PullRequest` - PRs with cycle_time, review_time, AI detection
- `PRReview` - Reviews with state, AI bot detection
- `PRFile` - File changes with categories
- `PRComment` - Comment counts
- `Commit` - Commits with AI co-author detection
- `JiraIssue` - Jira tickets with story points
- `AIUsageDaily` - Copilot metrics
- `PRSurvey` / `PRSurveyReview` - Survey responses
- `WeeklyMetrics` - Pre-aggregated metrics
- `ReviewerCorrelation` - Reviewer pair analysis
- `DailyInsight` - Auto-generated insights

---

## Proposed Future State

### Information Architecture

```
Analytics (metrics app)
├── /a/<team>/analytics/                → Overview (Health Check)
├── /a/<team>/analytics/ai-adoption/    → AI Adoption
├── /a/<team>/analytics/delivery/       → Delivery Metrics
├── /a/<team>/analytics/quality/        → Quality & Reviews
├── /a/<team>/analytics/team/           → Team Performance
└── /a/<team>/pull-requests/            → Pull Requests (data explorer)
```

### Page Specifications

#### Page 1: Overview (Health Check)
**Route:** `/a/<team>/analytics/`
**Purpose:** Quick glance to see if anything needs attention
**Target User:** CTO daily/weekly check-in

**Widgets (5-6 max):**
1. Key Metrics Cards with week-over-week change
2. Alerts/Anomalies Panel (DailyInsight)
3. PR Velocity Trend (weekly bar, 8 weeks)
4. Active Blockers (PRs open >3 days)
5. Quick Links to other pages

#### Page 2: AI Adoption
**Route:** `/a/<team>/analytics/ai-adoption/`
**Purpose:** Answer "Is AI actually helping my team?"
**Target User:** CTO monthly/quarterly review

**Widgets:**
1. AI Adoption Trend (weekly line chart)
2. AI vs Non-AI Comparison Table (key differentiator)
3. Copilot Metrics section (if available)
4. AI Tools Breakdown (pie chart)
5. AI Modification Effort (from surveys)

#### Page 3: Delivery Metrics
**Route:** `/a/<team>/analytics/delivery/`
**Purpose:** Track velocity and throughput over time
**Target User:** CTO/Lead sprint review

**Widgets:**
1. PR Throughput Trend (weekly bar)
2. Cycle Time Trend (line with P50/P90)
3. Velocity Trend (Jira story points)
4. PR Size Distribution (histogram)
5. Time Allocation (stacked bar - Epic/Non-Epic/Bug)
6. Deployment Frequency (DORA)

#### Page 4: Quality & Reviews
**Route:** `/a/<team>/analytics/quality/`
**Purpose:** Identify quality issues and review bottlenecks
**Target User:** Tech Lead, CTO 1:1 prep

**Widgets:**
1. Quality Indicators Cards (revert/hotfix rates)
2. Review Time Trend (line)
3. Reviewer Workload Table (color-coded)
4. Iteration Metrics (review rounds, fix response)
5. CI/CD Pass Rate
6. Reviewer Correlations (admin only)

#### Page 5: Team Performance
**Route:** `/a/<team>/analytics/team/`
**Purpose:** Individual member metrics with comparison
**Target User:** CTO 1:1 prep, performance reviews

**Widgets:**
1. Team Breakdown Table (color-coded)
2. Jira Performance Table (if connected)
3. Individual Trend (member selector)
4. Comparison View (select 2-3 members)

#### Page 6: Pull Requests (Data Explorer)
**Route:** `/a/<team>/pull-requests/`
**Purpose:** Drill-down into specific PRs
**Target User:** Anyone investigating specific data

**Features:**
- Full-width table with sortable columns
- Comprehensive filter panel
- Bulk stats row
- Export to CSV
- Deep link support via GET params

**Table Columns:**
- PR Title (GitHub link)
- Repository
- Author
- Reviewers
- State
- Cycle Time
- Review Time
- Lines Changed
- Review Rounds
- Comments
- AI Assisted
- Jira Link
- Merged At

**Filters (GET params):**
- `date_from`, `date_to` - Date range
- `repo` - Repository
- `author` - Team member
- `reviewer` - Reviewer
- `ai` - AI assisted (yes/no/all)
- `ai_tool` - Specific AI tool
- `size` - PR size bucket
- `state` - open/merged/closed
- `has_jira` - Has Jira link

---

## Implementation Phases

### Phase 1: Pull Requests Page (Foundation)
**Duration:** M
**Dependencies:** None

This page provides the data exploration foundation that all other pages will link to.

### Phase 2: Overview (Health Check)
**Duration:** M
**Dependencies:** Phase 1 (for "View PRs" links)

Most frequently used page - CTO's daily check-in view.

### Phase 3: AI Adoption Page
**Duration:** M
**Dependencies:** Phase 2

Core product differentiator - THE page that answers the main value prop.

### Phase 4: Delivery & Quality Pages
**Duration:** L
**Dependencies:** Phase 3

These can be done in parallel. Splits remaining widgets from current page.

### Phase 5: Team Performance Page
**Duration:** M
**Dependencies:** Phase 4

Individual comparison features, color-coded tables.

### Phase 6: Legacy Cleanup
**Duration:** S
**Dependencies:** Phase 5

Remove old cto_overview.html, update navigation, redirects.

---

## Technical Architecture

### File Structure Changes

```
apps/metrics/
├── views/
│   ├── __init__.py
│   ├── dashboard_views.py      # Keep, refactor for new pages
│   ├── chart_views.py          # Keep, reuse endpoints
│   ├── pr_list_views.py        # NEW - Pull Requests page
│   └── analytics_views.py      # NEW - New analytics pages
├── templates/metrics/
│   ├── analytics/
│   │   ├── base_analytics.html # NEW - Shared layout with nav
│   │   ├── overview.html       # NEW
│   │   ├── ai_adoption.html    # NEW
│   │   ├── delivery.html       # NEW
│   │   ├── quality.html        # NEW
│   │   └── team.html           # NEW
│   ├── pull_requests/
│   │   ├── list.html           # NEW - Main PR list page
│   │   ├── partials/
│   │   │   ├── filters.html    # NEW - Filter panel
│   │   │   ├── table.html      # NEW - PR table
│   │   │   └── stats_row.html  # NEW - Aggregate stats
│   └── partials/               # Keep existing, add new
│       └── ...
├── services/
│   ├── dashboard_service.py    # Keep, extend
│   └── pr_list_service.py      # NEW - PR list queries
└── urls.py                     # Update with new routes
```

### URL Structure

```python
# apps/metrics/urls.py additions
team_urlpatterns = [
    # New analytics pages
    path("analytics/", views.analytics_overview, name="analytics_overview"),
    path("analytics/ai-adoption/", views.analytics_ai_adoption, name="analytics_ai_adoption"),
    path("analytics/delivery/", views.analytics_delivery, name="analytics_delivery"),
    path("analytics/quality/", views.analytics_quality, name="analytics_quality"),
    path("analytics/team/", views.analytics_team, name="analytics_team"),

    # Pull Requests page
    path("pull-requests/", views.pr_list, name="pr_list"),
    path("pull-requests/export/", views.pr_list_export, name="pr_list_export"),

    # Keep existing chart endpoints for HTMX
    # ...
]
```

### Navigation Component

```html
<!-- templates/metrics/analytics/base_analytics.html -->
<nav class="tabs tabs-bordered mb-6">
    <a class="tab {% if active_page == 'overview' %}tab-active{% endif %}"
       href="{% url 'metrics:analytics_overview' %}">Overview</a>
    <a class="tab {% if active_page == 'ai_adoption' %}tab-active{% endif %}"
       href="{% url 'metrics:analytics_ai_adoption' %}">AI Adoption</a>
    <a class="tab {% if active_page == 'delivery' %}tab-active{% endif %}"
       href="{% url 'metrics:analytics_delivery' %}">Delivery</a>
    <a class="tab {% if active_page == 'quality' %}tab-active{% endif %}"
       href="{% url 'metrics:analytics_quality' %}">Quality</a>
    <a class="tab {% if active_page == 'team' %}tab-active{% endif %}"
       href="{% url 'metrics:analytics_team' %}">Team</a>
    <a class="tab {% if active_page == 'pull_requests' %}tab-active{% endif %}"
       href="{% url 'metrics:pr_list' %}">Pull Requests</a>
</nav>
```

### Color Coding System

```css
/* design-system.css additions */
.app-heatmap-good { @apply bg-success/20 text-success; }
.app-heatmap-neutral { @apply bg-warning/20 text-warning; }
.app-heatmap-bad { @apply bg-error/20 text-error; }

/* For performance comparison tables */
.app-performance-top { @apply bg-success/10; }      /* Top 25% */
.app-performance-mid { @apply bg-warning/10; }      /* Middle 50% */
.app-performance-low { @apply bg-error/10; }        /* Bottom 25% */
```

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing functionality | High | Keep old endpoints, add new ones |
| Performance with large datasets | Medium | Use existing pagination, indexes |
| Complex filter combinations | Medium | Server-side filtering with queryset |
| Chart rendering issues | Low | Reuse existing Chart.js components |

### User Experience Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Learning new navigation | Medium | Keep sidebar menu, add breadcrumbs |
| Missing data users expect | High | Ensure all current widgets available |
| Too many page loads | Medium | Use HTMX for in-page updates |

### Mitigation Strategy
1. Feature flag for new analytics (show both old/new temporarily)
2. Comprehensive test coverage before launch
3. User feedback collection during rollout
4. Keep legacy page accessible during transition

---

## Success Metrics

### Quantitative
- Page load time < 2s for each analytics page
- PR list page handles 10,000+ PRs efficiently
- All existing chart endpoints reused (zero duplication)

### Qualitative
- CTO can answer "Is AI helping?" in under 30 seconds
- Drill-down from any metric to specific PRs in 2 clicks
- Team comparison takes < 1 minute to configure

### Definition of Done
- [ ] All 6 pages implemented and tested
- [ ] Navigation between pages works correctly
- [ ] Filters persist via GET params
- [ ] All existing data is accessible
- [ ] Mobile-responsive layouts
- [ ] Tests for new views and services
- [ ] Documentation updated

---

## Dependencies

### Internal Dependencies
- Existing `dashboard_service.py` functions
- Existing chart partial templates
- DaisyUI/Tailwind design system
- HTMX lazy loading pattern

### External Dependencies
- Chart.js (already installed)
- None new required

---

## Resource Requirements

### Development Time
- Phase 1: 1-2 days (Pull Requests page)
- Phase 2: 1 day (Overview page)
- Phase 3: 1 day (AI Adoption page)
- Phase 4: 2 days (Delivery + Quality pages)
- Phase 5: 1 day (Team Performance page)
- Phase 6: 0.5 days (Cleanup)

**Total Estimate:** 6-8 days

### Review/Testing
- Code review: 1 day total
- Manual testing: 1 day
- E2E test updates: 0.5 days

---

## Appendix: CTO Questions Framework

Based on PRD research and CTO community analysis (88,939 messages):

### Daily/Weekly Questions (Health Check)
1. "Is everything on track?" → Overview page
2. "Where are the bottlenecks?" → Overview alerts + Quality page
3. "Is my team healthy?" → Team page

### Monthly/Quarterly Questions (Strategic)
4. "Is AI actually helping us?" → AI Adoption page
5. "Are we getting ROI on AI tools?" → AI Adoption page
6. "How is productivity trending?" → Delivery page
7. "What's our code quality like?" → Quality page

### 1:1/Planning Questions (Deep-Dive)
8. "How is [person] doing?" → Team page
9. "Where is time being spent?" → Delivery page
10. "Who is overloaded with reviews?" → Quality page
