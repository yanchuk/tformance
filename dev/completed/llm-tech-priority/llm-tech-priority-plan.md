# LLM Tech Priority Feature - Plan

**Created:** 2025-12-25
**Status:** Planning

---

## Overview

Implement a feature to **always prioritize LLM-detected technology categories** over pattern-based detection (from `PRFile.file_category`). When a PR has `llm_summary.tech.categories` populated, use that instead of the file pattern-derived categories.

---

## Current State

### Pattern-Based Detection (Current)

**Source:** `PRFile.categorize_file()` → `PRFile.file_category`

**How it works:**
1. Each PR has related `PRFile` records (one per changed file)
2. `PRFile.file_category` is set based on file path/extension patterns
3. `pr_list_service.py:94` aggregates these via `ArrayAgg("files__file_category")`

**Categories from patterns:**
- `frontend`, `backend`, `javascript`, `test`, `docs`, `config`, `other`

**Issues:**
- "javascript" is ambiguous (can be frontend or backend)
- Pattern-based detection has only 55.5% accuracy vs LLM (from recent experiment)
- No context awareness (file `api/handler.ts` could be FE or BE)

### LLM-Based Detection (Better)

**Source:** `PullRequest.llm_summary.tech.categories`

**How it works:**
1. LLM (Groq/Llama 3.3 70B) analyzes full PR context
2. Returns structured `tech` object with `categories`, `languages`, `frameworks`
3. Stored in `llm_summary` JSONField

**Categories from LLM:**
- `backend`, `frontend`, `devops`, `mobile`, `data`

**Advantages:**
- Context-aware (understands what the PR actually does)
- Consistent taxonomy (no ambiguous "javascript" category)
- Higher accuracy (treats as ground truth)

---

## Technical Analysis

### DB Changes: NOT REQUIRED

**Reasoning:**
1. `llm_summary` already stores `tech.categories` as JSONField
2. GIN indexes already exist (migration 0020):
   - `pr_llm_tech_categories_gin_idx` on `llm_summary->'tech'->'categories'`
   - `pr_llm_tech_languages_gin_idx` on `llm_summary->'tech'->'languages'`
3. All data is already present - just need to use it

### Query Changes Required

**Current annotation in `pr_list_service.py:93-100`:**
```python
qs = qs.annotate(
    tech_categories=ArrayAgg(
        "files__file_category",
        distinct=True,
        filter=~Q(files__file_category="") & Q(files__file_category__isnull=False),
        default=Value([]),
    )
)
```

**New approach - Priority Logic:**
```python
# Option A: Use Coalesce with JSONField extraction
from django.db.models.functions import Coalesce
from django.contrib.postgres.fields.jsonb import KeyTextTransform

qs = qs.annotate(
    # Extract LLM categories (returns array or None)
    llm_tech_categories=JSONBArrayElements("llm_summary__tech__categories"),
    # Fallback to pattern categories
    pattern_tech_categories=ArrayAgg(...),
    # Use LLM if available, else pattern
    tech_categories=Coalesce("llm_tech_categories", "pattern_tech_categories"),
)
```

**Option B: Simpler - Select in Python (Recommended for Phase 1)**
```python
# Annotate both, let template/view decide
qs = qs.annotate(
    pattern_tech_categories=ArrayAgg(...),  # Existing
)
# No change to annotation - handle in template:
# {% if pr.llm_summary.tech.categories %}
#   {{ pr.llm_summary.tech.categories }}
# {% else %}
#   {{ pr.tech_categories }}
# {% endif %}
```

### Category Mapping

LLM and pattern categories don't 1:1 map. Need translation:

| Pattern Category | Maps to LLM Category |
|------------------|---------------------|
| `frontend` | `frontend` |
| `backend` | `backend` |
| `javascript` | `frontend` or `backend` (ambiguous) |
| `test` | N/A (LLM doesn't have test category) |
| `docs` | N/A |
| `config` | `devops` |
| `other` | N/A |

**LLM categories not in patterns:**
- `devops` - CI/CD, infrastructure
- `mobile` - iOS/Android
- `data` - ML, analytics, databases

**Decision:** Use LLM categories as-is. Update template filters to handle both vocabularies.

---

## Implementation Plan

### Phase 1: PR List Service Update [S]

**Goal:** Prioritize LLM tech categories in `get_prs_queryset()`

**Tasks:**
1. Modify annotation to extract `llm_summary->'tech'->'categories'` as `llm_tech_categories`
2. Keep existing `tech_categories` as `pattern_tech_categories` (for fallback)
3. Create combined `display_tech_categories` that prefers LLM

### Phase 2: Template Filter Updates [S]

**Goal:** Handle LLM category vocabulary in display

**Tasks:**
1. Update `tech_abbrev` filter to handle LLM categories:
   - `backend` → `BE`
   - `frontend` → `FE`
   - `devops` → `DO`
   - `mobile` → `MB`
   - `data` → `DA`
2. Update `tech_badge_class` for new categories
3. Update `tech_display_name` for new categories

### Phase 3: Filter Dropdown Update [S]

**Goal:** Update tech filter options to use LLM vocabulary

**Tasks:**
1. Change `get_filter_options()` tech_categories to LLM vocabulary
2. Update filter logic to query `llm_summary->'tech'->'categories'` when LLM exists
3. Fallback to pattern filter for PRs without LLM analysis

### Phase 4: Dashboard Integration [M]

**Goal:** Use LLM tech categories in analytics dashboards

**Reference:** Check `dev/active/trends-benchmarks-dashboard/` for relevant pages

**Tasks:**
1. Update AI Adoption page tech breakdown to use LLM categories
2. Update any chart/table showing technology distribution
3. Ensure consistency across all views

### Phase 5: Testing & Verification [S]

**Tasks:**
1. Unit tests for priority logic
2. Verify UI displays correctly
3. Check performance (GIN indexes should help)
4. Manual E2E verification

---

## Decision: Simple Template-Level Priority (Recommended)

After analysis, the simplest approach is:

1. **Keep existing `tech_categories` annotation** - no service changes needed
2. **Modify template to prefer LLM** - check `pr.llm_summary.tech.categories` first
3. **Update filters to handle both** - expand vocabulary support

This minimizes code changes while achieving the goal.

---

## Out of Scope

- Re-running LLM analysis on PRs without `llm_summary` (separate task)
- Backfilling pattern categories to LLM format (not needed)
- Changing LLM prompt or schema (already correct)

---

## Files to Modify

| File | Change |
|------|--------|
| `templates/metrics/pull_requests/partials/table.html` | Priority display logic |
| `apps/metrics/templatetags/pr_list_tags.py` | Add LLM category filters |
| `apps/metrics/services/pr_list_service.py` | Optional: annotate `llm_tech_categories` |
| `apps/metrics/tests/test_pr_list_tags.py` | Tests for new filters |
| `templates/metrics/analytics/pull_requests.html` | Filter dropdown update |
