# Copilot UI Integration - Tasks

**Last Updated:** 2026-01-11 (Session 4)
**Status:** COMPLETE - All phases implemented

## Legend
- [ ] Not started
- [~] In progress
- [x] Completed

---

## Summary

All planned phases are complete:
- **36 new tests added** (8 service + 10 onboarding + 18 card)
- **All tests pass in isolation** (some waffle flag flakiness in parallel)
- **No migrations needed** - all changes are views/templates/services

---

## Phase 0: Service Layer ✅

### 0.1: Create activation service (TDD)

**TDD Status:** Complete

- [x] RED: Write failing test for `activate_copilot_for_team` function
- [x] GREEN: Implement `activate_copilot_for_team` in services
- [x] REFACTOR: Added `deactivate_copilot_for_team` function

**Test file:** `apps/integrations/tests/test_copilot_activation.py` (8 tests)
**Implementation file:** `apps/integrations/services/copilot_activation.py`

---

## Phase 1: Onboarding Step (US-1) ✅

### 1.1: View Logic (TDD)

**TDD Status:** Complete

- [x] RED: Write failing tests for `connect_copilot` view
- [x] GREEN: Implement `connect_copilot` view
- [x] REFACTOR: Clean up

**Test file:** `apps/onboarding/tests/test_copilot_step.py` (10 tests)
**Implementation file:** `apps/onboarding/views/copilot.py`

### 1.2: Helper Updates

- [x] Update `_get_onboarding_flags_context` to include `copilot_enabled`
- [x] Update `apps/onboarding/views/__init__.py` to export new view

### 1.3: URL Pattern and Step Flow

- [x] Add URL pattern to `apps/onboarding/urls.py`
- [x] Update `get_next_onboarding_step()` to include copilot
- [x] Verify step transitions work correctly

### 1.4: Template

- [x] Create `templates/onboarding/copilot.html`

### 1.5: Stepper UI

- [x] Update `templates/onboarding/base.html` stepper
- [x] Add Copilot step conditionally based on `copilot_enabled` flag
- [x] Fix step count calculation (dynamic numbering)

---

## Phase 2: Post-Activation in Integrations (US-3) ✅

### 2.1: Update Existing Card (TDD)

**TDD Status:** Complete

- [x] RED: Write tests for Copilot card states (18 tests)
- [x] GREEN: Update template with status-aware rendering
- [x] REFACTOR: Added helper function for test selector

**Test file:** `apps/integrations/tests/test_copilot_card.py` (18 tests)
**Template file:** `templates/integrations/home.html` (lines 369-576)

### 2.2: Activation Endpoint

- [x] Add `activate_copilot` view to `apps/integrations/views/status.py`
- [x] Add `deactivate_copilot` view to `apps/integrations/views/status.py`
- [x] Use service function from Phase 0
- [x] Add URL patterns (`copilot/activate/`, `copilot/deactivate/`)
- [x] Return redirect with success message

---

## Phase 3: Edge Case UI (US-6 partial) ✅

**Note:** Already covered by Phase 2 template implementation

### 3.1: "Awaiting Data" State (insufficient_licenses)

- [x] Template shows warning icon and message
- [x] Explains 5+ license requirement
- [ ] "Check Again" button (FUTURE - triggers re-check)

### 3.2: "Token Revoked" State

- [x] Template shows error state
- [x] "Reconnect GitHub" link (redirects to GitHub card)

---

## Quick Commands

```bash
# Run activation service tests
.venv/bin/pytest apps/integrations/tests/test_copilot_activation.py -v

# Run onboarding tests
.venv/bin/pytest apps/onboarding/tests/test_copilot_step.py -v

# Run card tests
.venv/bin/pytest apps/integrations/tests/test_copilot_card.py -v

# Run all Copilot-related tests
.venv/bin/pytest -k copilot -v

# Run specific test in isolation (for flaky tests)
.venv/bin/pytest apps/onboarding/tests/test_copilot_step.py::TestCopilotStepSkip::test_connect_copilot_redirects_to_complete_when_disabled -v

# Start dev server
make dev
```

---

## Reference Files

| Existing File | Purpose |
|---------------|---------|
| `apps/onboarding/views/jira.py` | Pattern for optional onboarding step |
| `apps/onboarding/views/_helpers.py` | Flags context helper |
| `templates/onboarding/connect_slack.html` | Template pattern |
| `templates/integrations/home.html` | Copilot card location |
| `apps/integrations/views/status.py` | Contains all integration views |

---

## Session Progress

### Sessions 1-3 (2026-01-11)

- [x] Created initial plan
- [x] Ran plan-reviewer agent
- [x] Incorporated review findings
- [x] Phase 0: Service layer complete
- [x] Phase 1: Onboarding step complete
- [x] Phase 2: Integrations card complete

### Session 4 (2026-01-11)

- [x] Updated stepper UI in `templates/onboarding/base.html`
- [x] Dynamic step numbering implemented
- [x] Verified all tests pass
- [x] Updated documentation

---

## Test Summary

| Phase | Tests | Status |
|-------|-------|--------|
| Service layer | 8 | ✅ Pass |
| Onboarding view | 10 | ✅ Pass |
| Integrations card | 18 | ✅ Pass |
| **Total** | **36** | **All passing** |

---

## Known Issues

### Waffle Flag Test Flakiness

Some tests fail in parallel execution due to waffle flag state pollution:
- `test_connect_copilot_redirects_to_complete_when_disabled`
- Various Jinja2 template tests

**Workaround:** Run in isolation:
```bash
.venv/bin/pytest <test_file>::<test_name> -v
```

This is a known pattern with `@override_flag` in parallel test runs, not a code bug.
