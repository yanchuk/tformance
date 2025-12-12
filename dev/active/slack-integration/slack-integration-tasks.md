# Slack Integration Tasks

> Last Updated: 2025-12-12 (COMPLETED)

## Progress Summary

| Section | Status | Tests |
|---------|--------|-------|
| 1. SlackIntegration Model | ✅ DONE | 8/8 |
| 2. Slack OAuth Service | ✅ DONE | 14/14 |
| 3. Slack OAuth Views | ✅ DONE | 27/27 |
| 4. Slack Client Service | ✅ DONE | 12/12 |
| 5. Slack User Matching | ✅ DONE | 8/8 |
| 6. Survey Message Templates | ✅ DONE | 13/13 |
| 7. Survey Service | ✅ DONE | 14/14 |
| 8. Slack Interactions Webhook | ✅ DONE | 16/16 |
| 9. PR Survey Celery Tasks | ✅ DONE | 12/12 |
| 10. Weekly Leaderboard | ✅ DONE | 10/10 |
| 11. GitHub Webhook Trigger | ✅ DONE | 4/4 |
| 12. UI Integration | ✅ DONE | N/A |
| **Total** | **12/12** | **138** |

**Total Test Count**: 929 tests (was 791 before Phase 4)

---

## Section 1: SlackIntegration Model ✅ COMPLETE

### Tasks
- [x] 1.1 Add `slack-sdk` package: `uv add slack-sdk` (v3.39.0)
- [x] 1.2 Add environment variables to `.env.example` and `settings.py`
- [x] 1.3 Write failing tests for SlackIntegration model (8 tests)
- [x] 1.4 Create SlackIntegration model in `apps/integrations/models.py`
- [x] 1.5 Create migrations (0011, 0012)
- [x] 1.6 Create SlackIntegrationFactory
- [x] 1.7 Register in admin with inline
- [x] 1.8 Run tests - all pass

**Files Created/Modified:**
- `apps/integrations/models.py` (lines 368-464)
- `apps/integrations/migrations/0011_slackintegration.py`
- `apps/integrations/migrations/0012_slackintegration_last_sync_error.py`
- `apps/integrations/factories.py` (lines 137-159)
- `apps/integrations/admin.py`
- `apps/integrations/tests/test_models.py`

---

## Section 2: Slack OAuth Service ✅ COMPLETE

### Tasks
- [x] 2.1 Write failing tests for OAuth service (14 tests)
- [x] 2.2 Create `apps/integrations/services/slack_oauth.py`
- [x] 2.3-2.6 Implement all OAuth functions
- [x] 2.7 REFACTOR: Extracted shared `oauth_utils.py` (~60 lines DRY)
- [x] 2.8 Run tests - all pass, ruff clean

**Files Created:**
- `apps/integrations/services/slack_oauth.py`
- `apps/integrations/services/oauth_utils.py` (shared OAuth state functions)
- `apps/integrations/tests/test_slack_oauth.py`

---

## Section 3: Slack OAuth Views ✅ COMPLETE

### Tasks
- [x] 3.1 Write failing tests for OAuth views (27 tests)
- [x] 3.2 Add URL patterns to `apps/integrations/urls.py`
- [x] 3.3-3.6 Implement all 4 views
- [x] 3.7 Create `templates/integrations/slack_settings.html`
- [x] 3.8 REFACTOR: Added Slack context to `integrations_home` view
- [x] 3.9 Run tests - all pass

**Files Created/Modified:**
- `apps/integrations/views.py` (4 new views + home context)
- `apps/integrations/urls.py` (4 URL patterns)
- `apps/integrations/tests/test_slack_views.py` (452 lines)
- `templates/integrations/slack_settings.html`

---

## Section 4: Slack Client Service ✅ COMPLETE

### Tasks
- [x] 4.1 Write failing tests for client service (12 tests)
- [x] 4.2-4.7 Create and implement `slack_client.py`
- [x] 4.8 Run tests - all pass

**Files Created:**
- `apps/integrations/services/slack_client.py`
- `apps/integrations/tests/test_slack_client.py`

---

## Section 5: Slack User Matching ✅ COMPLETE

### Tasks
- [x] 5.1 Write failing tests for user matching (8 tests)
- [x] 5.2-5.5 Create and implement `slack_user_matching.py` (105 lines)
- [x] 5.6 Run tests - all pass

**Files Created:**
- `apps/integrations/services/slack_user_matching.py`
- `apps/integrations/tests/test_slack_user_matching.py`

---

## Section 6: Survey Message Templates ✅ COMPLETE

### Tasks
- [x] 6.1 Write failing tests for message templates (13 tests)
- [x] 6.2-6.9 Create and implement `slack_surveys.py`
- [x] 6.10 Run tests - all pass

**Files Created:**
- `apps/integrations/services/slack_surveys.py` (7 action constants, 6 builder functions)
- `apps/integrations/tests/test_slack_surveys.py`

---

## Section 7: Survey Service ✅ COMPLETE

### Tasks
- [x] 7.1 Write failing tests for survey service (14 tests)
- [x] 7.2-7.8 Create and implement `survey_service.py`
- [x] 7.9 REFACTOR: Extracted `_can_send_reveal()` helper
- [x] 7.10 Run tests - all pass (214 metrics tests)

**Files Created:**
- `apps/metrics/services/survey_service.py`
- `apps/metrics/tests/test_survey_service.py`

---

## Section 8: Slack Interactions Webhook ✅ COMPLETE

### Tasks
- [x] 8.1 Write failing tests for interactions (16 tests)
- [x] 8.2-8.8 Create and implement `slack_interactions.py`
- [x] 8.9 Add URL pattern to both integrations and main urls.py
- [x] 8.10 Run tests - all pass

**Files Created/Modified:**
- `apps/integrations/webhooks/slack_interactions.py`
- `apps/integrations/urls.py` (added urlpatterns)
- `tformance/urls.py` (included integrations app)
- `apps/integrations/tests/test_slack_interactions.py`

---

## Section 9: PR Survey Celery Tasks ✅ COMPLETE

### Tasks
- [x] 9.1 Write failing tests for tasks (12 tests)
- [x] 9.2-9.5 Implement 3 tasks in `tasks.py`
- [x] 9.6 REFACTOR: Added `select_related()` optimization
- [x] 9.7 Run tests - all pass

**Files Modified:**
- `apps/integrations/tasks.py` (3 new tasks: send_pr_surveys_task, send_reveal_task, sync_slack_users_task)
- `apps/integrations/tests/test_slack_tasks.py`

---

## Section 10: Weekly Leaderboard ✅ COMPLETE

### Tasks
- [x] 10.1 Write failing tests for leaderboard (10 tests)
- [x] 10.2-10.5 Create and implement `slack_leaderboard.py` (225 lines)
- [x] 10.6 Add `post_weekly_leaderboards_task()` to tasks.py
- [x] 10.7 Add Celery Beat schedule entry (settings.py lines 533-537)
- [x] 10.8 Run tests - all pass

**Files Created/Modified:**
- `apps/integrations/services/slack_leaderboard.py`
- `apps/integrations/tests/test_slack_leaderboard.py` (355 lines)
- `apps/integrations/tasks.py`
- `tformance/settings.py` (Celery Beat schedule)

---

## Section 11: GitHub Webhook Trigger ✅ COMPLETE

### Tasks
- [x] 11.1 Write failing tests for webhook trigger (4 tests)
- [x] 11.2-11.3 Modify `apps/metrics/processors.py`
- [x] 11.4 REFACTOR: Extracted `_trigger_pr_surveys_if_merged()` helper
- [x] 11.5 Run tests - all pass (26 PR processor tests)

**Files Modified:**
- `apps/metrics/processors.py`
- `apps/metrics/tests/test_pr_processor.py`

---

## Section 12: UI Integration ✅ COMPLETE

### Tasks
- [x] 12.1 Update `integrations_home` view (already done in Section 3)
- [x] 12.2 Update `home.html` template with Slack card
- [x] 12.3 Removed "Coming Soon" placeholder
- [x] 12.4 Card shows connected/not connected status
- [x] 12.5 Settings link works

**Files Modified:**
- `apps/integrations/templates/integrations/home.html`

---

## Session Checklist ✅

- [x] All tests pass: `make test ARGS='--keepdb'` → 929 tests OK
- [x] Linting passes: `make ruff` → All checks passed
- [x] No pending migrations: All applied (0011, 0012)
- [x] This file updated with progress
- [ ] Commit changes with descriptive message

---

## Verification Commands

```bash
# Run all tests
make test ARGS='--keepdb'  # 929 tests

# Run Slack-specific tests
make test ARGS='apps.integrations.tests.test_slack_oauth --keepdb'
make test ARGS='apps.integrations.tests.test_slack_views --keepdb'
make test ARGS='apps.integrations.tests.test_slack_client --keepdb'
make test ARGS='apps.integrations.tests.test_slack_user_matching --keepdb'
make test ARGS='apps.integrations.tests.test_slack_surveys --keepdb'
make test ARGS='apps.integrations.tests.test_slack_interactions --keepdb'
make test ARGS='apps.integrations.tests.test_slack_tasks --keepdb'
make test ARGS='apps.integrations.tests.test_slack_leaderboard --keepdb'
make test ARGS='apps.metrics.tests.test_survey_service --keepdb'
make test ARGS='apps.metrics.tests.test_pr_processor --keepdb'

# Linting
make ruff
```

---

## Next Phase: Phase 5 - Basic Dashboard

Per IMPLEMENTATION-PLAN.md, next implement:
- Native dashboards (Chart.js + HTMX)
- Team metrics visualization
- AI correlation views
