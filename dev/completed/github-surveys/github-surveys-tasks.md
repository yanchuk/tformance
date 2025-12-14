# GitHub Surveys - Task Checklist

**Last Updated:** 2025-12-13

## Status: ALL PHASES COMPLETE ✅

All 6 implementation phases are complete with 94+ tests passing.

## Phase 1: Foundation - Token System ✅

### 1.1 Model Fields ✅
- [x] Add `token` field to PRSurvey (CharField, unique, indexed)
- [x] Add `token_expires_at` field (DateTimeField, indexed)
- [x] Add `github_comment_id` field (BigIntegerField, nullable)
- [x] Add `is_token_expired()` method
- [x] Create migrations
- [x] Tests: 13 tests in `TestPRSurveyTokenFields`

### 1.2 Token Generation ✅
- [x] Create `apps/metrics/services/survey_tokens.py`
- [x] Implement `generate_survey_token()` - 43-char URL-safe token
- [x] Implement `set_survey_token(survey, expiry_days=7)`
- [x] Integrate with `create_pr_survey()` - auto-generate token
- [x] Tests: 10 tests in `TestTokenGenerationService` + `TestCreatePRSurveyIntegration`

### 1.3 Token Validation ✅
- [x] Implement `validate_survey_token(token)` - returns PRSurvey or raises
- [x] Add `SurveyTokenError` base exception
- [x] Add `InvalidTokenError` for None/empty/not-found
- [x] Add `ExpiredTokenError` for expired tokens
- [x] Add structured logging (WARNING/INFO/DEBUG levels)
- [x] Tests: 9 tests in `TestTokenValidationService`

## Phase 2: Web Survey Views ✅

- [x] Add 5 URL patterns in `apps/web/urls.py`
- [x] Create `survey_landing` view
- [x] Create `survey_author` view
- [x] Create `survey_reviewer` view
- [x] Create `survey_submit` view (POST handler)
- [x] Create `survey_complete` view
- [x] Tests: 26 tests in `apps/web/tests/test_survey_views.py`

## Phase 3: Form Submission ✅

- [x] Implement author form submission logic
- [x] Implement reviewer form submission logic
- [x] Handle duplicate submissions gracefully
- [x] Tests: 10 additional tests

## Phase 4: Authorization ✅

- [x] Create `@require_valid_survey_token` decorator
- [x] Create `@require_survey_author_access` decorator
- [x] Create `@require_survey_reviewer_access` decorator
- [x] Verify GitHub identity via `SocialAccount`
- [x] Add authorization logging
- [x] Tests: 7 authorization tests

## Phase 5: GitHub Comment Service ✅

- [x] Create `apps/integrations/services/github_comments.py`
- [x] Implement `build_survey_comment_body()` with @mentions
- [x] Implement `post_survey_comment()` using PyGithub
- [x] Handle `GithubException` with logging
- [x] Store `github_comment_id` after posting
- [x] Tests: 11 tests in `test_github_comments.py`

## Phase 6: Celery Task Integration ✅

- [x] Add `post_survey_comment_task` to `apps/integrations/tasks.py`
- [x] Idempotency checks (skip if survey exists, PR not merged, no integration)
- [x] Retry logic (3x with exponential backoff: 60s, 120s, 240s)
- [x] Sentry integration for final failures
- [x] Tests: 8 tests in `TestPostSurveyCommentTask`

## Phase 7: Skip Responded Reviewers ✅

- [x] Add `has_author_responded()` method to PRSurvey model
- [x] Skip author Slack DM if already responded via GitHub
- [x] Skip reviewer Slack DM if already responded via GitHub
- [x] Optimize reviewer check (single query vs N+1)
- [x] Return `author_skipped` and `reviewers_skipped` in task result
- [x] Tests: 5 tests in `TestSkipRespondedReviewers`

## Remaining Work (Not Started)

### Phase 8: Trigger Integration
- [ ] Wire up `post_survey_comment_task` to GitHub webhook (on PR merge)
- [ ] Add team setting for survey channel preference (github/slack/both)

### Phase 9: Manual E2E Testing
- [ ] Test full flow: PR merge → GitHub comment → web form → response saved
- [ ] Verify Slack skip logic works when GitHub response exists

## Files Created

| File | Purpose |
|------|---------|
| `apps/metrics/services/survey_tokens.py` | Token generation/validation |
| `apps/metrics/tests/test_survey_tokens.py` | Token tests (32) |
| `apps/web/decorators.py` | Survey view decorators |
| `apps/web/tests/test_survey_views.py` | View tests (43) |
| `apps/integrations/services/github_comments.py` | Comment service |
| `apps/integrations/tests/test_github_comments.py` | Comment tests (11) |
| `templates/web/surveys/*.html` | Survey templates (4) |

## Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/models.py` | Token fields, `is_token_expired()`, `has_author_responded()` |
| `apps/metrics/factories.py` | `token_expires_at` default |
| `apps/metrics/services/survey_service.py` | Auto-generate token in `create_pr_survey()` |
| `apps/web/urls.py` | 5 survey URL patterns |
| `apps/web/views.py` | 5 survey views + helpers |
| `apps/integrations/tasks.py` | `post_survey_comment_task`, skip logic in `send_pr_surveys_task` |
| `apps/integrations/tests/test_tasks.py` | Task tests (8 + 5) |

## Migrations

- `apps/metrics/migrations/0001_prsurvey_github_comment_id_prsurvey_token_and_more.py`
- `apps/metrics/migrations/0002_alter_prsurvey_token_expires_at.py`

All migrations applied.
