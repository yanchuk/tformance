# GitHub Surveys - Task Checklist

**Last Updated:** 2024-12-13

## Overview

This checklist tracks implementation progress for the GitHub-based survey system.

**Estimated Total Effort:** 10-12 days
**Status:** ✅ COMPLETED

---

## Phase 1: Foundation - Token System ✅

### 1.1 Model Updates ✅

- [x] Add `token` field to `PRSurvey` model (CharField, max_length=64, unique, indexed)
- [x] Add `token_expires_at` field to `PRSurvey` model (DateTimeField, null=True, indexed)
- [x] Add `github_comment_id` field to `PRSurvey` model (BigIntegerField, null=True)
- [x] Add `is_token_expired()` method to PRSurvey model
- [x] Create and run migrations (0001, 0002)
- [x] Update `PRSurveyFactory` to generate tokens

### 1.2 Token Service ✅

- [x] Create `apps/metrics/services/survey_tokens.py`
- [x] Implement `generate_survey_token()` function (secrets.token_urlsafe(32))
- [x] Implement `set_survey_token(survey, expiry_days=7)` function
- [x] Implement `validate_survey_token(token)` function
- [x] Create custom exceptions: `SurveyTokenError`, `InvalidTokenError`, `ExpiredTokenError`
- [x] Integrate token generation into `create_pr_survey()` in survey_service.py

### 1.3 Token Tests ✅ (32 tests)

- [x] Test token field exists and is unique
- [x] Test token generation produces unique URL-safe tokens
- [x] Test token validation with valid/invalid/expired tokens
- [x] Test custom exceptions

---

## Phase 2: Web Survey Views ✅

### 2.1 URL Configuration ✅

- [x] `survey/<str:token>/` - landing (survey_landing)
- [x] `survey/<str:token>/author/` - author form (survey_author)
- [x] `survey/<str:token>/reviewer/` - reviewer form (survey_reviewer)
- [x] `survey/<str:token>/submit/` - form submission (survey_submit)
- [x] `survey/<str:token>/complete/` - completion (survey_complete)

### 2.2 Survey Views ✅

- [x] `survey_landing()` - validates token, redirects to appropriate form
- [x] `survey_author()` - shows author survey form
- [x] `survey_reviewer()` - shows reviewer survey form
- [x] `survey_submit()` - handles POST, records responses
- [x] `survey_complete()` - shows thank you message

### 2.3 View Tests ✅ (43 tests)

- [x] URL pattern tests
- [x] Authentication requirement tests
- [x] Token validation tests (invalid, expired)
- [x] Form submission tests

---

## Phase 3: Survey Templates ✅

### 3.1 Templates Created ✅

- [x] `templates/web/surveys/base.html` - base template
- [x] `templates/web/surveys/author.html` - AI assistance question
- [x] `templates/web/surveys/reviewer.html` - quality + AI guess
- [x] `templates/web/surveys/complete.html` - thank you page

### 3.2 Form Submission ✅

- [x] Author submission records `author_ai_assisted` and `author_responded_at`
- [x] Reviewer submission creates `PRSurveyReview` with quality_rating, ai_guess
- [x] Duplicate submissions are ignored (idempotent)

---

## Phase 4: Authorization ✅

### 4.1 Authorization Decorators ✅

- [x] `get_user_github_id(user)` - gets GitHub ID from SocialAccount
- [x] `verify_author_access(user, survey)` - verifies user is PR author
- [x] `verify_reviewer_access(user, survey)` - verifies user is PR reviewer
- [x] `@require_survey_author_access` decorator
- [x] `@require_survey_reviewer_access` decorator

### 4.2 Authorization Tests ✅ (7 tests)

- [x] Author can access author survey
- [x] Non-author gets 403
- [x] Reviewer can access reviewer survey
- [x] Non-reviewer gets 403
- [x] User without GitHub account gets 403

---

## Phase 5: GitHub Comment Service ✅

### 5.1 Comment Service ✅

- [x] `build_survey_comment_body(pr, survey)` - builds markdown with @mentions and URLs
- [x] `post_survey_comment(pr, survey, access_token)` - posts to GitHub API
- [x] Error handling with GithubException
- [x] Logging for success and failure

### 5.2 Comment Tests ✅ (11 tests)

- [x] Comment body generation tests
- [x] @mention tests (author and reviewers)
- [x] URL generation tests
- [x] GitHub API call tests (mocked)

---

## Phase 6: Celery Task Integration ✅

### 6.1 Task Implementation ✅

- [x] `post_survey_comment_task(pull_request_id)` - main task
- [x] Creates PRSurvey with token
- [x] Posts comment to GitHub
- [x] Stores github_comment_id
- [x] Retry logic (3 retries, exponential backoff)
- [x] Sentry integration for permanent failures

### 6.2 Task Tests ✅ (8 tests)

- [x] Task creates survey for merged PR
- [x] Task posts comment to GitHub
- [x] Task skips non-merged PRs
- [x] Task is idempotent (skips existing surveys)
- [x] Task handles missing GitHub integration
- [x] Task handles GitHub API errors gracefully

---

## Test Summary

| Category | Tests |
|----------|-------|
| Token System | 32 |
| Survey Views | 43 |
| GitHub Comments | 11 |
| Celery Task | 8 |
| **Total New Tests** | **94** |
| **Full Suite** | **1185** |

---

## Files Created/Modified

### New Files
- `apps/metrics/services/survey_tokens.py` - Token generation/validation
- `apps/metrics/tests/test_survey_tokens.py` - Token tests
- `apps/integrations/services/github_comments.py` - GitHub comment service
- `apps/integrations/tests/test_github_comments.py` - Comment tests
- `apps/web/tests/test_survey_views.py` - View tests
- `templates/web/surveys/base.html` - Base template
- `templates/web/surveys/author.html` - Author form
- `templates/web/surveys/reviewer.html` - Reviewer form
- `templates/web/surveys/complete.html` - Completion page

### Modified Files
- `apps/metrics/models.py` - Added token fields to PRSurvey
- `apps/metrics/services/survey_service.py` - Token integration
- `apps/metrics/factories.py` - Factory updates
- `apps/web/urls.py` - Survey URL patterns
- `apps/web/views.py` - Survey views
- `apps/web/decorators.py` - Authorization decorators
- `apps/integrations/tasks.py` - Celery task

### Migrations
- `apps/metrics/migrations/0001_prsurvey_github_comment_id_prsurvey_token_and_more.py`
- `apps/metrics/migrations/0002_alter_prsurvey_token_expires_at.py`

---

## Completion Checklist

- [x] All tests pass (`make test`)
- [x] Code formatted (`make ruff`)
- [x] No new linting errors
- [x] Migration tested
- [x] Documentation updated
