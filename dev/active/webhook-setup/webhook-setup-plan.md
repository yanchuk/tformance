# Phase 2.5: Webhook Setup - Implementation Plan

> Last Updated: 2025-12-10

## Executive Summary

This phase implements GitHub webhook registration and event handling for tracked repositories. When a repository is tracked (Phase 2.4), we automatically register a webhook to receive real-time `pull_request` and `pull_request_review` events. These events populate the metrics models (PullRequest, PRReview) that power the dashboards.

### Key Outcomes
- Auto-register webhooks when repositories are tracked
- Auto-delete webhooks when repositories are untracked
- Receive and validate webhook payloads
- Process `pull_request` events → create/update PullRequest records
- Process `pull_request_review` events → create PRReview records
- Foundation for PR survey triggers (Phase 5)

### Dependencies
- Phase 2.1 Integration App Foundation ✅ Complete
- Phase 2.2 GitHub OAuth Flow ✅ Complete
- Phase 2.3 Organization Discovery ✅ Complete
- Phase 2.4 Repository Selection ✅ Complete

---

## Current State Analysis

### Existing Infrastructure

**Models (apps/integrations/models.py)**
- `GitHubIntegration` - Has `webhook_secret` field for payload validation
- `TrackedRepository` - Has `webhook_id` field (nullable) for storing GitHub webhook ID

**Models (apps/metrics/models.py)**
- `PullRequest` - Ready to receive webhook data
- `PRReview` - Ready to receive webhook data
- `TeamMember` - For author/reviewer lookups

**Services (apps/integrations/services/github_oauth.py)**
- `_make_github_api_request()` - Reusable for POST/DELETE webhook calls
- Existing token decryption pattern

### Missing Components
- Webhook registration service (create/delete webhooks via GitHub API)
- Webhook endpoint (receive POST from GitHub)
- Payload signature validation (HMAC-SHA256)
- Event handlers for `pull_request` and `pull_request_review`
- Auto-registration on repository tracking

---

## Technical Architecture

### Webhook Registration Flow
```
User tracks repository (Phase 2.4)
    │
    ▼
github_repo_toggle creates TrackedRepository
    │
    ▼
Signal: post_save on TrackedRepository
    │
    ▼
register_webhook(tracked_repo)
    │
    ▼
GitHub API: POST /repos/{owner}/{repo}/hooks
    │
    ▼
Store webhook_id in TrackedRepository
```

### Webhook Event Flow
```
GitHub event occurs (PR opened, merged, reviewed)
    │
    ▼
GitHub POSTs to /webhooks/github/
    │
    ▼
Validate X-Hub-Signature-256 header
    │
    ▼
Dispatch to handler based on X-GitHub-Event header
    │
    ▼
Handler creates/updates metrics records
```

### GitHub API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/repos/{owner}/{repo}/hooks` | POST | Create webhook |
| `/repos/{owner}/{repo}/hooks/{hook_id}` | DELETE | Remove webhook |
| `/repos/{owner}/{repo}/hooks/{hook_id}` | PATCH | Update webhook (if needed) |

### Webhook Configuration

```json
{
  "name": "web",
  "active": true,
  "events": ["pull_request", "pull_request_review"],
  "config": {
    "url": "https://app.tformance.com/webhooks/github/",
    "content_type": "json",
    "secret": "<webhook_secret>",
    "insecure_ssl": "0"
  }
}
```

---

## Implementation Phases

### 2.5.1: Webhook Service Functions [Effort: M]
Create GitHub API functions for webhook management.

**Deliverables:**
- `create_repository_webhook(access_token, repo_full_name, webhook_url, secret)`
- `delete_repository_webhook(access_token, repo_full_name, webhook_id)`
- Return webhook_id on success
- Handle errors (404 repo, 403 permissions, etc.)

### 2.5.2: Webhook Registration Integration [Effort: S]
Integrate webhook registration with repository tracking.

**Deliverables:**
- Call `create_repository_webhook` when TrackedRepository is created
- Call `delete_repository_webhook` when TrackedRepository is deleted
- Update `webhook_id` field on TrackedRepository
- Handle registration failures gracefully (don't fail the toggle)

### 2.5.3: Webhook Endpoint [Effort: M]
Create endpoint to receive GitHub webhook payloads.

**Deliverables:**
- `/webhooks/github/` endpoint (exempt from CSRF)
- Validate `X-Hub-Signature-256` header using HMAC-SHA256
- Extract team/repo from payload
- Dispatch to appropriate event handler
- Return 200 OK quickly (async processing for heavy work)

### 2.5.4: Pull Request Event Handler [Effort: M]
Process `pull_request` webhook events.

**Deliverables:**
- Handle actions: `opened`, `closed`, `reopened`, `edited`, `synchronize`
- Create/update PullRequest records
- Map GitHub user to TeamMember (by github_id)
- Calculate cycle_time_hours when merged
- Detect reverts (title contains "Revert")
- Detect hotfixes (title/labels contain "hotfix")

### 2.5.5: Pull Request Review Event Handler [Effort: S]
Process `pull_request_review` webhook events.

**Deliverables:**
- Handle actions: `submitted`, `edited`, `dismissed`
- Create PRReview records
- Map reviewer to TeamMember
- Update PullRequest.first_review_at if first review
- Calculate review_time_hours

### 2.5.6: Admin UI for Webhook Status [Effort: S]
Show webhook status in the UI.

**Deliverables:**
- Show webhook status badge on repo list (registered/pending/failed)
- Show last event received timestamp
- Manual "Re-register webhook" button for failed webhooks

---

## API Endpoints

### New Endpoints

| Method | URL | View | Purpose |
|--------|-----|------|---------|
| POST | `/webhooks/github/` | `github_webhook` | Receive GitHub webhooks |

### Internal Service Functions

```python
# apps/integrations/services/github_webhooks.py

def create_repository_webhook(
    access_token: str,
    repo_full_name: str,
    webhook_url: str,
    secret: str
) -> int:
    """Create webhook, return webhook_id."""

def delete_repository_webhook(
    access_token: str,
    repo_full_name: str,
    webhook_id: int
) -> bool:
    """Delete webhook, return success."""

def validate_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """Validate X-Hub-Signature-256 using HMAC-SHA256."""
```

---

## Data Flow

### Pull Request Event → PullRequest Model

```python
# GitHub webhook payload (pull_request event)
{
    "action": "closed",
    "pull_request": {
        "id": 123456789,
        "number": 42,
        "title": "Add new feature",
        "state": "closed",
        "merged": true,
        "user": {"id": 12345, "login": "developer"},
        "created_at": "2025-01-01T10:00:00Z",
        "merged_at": "2025-01-02T15:00:00Z",
        "additions": 150,
        "deletions": 50,
        "base": {"repo": {"full_name": "acme-corp/api-server"}}
    }
}

# Maps to PullRequest model
{
    "team": <team>,
    "github_pr_id": 42,
    "github_repo": "acme-corp/api-server",
    "title": "Add new feature",
    "author": <TeamMember lookup by github_id=12345>,
    "state": "merged",
    "pr_created_at": "2025-01-01T10:00:00Z",
    "merged_at": "2025-01-02T15:00:00Z",
    "cycle_time_hours": 29.0,  # calculated
    "additions": 150,
    "deletions": 50,
    "is_revert": False,
    "is_hotfix": False
}
```

---

## Security Considerations

### Webhook Signature Validation

**CRITICAL:** All webhook payloads MUST be validated before processing.

```python
import hmac
import hashlib

def validate_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate GitHub webhook signature.

    GitHub sends X-Hub-Signature-256 header with format: sha256=<hex_digest>
    """
    if not signature.startswith("sha256="):
        return False

    expected_sig = signature[7:]  # Remove "sha256=" prefix
    computed_sig = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, computed_sig)
```

### Webhook Secret Storage
- Each team has unique `webhook_secret` in GitHubIntegration
- Generated during OAuth flow (already exists)
- Used for all webhooks in that organization

### CSRF Exemption
- Webhook endpoint must be CSRF-exempt (external POST)
- Use `@csrf_exempt` decorator
- Signature validation provides authentication

---

## Risk Assessment

### High Risk
1. **Webhook Secret Exposure**
   - Mitigation: Never log secrets, use environment variables
   - Validate signatures before any processing

2. **Replay Attacks**
   - Mitigation: Check timestamp if GitHub provides it
   - Idempotent handlers (same event processed twice = no duplicate data)

### Medium Risk
1. **GitHub API Rate Limits**
   - Webhook registration is rare (only on track/untrack)
   - Mitigation: Graceful error handling

2. **Missing TeamMember**
   - PR author may not be in TeamMember table
   - Mitigation: Create placeholder or skip, log warning

3. **Out-of-Order Events**
   - Review might arrive before PR
   - Mitigation: Create PR stub if needed, or queue for retry

### Low Risk
1. **Webhook Delivery Failures**
   - GitHub retries webhook delivery automatically
   - Log failed validations for debugging

---

## Testing Strategy

### Unit Tests
- Webhook signature validation (valid, invalid, missing)
- Event payload parsing
- TeamMember lookup logic
- Cycle time calculation

### Integration Tests
- Webhook endpoint returns 200 for valid payload
- Webhook endpoint returns 401 for invalid signature
- PullRequest created from webhook
- PRReview created from webhook

### Manual Testing Checklist
1. Track a repository → webhook registered (check GitHub repo settings)
2. Open a PR in tracked repo → PullRequest created
3. Submit review on PR → PRReview created
4. Merge PR → PullRequest updated with merged_at, cycle_time
5. Untrack repository → webhook deleted

---

## File Structure

```
apps/integrations/
├── services/
│   ├── github_oauth.py        # ⬆️ EXTEND - Add webhook API calls
│   └── github_webhooks.py     # ❌ CREATE - Webhook handlers
├── views.py                   # ⬆️ EXTEND - Add github_repo_toggle webhook calls
├── urls.py                    # No change (team URLs)
└── tests/
    ├── test_github_webhooks.py    # ❌ CREATE
    └── test_views.py              # ⬆️ EXTEND

apps/web/
├── views/
│   └── webhooks.py            # ❌ CREATE - Webhook endpoint
└── urls.py                    # ⬆️ EXTEND - Add /webhooks/github/

apps/metrics/
└── services/
    └── pr_processor.py        # ❌ CREATE - PR event processing logic
```

---

## Development Environment

### Local Webhook Testing

Use ngrok or similar for local development:

```bash
# Terminal 1: Start Django
make dev

# Terminal 2: Start ngrok
ngrok http 8000

# Use ngrok URL for webhook registration during development
# e.g., https://abc123.ngrok.io/webhooks/github/
```

### Environment Variables

```bash
# .env additions (if needed)
WEBHOOK_BASE_URL=https://app.tformance.com  # Production webhook URL
```

---

## Timeline Considerations

**Critical Path:**
1. Webhook service functions (blocks everything)
2. Webhook endpoint (blocks event handling)
3. Event handlers (can be parallel)

**Estimated Total Effort:** Medium (2-3 days of focused work)

**Parallelization:** PR and Review event handlers can be developed in parallel

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Webhook registration success | >99% | Successful registrations / attempts |
| Event processing latency | <500ms | Time from receipt to DB write |
| Signature validation accuracy | 100% | No invalid payloads processed |
| Data completeness | >95% | PRs with author matched |
