# Slack Onboarding OAuth - Tasks

**Last Updated:** 2025-12-28

## Phase 1: OAuth State Management ✅
- [x] Add `FLOW_TYPE_SLACK_ONBOARDING` constant
- [x] Add `FLOW_TYPE_SLACK_INTEGRATION` constant
- [x] Add to `VALID_FLOW_TYPES` tuple
- [x] Update validation rules (Slack onboarding team_id optional)
- [x] Add tests for new flow types (5 tests)

## Phase 2: Unified Slack Callback ✅
- [x] Create `slack_callback()` function in auth/views.py
- [x] Create `_handle_slack_onboarding_callback()` helper
- [x] Create `_handle_slack_integration_callback()` helper
- [x] Add URL pattern `slack/callback/`
- [x] Add imports for Slack models and services
- [x] Create test file `test_slack_callback.py` (13 tests)

## Phase 3: Onboarding View Update ✅
- [x] Update `connect_slack()` to handle `action=connect`
- [x] Check if Slack already connected
- [x] Build Slack OAuth authorization URL
- [x] Update template to enable button
- [x] Remove "Coming Soon" badge
- [x] Show workspace name after connection
- [x] Add tests for OAuth initiation (5 tests)

## Phase 4: Integration View Cleanup ✅
- [x] Update `slack_connect()` to use unified state
- [x] Update to use unified callback URL
- [x] Simplify old `slack_callback()` (redirect to unified)

## Final Verification ✅
- [x] Run all related tests (43 tests pass)
- [ ] Manual test onboarding flow
- [ ] Manual test integration flow
