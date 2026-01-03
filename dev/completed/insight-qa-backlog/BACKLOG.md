# Insight QA Backlog

Issues discovered during LLM insight QA session (January 2026).

---

## OPEN ISSUES

*All issues have been resolved. See RESOLVED ISSUES section below.*

---

## RESOLVED ISSUES

### ISS-005: Onboarding sync page shows wrong team (FIXED)

**Status:** Resolved
**Fixed In:** TDD session (January 2026)
**Component:** Onboarding / Team Context

#### Problem
`sync_progress` view used `request.user.teams.first()` instead of respecting session team context.

#### Resolution
Updated `sync_progress` and `start_sync` views to use `request.default_team` which respects:
1. Session team (if user navigated from a specific team's dashboard)
2. User's first team (fallback)

#### Files Changed
- `apps/onboarding/views.py` - Use `request.default_team` instead of `request.user.teams.first()`
- `apps/onboarding/tests/test_team_context.py` - New test file with 5 tests

---

### ISS-006: AI Adoption sparkline uses different data source than card (FIXED)

**Status:** Resolved
**Fixed In:** TDD session (January 2026)
**Component:** Dashboard Sparklines / AI Adoption

#### Problem
AI Adoption card used survey data (`PRSurvey.author_ai_assisted`) but sparkline used pattern detection (`PullRequest.is_ai_assisted`), causing inconsistent metrics.

#### Resolution
Updated `get_sparkline_data()` to use survey data for AI adoption, matching the card calculation.

#### Files Changed
- `apps/metrics/services/dashboard_service.py` - AI adoption sparkline query now uses survey data
- `apps/metrics/tests/dashboard/test_sparkline_data.py` - Added `TestAIAdoptionSparklineDataSource` with 4 tests

---

### ISS-007: Review Time sparkline shows extreme percentages with low-data weeks (FIXED)

**Status:** Resolved
**Fixed In:** TDD session (January 2026)
**Component:** Dashboard Sparklines
**Related To:** ISS-001

#### Problem
Review Time showed +44321% trend because first week had only 1 PR, creating unrealistic baseline.

#### Resolution
Same fix as ISS-001 - added minimum sample size requirement (3 PRs per week) for trend calculation.

#### Files Changed
- Same as ISS-001

---

### ISS-001: Sparkline trend misleading during low-data periods (FIXED)

**Status:** Resolved
**Fixed In:** TDD session (January 2026)
**Component:** Dashboard Sparklines

#### Problem
Sparkline trends showed extreme percentages (-98%, +44321%) when comparing weeks with very low PR counts (e.g., holiday weeks with 1-2 PRs).

#### Resolution
Added `MIN_SPARKLINE_SAMPLE_SIZE = 3` constant. The `_calculate_change_and_trend()` function now:
1. Accepts optional `sample_sizes` list alongside values
2. Finds first valid week (with >= 3 PRs) for baseline
3. Finds last valid week (with >= 3 PRs) for comparison
4. Returns `(0, "flat")` if no valid weeks exist

#### Files Changed
- `apps/metrics/services/dashboard_service.py`:
  - Added `MIN_SPARKLINE_SAMPLE_SIZE = 3` constant
  - Updated `_calculate_change_and_trend()` to accept sample_sizes parameter
  - Updated `get_sparkline_data()` to pass sample sizes
- `apps/metrics/tests/dashboard/test_sparkline_data.py` - Added `TestSparklineLowDataHandling` with 4 tests

---

### ISS-002: Reviewer mention URL included @ symbol (FIXED)

**Status:** Resolved
**Fixed In:** This session
**Component:** Template Tags

#### Problem
Clicking `@@DanRibbens` in insight generated URL with `reviewer_name=@DanRibbens` instead of `reviewer_name=DanRibbens`.

#### Resolution
Updated `linkify_mentions` template tag to strip `@` from URL parameter.

#### Files Changed
- `apps/metrics/templatetags/pr_list_tags.py`

---

### ISS-003: Default date filter hiding reviewer PRs (FIXED)

**Status:** Resolved
**Fixed In:** This session
**Component:** PR List Filtering

#### Problem
Reviewer bottleneck links showed only 3 PRs due to default 30-day date filter, when bottleneck detection counted 13 PRs across all time.

#### Resolution
Added `no_date_filter=1` parameter to reviewer links to disable default date range.

#### Files Changed
- `apps/metrics/templatetags/pr_list_tags.py`
- `apps/metrics/views/pr_list_views.py`

---

### ISS-004: "Pending reviews" semantic mismatch (FIXED)

**Status:** Resolved
**Fixed In:** This session
**Component:** PR List Service

#### Problem
"Pending reviews" was interpreted two ways:
- Bottleneck detection: PRs reviewer HAS reviewed but NOT approved (13 PRs)
- Filter: PRs reviewer has NOT reviewed at all (274 PRs)

User clicked link expecting 13 PRs, saw 274.

#### Resolution
1. Aligned `reviewer_name` filter with bottleneck detection logic
2. Updated prompt wording from "pending reviews" to "PRs awaiting approval"
3. Updated docstrings to clarify semantics

#### Files Changed
- `apps/metrics/services/pr_list_service.py` - Filter logic
- `apps/metrics/services/insight_llm.py` - Prompt wording
- `apps/metrics/services/dashboard_service.py` - Docstrings

---

## QA Progress

| Team | Status | Issues Found |
|------|--------|--------------|
| Netdata | Reviewed earlier | Bot contributors, redundant bullets |
| Novu | Reviewed earlier | Backwards AI logic |
| Payload CMS | Reviewed | ISS-002, ISS-003, ISS-004 |
| Budibase | Reviewed | ISS-001, ISS-005 |
| Plausible | Reviewed | ISS-006, ISS-007 |

---

## Notes

### Prompt Improvements Made (Earlier Session)
1. Added `BOT_USERNAME_PATTERNS` to filter bot contributors
2. Added "Contributor Analysis Rules" to not flag healthy lead contributor patterns
3. Added anti-redundancy rules to prevent restating same fact
4. Added rule against backwards AI logic ("few PRs not using AI = need more adoption")
5. Updated mention syntax documentation for `@` vs `@@`
