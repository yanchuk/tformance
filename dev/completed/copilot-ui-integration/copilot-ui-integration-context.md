# Copilot UI Integration - Context

**Created:** 2026-01-11
**Last Updated:** 2026-01-11 (Session 4)
**Status:** COMPLETE - All phases implemented

## Overview

Implement the frontend/UI components for GitHub Copilot integration:
1. **US-1**: Onboarding step for connecting Copilot during initial setup ✅
2. **US-3**: Post-activation settings page for connecting Copilot later ✅

## Implementation Summary

### Phase 0: Service Layer ✅
- Created `apps/integrations/services/copilot_activation.py`
- Functions: `activate_copilot_for_team()`, `deactivate_copilot_for_team()`
- 8 unit tests passing

### Phase 1: Onboarding Step ✅
- Created `apps/onboarding/views/copilot.py` with `connect_copilot` view
- Created `templates/onboarding/copilot.html` template
- Added URL pattern to `apps/onboarding/urls.py`
- Updated `apps/onboarding/views/_helpers.py` with `copilot_enabled` context
- Updated `apps/integrations/services/integration_flags.py` step flow
- 10 unit tests passing

### Phase 1.5: Stepper UI ✅
- Updated `templates/onboarding/base.html` with dynamic Copilot step
- Step appears conditionally based on `copilot_enabled` flag
- Dynamic step numbering for Copilot → Jira → Slack sequence

### Phase 2: Integrations Card ✅
- Updated `apps/integrations/views/status.py`:
  - Added `copilot_status` to context
  - Added `activate_copilot` view
  - Added `deactivate_copilot` view
- Added URL patterns: `copilot/activate/`, `copilot/deactivate/`
- Rewrote Copilot card in `templates/integrations/home.html` (lines 369-576)
- Added `app-status-pill-error` CSS class to `design-system.css`
- 18 unit tests passing

## Key Files Modified

| File | Change |
|------|--------|
| `apps/integrations/services/copilot_activation.py` | NEW: Activation service |
| `apps/integrations/tests/test_copilot_activation.py` | NEW: 8 service tests |
| `apps/onboarding/views/copilot.py` | NEW: Onboarding view |
| `apps/onboarding/tests/test_copilot_step.py` | NEW: 10 view tests |
| `apps/integrations/tests/test_copilot_card.py` | NEW: 18 card tests |
| `templates/onboarding/copilot.html` | NEW: Template |
| `apps/onboarding/urls.py` | Added URL pattern |
| `apps/onboarding/views/_helpers.py` | Added copilot_enabled |
| `apps/onboarding/views/__init__.py` | Export new view |
| `apps/integrations/services/integration_flags.py` | Updated step flow |
| `templates/onboarding/base.html` | Dynamic stepper |
| `apps/integrations/views/status.py` | Added activate/deactivate views |
| `apps/integrations/urls.py` | Added 2 URL patterns |
| `apps/integrations/views/__init__.py` | Export new views |
| `templates/integrations/home.html` | Rewrote Copilot card |
| `assets/styles/app/tailwind/design-system.css` | Added error pill class |

## Test Summary

```
Total Copilot UI tests: 36 new tests
- 8 activation service tests
- 10 onboarding view tests
- 18 integrations card tests
```

## Known Test Flakiness

Some waffle flag tests fail in parallel execution but pass in isolation:
- `test_connect_copilot_redirects_to_complete_when_disabled`
- Various Jinja2 template tests

This is a known issue with waffle flag state pollution in parallel test runs, not a code bug.

## Architecture Decisions

### 1. Copilot Card States
The integrations home Copilot card renders 4 distinct states based on `team.copilot_status`:
- `disabled`: Shows "Connect Copilot" button
- `connected`: Shows "Connected" badge, "Sync Now" button, "Disconnect" button
- `insufficient_licenses`: Shows "Awaiting Data" with license requirement explanation
- `token_revoked`: Shows "Reconnect Required" error state

### 2. Dynamic Stepper Numbering
The onboarding stepper calculates step numbers dynamically:
```django
{% with done_step=3|add:copilot_enabled|add:jira_enabled|add:slack_enabled %}
{% with copilot_step=3 jira_step_num=3|add:copilot_enabled slack_step_num=3|add:copilot_enabled|add:jira_enabled %}
```

### 3. Service Layer Pattern
Used activation service functions to encapsulate business logic:
```python
def activate_copilot_for_team(team: Team) -> dict:
    """Returns {"status": "activated"} or {"status": "already_connected"}"""
```

## Related Code References

### Extract Copilot Card Test Helper
```python
def extract_copilot_card(content: str) -> str:
    """Extract Copilot card HTML between headings."""
    pattern = r"<h2[^>]*>GitHub Copilot</h2>.*?(?=<h2[^>]*>Google Workspace</h2>|$)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(0) if match else ""
```

## Next Steps (If Extending)

Phase 3 edge cases are already covered by Phase 2 template:
- ✅ "Awaiting Data" state for insufficient_licenses
- ✅ "Reconnect Required" state for token_revoked
- Future: "Check Again" button to re-check license count
- Future: Email notification when Copilot data becomes available
