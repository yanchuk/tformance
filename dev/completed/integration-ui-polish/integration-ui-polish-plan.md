# Integration Page UI Polish - Plan

**Last Updated:** 2026-01-03
**Status:** In Progress

---

## Executive Summary

Polish the integrations page (`/app/integrations/`) to ensure consistent styling and behavior across all integration cards when feature flags are disabled. This includes removing icon backgrounds, adding Coming Soon states with benefits lists and "I'm Interested" buttons to Slack and Copilot cards, improving badge contrast, and fixing the Google Workspace icon.

---

## Current State Analysis

### Template: `apps/integrations/templates/integrations/home.html`
- All icons have `bg-base-300 rounded-lg p-3` background containers
- **Jira card**: Correctly shows Coming Soon + benefits + I'm Interested when flag disabled
- **Slack card**: Shows "Not connected" instead of Coming Soon when flag disabled
- **Copilot card**: Shows "Not available" text, no Coming Soon state
- **Google Workspace**: Uses generic globe SVG instead of Google brand icon
- **Coming Soon badge**: Uses `app-badge-warning` with poor contrast

### Service: `apps/integrations/services/integration_flags.py`
- `IntegrationStatus` dataclass already has `benefits` field
- Benefits already defined for all integrations (Jira, Copilot, Slack, Google Workspace)
- `get_integration_status()` returns status with enabled flag and benefits

### Current Flag States (all disabled)
- `integration_jira_enabled`: False
- `integration_slack_enabled`: False
- `integration_copilot_enabled`: False
- `integration_google_workspace_enabled`: False

---

## Proposed Future State

1. **Icons**: Clean icons without background containers
2. **Slack Card**: Shows Coming Soon + benefits + I'm Interested when disabled
3. **Copilot Card**: Shows Coming Soon + benefits + I'm Interested when disabled
4. **Google Icon**: FontAwesome Google brand icon
5. **Coming Soon Badge**: High-contrast styling (WCAG AA compliant)

---

## Implementation Phases (TDD)

### Phase 1: RED - Write Failing E2E Tests (S)
Write Playwright tests that will fail against current implementation.

**Tests to Add:**
1. `test_slack_shows_coming_soon_when_disabled` - Slack card shows "Coming Soon" badge
2. `test_slack_shows_benefits_when_disabled` - Slack card shows benefits list
3. `test_slack_shows_interested_button_when_disabled` - Slack card has "I'm Interested" button
4. `test_copilot_shows_coming_soon_when_disabled` - Copilot card shows "Coming Soon" badge
5. `test_copilot_shows_benefits_when_disabled` - Copilot card shows benefits list
6. `test_copilot_shows_interested_button_when_disabled` - Copilot card has "I'm Interested" button
7. `test_icons_have_no_background` - Icon containers don't have bg-base-300

**Verification:** Run tests, confirm all NEW tests fail

### Phase 2: GREEN - Implement Template Changes (M)
Make minimal changes to pass all tests.

1. Remove `bg-base-300 rounded-lg p-3` from all icon containers
2. Update Slack card to check `slack_status.enabled` and show Coming Soon state
3. Update Copilot card to check `copilot_status.enabled` and show Coming Soon state
4. Replace Google Workspace globe SVG with FontAwesome icon
5. Improve Coming Soon badge contrast

**Verification:** Run tests, confirm all tests pass

### Phase 3: REFACTOR - Polish & Verify (S)
1. Run full E2E test suite
2. Visual verification with Playwright
3. Clean up any duplicate code

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing Jira Coming Soon | Keep Jira card unchanged, only modify Slack/Copilot |
| FontAwesome icon not available | Verify fa-brands fa-google exists in project |
| HTMX swap not working | Copy exact pattern from Jira/Google cards |
| Badge contrast insufficient | Test with WCAG contrast checker |

---

## Success Metrics

- All E2E tests pass
- Visual consistency across all Coming Soon cards
- Coming Soon badge passes WCAG AA contrast (4.5:1 ratio)
- I'm Interested buttons swap to "Thanks!" on click
