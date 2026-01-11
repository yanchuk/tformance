# AI Adoption Dashboard Improvements

**Last Updated:** 2026-01-11

## Executive Summary

Fix broken UI elements and improve UX of the AI Adoption dashboard to better serve CTOs who need actionable insights about Copilot ROI.

**Scope:** P0 (broken) + P1 (confusing) issues only. P2 items deferred.

**Estimated Effort:** ~9 hours total

---

## Current State Analysis

### Issues Identified

| Priority | Issue | Impact | Status |
|----------|-------|--------|--------|
| **P0** | Layout overflow (large numbers) | Broken UX | Numbers like "1816130" overflow cards |
| **P0** | Language/Editor cards empty | Missing feature | Mock data not saved to DB |
| **P1** | Champions card confusing | Poor UX | Metrics need explanation |
| **P1** | AI Quality metric misleading | Wrong data source | Uses survey instead of LLM detection |

### Root Causes

1. **Layout overflow:** Missing `format_compact` filter and `tabular-nums` CSS class
2. **Empty cards:** Two issues:
   - Mock generator missing `total_lines_suggested`, `total_lines_accepted` fields
   - Seed command doesn't call `sync_copilot_language_data()` / `sync_copilot_editor_data()`
3. **Champions UX:** Tooltip-only labels, no color coding, no scoring explanation
4. **AI Quality:** Uses `survey.author_ai_assisted` instead of `effective_is_ai_assisted`

---

## Proposed Future State

### After Implementation

1. **Large numbers display as:** 1.8M, 906.7K (compact format)
2. **Language/Editor cards show:** Python 45%, TypeScript 30%, etc.
3. **Champions card shows:**
   - Visible metric labels (not just tooltips)
   - Color-coded cycle time (green <24h, yellow 24-72h, red >72h)
   - Info tooltip explaining scoring methodology
4. **AI Quality shows:**
   - Objective metrics (cycle time, revert rate comparison)
   - Uses LLM-detected `effective_is_ai_assisted`

---

## Implementation Phases

### Phase 1: P0 - Fix Broken UI (TDD)

**Goal:** Fix layout overflow and populate empty cards

#### 1.1 Layout Overflow Fix
- Add `{% load number_filters %}` to templates
- Replace `floatformat:0` with `format_compact`
- Add `tabular-nums font-mono` classes for consistent width

#### 1.2 Language/Editor Data Pipeline
- Update mock generator to include `total_lines_suggested`, `total_lines_accepted`
- Update seed command to call sync functions
- Verify data appears in dashboard

### Phase 2: P1 - Improve UX (TDD)

**Goal:** Make metrics understandable and use accurate data sources

#### 2.1 Champions Card UX
- Add visible labels instead of tooltip-only
- Add color-coded cycle time indicators
- Add info tooltip with scoring explanation
- Update subtitle to explain metrics

#### 2.2 AI Quality Metric Rethink
- Reuse existing `get_ai_impact_stats()` function
- Add revert rate comparison
- Replace survey-based chart with objective metrics table
- Use `effective_is_ai_assisted` (LLM detection)

---

## TDD Workflow for Each Task

```
1. RED: Write failing test describing expected behavior
2. GREEN: Write minimum code to pass test
3. REFACTOR: Clean up while keeping tests green
```

**Test Files:**
- `apps/metrics/tests/test_copilot_mock_data.py` - Mock generator tests
- `apps/integrations/tests/test_copilot_language_editor_sync.py` - Sync tests
- `apps/metrics/tests/dashboard/test_ai_metrics.py` - Quality comparison tests

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Schema mismatch breaks existing sync | Medium | High | Test both mock and real API paths |
| Large number format breaks internationalization | Low | Medium | Use existing `format_compact` filter |
| Champions color thresholds don't fit all teams | Medium | Low | Consider team-relative percentiles later |

---

## Success Metrics

1. **Layout:** No horizontal overflow on any card with large numbers
2. **Language/Editor:** Cards show data after `seed_copilot_demo --clear-existing`
3. **Champions:** All labels visible without hover, cycle time color-coded
4. **AI Quality:** Shows cycle time and revert rate, not survey ratings

---

## Dependencies

- Existing `format_compact` filter in `apps/web/templatetags/number_filters.py`
- Existing `sync_copilot_language_data()` and `sync_copilot_editor_data()` functions
- Existing `get_ai_impact_stats()` function in `ai_metrics.py`
