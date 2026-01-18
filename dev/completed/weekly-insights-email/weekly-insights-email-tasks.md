# Weekly Insights Email - Task Checklist

**Last Updated: 2026-01-18**

## Pre-Implementation Checklist

- [ ] Run existing tests: `make test` (ensure clean state)
- [ ] Read reference files to understand patterns:
  - [ ] `apps/onboarding/services/notifications.py`
  - [ ] `apps/onboarding/tests/test_welcome_email.py`
  - [ ] `apps/metrics/models/insights.py`

---

## Phase 1: TDD RED - Write Failing Tests

> **Agent**: Use `tdd-test-writer` for this phase
> **Goal**: Tests must FAIL (proves they're valid)

### 1.1 Create Test File Structure
- [ ] Create `apps/insights/tests/__init__.py` (if not exists)
- [ ] Create `apps/insights/tests/test_weekly_email.py`

### 1.2 Write Tests for `get_latest_weekly_insight()` [Effort: S]
- [ ] `test_returns_insight_when_exists_for_current_monday`
- [ ] `test_returns_none_when_no_insight_exists`
- [ ] `test_filters_by_team_correctly`
- [ ] `test_filters_by_comparison_period_7`
- [ ] `test_ignores_insights_from_other_dates`

### 1.3 Write Tests for `send_weekly_insight_email()` [Effort: M]
- [ ] `test_send_email_success_when_insight_exists`
- [ ] `test_returns_skipped_when_no_insight`
- [ ] `test_returns_skipped_when_no_admins_with_email`
- [ ] `test_email_subject_contains_headline`
- [ ] `test_email_body_contains_summary`
- [ ] `test_email_body_contains_dashboard_link`
- [ ] `test_multiple_admins_all_receive_email`
- [ ] `test_email_uses_first_name_in_greeting`
- [ ] `test_email_uses_fallback_greeting_when_no_name`

### 1.4 Verify Tests Fail
- [ ] Run: `.venv/bin/pytest apps/insights/tests/test_weekly_email.py -v`
- [ ] Confirm ALL tests fail (ImportError expected initially)

**Acceptance Criteria (Phase 1)**:
- Test file created with all test cases
- Tests fail with ImportError or AssertionError
- No implementation code exists yet

---

## Phase 2: TDD GREEN - Implement Minimum Code

> **Agent**: Use `tdd-implementer` for this phase
> **Goal**: Make tests PASS with minimum code

### 2.1 Create Service File Structure
- [ ] Create `apps/insights/services/__init__.py` (if not exists)
- [ ] Create `apps/insights/services/weekly_email.py`

### 2.2 Implement `get_latest_weekly_insight()` [Effort: S]
- [ ] Import DailyInsight model
- [ ] Calculate current Monday date
- [ ] Query with team, category, comparison_period, date filters
- [ ] Return first result or None
- [ ] Run tests: verify `get_latest_weekly_insight` tests pass

### 2.3 Implement `send_weekly_insight_email()` [Effort: M]
- [ ] Query insight using `get_latest_weekly_insight()`
- [ ] Early return if no insight
- [ ] Query team admins with email
- [ ] Early return if no admins
- [ ] Build email subject from headline
- [ ] Build email body with greeting, summary, link
- [ ] Send email with `send_mail()` to all admins
- [ ] Return result dict with `sent_to` count
- [ ] Run tests: verify ALL tests pass

### 2.4 Verify Tests Pass
- [ ] Run: `.venv/bin/pytest apps/insights/tests/test_weekly_email.py -v`
- [ ] Confirm ALL tests pass
- [ ] Run: `make test` (ensure no regressions)

**Acceptance Criteria (Phase 2)**:
- All unit tests pass
- Implementation uses minimum code
- No extra features beyond what tests require

---

## Phase 3: TDD REFACTOR - Clean Up

> **Agent**: Use `tdd-refactorer` for this phase
> **Goal**: Improve code quality while keeping tests green

### 3.1 Code Quality Improvements [Effort: S]
- [ ] Add type hints to all functions
- [ ] Add docstrings following project conventions
- [ ] Add logging for skip scenarios
- [ ] Add `# noqa: TEAM001` comment where needed
- [ ] Run tests after each change

### 3.2 Extract Helpers (if needed)
- [ ] Consider extracting `get_team_admins_with_email()` helper
- [ ] Consider extracting `build_email_content()` helper
- [ ] Run tests after any extraction

### 3.3 Final Verification
- [ ] Run: `.venv/bin/pytest apps/insights/tests/test_weekly_email.py -v`
- [ ] Run: `make ruff` (formatting and linting)
- [ ] Run: `make test` (full test suite)

**Acceptance Criteria (Phase 3)**:
- Code is clean and well-documented
- Follows project conventions
- All tests still pass
- No linting errors

---

## Phase 4: Integration

### 4.1 Add Celery Task [Effort: S]
- [ ] Edit `apps/metrics/tasks.py`
- [ ] Add `send_weekly_insight_emails()` task
- [ ] Import service function
- [ ] Iterate over teams with `onboarding_complete=True`
- [ ] Call service function for each team
- [ ] Return aggregated results

### 4.2 Configure Scheduled Task [Effort: S]
- [ ] Edit `tformance/settings.py`
- [ ] Add to `SCHEDULED_TASKS` dict:
  ```python
  "send-weekly-insights-email": {
      "task": "apps.metrics.tasks.send_weekly_insight_emails",
      "schedule": schedules.crontab(minute=0, hour=9, day_of_week=1),
      "expire_seconds": 60 * 60,
  },
  ```
- [ ] Add to `CELERY_TASK_ROUTES`:
  ```python
  "apps.metrics.tasks.send_weekly_insight_emails": {"queue": "sync"},
  ```

### 4.3 Bootstrap and Verify [Effort: S]
- [ ] Run: `.venv/bin/python manage.py bootstrap_celery_tasks`
- [ ] Verify task appears in admin (Django Celery Beat)

**Acceptance Criteria (Phase 4)**:
- Celery task registered
- Scheduled for Monday 9 AM UTC
- Task routing configured

---

## Phase 5: Manual Testing

### 5.1 Create Test Data [Effort: S]
- [ ] Open Django shell: `.venv/bin/python manage.py shell`
- [ ] Create test insight:
  ```python
  from datetime import date, timedelta
  from apps.metrics.factories import TeamFactory
  from apps.metrics.models import DailyInsight

  team = TeamFactory()
  today = date.today()
  monday = today - timedelta(days=today.weekday())

  DailyInsight.objects.create(
      team=team,
      date=monday,
      category="llm_insight",
      comparison_period="7",
      title="Test Headline",
      description="Test Description",
      metric_type="llm_dashboard_insight",
      metric_value={
          "headline": "AI adoption grew 15%",
          "detail": "Your team merged 25 PRs this week with strong AI tool usage."
      },
      priority="medium",
  )
  ```

### 5.2 Test Service Function [Effort: S]
- [ ] In Django shell:
  ```python
  from apps.insights.services.weekly_email import send_weekly_insight_email
  result = send_weekly_insight_email(team)
  print(result)
  ```
- [ ] Check console output for email (dev mode)

### 5.3 Test Celery Task [Effort: S]
- [ ] In Django shell:
  ```python
  from apps.metrics.tasks import send_weekly_insight_emails
  result = send_weekly_insight_emails()
  print(result)
  ```
- [ ] Verify result dict shows emails sent

**Acceptance Criteria (Phase 5)**:
- Email appears in console (dev) or Resend dashboard (prod)
- Content includes headline, summary, and dashboard link
- No errors in logs

---

## Post-Implementation

- [ ] Run full test suite: `make test`
- [ ] Commit with descriptive message
- [ ] Update this task file with completion date

---

## Summary

| Phase | Effort | Status |
|-------|--------|--------|
| Phase 1: RED (Tests) | M | ✅ Complete |
| Phase 2: GREEN (Impl) | M | ✅ Complete |
| Phase 3: REFACTOR | S | ✅ Complete |
| Phase 4: Integration | S | ✅ Complete |
| Phase 5: Manual Test | S | ⬜ Pending |

**Completed: 2026-01-18**

**Total Estimated Effort**: Medium (2-3 hours with TDD)
