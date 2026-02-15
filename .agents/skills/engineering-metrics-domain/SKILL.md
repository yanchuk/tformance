---
name: engineering-metrics-domain
description: Domain knowledge for engineering metrics CTOs care about. Triggers on DORA metrics, cycle time, lead time, deployment frequency, PR velocity, throughput, productivity metrics. Understanding what metrics matter and why.
---

# Engineering Metrics Domain Knowledge

## Purpose

Provide domain context for engineering metrics that CTOs use to measure team performance and AI tool impact.

## When to Use

**Automatically activates when:**
- Implementing dashboard metrics
- Working on analytics features
- Discussing productivity measurement
- Building reports for CTOs

## Core Metrics Categories

### 1. DORA Metrics (Industry Standard)

| Metric | Definition | Good Target |
|--------|------------|-------------|
| **Deployment Frequency** | How often code deploys to production | Multiple per day |
| **Lead Time for Changes** | Commit to production time | < 1 day |
| **Mean Time to Recovery** | Time to restore service after incident | < 1 hour |
| **Change Failure Rate** | % of deployments causing failures | < 15% |

### 2. PR/Code Review Metrics

| Metric | Definition | Why It Matters |
|--------|------------|----------------|
| **PR Cycle Time** | PR open → merged | Developer wait time |
| **Time to First Review** | PR open → first review | Review bottleneck indicator |
| **Review Rounds** | Number of review iterations | Code quality/clarity |
| **PR Size** | Lines changed per PR | Reviewability |
| **Merge Rate** | PRs merged vs opened | Completion rate |

### 3. AI Impact Metrics (Tformance Focus)

| Metric | Definition | What It Shows |
|--------|------------|---------------|
| **AI-Assisted PR %** | PRs using AI tools / total PRs | AI adoption |
| **AI vs Non-AI Cycle Time** | Compare cycle times | AI productivity impact |
| **AI Tool Distribution** | Which AI tools are used | Tool preferences |
| **AI by Developer** | Per-developer AI usage | Adoption patterns |
| **AI by Category** | AI usage by tech area | Where AI helps most |

## Tformance Data Model Mapping

```
Metric Category → Tformance Model → Key Fields
────────────────────────────────────────────────
PR Velocity     → PullRequest      → created_at, merged_at, state
Cycle Time      → PullRequest      → created_at, merged_at
Review Time     → PRReview         → submitted_at, pull_request.created_at
AI Usage        → PullRequest      → effective_is_ai_assisted, effective_ai_tools
                → AIUsageDaily     → tool, usage_minutes
                → PRSurvey         → ai_tools_used, satisfaction
Weekly Trends   → WeeklyMetrics    → prs_merged, avg_cycle_time_hours
```

## Calculation Examples

### PR Cycle Time

```python
# Time from PR creation to merge
cycle_time = pr.merged_at - pr.created_at

# Average for team
from django.db.models import Avg, F
avg_cycle = PullRequest.for_team.filter(
    state='merged'
).annotate(
    cycle_time=F('merged_at') - F('created_at')
).aggregate(avg=Avg('cycle_time'))
```

### AI Impact Comparison

```python
# Compare AI vs non-AI assisted PRs
ai_prs = PullRequest.for_team.filter(state='merged')

# Note: Use service layer for effective_* property handling
ai_assisted_times = [
    pr.cycle_time for pr in ai_prs
    if pr.effective_is_ai_assisted
]
non_ai_times = [
    pr.cycle_time for pr in ai_prs
    if not pr.effective_is_ai_assisted
]
```

### Weekly Throughput

```python
from django.db.models.functions import TruncWeek
from django.db.models import Count

weekly = PullRequest.for_team.filter(
    state='merged'
).annotate(
    week=TruncWeek('merged_at')
).values('week').annotate(
    count=Count('id')
).order_by('week')
```

## CTO Perspectives

### What CTOs Want to Know

1. **"Is AI actually helping?"** → Compare AI vs non-AI metrics
2. **"Who's adopting AI tools?"** → Per-developer AI usage
3. **"Where does AI help most?"** → AI usage by tech category
4. **"Are we getting faster?"** → Trend lines over time
5. **"How do we compare?"** → Benchmarks (future feature)

### Dashboard Priorities

| Priority | Metric | Why |
|----------|--------|-----|
| P0 | AI Adoption Rate | Core value prop |
| P0 | AI Impact on Cycle Time | Proves ROI |
| P1 | Team Throughput Trend | Overall health |
| P1 | Per-Developer AI Usage | Adoption gaps |
| P2 | Review Bottlenecks | Process improvement |
| P2 | PR Size Distribution | Code quality |

## Anti-Patterns to Avoid

| Don't Do | Why | Instead |
|----------|-----|---------|
| Lines of code as productivity | Gameable, misleading | PR count, cycle time |
| Raw commit count | Quality > quantity | PRs merged |
| Individual rankings | Discourages collaboration | Team metrics |
| Daily metrics | Too noisy | Weekly/monthly trends |

## Related Services

- `DashboardService` - Main metrics aggregation
- `PRListService` - PR-level data with AI info
- `WeeklyMetricsService` - Pre-aggregated weekly data

---

**Enforcement Level**: SUGGEST
**Priority**: Medium
