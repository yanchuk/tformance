# GitHub App Migration - Tasks

**Last Updated:** 2026-01-01
**Status:** In Progress

---

## Phase 1: Infrastructure & Models

### 1.1 Settings Configuration
- [ ] Add `GITHUB_APP_ID` to settings.py
- [ ] Add `GITHUB_APP_PRIVATE_KEY` to settings.py
- [ ] Add `GITHUB_APP_WEBHOOK_SECRET` to settings.py
- [ ] Add `GITHUB_APP_CLIENT_ID` to settings.py
- [ ] Add `GITHUB_APP_CLIENT_SECRET` to settings.py
- [ ] Update `.env.example` with new variables

### 1.2 GitHubAppInstallation Model (TDD)
- [ ] Write test: `test_github_app_installation_model_creation`
- [ ] Write test: `test_github_app_installation_unique_installation_id`
- [ ] Write test: `test_github_app_installation_team_relationship`
- [ ] Create `GitHubAppInstallation` model in `models.py`
- [ ] Create migration
- [ ] Run migration
- [ ] Add factory: `GitHubAppInstallationFactory`

### 1.3 GitHubAppService (TDD)
- [ ] Write test: `test_get_jwt_returns_valid_jwt`
- [ ] Write test: `test_get_jwt_expires_in_10_minutes`
- [ ] Write test: `test_get_installation_token_success`
- [ ] Write test: `test_get_installation_token_not_found`
- [ ] Write test: `test_get_installation_client_returns_github_instance`
- [ ] Write test: `test_get_installation_returns_dict`
- [ ] Write test: `test_get_installation_repositories_returns_list`
- [ ] Create `apps/integrations/services/github_app.py`
- [ ] Implement `GitHubAppService.__init__`
- [ ] Implement `GitHubAppService.get_jwt`
- [ ] Implement `GitHubAppService.get_installation_token`
- [ ] Implement `GitHubAppService.get_installation_client`
- [ ] Implement `GitHubAppService.get_installation`
- [ ] Implement `GitHubAppService.get_installation_repositories`
- [ ] Add `GitHubAppError` exception class

---

## Phase 2: Webhook Infrastructure

### 2.1 Webhook Handlers (TDD)
- [ ] Write test: `test_handle_installation_created`
- [ ] Write test: `test_handle_installation_deleted`
- [ ] Write test: `test_handle_installation_suspended`
- [ ] Write test: `test_handle_installation_unsuspended`
- [ ] Write test: `test_handle_installation_repositories_added`
- [ ] Write test: `test_handle_installation_repositories_removed`
- [ ] Create `apps/integrations/webhooks/github_app.py`
- [ ] Implement `handle_installation_event`
- [ ] Implement `handle_installation_repositories_event`

### 2.2 Webhook Endpoint (TDD)
- [ ] Write test: `test_webhook_signature_verification`
- [ ] Write test: `test_webhook_invalid_signature_returns_403`
- [ ] Write test: `test_webhook_routes_to_correct_handler`
- [ ] Add webhook view to `apps/web/views.py`
- [ ] Add URL route: `/webhooks/github/app/`
- [ ] Test webhook endpoint manually with ngrok

---

## Phase 3: Onboarding Flow

### 3.1 Installation Initiation (TDD)
- [ ] Write test: `test_github_app_install_redirects_to_github`
- [ ] Write test: `test_github_app_install_includes_state`
- [ ] Add `github_app_install` view to onboarding
- [ ] Add URL route

### 3.2 Installation Callback (TDD)
- [ ] Write test: `test_github_app_callback_creates_team`
- [ ] Write test: `test_github_app_callback_creates_installation`
- [ ] Write test: `test_github_app_callback_invalid_installation_id`
- [ ] Write test: `test_github_app_callback_syncs_members`
- [ ] Add `github_app_callback` view to onboarding
- [ ] Add URL route
- [ ] Integrate with existing team creation logic

### 3.3 Repository Selection (TDD)
- [ ] Write test: `test_select_repos_uses_installation_token`
- [ ] Write test: `test_fetch_repos_uses_installation_client`
- [ ] Update `select_repositories` view to support GitHub App
- [ ] Update `fetch_repos` HTMX endpoint
- [ ] Test full onboarding flow manually

---

## Phase 4: Sync Task Updates

### 4.1 Client Resolution (TDD)
- [ ] Write test: `test_get_github_client_prefers_app_installation`
- [ ] Write test: `test_get_github_client_falls_back_to_oauth`
- [ ] Write test: `test_get_github_client_no_connection_raises`
- [ ] Update `get_github_client_for_team` in `github_client.py`

### 4.2 Sync Tasks (TDD)
- [ ] Write test: `test_sync_repository_uses_installation_token`
- [ ] Write test: `test_sync_pr_uses_installation_token`
- [ ] Update `sync_repository_initial_task`
- [ ] Update `sync_repository_manual_task`
- [ ] Update PR sync tasks
- [ ] Verify existing tests still pass

---

## Phase 5: Integration Views

### 5.1 Installation Status View (TDD)
- [ ] Write test: `test_installation_status_shows_details`
- [ ] Write test: `test_installation_status_shows_repos`
- [ ] Create status view for GitHub App installation
- [ ] Add template

### 5.2 Reconfigure Installation
- [ ] Add link to GitHub App settings page
- [ ] Handle installation updates via webhook

---

## Phase 6: Documentation & Cleanup

### 6.1 Documentation
- [ ] Update `CLAUDE.md` with GitHub App info
- [ ] Update `dev/guides/AUTHENTICATION-FLOWS.md`
- [ ] Add inline code documentation

### 6.2 Admin Interface
- [ ] Register `GitHubAppInstallation` in admin
- [ ] Add filters and search

### 6.3 Verification
- [ ] Run full test suite: `make test`
- [ ] Run linting: `make ruff`
- [ ] Manual E2E test with real GitHub App

---

## Completion Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Manual onboarding flow works
- [ ] Webhooks are received and processed
- [ ] Sync tasks use installation tokens
- [ ] OAuth still works for Copilot
- [ ] Documentation updated

---

## Notes

- **Copilot**: Not part of this migration (handled separately)
- **Existing OAuth**: Keep working for Copilot and legacy
- **Migration of existing teams**: Future phase (not in scope)
