# Phase 3.1: Jira OAuth - Task Checklist

**Last Updated:** 2025-12-11
**Status:** COMPLETE

---

## Section 1: Configuration & Settings

### 1.1 Django Settings
- [x] Add `JIRA_CLIENT_ID` to settings.py with env default
- [x] Add `JIRA_CLIENT_SECRET` to settings.py with env default
- [x] Update `.env.example` with Jira placeholders

**Status:** COMPLETE

---

## Section 2: OAuth Service Layer (TDD)

### 2.1 Create jira_oauth.py with JiraOAuthError exception
- [x] Create `apps/integrations/services/jira_oauth.py`
- [x] Define `JiraOAuthError` exception class
- [x] Add constants (AUTH_URL, TOKEN_URL, etc.)
- [x] Write test for exception handling

### 2.2 State management functions
- [x] Implement `create_oauth_state(team_id)` - reuse GitHub pattern
- [x] Implement `verify_oauth_state(state)` - reuse GitHub pattern
- [x] Write tests for valid/invalid state scenarios

### 2.3 Authorization URL generation
- [x] Implement `get_authorization_url(team_id, redirect_uri)`
- [x] Include all required Atlassian params (audience, prompt, scope)
- [x] Write tests verifying URL structure

### 2.4 Token exchange
- [x] Implement `exchange_code_for_token(code, redirect_uri)`
- [x] Handle error responses
- [x] Parse access_token, refresh_token, expires_in
- [x] Write tests with mocked responses

### 2.5 Token refresh
- [x] Implement `refresh_access_token(refresh_token)`
- [x] Handle rotating refresh token (new one returned)
- [x] Write tests with mocked responses

### 2.6 Accessible resources
- [x] Implement `get_accessible_resources(access_token)`
- [x] Parse site id, name, url, scopes
- [x] Write tests with mocked responses

**Status:** COMPLETE (29 tests)

---

## Section 3: Data Model (TDD)

### 3.1 JiraIntegration model
- [x] Create model class in `models.py`
- [x] Fields: credential (OneToOne), cloud_id, site_name, site_url
- [x] Fields: last_sync_at, sync_status (reuse constants)
- [x] Add indexes on cloud_id and sync_status
- [x] Write model tests

### 3.2 Migration
- [x] Generate migration with `make migrations`
- [x] Review migration file
- [x] Apply with `make migrate`

### 3.3 Admin registration
- [x] Add JiraIntegration to admin.py
- [x] Configure list_display, search_fields

### 3.4 Factory for testing
- [x] Add `JiraIntegrationFactory` to factories.py
- [x] Include related IntegrationCredential creation

**Status:** COMPLETE (12 tests)

---

## Section 4: Views (TDD)

### 4.1 jira_connect view
- [x] Create `jira_connect(request, team_slug)` view
- [x] Require team admin role
- [x] Check if already connected
- [x] Generate authorization URL and redirect
- [x] Write tests (auth, redirect, already-connected)

### 4.2 jira_callback view
- [x] Create `jira_callback(request, team_slug)` view
- [x] Require login
- [x] Handle access_denied error
- [x] Verify state parameter
- [x] Exchange code for tokens
- [x] Get accessible resources
- [x] Create credential + integration (single site) OR redirect to selection (multiple)
- [x] Write comprehensive tests

### 4.3 jira_disconnect view
- [x] Create `jira_disconnect(request, team_slug)` view
- [x] Require team admin role + POST
- [x] Delete JiraIntegration and associated credential
- [x] Show success message
- [x] Write tests

### 4.4 jira_select_site view
- [x] Create `jira_select_site(request, team_slug)` view
- [x] Require login
- [x] GET: Show available sites from credential metadata
- [x] POST: Create JiraIntegration with selected site
- [x] Write tests for both GET and POST

**Status:** COMPLETE (36 tests)

---

## Section 5: URL Routing

### 5.1 Add Jira URL patterns
- [x] Add `jira/connect/` → `jira_connect`
- [x] Add `jira/callback/` → `jira_callback`
- [x] Add `jira/disconnect/` → `jira_disconnect`
- [x] Add `jira/select-site/` → `jira_select_site`
- [x] Write URL resolution tests

**Status:** COMPLETE (included in Section 4)

---

## Section 6: Templates & UI

### 6.1 Update integrations home.html
- [ ] Add Jira connection card (similar to GitHub) - DEFERRED to Phase 3.2

### 6.2 Create jira_select_site.html
- [x] Create template similar to github select_org.html
- [x] List sites with name, URL, avatar
- [x] Radio button or card selection
- [x] Submit button to select

**Status:** PARTIAL (minimal template created, full styling in Phase 3.2)

---

## Section 7: Token Refresh Integration

### 7.1 Create ensure_valid_token helper
- [x] Create helper function in jira_oauth.py
- [x] Check if token_expires_at is approaching (< 5 min)
- [x] Auto-refresh if needed
- [x] Update credential with new tokens
- [x] Write tests for refresh scenarios

**Status:** COMPLETE (7 tests)

---

## Section 8: PR ↔ Jira Linkage (GitHub Sync Enhancement)

> **Note**: Completed in earlier session as prerequisite.

### 8.1 Add jira_key field to PullRequest model
- [x] Add `jira_key = models.CharField(max_length=50, blank=True, db_index=True)`
- [x] Add help_text: "Extracted Jira issue key from PR title/branch"
- [x] Generate and apply migration
- [x] Update PullRequestFactory

### 8.2 Create extract_jira_key helper function
- [x] Create function in `apps/integrations/services/jira_utils.py`
- [x] Regex pattern: `r'[A-Z][A-Z0-9]+-\d+'`
- [x] Extract from title first, fall back to branch name
- [x] Write tests for various formats (PROJ-123, ABC-1, etc.)

### 8.3 Integrate jira_key extraction into PR sync
- [x] Update `_convert_pr_to_dict()` to extract jira_key
- [x] Update `sync_repository_history()` to save jira_key
- [x] Update `sync_repository_incremental()` to save jira_key
- [x] Write integration tests

### 8.4 Backfill existing PRs (optional migration)
- [x] Create data migration to extract jira_key from existing PR titles
- [x] Run as one-time operation
- [x] Verify with spot checks

**Status:** COMPLETE (35 tests)

---

## Summary

| Section | Tasks | Status | Tests |
|---------|-------|--------|-------|
| 1. Configuration | 1 | COMPLETE | - |
| 2. OAuth Service | 6 | COMPLETE | 29 |
| 3. Data Model | 4 | COMPLETE | 12 |
| 4. Views | 4 | COMPLETE | 36 |
| 5. URL Routing | 1 | COMPLETE | - |
| 6. Templates | 2 | PARTIAL | - |
| 7. Token Refresh | 1 | COMPLETE | 7 |
| 8. PR↔Jira Linkage | 4 | COMPLETE | 35 |
| **Total** | **23** | **COMPLETE** | **119** |

---

## Final Test Results

```bash
make test ARGS='--keepdb'
# Ran 707 tests in 13.453s - OK

make ruff
# All checks passed!
```

---

## Next Phase: 3.2 Jira Projects Sync

See IMPLEMENTATION-PLAN.md for next steps.
