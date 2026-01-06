# CI/CD Feature Flag - Tasks

**Last Updated: 2026-01-06**
**Status: COMPLETED**

## Phase 1: TDD RED - Write Failing Tests

- [x] **1.1** Add test class `TestCicdFeatureFlag` to `test_integration_flags.py`
- [x] **1.2** Write `test_is_cicd_enabled_returns_false_by_default`
- [x] **1.3** Write `test_is_cicd_enabled_returns_true_when_flag_active`
- [x] **1.4** Run tests - verify they FAIL (function doesn't exist yet)

## Phase 2: TDD GREEN - Implement Helper

- [x] **2.1** Add `FLAG_CICD = "cicd_enabled"` constant to `integration_flags.py`
- [x] **2.2** Implement `is_cicd_enabled(request)` function
- [x] **2.3** Run tests - verify they PASS

## Phase 3: Update Views

- [x] **3.1** Import `is_cicd_enabled` in `dashboard_views.py`
- [x] **3.2** Add `context["cicd_enabled"]` in `cto_overview()` view
- [x] **3.3** Import `is_cicd_enabled` in `analytics_views.py`
- [x] **3.4** Add `context["cicd_enabled"]` in `_get_analytics_context()` helper

## Phase 4: Update Templates

- [x] **4.1** Wrap CI/CD row in `cto_overview.html` with `{% if cicd_enabled %}`
- [x] **4.2** Wrap CI/CD card in `analytics/quality.html` with `{% if cicd_enabled %}`
- [x] **4.3** Wrap deployment card in `analytics/delivery.html` with `{% if cicd_enabled %}`

## Phase 5: Verification

- [x] **5.1** Run full test suite: 437 dashboard tests passed
- [x] **5.2** Code formatted with ruff
- [x] **5.3** All 14 integration flag tests passed

## Completion Checklist

- [x] All tests pass (14 integration flag tests + 437 dashboard tests)
- [x] Code formatted with ruff
- [x] CI/CD hidden by default (flag not created)
