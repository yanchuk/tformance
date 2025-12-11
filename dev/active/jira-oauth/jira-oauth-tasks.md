# Phase 3.1: Jira OAuth - Task Checklist

**Last Updated:** 2025-12-11

---

## Section 1: Configuration & Settings

### 1.1 Django Settings
- [ ] Add `JIRA_CLIENT_ID` to settings.py with env default
- [ ] Add `JIRA_CLIENT_SECRET` to settings.py with env default
- [ ] Update `.env.example` with Jira placeholders

**Effort:** S
**Dependencies:** None
**Acceptance Criteria:**
- Settings accessible via `settings.JIRA_CLIENT_ID`
- No errors when env vars are missing (empty default)

---

## Section 2: OAuth Service Layer (TDD)

### 2.1 Create jira_oauth.py with JiraOAuthError exception
- [ ] Create `apps/integrations/services/jira_oauth.py`
- [ ] Define `JiraOAuthError` exception class
- [ ] Add constants (AUTH_URL, TOKEN_URL, etc.)
- [ ] Write test for exception handling

**Effort:** S
**Dependencies:** None

### 2.2 State management functions
- [ ] Implement `create_oauth_state(team_id)` - reuse GitHub pattern
- [ ] Implement `verify_oauth_state(state)` - reuse GitHub pattern
- [ ] Write tests for valid/invalid state scenarios

**Effort:** S
**Dependencies:** 2.1

### 2.3 Authorization URL generation
- [ ] Implement `get_authorization_url(team_id, redirect_uri)`
- [ ] Include all required Atlassian params (audience, prompt, scope)
- [ ] Write tests verifying URL structure

**Effort:** S
**Dependencies:** 2.2

### 2.4 Token exchange
- [ ] Implement `exchange_code_for_token(code, redirect_uri)`
- [ ] Handle error responses
- [ ] Parse access_token, refresh_token, expires_in
- [ ] Write tests with mocked responses

**Effort:** M
**Dependencies:** 2.1

### 2.5 Token refresh
- [ ] Implement `refresh_access_token(refresh_token)`
- [ ] Handle rotating refresh token (new one returned)
- [ ] Write tests with mocked responses

**Effort:** M
**Dependencies:** 2.1

### 2.6 Accessible resources
- [ ] Implement `get_accessible_resources(access_token)`
- [ ] Parse site id, name, url, scopes
- [ ] Write tests with mocked responses

**Effort:** M
**Dependencies:** 2.1

---

## Section 3: Data Model (TDD)

### 3.1 JiraIntegration model
- [ ] Create model class in `models.py`
- [ ] Fields: credential (OneToOne), cloud_id, site_name, site_url
- [ ] Fields: last_sync_at, sync_status (reuse constants)
- [ ] Add indexes on cloud_id and sync_status
- [ ] Write model tests

**Effort:** M
**Dependencies:** None

### 3.2 Migration
- [ ] Generate migration with `make migrations`
- [ ] Review migration file
- [ ] Apply with `make migrate`

**Effort:** S
**Dependencies:** 3.1

### 3.3 Admin registration
- [ ] Add JiraIntegration to admin.py
- [ ] Configure list_display, search_fields

**Effort:** S
**Dependencies:** 3.1

### 3.4 Factory for testing
- [ ] Add `JiraIntegrationFactory` to factories.py
- [ ] Include related IntegrationCredential creation

**Effort:** S
**Dependencies:** 3.1

---

## Section 4: Views (TDD)

### 4.1 jira_connect view
- [ ] Create `jira_connect(request, team_slug)` view
- [ ] Require team admin role
- [ ] Check if already connected
- [ ] Generate authorization URL and redirect
- [ ] Write tests (auth, redirect, already-connected)

**Effort:** M
**Dependencies:** 2.3, 3.1

### 4.2 jira_callback view
- [ ] Create `jira_callback(request, team_slug)` view
- [ ] Require login
- [ ] Handle access_denied error
- [ ] Verify state parameter
- [ ] Exchange code for tokens
- [ ] Get accessible resources
- [ ] Create credential + integration (single site) OR redirect to selection (multiple)
- [ ] Write comprehensive tests

**Effort:** L
**Dependencies:** 2.4, 2.6, 3.1

### 4.3 jira_disconnect view
- [ ] Create `jira_disconnect(request, team_slug)` view
- [ ] Require team admin role + POST
- [ ] Delete JiraIntegration and associated credential
- [ ] Show success message
- [ ] Write tests

**Effort:** S
**Dependencies:** 3.1

### 4.4 jira_select_site view
- [ ] Create `jira_select_site(request, team_slug)` view
- [ ] Require login
- [ ] GET: Show available sites from credential metadata
- [ ] POST: Create JiraIntegration with selected site
- [ ] Write tests for both GET and POST

**Effort:** M
**Dependencies:** 3.1

---

## Section 5: URL Routing

### 5.1 Add Jira URL patterns
- [ ] Add `jira/connect/` → `jira_connect`
- [ ] Add `jira/callback/` → `jira_callback`
- [ ] Add `jira/disconnect/` → `jira_disconnect`
- [ ] Add `jira/select-site/` → `jira_select_site`
- [ ] Write URL resolution tests

**Effort:** S
**Dependencies:** 4.1, 4.2, 4.3, 4.4

---

## Section 6: Templates & UI

### 6.1 Update integrations home.html
- [ ] Add Jira connection card (similar to GitHub)
- [ ] Show connected status when JiraIntegration exists
- [ ] Show site name and URL when connected
- [ ] Add connect/disconnect buttons

**Effort:** M
**Dependencies:** 5.1

### 6.2 Create jira_select_site.html
- [ ] Create template similar to github select_org.html
- [ ] List sites with name, URL, avatar
- [ ] Radio button or card selection
- [ ] Submit button to select

**Effort:** M
**Dependencies:** 5.1

---

## Section 7: Token Refresh Integration

### 7.1 Create ensure_valid_token helper
- [ ] Create helper function in jira_oauth.py
- [ ] Check if token_expires_at is approaching (< 5 min)
- [ ] Auto-refresh if needed
- [ ] Update credential with new tokens
- [ ] Write tests for refresh scenarios

**Effort:** M
**Dependencies:** 2.5, 3.1

---

## Section 8: PR ↔ Jira Linkage (GitHub Sync Enhancement)

> **Note**: This section enhances Phase 2 (GitHub) to extract Jira keys from PR data.
> Can be done in parallel with Jira OAuth or as a prerequisite.

### 8.1 Add jira_key field to PullRequest model
- [ ] Add `jira_key = models.CharField(max_length=50, blank=True, db_index=True)`
- [ ] Add help_text: "Extracted Jira issue key from PR title/branch"
- [ ] Generate and apply migration
- [ ] Update PullRequestFactory

**Effort:** S
**Dependencies:** None

### 8.2 Create extract_jira_key helper function
- [ ] Create function in `apps/integrations/services/github_sync.py` or new `jira_utils.py`
- [ ] Regex pattern: `r'[A-Z][A-Z0-9]+-\d+'`
- [ ] Extract from title first, fall back to branch name
- [ ] Write tests for various formats (PROJ-123, ABC-1, etc.)

**Effort:** S
**Dependencies:** 8.1

### 8.3 Integrate jira_key extraction into PR sync
- [ ] Update `_convert_pr_to_dict()` to extract jira_key
- [ ] Update `sync_repository_history()` to save jira_key
- [ ] Update `sync_repository_incremental()` to save jira_key
- [ ] Write integration tests

**Effort:** M
**Dependencies:** 8.2

### 8.4 Backfill existing PRs (optional migration)
- [ ] Create data migration to extract jira_key from existing PR titles
- [ ] Run as one-time operation
- [ ] Verify with spot checks

**Effort:** S
**Dependencies:** 8.3

---

## Summary

| Section | Tasks | Effort |
|---------|-------|--------|
| 1. Configuration | 1 | S |
| 2. OAuth Service | 6 | S+S+S+M+M+M |
| 3. Data Model | 4 | M+S+S+S |
| 4. Views | 4 | M+L+S+M |
| 5. URL Routing | 1 | S |
| 6. Templates | 2 | M+M |
| 7. Token Refresh | 1 | M |
| 8. PR↔Jira Linkage | 4 | S+S+M+S |
| **Total** | **23** | |

**Estimated Total Effort:** Medium-Large (follows GitHub OAuth pattern closely)

---

## TDD Workflow Reminder

For each task:

1. **RED**: Write failing test first
2. **GREEN**: Write minimum code to pass
3. **REFACTOR**: Clean up while keeping tests green

Use TDD agents:
- `tdd-test-writer` - RED phase
- `tdd-implementer` - GREEN phase
- `tdd-refactorer` - REFACTOR phase
