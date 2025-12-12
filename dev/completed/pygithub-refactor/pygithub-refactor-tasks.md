# PyGithub Refactor - Task Checklist

> Last Updated: 2025-12-11

## Progress Summary

| Section | Status | Progress |
|---------|--------|----------|
| 1. Foundation | Not Started | 0/4 |
| 2. github_oauth.py | Not Started | 0/7 |
| 3. github_webhooks.py | Not Started | 0/3 |
| 4. github_sync.py | Not Started | 0/6 |
| 5. Cleanup | Not Started | 0/5 |

**Overall:** 0/25 tasks complete

---

## Section 1: Foundation - PyGithub Setup

- [ ] **1.1** Add PyGithub dependency
  - Add `PyGithub>=2.1.0` to pyproject.toml
  - Run `uv sync`
  - Verify: `python -c "from github import Github; print('OK')"`
  - **Effort:** S

- [ ] **1.2** Create `github_client.py`
  - Create `apps/integrations/services/github_client.py`
  - Implement `get_github_client(access_token: str) -> Github`
  - Handle token validation
  - **Effort:** S
  - **Depends on:** 1.1

- [ ] **1.3** Write tests for github_client
  - Test client creation with valid token
  - Test returns Github instance
  - Mock Github class
  - **Effort:** S
  - **Depends on:** 1.2

- [ ] **1.4** Define exception mapping
  - Create helper to convert PyGithub exceptions to GitHubOAuthError
  - Document mapping in context file
  - **Effort:** S
  - **Depends on:** 1.2

---

## Section 2: Refactor github_oauth.py

- [ ] **2.1** Refactor `get_authenticated_user()`
  - Use `Github(token).get_user()`
  - Convert PyGithub User to dict
  - Update tests to mock Github class
  - Verify: `make test ARGS='apps.integrations.tests.test_github_oauth::TestGetAuthenticatedUser'`
  - **Effort:** M
  - **Depends on:** 1.4

- [ ] **2.2** Refactor `get_user_organizations()`
  - Use `github.get_user().get_orgs()`
  - Convert PaginatedList to list of dicts
  - Update tests to mock Github class
  - Verify: `make test ARGS='apps.integrations.tests.test_github_oauth::TestGetUserOrganizations'`
  - **Effort:** M
  - **Depends on:** 2.1

- [ ] **2.3** Refactor `get_user_details()`
  - Use `Github(token).get_user(username)`
  - Convert PyGithub User to dict
  - Update tests to mock Github class
  - Verify: `make test ARGS='apps.integrations.tests.test_github_oauth::TestGetUserDetails'`
  - **Effort:** M
  - **Depends on:** 2.1

- [ ] **2.4** Refactor `get_organization_members()`
  - Use `github.get_organization(org_slug).get_members()`
  - Convert PaginatedList to list of dicts
  - Update pagination tests (no longer needed - PyGithub handles it)
  - Verify: `make test ARGS='apps.integrations.tests.test_github_oauth::TestGetOrganizationMembers'`
  - **Effort:** M
  - **Depends on:** 2.1

- [ ] **2.5** Refactor `get_organization_repositories()`
  - Use `github.get_organization(org_slug).get_repos()`
  - Convert PaginatedList to list of dicts
  - Preserve `exclude_archived` filter logic
  - Update pagination tests
  - Verify: `make test ARGS='apps.integrations.tests.test_github_oauth::TestGetOrganizationRepositories'`
  - **Effort:** M
  - **Depends on:** 2.1

- [ ] **2.6** Remove dead code from github_oauth.py
  - Delete `_make_github_api_request()`
  - Delete `_make_paginated_github_api_request()`
  - Delete `_parse_next_link()`
  - Remove unused constants if any
  - Verify no import errors
  - **Effort:** S
  - **Depends on:** 2.5

- [ ] **2.7** Final verification for github_oauth.py
  - Run all oauth tests: `make test ARGS='apps.integrations.tests.test_github_oauth'`
  - All 77 tests must pass
  - **Effort:** S
  - **Depends on:** 2.6

---

## Section 3: Refactor github_webhooks.py

- [ ] **3.1** Refactor `create_repository_webhook()`
  - Use `github.get_repo(full_name).create_hook()`
  - Return `hook.id`
  - Map exceptions to GitHubOAuthError
  - Update tests to mock Github class
  - Verify: `make test ARGS='apps.integrations.tests.test_github_webhooks::TestCreateRepositoryWebhook'`
  - **Effort:** M
  - **Depends on:** 1.4

- [ ] **3.2** Refactor `delete_repository_webhook()`
  - Use `repo.get_hook(id).delete()`
  - Handle 404 as success (idempotent)
  - Map exceptions to GitHubOAuthError
  - Update tests to mock Github class
  - Verify: `make test ARGS='apps.integrations.tests.test_github_webhooks::TestDeleteRepositoryWebhook'`
  - **Effort:** M
  - **Depends on:** 3.1

- [ ] **3.3** Final verification for github_webhooks.py
  - Run all webhook tests: `make test ARGS='apps.integrations.tests.test_github_webhooks'`
  - All 18 tests must pass
  - **Effort:** S
  - **Depends on:** 3.2

---

## Section 4: Refactor github_sync.py

- [ ] **4.1** Refactor `get_repository_pull_requests()`
  - Use `github.get_repo(full_name).get_pulls(state=state)`
  - Convert PaginatedList to list of dicts
  - Update tests to mock Github class
  - Verify tests pass
  - **Effort:** M
  - **Depends on:** 1.4

- [ ] **4.2** Refactor `get_pull_request_reviews()`
  - Use `repo.get_pull(number).get_reviews()`
  - Convert PaginatedList to list of dicts
  - Update tests to mock Github class
  - Verify tests pass
  - **Effort:** M
  - **Depends on:** 4.1

- [ ] **4.3** Update `sync_repository_history()`
  - Use refactored `get_repository_pull_requests()`
  - Ensure dict format matches what `_map_github_pr_to_fields()` expects
  - Verify integration with processors.py
  - Run sync tests
  - **Effort:** M
  - **Depends on:** 4.2

- [ ] **4.4** Update `_sync_pr_reviews()`
  - Use refactored `get_pull_request_reviews()`
  - Ensure dict format matches what review sync expects
  - Verify review data is correctly processed
  - **Effort:** S
  - **Depends on:** 4.3

- [ ] **4.5** Remove duplicate pagination helper
  - Delete `_make_paginated_github_request()` from github_sync.py
  - Verify no import errors
  - **Effort:** S
  - **Depends on:** 4.4

- [ ] **4.6** Final verification for github_sync.py
  - Run all sync tests: `make test ARGS='apps.integrations.tests.test_github_sync'`
  - All 24 tests must pass
  - **Effort:** S
  - **Depends on:** 4.5

---

## Section 5: Cleanup & Verification

- [ ] **5.1** Remove `requests` import from services
  - Check github_oauth.py - remove `import requests` (keep only for exchange_code_for_token)
  - Check github_webhooks.py - remove `import requests`
  - Check github_sync.py - remove `import requests`
  - **Effort:** S
  - **Depends on:** 4.6

- [ ] **5.2** Run full test suite
  - Command: `make test ARGS='--keepdb'`
  - All 560+ tests must pass
  - **Effort:** S
  - **Depends on:** 5.1

- [ ] **5.3** Run lint
  - Command: `make ruff`
  - No errors
  - **Effort:** S
  - **Depends on:** 5.2

- [ ] **5.4** Manual smoke test
  - Start dev server: `make dev`
  - Test GitHub OAuth flow
  - Test organization discovery
  - Test repository selection
  - Test webhook creation
  - Test manual sync
  - **Effort:** M
  - **Depends on:** 5.3

- [ ] **5.5** Update documentation
  - Update `pygithub-refactor-context.md` with completion status
  - Archive to `dev/completed/` if done
  - Note any learnings or issues
  - **Effort:** S
  - **Depends on:** 5.4

---

## TDD Cycle Tracking

Use this section to track RED-GREEN-REFACTOR cycles during implementation.

| Cycle | Function | RED (Test) | GREEN (Impl) | REFACTOR | Notes |
|-------|----------|------------|--------------|----------|-------|
| 1 | github_client | | | | |
| 2 | get_authenticated_user | | | | |
| 3 | get_user_organizations | | | | |
| 4 | get_user_details | | | | |
| 5 | get_organization_members | | | | |
| 6 | get_organization_repositories | | | | |
| 7 | create_repository_webhook | | | | |
| 8 | delete_repository_webhook | | | | |
| 9 | get_repository_pull_requests | | | | |
| 10 | get_pull_request_reviews | | | | |
| 11 | sync_repository_history | | | | |

---

## Completion Checklist

Before marking PyGithub Refactor complete:

- [ ] PyGithub installed and working
- [ ] All github_oauth.py functions refactored
- [ ] All github_webhooks.py functions refactored
- [ ] All github_sync.py functions refactored
- [ ] Dead code removed
- [ ] All 560+ tests pass
- [ ] No lint errors
- [ ] Manual smoke test passed
- [ ] Documentation updated
- [ ] Ready for Phase 2.6: Incremental Sync

---

## Notes

*Add implementation notes here as you work:*

-

---

## After Completion

Once this refactor is complete, proceed to:
- **Phase 2.6: Incremental Sync** - Add daily Celery task with `since` parameter
- See `dev/active/incremental-sync/` for that plan
