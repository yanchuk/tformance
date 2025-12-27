# AI Tool Categories - Task Checklist

**Last Updated:** 2025-12-27 (Session 3)
**Status:** ALL PHASES COMPLETE

## Overview

Implement AI tool categorization to distinguish Code AI vs Review AI tools.

**Dependencies:** None (builds on existing infrastructure)

---

## Phase 1: Core Category Service ✅ COMPLETE

**Goal:** Create the mapping service with all tool classifications

### Tasks

- [x] **1.1** Create `apps/metrics/services/ai_categories.py`
  - Define CODE_TOOLS set (30+ tools)
  - Define REVIEW_TOOLS set (10+ tools)
  - Define MIXED_TOOLS set (5 tools) → treated as code
  - Define EXCLUDED_TOOLS set (6 tools)

- [x] **1.2** Implement `get_tool_category(tool_name: str) -> str | None`

- [x] **1.3** Implement `categorize_tools(tools: list) -> dict`

- [x] **1.4** Implement `get_ai_category(tools: list) -> str | None`

- [x] **1.5** Add display name constants

- [x] **1.6** Write unit tests for category service (38 tests pass)

---

## Phase 2: Model Integration ✅ COMPLETE

**Goal:** Add computed properties to PullRequest model

### Tasks

- [x] **2.1** Add `ai_code_tools` property to PullRequest
- [x] **2.2** Add `ai_review_tools` property to PullRequest
- [x] **2.3** Add `ai_category` property to PullRequest
- [x] **2.4** Write model tests (11 tests pass)

---

## Phase 3: PR List Filter ✅ COMPLETE

**Goal:** Enable filtering PRs by AI category

### Tasks

- [x] **3.1** Update `get_filter_options()` in `pr_list_service.py`
  - Added `ai_categories` to returned options

- [x] **3.2** Implement category filter logic in `get_prs_queryset()`
  - Created `_apply_ai_category_filter()` helper function

- [x] **3.3** Add category dropdown to PR list template
  - Updated `templates/metrics/analytics/pull_requests.html`

- [x] **3.4** Update PR list stats to show category breakdown
  - Added `code_ai_count`, `review_ai_count`, `both_ai_count` to stats

- [x] **3.5** Update view to accept `ai_category` filter
  - Added to `filter_keys` in `pr_list_views.py`

- [x] **3.6** Write filter tests (14 tests pass)

---

## Phase 4: Dashboard Charts ✅ COMPLETE

**Goal:** Show category breakdown in dashboard visualizations

### Tasks

- [x] **4.1** Update `get_ai_tool_breakdown()` in dashboard_service.py
  - Returns `category` field for each tool
  - Excludes excluded tools
  - Sorts by category then count

- [x] **4.2** Update AI tool breakdown chart template
  - Uses `{% regroup %}` to group by category
  - Shows "Code AI" and "Review AI" badges
  - Color-coded progress bars

- [x] **4.3** Create `get_ai_category_breakdown()` function
  - Returns total_ai_prs, code_ai_count, review_ai_count, both_ai_count
  - Calculates percentages

- [x] **4.4** Write dashboard service tests (12 tests)

- [x] **4.5** Wire up `get_ai_category_breakdown()` to a view/card (OPTIONAL)
  - Skipped - data available via PR list stats badges

---

## Phase 5: PR Row Display ✅ COMPLETE

**Goal:** Show category indicator in PR list rows

### Tasks

- [x] **5.1** Add category template filters to `pr_list_tags.py`
  - `ai_category_display` - Returns "Code", "Review", "Both"
  - `ai_category_badge_class` - Returns badge-primary/secondary/accent

- [x] **5.2** Update PR table AI column
  - Replaced confidence level with category badge
  - Shows tool names in tooltip

- [x] **5.3** Update expanded row with category
  - Added "Category:" row in AI Details section
  - Shows "Code AI" / "Review AI" / "Both AI"

- [x] **5.4** Write template tag tests (12 tests)

---

## Final Checklist

- [x] Phases 1-3 complete
- [x] Phase 4 complete
- [x] Phase 5 complete
- [x] All tests passing (`make test`) - 102 category-specific tests pass
- [x] Code formatted (`make ruff`)
- [ ] Manual QA in browser:
  - [ ] PR list filter works
  - [ ] Dashboard charts show categories
  - [ ] PR rows display category
- [x] Documentation updated

---

## Notes

- **No migrations required** - all computed properties
- **No reprocessing of existing PRs** - uses existing tool data
- **Mixed tools default to "code" category** - user decision
- **Excluded tools (snyk, mintlify) don't appear in AI metrics**

---

## Commands to Run

```bash
# Run all category tests
.venv/bin/pytest apps/metrics/tests/test_ai_categories.py apps/metrics/tests/test_ai_model_fields.py apps/metrics/tests/test_pr_list_service.py::TestAICategoryFilter apps/metrics/tests/test_pr_list_service.py::TestAICategoryFilterOptions apps/metrics/tests/test_pr_list_service.py::TestAICategoryStats apps/metrics/tests/dashboard/test_ai_metrics.py::TestGetAIToolBreakdown apps/metrics/tests/dashboard/test_ai_metrics.py::TestGetAICategoryBreakdown -v

# Format code
make ruff

# Check for migrations (should be none)
make migrations
```
