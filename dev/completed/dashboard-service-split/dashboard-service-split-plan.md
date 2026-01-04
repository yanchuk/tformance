# Dashboard Service Split - Implementation Plan

**Last Updated:** 2026-01-04

## Executive Summary

Split the monolithic `apps/metrics/services/dashboard_service.py` (3,712 lines, 69 functions) into domain-focused modules following the same successful pattern used for `integrations/tasks.py`. This refactoring improves maintainability, reduces cognitive load, and makes the codebase easier to navigate.

**Approach:** TDD-driven incremental extraction using `_service_modules/` directory during migration, with re-exports in `__init__.py` for backward compatibility.

## Current State Analysis

| Metric | Value |
|--------|-------|
| File size | 3,712 lines |
| Total functions | 69 |
| Private helpers | 15 |
| Public functions | 54 |
| Existing tests | 25+ test files in `tests/dashboard/` |

### Function Categories (by domain)

| Domain | Functions | Est. Lines |
|--------|-----------|------------|
| Helpers (private) | 15 | ~400 |
| Key Metrics | 1 | ~75 |
| AI Metrics | 9 | ~600 |
| Team Metrics | 3 | ~250 |
| Review Metrics | 5 | ~400 |
| PR Metrics | 10 | ~500 |
| Copilot Metrics | 2 | ~150 |
| CI/CD & Deploy | 2 | ~200 |
| Tech Categories | 4 | ~300 |
| Survey/Response | 2 | ~250 |
| Trends | 7 | ~400 |

## Proposed Future State

```
apps/metrics/services/dashboard/
├── __init__.py           # Re-exports all 54 public functions
├── _helpers.py           # 15 private helper functions (~400 lines)
├── key_metrics.py        # get_key_metrics (~75 lines)
├── ai_metrics.py         # 9 AI-related functions (~600 lines)
├── team_metrics.py       # 3 team breakdown functions (~250 lines)
├── review_metrics.py     # 5 review functions (~400 lines)
├── pr_metrics.py         # 10 PR-related functions (~500 lines)
├── copilot_metrics.py    # 2 Copilot functions (~150 lines)
├── cicd_metrics.py       # 2 CI/CD & deployment functions (~200 lines)
├── tech_metrics.py       # 4 tech category functions (~300 lines)
├── survey_metrics.py     # 2 survey/response functions (~250 lines)
└── trend_metrics.py      # 7 trend functions (~400 lines)
```

**Result:** `dashboard_service.py` becomes ~100 lines (re-exports only)

## Implementation Phases

### Phase 1: Setup & Helpers (TDD)
- Create directory structure
- Extract 15 private helpers to `_helpers.py`
- Verify all tests pass

### Phase 2: Core Metrics (TDD)
- Extract `key_metrics.py`
- Extract `ai_metrics.py`
- Extract `team_metrics.py`

### Phase 3: Review & PR Metrics (TDD)
- Extract `review_metrics.py`
- Extract `pr_metrics.py`

### Phase 4: Specialized Metrics (TDD)
- Extract `copilot_metrics.py`
- Extract `cicd_metrics.py`
- Extract `tech_metrics.py`
- Extract `survey_metrics.py`
- Extract `trend_metrics.py`

### Phase 5: Finalization
- Convert `dashboard_service.py` to re-exports only
- Update any test patches
- Verify backward compatibility
- Update documentation

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Test patch breaks | Medium | Medium | Use `_service_modules/` prefix, update patches systematically |
| Circular imports | Low | High | Keep helpers separate, import carefully |
| Missing re-export | Low | Medium | Comprehensive `__all__` list, test imports |
| Performance regression | Very Low | Low | No logic changes, only reorganization |

## Success Metrics

| Metric | Target |
|--------|--------|
| `dashboard_service.py` lines | <150 (re-exports) |
| Largest module | <600 lines |
| All tests pass | 100% |
| Backward compatibility | 100% |
| No circular imports | ✓ |

## Dependencies

- No database migrations
- No API changes
- No functional changes
- Tests already organized by domain in `tests/dashboard/`

## Effort Estimate

| Phase | Effort | Time |
|-------|--------|------|
| Phase 1 | Medium | 1 hour |
| Phase 2 | Large | 2 hours |
| Phase 3 | Large | 2 hours |
| Phase 4 | Large | 2 hours |
| Phase 5 | Small | 30 min |
| **Total** | **XL** | **~8 hours** |

## Testing Strategy

1. Run existing tests after each extraction: `make test ARGS='apps.metrics.tests.dashboard'`
2. Verify imports work: `python -c "from apps.metrics.services.dashboard import get_key_metrics"`
3. Check for circular imports during each phase
4. Full test suite before final commit
