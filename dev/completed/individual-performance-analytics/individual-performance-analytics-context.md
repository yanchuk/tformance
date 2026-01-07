# Individual Performance Analytics - Context Document

**Last Updated**: 2026-01-05 (Session 2 - Phase 1 Complete)

## Current Implementation State

### Phase 1: Service Layer - COMPLETE ✅

**Commit**: `d2dba34` on branch `feature/individual-performance-analytics`

**What was implemented:**
1. Enhanced `get_team_breakdown()` with new metrics:
   - `avg_pr_size`: Average PR size (additions + deletions)
   - `reviews_given`: Count of reviews given as reviewer (excludes AI reviews)
   - `avg_review_response_hours`: Average time from PR creation to first review
   - `ai_pct`: Now uses `is_ai_assisted` field (NOT surveys)

2. Added `get_team_averages()` function for team-wide comparison

3. Added new sort options: `pr_size`, `reviews`, `response_time`

**Test Results**: 27 tests pass (10 new tests added)

### Key Decisions Made This Session

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI Detection | Use `is_ai_assisted` field | Surveys are often empty, PR detection is reliable |
| Team Averages | Average of member averages | Equal weight per member for fair comparison |
| Query Count | 3 queries (not N+1) | PR aggregates + reviews + response times |
| Bot Reviews | Excluded via `is_ai_review=False` | Don't count bot reviews in human metrics |

### Worktree Setup

```bash
# Active worktree
cd /Users/yanchuk/Documents/GitHub/tformance-individual-perf

# Run tests
/Users/yanchuk/Documents/GitHub/tformance/.venv/bin/python -m pytest apps/metrics/tests/dashboard/test_team_breakdown.py -v
```

## Key Files

### Service Layer

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/metrics/services/dashboard/team_metrics.py` | Team member aggregation | `get_team_breakdown()`, `get_team_velocity()` |
| `apps/metrics/services/dashboard/_helpers.py` | Shared helpers | `_get_merged_prs_in_range()`, `_avatar_url_from_github_id()` |
| `apps/metrics/services/dashboard/review_metrics.py` | Review aggregation | Reference for PRReview queries |

### Views

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/metrics/views/chart_views.py` | Chart/table endpoints | `team_breakdown_table()` (line 103) |
| `apps/metrics/views/analytics_views.py` | Analytics pages | `analytics_team()` hosts the page |

### Templates

| File | Purpose |
|------|---------|
| `templates/metrics/partials/team_breakdown_table.html` | Team breakdown table partial |
| `templates/metrics/analytics/team.html` | Team Performance page container |

### Tests

| File | Purpose |
|------|---------|
| `apps/metrics/tests/test_chart_views.py` | View tests including `TeamBreakdownTableViewTests` |
| `apps/metrics/tests/dashboard/test_team_metrics.py` | Service layer tests (if exists) |

## Models Involved

### PullRequest

```python
# Key fields for this feature
class PullRequest(BaseTeamModel):
    author = ForeignKey(TeamMember)
    state = CharField()  # 'merged', 'open', 'closed'
    merged_at = DateTimeField()
    cycle_time_hours = DecimalField()
    additions = IntegerField()
    deletions = IntegerField()

    @property
    def effective_is_ai_assisted(self) -> bool:
        """Returns LLM-based AI detection if available, else pattern-based."""
```

### PRReview

```python
class PRReview(BaseTeamModel):
    pr = ForeignKey(PullRequest)
    reviewer = ForeignKey(TeamMember)
    state = CharField()  # 'approved', 'changes_requested', 'commented'
    submitted_at = DateTimeField()
```

### TeamMember

```python
class TeamMember(BaseTeamModel):
    display_name = CharField()
    github_id = IntegerField()
    github_username = CharField()
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| AI Detection Source | `effective_is_ai_assisted` | Survey-based is often empty, LLM detection is more reliable |
| Comparison Threshold | 20% deviation | Standard threshold for meaningful variance |
| New Sort Fields | `pr_size`, `reviews`, `response_time` | Match new columns |
| Team Average Calculation | Exclude outliers? | TBD - initially include all members |
| Responsive Design | Hide PR Size, Response on mobile | Keep core metrics visible |

## Query Patterns

### Current: get_team_breakdown Query

```python
# Single aggregated query for PR metrics per author
query = (
    prs.exclude(author__isnull=True)
    .values("author__id", "author__display_name", "author__github_id")
    .annotate(
        prs_merged=Count("id"),
        avg_cycle_time=Avg("cycle_time_hours"),
    )
)
```

### New: Reviews Given Query (to add)

```python
# Reviews given per member
review_counts = (
    PRReview.objects.filter(
        team=team,
        submitted_at__range=(start_date, end_date),
        is_ai_review=False,  # Exclude bot reviews
    )
    .values("reviewer_id")
    .annotate(reviews_given=Count("id"))
)
```

### New: Review Response Time Query (to add)

```python
# Average time from PR creation to first review (as reviewer)
# This requires looking at PRs where member was reviewer
```

### New: PR Size Query (to add)

```python
# Add to existing PR aggregation
.annotate(
    avg_pr_size=Avg(F("additions") + F("deletions")),
)
```

### New: AI % Query (to add)

```python
# Count AI-assisted using effective property
# Note: effective_is_ai_assisted is a property, may need to filter differently
ai_count = prs.filter(author_id=author_id).annotate(
    is_ai=Case(
        When(llm_summary__ai__is_assisted__gte=0.5, then=Value(True)),
        default=F("is_ai_assisted"),
    )
).filter(is_ai=True).count()
```

## Dependencies

### Python Packages
- Django ORM (existing)
- No new packages required

### Frontend
- DaisyUI table classes (existing)
- Tailwind CSS (existing)
- HTMX for sorting (existing)

## Existing Test Patterns

### TeamBreakdownTableViewTests (from test_chart_views.py)

```python
class TeamBreakdownTableViewTests(AuthenticatedAdminTestCase):
    def test_breakdown_empty_team(self):
        response = self.client.get(reverse("metrics:table_breakdown"))
        self.assertEqual(response.status_code, 200)

    def test_breakdown_with_prs(self):
        # Create PRs with factory
        response = self.client.get(reverse("metrics:table_breakdown"))
        self.assertContains(response, member.display_name)

    def test_breakdown_sort_by_cycle_time(self):
        response = self.client.get(reverse("metrics:table_breakdown"), {"sort": "cycle_time"})
```

## Related PRD

See `/Users/yanchuk/.claude/plans/sharded-wiggling-bunny.md` for full PRD with table structure and visual mockups.

## Worktree Setup

**Branch**: Create feature branch from main
**Worktree**: Use worktree for isolated development

```bash
# Create worktree
git worktree add ../tformance-individual-perf feature/individual-performance-analytics

# Navigate to worktree
cd ../tformance-individual-perf
```
