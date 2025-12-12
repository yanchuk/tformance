# Phase 2: GitHub Integration - Implementation Plan

> Last Updated: 2025-12-10

## Executive Summary

This phase implements the GitHub integration for tformance, enabling teams to connect their GitHub organization, discover team members, select repositories to track, and sync pull request data. This is a **high complexity** phase that establishes the foundation for all delivery metrics.

### Key Outcomes
- GitHub OAuth flow with secure token storage
- Automatic team member discovery from GitHub org
- Repository selection and configuration
- Real-time PR updates via webhooks
- Historical and incremental data sync

### Dependencies
- Phase 0 (Foundation) - ✅ Complete
- Phase 1 (Core Data Models) - ✅ Complete

---

## Current State Analysis

### Existing Infrastructure
- **Team model**: `apps/teams/models.py` - handles multi-tenancy
- **TeamMember model**: `apps/metrics/models.py` - already has `github_username`, `github_id` fields
- **PullRequest model**: `apps/metrics/models.py` - complete schema for PR data
- **PRReview model**: `apps/metrics/models.py` - tracks reviews
- **Commit model**: `apps/metrics/models.py` - tracks commits
- **Celery**: Configured for background jobs
- **Redis**: Available for caching

### Missing Components
- No `apps/integrations/` app for OAuth/integration logic
- No GitHub OAuth provider configured in django-allauth
- No webhook endpoint for GitHub events
- No sync service for fetching historical data
- No Team integration settings model

---

## Technical Architecture

### OAuth Flow
```
User clicks "Connect GitHub"
    │
    ▼
Redirect to GitHub OAuth
(scopes: read:org, repo, read:user)
    │
    ▼
GitHub redirects back with code
    │
    ▼
Exchange code for access token
    │
    ▼
Store encrypted token in IntegrationCredential
    │
    ▼
Fetch org members, create TeamMember records
    │
    ▼
Redirect to repository selection
```

### Data Sync Flow
```
Trigger: Webhook (real-time) OR Celery beat (daily)
    │
    ▼
For each configured repo:
  - Fetch PRs (open, merged since last sync)
  - Fetch reviews per PR
  - Fetch commits per PR
    │
    ▼
Match authors to TeamMembers (by github_id)
    │
    ▼
Calculate metrics (cycle_time, review_time)
    │
    ▼
Upsert to database
```

### GitHub API Scopes Required
| Scope | Purpose |
|-------|---------|
| `read:org` | List org members, teams |
| `repo` | Read repository data, PRs, commits |
| `read:user` | Read user profile data |

---

## Implementation Phases

### Phase 2.1: Integration App Foundation (Effort: M)
Create the integrations app with models for storing OAuth credentials and integration configuration.

**Deliverables:**
- New `apps/integrations/` Django app
- `IntegrationCredential` model (encrypted token storage)
- `GitHubIntegration` model (org settings, repo config)
- Admin interface for debugging

### Phase 2.2: GitHub OAuth Flow (Effort: L)
Implement the OAuth authorization flow using django-allauth's social auth.

**Deliverables:**
- GitHub OAuth app registration guide
- Social app configuration in Django
- Custom adapter for scope handling
- OAuth callback handling
- Token storage post-authentication

### Phase 2.3: Organization Discovery (Effort: M)
After OAuth, fetch org members and create TeamMember records.

**Deliverables:**
- GitHub API client service
- Org member fetching logic
- TeamMember creation/matching
- UI showing discovered members

### Phase 2.4: Repository Selection (Effort: S)
Allow admins to select which repositories to track.

**Deliverables:**
- Repo listing API endpoint
- Repository selection UI
- TrackedRepository model
- Repository configuration storage

### Phase 2.5: Webhook Setup (Effort: M)
Register webhooks for real-time PR events.

**Deliverables:**
- Webhook endpoint (`/webhooks/github/`)
- Webhook registration service
- `pull_request` event handler
- `pull_request_review` event handler
- Webhook signature verification

### Phase 2.6: Historical Data Sync (Effort: L)
Fetch existing PRs for initial data population.

**Deliverables:**
- PR fetching service
- Commit fetching per PR
- Review fetching per PR
- Cycle time calculation
- Revert/hotfix detection
- Celery task for background sync

### Phase 2.7: Incremental Sync (Effort: M)
Daily sync job to fetch updates.

**Deliverables:**
- Celery beat schedule
- Delta sync logic (since last sync)
- Sync status tracking
- Error handling and retry logic

---

## Data Models

### New Models (apps/integrations/)

```python
class IntegrationCredential(BaseTeamModel):
    """Encrypted storage for OAuth tokens."""
    provider = models.CharField(max_length=50)  # 'github', 'jira', 'slack'
    access_token = models.TextField()  # encrypted
    refresh_token = models.TextField(blank=True)  # encrypted
    token_expires_at = models.DateTimeField(null=True)
    scopes = models.JSONField(default=list)
    connected_at = models.DateTimeField(auto_now_add=True)
    connected_by = models.ForeignKey(User, on_delete=models.SET_NULL)

class GitHubIntegration(BaseTeamModel):
    """GitHub-specific integration settings."""
    credential = models.OneToOneField(IntegrationCredential, on_delete=models.CASCADE)
    organization_slug = models.CharField(max_length=100)
    organization_id = models.BigIntegerField()
    webhook_secret = models.CharField(max_length=100)  # for verifying webhooks
    last_sync_at = models.DateTimeField(null=True)
    sync_status = models.CharField(max_length=20)  # pending, syncing, complete, error

class TrackedRepository(BaseTeamModel):
    """Repositories selected for tracking."""
    integration = models.ForeignKey(GitHubIntegration, on_delete=models.CASCADE)
    github_repo_id = models.BigIntegerField()
    full_name = models.CharField(max_length=255)  # owner/repo
    is_active = models.BooleanField(default=True)
    webhook_id = models.BigIntegerField(null=True)
    last_sync_at = models.DateTimeField(null=True)
```

---

## API Endpoints

### Integration Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/a/{team}/integrations/` | List integrations status |
| POST | `/a/{team}/integrations/github/connect/` | Initiate OAuth |
| GET | `/a/{team}/integrations/github/callback/` | OAuth callback |
| DELETE | `/a/{team}/integrations/github/disconnect/` | Remove integration |

### Repository Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/a/{team}/integrations/github/repos/` | List available repos |
| POST | `/a/{team}/integrations/github/repos/` | Select repos to track |
| DELETE | `/a/{team}/integrations/github/repos/{id}/` | Stop tracking repo |

### Webhooks
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/webhooks/github/` | Receive GitHub events |

### Sync Management
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/a/{team}/integrations/github/sync/` | Trigger manual sync |
| GET | `/a/{team}/integrations/github/sync/status/` | Check sync status |

---

## Risk Assessment

### High Risk
1. **Rate Limiting**: GitHub API has rate limits (5000/hr authenticated)
   - Mitigation: Implement exponential backoff, cache responses, batch requests

2. **Token Expiration**: OAuth tokens may expire
   - Mitigation: Store refresh tokens, implement auto-refresh logic

3. **Webhook Reliability**: Events may be missed or duplicated
   - Mitigation: Implement idempotent handlers, use incremental sync as backup

### Medium Risk
1. **Large Organizations**: Orgs with 1000+ repos may timeout
   - Mitigation: Paginate all API calls, use background tasks

2. **User Matching**: Not all GitHub users may have emails
   - Mitigation: Fall back to username matching, manual resolution UI

### Low Risk
1. **Schema Changes**: GitHub API v3 is stable
   - Mitigation: Use version headers, test against API changes

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| OAuth completion rate | >90% | Teams that complete OAuth flow |
| Sync reliability | >99% | Successful sync jobs / total |
| PR data accuracy | 100% | Spot checks against GitHub UI |
| Webhook latency | <5 min | Time from PR merge to database |

---

## Security Considerations

1. **Token Encryption**: All OAuth tokens encrypted at rest using Fernet
2. **Webhook Verification**: Validate webhook signatures using HMAC-SHA256
3. **Scope Minimization**: Request only necessary GitHub scopes
4. **Audit Logging**: Log all OAuth events, sync operations
5. **Token Revocation**: Provide clear disconnect flow that revokes tokens

---

## Testing Strategy

### Unit Tests
- Token encryption/decryption
- PR data transformation
- Cycle time calculation
- Webhook signature verification

### Integration Tests
- OAuth flow (mocked GitHub)
- API sync (mocked GitHub responses)
- Webhook handling (test payloads)

### End-to-End Tests
- Full OAuth flow with test GitHub org
- Sync with real test repository
- Webhook with actual GitHub events

---

## Timeline Considerations

**Critical Path:**
1. Integration app + models must be first
2. OAuth flow blocks all other work
3. Org discovery blocks repository selection
4. Webhook setup can parallel historical sync

**Parallelization Opportunities:**
- UI work can start after OAuth flow
- Tests can be written alongside implementation
- Documentation can be prepared early
