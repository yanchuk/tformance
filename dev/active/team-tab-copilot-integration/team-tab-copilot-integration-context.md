# Team Tab Copilot Integration - Context

**Last Updated:** 2026-01-11 (Session Start)
**Status:** STARTING - Plan approved, TDD tests not yet written

---

## Overview

Integrate Copilot metrics into the Team Performance tab to show per-member Copilot effectiveness alongside existing PR metrics.

### Two Features (Issues 7 & 8)

| Issue | Feature | Description |
|-------|---------|-------------|
| 7 | Copilot Acceptance Column | New "Copilot %" column showing suggestion acceptance rate |
| 8 | Champion Badges | 🏆 badge next to Copilot Champions |

---

## Current State

### NOT YET STARTED
- No code written yet
- Plan approved by user
- Plan reviewed by plan-reviewer agent with recommendations incorporated

### Prerequisites Complete
- AI Adoption Dashboard P0/P1 tasks committed (includes Champions logic)
- `AIUsageDaily` model has per-member Copilot data
- `get_copilot_champions()` function exists and works

---

## Key Technical Context

### Data Sources

**For Copilot % Column:**
```python
# AIUsageDaily model (apps/metrics/models/aggregations.py:12)
class AIUsageDaily(BaseTeamModel):
    member = models.ForeignKey(TeamMember, ...)  # Per-member!
    source = ["copilot", "cursor"]
    acceptance_rate = models.DecimalField(...)  # This is what we need
```

**For Champion Badges:**
```python
# apps/metrics/services/dashboard/ai_metrics.py
def get_copilot_champions(team, start_date, end_date) -> list[dict]:
    # Returns list with member_id, acceptance_rate, cycle_time, score
```

### Existing Team Breakdown

**View:** `apps/metrics/views/chart_views.py` - `table_breakdown()`
**Service:** `apps/metrics/services/dashboard/team_metrics.py` - `get_team_breakdown()`
**Template:** `templates/metrics/partials/team_breakdown_table.html`

Current columns: Member, PRs, Cycle, PR Size, Reviews, Response, AI%

---

## Plan Reviewer Recommendations (MUST FOLLOW)

1. **Column Clarity:** Add tooltips distinguishing:
   - "AI %" = % of PRs using AI tools (LLM detection)
   - "Copilot %" = Copilot suggestion acceptance rate (GitHub API)

2. **Edge Cases:** Handle members without Copilot data:
   - Show "-" with tooltip "No Copilot usage data"
   - 0% acceptance should show "0%" not "-"

3. **Sorting Support:** Add `copilot_pct` to `SORT_FIELDS` in team_metrics.py

4. **Performance:** Use set for O(1) champion lookup:
   ```python
   champion_ids = {c["member_id"] for c in champions}
   ```

5. **Date Range Consistency:** Ensure `get_copilot_champions()` uses same dates as `get_team_breakdown()`

---

## Files to Modify

| File | Changes |
|------|---------|
| `apps/metrics/services/dashboard/team_metrics.py` | Add Copilot aggregation + SORT_FIELDS |
| `apps/metrics/views/chart_views.py` | Add champion_ids to `table_breakdown` context |
| `templates/metrics/partials/team_breakdown_table.html` | Add column + 🏆 badge |

### Test Files to Create/Modify

| File | Purpose |
|------|---------|
| `apps/metrics/tests/test_chart_views.py` | Test `table_breakdown` with copilot_pct and champion_ids |
| `apps/metrics/tests/dashboard/test_team_metrics.py` | Test `get_team_breakdown()` with Copilot data |

---

## TDD Workflow (Next Steps)

### Issue 7: Copilot Acceptance Column

1. **RED:** Write test in `test_team_metrics.py`:
   ```python
   def test_get_team_breakdown_includes_copilot_acceptance(self):
       # Create TeamMember with AIUsageDaily records
       # Call get_team_breakdown()
       # Assert 'copilot_pct' in result rows
   ```

2. **GREEN:** Modify `get_team_breakdown()` to aggregate AIUsageDaily

3. **REFACTOR:** Add sorting support

### Issue 8: Champion Badges

1. **RED:** Write test in `test_chart_views.py`:
   ```python
   def test_table_breakdown_includes_champion_ids(self):
       # Assert 'champion_ids' in response.context
   ```

2. **GREEN:** Import and call `get_copilot_champions()` in view

3. **REFACTOR:** Optimize with set lookup

---

## No Migrations Needed

All changes are in Python services, views, and templates. No model changes.

---

## Commands Reference

```bash
# Run tests for team breakdown
.venv/bin/pytest apps/metrics/tests/test_chart_views.py -k table_breakdown -v
.venv/bin/pytest apps/metrics/tests/dashboard/test_team_metrics.py -v

# Visual verification
make dev
# Navigate to http://localhost:8000/a/{team}/metrics/analytics/team/
```

---

## Related Documentation

- Plan file: `/Users/yanchuk/.claude/plans/snappy-floating-eich.md`
- Parent task: `dev/active/ai-adoption-dashboard-improvements/`
