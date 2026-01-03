# Reviewer @Mention Links - Task Checklist

**Last Updated**: 2026-01-02
**Methodology**: Strict TDD (Red-Green-Refactor)

## Pre-Flight Check

- [ ] Run existing tests to ensure clean baseline: `make test`
- [ ] Verify dev server running: `curl -s http://localhost:8000/`

---

## Phase 1: Backend Filter (reviewer_name)

### 1.1 RED - Write Failing Tests

**File:** `apps/metrics/tests/test_pr_list_service.py`

- [ ] Write `test_filter_by_reviewer_name` - basic filtering with @ prefix
- [ ] Write `test_filter_by_reviewer_name_without_prefix` - filtering without @
- [ ] Write `test_filter_by_reviewer_name_case_insensitive` - case insensitivity
- [ ] Write `test_filter_by_reviewer_name_not_found_returns_empty` - no match handling
- [ ] Write `test_filter_by_reviewer_name_team_scoped` - security/isolation
- [ ] Run tests and verify they FAIL: `make test ARGS='-k reviewer_name'`

### 1.2 GREEN - Implement Filter

**File:** `apps/metrics/services/pr_list_service.py`

- [ ] Add `reviewer_name` filter after `github_name` filter (around line 155)
- [ ] Strip @ prefix if present
- [ ] Look up TeamMember by github_username (case-insensitive, team-scoped)
- [ ] Filter PRs via PRReview where reviewer matches
- [ ] Return empty queryset if member not found
- [ ] Run tests and verify they PASS: `make test ARGS='-k reviewer_name'`

**File:** `apps/metrics/views/pr_list_views.py`

- [ ] Add `"reviewer_name"` to filter_keys list (around line 47)

### 1.3 REFACTOR

- [ ] Review for code duplication between github_name and reviewer_name
- [ ] Consider extracting shared member lookup if beneficial
- [ ] Run all PR list tests: `make test ARGS='apps.metrics.tests.test_pr_list_service'`
- [ ] All tests still pass

---

## Phase 2: Template Filter (@@ Syntax)

### 2.1 RED - Write Failing Tests

**File:** `apps/metrics/tests/test_pr_list_tags.py`

- [ ] Write `test_converts_reviewer_mention_to_link` - `@@alice` → reviewer link
- [ ] Write `test_reviewer_mention_displays_single_at` - displays as `@alice`
- [ ] Write `test_reviewer_mention_uses_reviewer_name_param` - correct URL param
- [ ] Write `test_mixed_author_and_reviewer_mentions` - both types in same text
- [ ] Write `test_reviewer_mention_hyphenated_username` - `@@alice-dev` works
- [ ] Write `test_triple_at_treated_as_reviewer_plus_author` - `@@@alice` edge case
- [ ] Run tests and verify they FAIL: `make test ARGS='-k reviewer_mention'`

### 2.2 GREEN - Extend linkify_mentions

**File:** `apps/metrics/templatetags/pr_list_tags.py`

- [ ] Add `REVIEWER_MENTION_PATTERN` for `@@username`
- [ ] Update `linkify_mentions` to process `@@` first (before `@`)
- [ ] Generate `reviewer_name=@username` URL for `@@` matches
- [ ] Display as `@username` (single @) in link text
- [ ] Run tests and verify they PASS: `make test ARGS='-k reviewer_mention'`

### 2.3 REFACTOR

- [ ] Verify single-pass processing if possible
- [ ] Check regex efficiency (no catastrophic backtracking)
- [ ] Run all template tag tests: `make test ARGS='apps.metrics.tests.test_pr_list_tags'`
- [ ] All tests still pass

---

## Phase 3: Prompt Updates

### 3.1 Update User Prompt Template

**File:** `apps/metrics/prompts/templates/insight/user.jinja2`

- [ ] Change bottleneck line (around line 40) from:
  ```
  - ⚠️ BOTTLENECK: @{{ team_health.bottleneck.github_username }}
  ```
  To:
  ```
  - ⚠️ BOTTLENECK: @@{{ team_health.bottleneck.github_username }}
  ```
- [ ] Add comment explaining `@@` = reviewer context

### 3.2 Update System Prompt

**File:** `apps/metrics/services/insight_llm.py`

- [ ] Add `@@username` format documentation in "## @Username Format" section
- [ ] Update examples to show `@@` for bottleneck/reviewer mentions
- [ ] Clarify: `@username` = author, `@@username` = reviewer

---

## Phase 4: Integration Testing

### 4.1 Regenerate Insights

- [ ] Run: `GROQ_API_KEY=xxx .venv/bin/python gen_insights.py`
- [ ] Verify insights regenerate without errors

### 4.2 Verify Database

- [ ] Query insights: Check for `@@` in bottleneck-related text
  ```sql
  SELECT title, description FROM metrics_dailyinsight
  WHERE category = 'llm_insight' AND description LIKE '%@@%';
  ```

### 4.3 End-to-End Browser Test

- [ ] View dashboard with engineering insights
- [ ] Click an author `@mention` → verify shows authored PRs
- [ ] Click a reviewer `@@mention` → verify shows PRs to review
- [ ] Both display as `@username` (single @) in UI

---

## Final Checklist

- [ ] All tests pass: `make test`
- [ ] No linting errors: `make ruff`
- [ ] Commit changes with descriptive message
- [ ] Push to remote

---

## Commands Quick Reference

```bash
# Phase 1 Tests
make test ARGS='-k reviewer_name -v'

# Phase 2 Tests
make test ARGS='-k reviewer_mention -v'

# All related tests
make test ARGS='apps.metrics.tests.test_pr_list_service apps.metrics.tests.test_pr_list_tags -v'

# Regenerate insights
GROQ_API_KEY=xxx .venv/bin/python gen_insights.py

# Check for @@ in database
psql -d tformance -c "SELECT title, substring(description, 1, 100) FROM metrics_dailyinsight WHERE description LIKE '%@@%';"
```
