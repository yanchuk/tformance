# Phase 2: GitHub Integration - Task Checklist

> Last Updated: 2025-12-10

## Overview

Total tasks: 38
Estimated effort: Large (Phase complexity: High)

---

## 2.1 Integration App Foundation [Effort: M] ✅ COMPLETE

### Setup
- [x] Create `apps/integrations/` Django app structure
- [x] Register app in `INSTALLED_APPS` (settings.py)
- [x] Create `apps/integrations/services/` package
- [x] Create `apps/integrations/webhooks/` package

### Models
- [x] Implement `IntegrationCredential` model
  - Provider field (github, jira, slack)
  - Encrypted access_token and refresh_token
  - Token expiration tracking
  - Scopes as JSONField
  - Connected timestamp and user reference
- [x] Implement `GitHubIntegration` model
  - OneToOne to IntegrationCredential
  - Organization slug and ID
  - Webhook secret for verification
  - Sync status and last_sync_at
- [x] Implement `TrackedRepository` model
  - ForeignKey to GitHubIntegration
  - GitHub repo ID and full_name
  - Active flag
  - Webhook ID reference
- [x] Create and apply migrations

### Encryption Service
- [x] Implement `apps/integrations/services/encryption.py`
  - Fernet-based encryption for tokens
  - Key from settings
  - encrypt() and decrypt() functions

### Admin
- [x] Register models in admin.py
- [x] Add read-only token display (masked)

### Tests
- [x] Test encryption service (19 tests)
- [x] Test model creation and constraints (33 tests)
- [x] Test team scoping

---

## 2.2 GitHub OAuth Flow [Effort: L]

### Configuration
- [ ] Document GitHub OAuth App creation steps
- [ ] Add GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET to settings
- [ ] Configure django-allauth GitHub provider

### Views
- [ ] Create `github_connect` view - initiates OAuth
- [ ] Create `github_callback` view - handles callback
- [ ] Create `github_disconnect` view - removes integration

### OAuth Logic
- [ ] Implement `apps/integrations/services/github_oauth.py`
  - Exchange code for token
  - Fetch authenticated user info
  - Determine organization from user orgs

### Token Storage
- [ ] Store encrypted token in IntegrationCredential
- [ ] Create GitHubIntegration record
- [ ] Handle token refresh (if needed)

### URL Configuration
- [ ] Add team_urlpatterns for OAuth views
- [ ] Configure callback URL handling

### UI
- [ ] Create connect integration button template
- [ ] Create success/error states
- [ ] Add disconnect confirmation

### Tests
- [ ] Test OAuth initiation redirect
- [ ] Test callback handling (mocked GitHub)
- [ ] Test token storage encryption
- [ ] Test error cases (invalid code, network error)

---

## 2.3 Organization Discovery [Effort: M]

### GitHub Client
- [ ] Implement `apps/integrations/services/github_client.py`
  - Authenticated HTTP requests
  - Rate limit header tracking
  - Pagination handling
  - Error response handling

### Org Member Sync
- [ ] Fetch organization members from GitHub API
- [ ] Create/update TeamMember records
  - Match by github_id (primary)
  - Match by email (secondary)
  - Update existing records if found
- [ ] Handle private emails (request additional scope or skip)

### UI
- [ ] Display discovered team members
- [ ] Show match status (new, existing, unmatched)
- [ ] Allow manual email matching for unmatched users

### Tests
- [ ] Test org member fetching
- [ ] Test TeamMember creation
- [ ] Test matching logic
- [ ] Test pagination handling

---

## 2.4 Repository Selection [Effort: S]

### Repository Listing
- [ ] Fetch available repositories from GitHub API
- [ ] Filter by organization
- [ ] Handle pagination for large orgs

### Repository Selection UI
- [ ] Create repository list view
- [ ] Checkbox selection for repos to track
- [ ] Show repo metadata (name, private/public, activity)

### Storage
- [ ] Create TrackedRepository records for selected repos
- [ ] Handle deselection (soft delete with is_active=False)

### Tests
- [ ] Test repo listing
- [ ] Test repo selection/deselection
- [ ] Test TrackedRepository model

---

## 2.5 Webhook Setup [Effort: M]

### Webhook Endpoint
- [ ] Create `/webhooks/github/` endpoint
- [ ] Exempt from CSRF (using GitHub signature instead)
- [ ] Route to handler based on event type

### Signature Verification
- [ ] Implement `apps/integrations/webhooks/signature.py`
  - HMAC-SHA256 verification
  - Timing-safe comparison

### Event Handlers
- [ ] Implement `pull_request` event handler
  - Create/update PullRequest record
  - Calculate metrics on merge
- [ ] Implement `pull_request_review` event handler
  - Create PRReview record
  - Update first_review_at on PR

### Webhook Registration
- [ ] Create webhook on GitHub for each tracked repo
- [ ] Store webhook_id on TrackedRepository
- [ ] Handle webhook creation errors

### Tests
- [ ] Test signature verification
- [ ] Test pull_request event handling
- [ ] Test pull_request_review event handling
- [ ] Test invalid signature rejection

---

## 2.6 Historical Data Sync [Effort: L]

### PR Sync Service
- [ ] Implement `apps/integrations/services/github_sync.py`
  - Fetch PRs for date range
  - Fetch reviews per PR
  - Fetch commits per PR
  - Calculate cycle_time_hours
  - Calculate review_time_hours
  - Detect reverts (title/message patterns)
  - Detect hotfixes (branch name patterns)

### Author Matching
- [ ] Match PR author to TeamMember by github_id
- [ ] Handle unknown authors (create TeamMember or skip)

### Celery Task
- [ ] Create `sync_github_historical` task
- [ ] Accept team_id and date range params
- [ ] Update sync status during execution
- [ ] Handle errors with retry logic

### Progress Tracking
- [ ] Update GitHubIntegration.sync_status
- [ ] Track repos synced / total
- [ ] Store last successful sync timestamp

### Tests
- [ ] Test PR data transformation
- [ ] Test cycle time calculation
- [ ] Test review time calculation
- [ ] Test revert detection
- [ ] Test hotfix detection
- [ ] Test Celery task execution

---

## 2.7 Incremental Sync [Effort: M]

### Delta Sync Logic
- [ ] Fetch PRs updated since last_sync_at
- [ ] Use `since` parameter in GitHub API
- [ ] Handle PRs that moved between states

### Celery Beat Schedule
- [ ] Add periodic task to celery beat schedule
- [ ] Configure time (e.g., 2 AM in team timezone)
- [ ] Run for all teams with active GitHub integration

### Sync Status UI
- [ ] Show last sync time
- [ ] Show sync status (pending, running, complete, error)
- [ ] Manual sync trigger button

### Error Handling
- [ ] Implement retry with exponential backoff
- [ ] Alert on repeated failures
- [ ] Log detailed error info

### Tests
- [ ] Test delta sync logic
- [ ] Test Celery beat task
- [ ] Test error handling and retries

---

## Post-Implementation

### Documentation
- [ ] Update CLAUDE.md with integrations app info
- [ ] Create setup guide for GitHub OAuth App
- [ ] Document webhook configuration for production

### Cleanup
- [ ] Remove any debug logging
- [ ] Verify all tests pass
- [ ] Run ruff format and lint

---

## Completion Criteria

Phase 2 is complete when:
1. [ ] Team can connect GitHub via OAuth
2. [ ] Team members are discovered from GitHub org
3. [ ] Repositories can be selected for tracking
4. [ ] PRs sync to database (historical and incremental)
5. [ ] Webhooks update PRs in real-time
6. [ ] All tests pass
7. [ ] Code reviewed and merged to main
