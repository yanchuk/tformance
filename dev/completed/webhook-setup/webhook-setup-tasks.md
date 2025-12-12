# Phase 2.5: Webhook Setup - Task Checklist

> Last Updated: 2025-12-10

## Overview

Total tasks: 34
Estimated effort: Medium (Phase complexity: M)

---

## 2.5.1 Webhook Service Functions [Effort: M]

### Create Webhook Function
- [ ] Create `apps/integrations/services/github_webhooks.py`
- [ ] Add `create_repository_webhook(access_token, repo_full_name, webhook_url, secret)` function
- [ ] POST to GitHub API: `/repos/{owner}/{repo}/hooks`
- [ ] Configure webhook for `pull_request` and `pull_request_review` events
- [ ] Return webhook_id from response
- [ ] Raise `GitHubOAuthError` on failure (403, 404, etc.)

### Delete Webhook Function
- [ ] Add `delete_repository_webhook(access_token, repo_full_name, webhook_id)` function
- [ ] DELETE to GitHub API: `/repos/{owner}/{repo}/hooks/{hook_id}`
- [ ] Return True on success (204 response)
- [ ] Handle 404 gracefully (webhook already deleted)

### Signature Validation
- [ ] Add `validate_webhook_signature(payload, signature_header, secret)` function
- [ ] Implement HMAC-SHA256 validation
- [ ] Use `hmac.compare_digest` for timing-safe comparison

### Tests
- [ ] Test `create_repository_webhook` returns webhook_id
- [ ] Test `create_repository_webhook` raises error on 403 (no permission)
- [ ] Test `create_repository_webhook` raises error on 404 (repo not found)
- [ ] Test `delete_repository_webhook` returns True on success
- [ ] Test `delete_repository_webhook` handles 404 gracefully
- [ ] Test `validate_webhook_signature` accepts valid signature
- [ ] Test `validate_webhook_signature` rejects invalid signature
- [ ] Test `validate_webhook_signature` rejects missing signature

---

## 2.5.2 Webhook Registration Integration [Effort: S]

### Toggle View Updates
- [ ] Update `github_repo_toggle` to call `create_repository_webhook` on create
- [ ] Update `github_repo_toggle` to call `delete_repository_webhook` on delete
- [ ] Store `webhook_id` in TrackedRepository after successful registration
- [ ] Clear `webhook_id` after successful deletion
- [ ] Handle registration failures gracefully (don't fail toggle)
- [ ] Log errors for failed registrations

### Webhook URL Configuration
- [ ] Add `WEBHOOK_BASE_URL` setting (or derive from `SITE_URL`)
- [ ] Build webhook URL: `{base_url}/webhooks/github/`

### Tests
- [ ] Test toggle creates webhook on track
- [ ] Test toggle deletes webhook on untrack
- [ ] Test toggle succeeds even if webhook registration fails
- [ ] Test webhook_id is stored in TrackedRepository

---

## 2.5.3 Webhook Endpoint [Effort: M]

### View Implementation
- [ ] Create `apps/web/views/webhooks.py` (or add to existing views)
- [ ] Create `github_webhook` view function
- [ ] Apply `@csrf_exempt` decorator
- [ ] Accept only POST method
- [ ] Extract `X-GitHub-Event` header
- [ ] Extract `X-Hub-Signature-256` header
- [ ] Extract repository from payload
- [ ] Look up TrackedRepository to find team
- [ ] Validate signature using team's webhook_secret
- [ ] Dispatch to appropriate event handler
- [ ] Return 200 OK (or 204 No Content)

### URL Configuration
- [ ] Add URL pattern in `apps/web/urls.py`: `path("webhooks/github/", ...)`
- [ ] Ensure NOT in team_urlpatterns (no team_slug prefix)

### Tests
- [ ] Test endpoint returns 405 for GET
- [ ] Test endpoint returns 401 for missing signature
- [ ] Test endpoint returns 401 for invalid signature
- [ ] Test endpoint returns 200 for valid payload
- [ ] Test endpoint dispatches to correct handler based on event type

---

## 2.5.4 Pull Request Event Handler [Effort: M]

### Handler Implementation
- [ ] Create `apps/metrics/services/pr_processor.py` (or similar)
- [ ] Create `handle_pull_request_event(team, payload)` function
- [ ] Handle action: `opened` → create PullRequest
- [ ] Handle action: `closed` → update state, merged_at, cycle_time
- [ ] Handle action: `reopened` → update state back to open
- [ ] Handle action: `edited` → update title
- [ ] Handle action: `synchronize` → update additions/deletions

### Data Mapping
- [ ] Map `payload["pull_request"]["number"]` → `github_pr_id`
- [ ] Map `payload["repository"]["full_name"]` → `github_repo`
- [ ] Map `payload["pull_request"]["title"]` → `title`
- [ ] Map `payload["pull_request"]["user"]["id"]` → lookup TeamMember
- [ ] Map `payload["pull_request"]["state"]` + `merged` → state
- [ ] Map timestamps → `pr_created_at`, `merged_at`
- [ ] Map `additions`, `deletions`

### Calculated Fields
- [ ] Calculate `cycle_time_hours` when merged (merged_at - pr_created_at)
- [ ] Detect `is_revert` from title (contains "Revert" or "revert")
- [ ] Detect `is_hotfix` from title/labels (contains "hotfix" or "fix")

### Edge Cases
- [ ] Handle author not in TeamMember (set author=None, log warning)
- [ ] Handle duplicate events (use `get_or_create` or `update_or_create`)

### Tests
- [ ] Test `opened` action creates PullRequest
- [ ] Test `closed` + merged updates state and merged_at
- [ ] Test `closed` + not merged updates state only
- [ ] Test cycle_time_hours calculated correctly
- [ ] Test is_revert detection
- [ ] Test is_hotfix detection
- [ ] Test unknown author handled gracefully

---

## 2.5.5 Pull Request Review Event Handler [Effort: S]

### Handler Implementation
- [ ] Create `handle_pull_request_review_event(team, payload)` function
- [ ] Handle action: `submitted` → create PRReview
- [ ] Handle action: `edited` → update PRReview
- [ ] Handle action: `dismissed` → delete or mark dismissed

### Data Mapping
- [ ] Map `payload["review"]["id"]` → for uniqueness
- [ ] Map `payload["pull_request"]["number"]` → lookup PullRequest
- [ ] Map `payload["review"]["user"]["id"]` → lookup TeamMember (reviewer)
- [ ] Map `payload["review"]["state"]` → state (approved/changes_requested/commented)
- [ ] Map `payload["review"]["submitted_at"]` → submitted_at

### PullRequest Updates
- [ ] Update `first_review_at` if this is the first review
- [ ] Calculate `review_time_hours` (first_review_at - pr_created_at)

### Edge Cases
- [ ] Handle review on PR that doesn't exist yet (create stub or skip)
- [ ] Handle reviewer not in TeamMember

### Tests
- [ ] Test `submitted` action creates PRReview
- [ ] Test first review updates PullRequest.first_review_at
- [ ] Test review_time_hours calculated correctly
- [ ] Test unknown reviewer handled gracefully
- [ ] Test review on unknown PR handled gracefully

---

## 2.5.6 Admin UI Updates [Effort: S]

### Repo Card Enhancement
- [ ] Show webhook status indicator on repo card (registered/not registered)
- [ ] Show error state if webhook_id is null after tracking

### Optional: Manual Re-register
- [ ] (Optional) Add "Re-register webhook" button for failed registrations
- [ ] (Optional) Create `github_repo_reregister_webhook` view

---

## Post-Implementation

### Documentation
- [ ] Update webhook-setup-tasks.md to mark complete
- [ ] Update webhook-setup-context.md with implementation notes
- [ ] Document webhook URL for production deployment

### Cleanup
- [ ] Run ruff format and lint
- [ ] Ensure all tests pass
- [ ] Remove any debug logging

---

## Completion Criteria

Phase 2.5 is complete when:
1. [ ] Webhooks auto-register when repos are tracked
2. [ ] Webhooks auto-delete when repos are untracked
3. [ ] Webhook endpoint validates signatures correctly
4. [ ] `pull_request` events create/update PullRequest records
5. [ ] `pull_request_review` events create PRReview records
6. [ ] Cycle time and review time calculated on merge
7. [ ] All tests pass
8. [ ] Code reviewed and merged

---

## Quick Reference

### New URLs to implement:
```
/webhooks/github/                              → github_webhook (NOT team-scoped)
```

### New files to create:
```
apps/integrations/services/github_webhooks.py  → Webhook service functions
apps/metrics/services/pr_processor.py          → PR event processing
apps/web/views/webhooks.py                     → Webhook endpoint (or add to existing)
apps/integrations/tests/test_github_webhooks.py → Webhook service tests
apps/metrics/tests/test_pr_processor.py        → PR processor tests
```

### Key imports:
```python
from apps.integrations.models import GitHubIntegration, TrackedRepository
from apps.integrations.services.encryption import decrypt
from apps.integrations.services.github_webhooks import (
    create_repository_webhook,
    delete_repository_webhook,
    validate_webhook_signature,
)
from apps.metrics.models import PullRequest, PRReview, TeamMember
from apps.metrics.services.pr_processor import (
    handle_pull_request_event,
    handle_pull_request_review_event,
)
```

### TDD Reminder:
Follow Red-Green-Refactor cycle for each feature:
1. Write failing test
2. Implement minimum code to pass
3. Refactor while keeping tests green
