# AI Adoption Feature Flag - Context Document

**Last Updated:** 2026-01-02

---

## Key Files

### Core Implementation Files

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/metrics/services/dashboard_service.py` | Main dashboard data aggregation | Add flag checks to 6+ functions |
| `apps/metrics/services/aggregation_service.py` | Weekly metrics aggregation | Update `compute_metrics_for_day`, `compute_ai_adoption_weekly` |
| `apps/metrics/services/quick_stats.py` | Quick stats for dashboard | Update `get_quick_stats_data`, `get_recent_activity` |
| `apps/metrics/services/insight_llm.py` | LLM insight data gathering | Verify `gather_insight_data` uses correct source |
| `apps/teams/models.py` | Waffle Flag model (teams.Flag) | No changes, use existing |

### Model Files (Reference Only)

| File | Purpose | Key Properties |
|------|---------|----------------|
| `apps/metrics/models/github.py` | PullRequest model | `effective_is_ai_assisted` property (line 334) |
| `apps/metrics/models/surveys.py` | PRSurvey model | `author_ai_assisted` field (line 72) |

### Test Files to Update

| File | Tests to Add/Modify |
|------|---------------------|
| `apps/metrics/tests/dashboard/test_key_metrics.py` | Flag-aware tests for `get_key_metrics` |
| `apps/metrics/tests/dashboard/test_sparkline_data.py` | Flag-aware tests for sparklines |
| `apps/metrics/tests/dashboard/test_ai_impact.py` | Flag-aware tests for AI impact |
| `apps/metrics/tests/dashboard/test_ai_metrics.py` | Flag-aware tests for AI trend |
| `apps/metrics/tests/test_aggregation_service.py` | Flag-aware tests for aggregation |
| `apps/metrics/tests/test_quick_stats.py` | Flag-aware tests for quick stats |

---

## Key Decisions

### D1: Flag Scope - Per-Team

**Decision**: Use per-team flag (via `teams.Flag` model)

**Rationale**:
- Different teams have different survey response rates
- Teams with high survey adoption should use survey data
- Teams with low/no surveys should use detection data
- Existing `teams.Flag` model already supports team-scoped flags

**Implementation**: Use `waffle.flag_is_active(request)` with team context

### D2: Default Value - False (Use Detection)

**Decision**: Default to `false` (use `effective_is_ai_assisted` only)

**Rationale**:
- User explicitly stated "we don't have survey data yet"
- Detection data is always available
- Survey data requires user action and has low response rates
- Safer default - teams can opt-in to surveys when ready

### D3: Fallback Behavior

**Decision**: When flag=true but no survey data, fall back to detection

**Rationale**:
- Prevents showing 0% AI adoption when surveys aren't answered
- Maintains consistency with current `get_ai_impact_stats` behavior
- Provides best available data without requiring all PRs to have surveys

### D4: Cache Strategy

**Decision**: Clear dashboard caches when flag changes

**Rationale**:
- Dashboard metrics are cached (5 minute TTL)
- Flag change should immediately reflect in UI
- Use `cache.delete_pattern()` or targeted cache clear

---

## Data Flow Diagrams

### Current Flow (Inconsistent)

```
Dashboard Card          → PRSurvey.author_ai_assisted (surveys)
Sparklines              → PRSurvey.author_ai_assisted (surveys)
LLM Insights            → PRSurvey + effective_is_ai_assisted (hybrid)
PR Filters              → PullRequest.effective_is_ai_assisted (detection)
```

### Proposed Flow (Flag-Controlled)

```
Flag = FALSE (default):
  All metrics → PullRequest.effective_is_ai_assisted (detection only)

Flag = TRUE:
  All metrics → PRSurvey.author_ai_assisted (surveys)
              → Fallback: effective_is_ai_assisted (when no survey)
```

---

## Code Patterns

### Helper Function Pattern

```python
# apps/metrics/services/ai_adoption_helpers.py (new file)

from waffle import flag_is_active

AI_ADOPTION_FLAG = "rely_on_surveys_for_ai_adoption"


def should_use_survey_data(request_or_team) -> bool:
    """Check if AI adoption should use survey data.

    Args:
        request_or_team: HttpRequest (with team attribute) or Team instance

    Returns:
        True if surveys should be primary source, False for detection-only
    """
    if hasattr(request_or_team, 'team'):
        # It's a request object
        return flag_is_active(AI_ADOPTION_FLAG, request_or_team)
    else:
        # It's a Team object - create mock request for flag check
        from django.test import RequestFactory
        from apps.users.models import CustomUser

        request = RequestFactory().get('/')
        request.team = request_or_team
        request.user = CustomUser.objects.filter(teams=request_or_team).first()
        return flag_is_active(AI_ADOPTION_FLAG, request)


def get_pr_ai_status(pr, use_surveys: bool) -> bool:
    """Get AI assisted status for a PR based on data source.

    Args:
        pr: PullRequest instance
        use_surveys: Whether to check survey data first

    Returns:
        True if PR is AI-assisted, False otherwise
    """
    if use_surveys:
        try:
            survey = pr.survey
            if survey.author_ai_assisted is not None:
                return survey.author_ai_assisted
        except pr.survey.RelatedObjectDoesNotExist:
            pass

    # Use detection (or fallback when survey unavailable)
    return pr.effective_is_ai_assisted
```

### Dashboard Function Update Pattern

```python
# Before
def get_key_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    # ... existing code ...
    surveys = PRSurvey.objects.filter(pull_request__in=prs)
    ai_assisted_pct = _calculate_ai_percentage(surveys)
    # ...

# After
def get_key_metrics(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,
    use_survey_data: bool | None = None,  # New parameter
) -> dict:
    # Determine data source (allow override for testing)
    if use_survey_data is None:
        use_survey_data = should_use_survey_data(team)

    # ... existing code ...

    if use_survey_data:
        surveys = PRSurvey.objects.filter(pull_request__in=prs)
        ai_assisted_pct = _calculate_ai_percentage(surveys)
    else:
        # Use detection-based calculation
        ai_count = sum(1 for pr in prs if pr.effective_is_ai_assisted)
        ai_assisted_pct = Decimal(str(round(ai_count * 100.0 / prs.count(), 2))) if prs.count() > 0 else Decimal("0.00")
    # ...
```

---

## Related Issues

| Issue | Status | Relationship |
|-------|--------|--------------|
| ISS-006 | Fixed | Changed sparkline to use surveys (will be affected by flag) |
| ISS-001/007 | Fixed | Low-data week handling (unrelated) |
| ISS-005 | Fixed | Team context (unrelated) |

---

## Testing Strategy

### Unit Tests

1. **Flag Helper Tests**
   - Test `should_use_survey_data` with flag active/inactive
   - Test `get_pr_ai_status` with both data sources

2. **Dashboard Function Tests**
   - Each function tested with flag=True and flag=False
   - Verify detection-only returns expected values
   - Verify survey+fallback returns expected values

3. **Edge Case Tests**
   - PR with no survey, flag=True (should use detection)
   - PR with survey=None, flag=True (should use detection)
   - PR with survey=True, flag=False (should use detection)

### Integration Tests

1. **E2E Dashboard Tests**
   - Toggle flag and verify dashboard updates
   - Verify insights match dashboard

---

## Migration Strategy

### Database Migration

```python
# apps/teams/migrations/XXXX_add_ai_adoption_flag.py

from django.db import migrations


def create_flag(apps, schema_editor):
    Flag = apps.get_model('teams', 'Flag')
    Flag.objects.get_or_create(
        name='rely_on_surveys_for_ai_adoption',
        defaults={
            'everyone': None,  # Not active for everyone
            'superusers': False,
            'staff': False,
            'authenticated': False,
            'note': 'When active, AI adoption metrics use survey data. Default: use LLM/pattern detection only.',
        }
    )


def delete_flag(apps, schema_editor):
    Flag = apps.get_model('teams', 'Flag')
    Flag.objects.filter(name='rely_on_surveys_for_ai_adoption').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('teams', 'XXXX_previous'),  # Replace with actual
    ]

    operations = [
        migrations.RunPython(create_flag, delete_flag),
    ]
```

---

## Constants Reference

```python
# apps/metrics/constants.py (or add to existing)

# Feature flag name for AI adoption data source
AI_ADOPTION_SURVEY_FLAG = "rely_on_surveys_for_ai_adoption"

# Minimum sample size for sparkline trends
MIN_SPARKLINE_SAMPLE_SIZE = 3  # Already exists in dashboard_service.py
```

---

## Admin Configuration

The flag will be accessible in Django admin at `/admin/teams/flag/`.

Fields to configure:
- **Name**: `rely_on_surveys_for_ai_adoption`
- **Note**: "When active for a team, AI adoption metrics prioritize survey responses. When inactive (default), only LLM and pattern detection are used."
- **Teams**: Select specific teams to enable
- **Everyone**: Leave as None (team-specific only)
