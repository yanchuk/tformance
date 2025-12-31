# Security Remediation Context

**Last Updated:** 2025-12-31

## Key Files

### Critical Files to Modify

| File | Purpose | Changes Needed |
|------|---------|---------------|
| `apps/web/views.py:189-220` | GitHub webhook handler | Multi-team signature routing |
| `apps/integrations/models.py:112-116` | GitHubIntegration model | Encrypt webhook_secret |
| `tformance/settings.py` | Django settings | Hijack, rate limits, logout, session |
| `apps/teams/models.py` | Team model | Add llm_analysis_enabled field |
| `apps/integrations/tasks.py` | Celery sync tasks | Error sanitization, LLM opt-out |
| `apps/integrations/services/copilot_metrics.py` | Copilot API client | JSON error handling |
| `apps/integrations/webhooks/slack_interactions.py` | Slack webhook handler | JSON error handling |

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/utils/errors.py` | Error sanitization utility |
| `apps/utils/tests/test_errors.py` | Tests for error sanitization |
| `apps/web/tests/test_github_webhook.py` | Extended webhook tests |

### Reference Files (Read-Only)

| File | Purpose |
|------|---------|
| `apps/utils/fields.py` | EncryptedTextField implementation |
| `apps/integrations/services/github_webhooks.py` | validate_webhook_signature() |
| `apps/integrations/services/encryption.py` | Fernet encryption service |

---

## Key Decisions Made

### 1. GitHub Auth Only in Production
- **Decision:** No email verification needed
- **Rationale:** `AUTH_MODE = "github_only"` in production means all users authenticate via GitHub OAuth
- **Impact:** Skip email verification task, simplifies security model

### 2. CSP Nonces Deferred
- **Decision:** Keep permissive CSP (`unsafe-inline`, `unsafe-eval`) for now
- **Rationale:**
  - Django auto-escapes templates (mitigates XSS)
  - HTMX/Alpine.js require inline scripts
  - Nonce implementation requires template changes
- **Impact:** Added to future backlog

### 3. Multi-Team Webhook Routing via Signature
- **Decision:** Validate signature against all matching repos
- **Rationale:**
  - Same GitHub repo can be tracked by multiple teams (e.g., OSS repos)
  - Each team has unique webhook secret
  - Signature validation determines correct team
- **Impact:** Changes webhook lookup from `.get()` to `.filter()` + loop

### 4. Hijack Kept for Support
- **Decision:** Keep hijack, restrict to superusers
- **Rationale:** Useful for customer support debugging
- **Impact:** Add `HIJACK_PERMISSION_CHECK` setting

### 5. Strict TDD Workflow
- **Decision:** All code changes follow Red-Green-Refactor
- **Rationale:** Project guidelines require TDD for new features
- **Impact:** Write failing tests before implementation

---

## Dependencies

### Python Packages (Already Installed)

```
django-allauth       # Auth, rate limiting
django-hijack        # User impersonation
cryptography         # Fernet encryption
pytest-django        # TDD testing
```

### Internal Dependencies

| Module | Provides |
|--------|----------|
| `apps.utils.fields.EncryptedTextField` | Encryption for model fields |
| `apps.integrations.services.github_webhooks.validate_webhook_signature` | HMAC-SHA256 validation |
| `apps.teams.models.BaseTeamModel` | Team-scoped model base |
| `apps.integrations.models.TrackedRepository` | Repo tracking model |

---

## Code Patterns to Follow

### 1. Encrypted Fields

```python
from apps.utils.fields import EncryptedTextField

class GitHubIntegration(BaseTeamModel):
    webhook_secret = EncryptedTextField(
        verbose_name="Webhook secret",
        help_text="Secret for validating GitHub webhook payloads (encrypted at rest)",
    )
```

### 2. Team-Scoped Queries

```python
# Safe: Uses for_team manager
repos = TrackedRepository.for_team.filter(is_active=True)

# Safe: Explicit team filter
repos = TrackedRepository.objects.filter(team=team, is_active=True)

# Unsafe but justified with noqa comment:
repos = TrackedRepository.objects.filter(github_repo_id=id)  # noqa: TEAM001 - Webhook lookup
```

### 3. Error Sanitization Pattern

```python
from apps.utils.errors import sanitize_error

try:
    sync_repository(repo)
except Exception as exc:
    logger.exception("Sync failed for repo %s", repo.id)
    repo.last_sync_error = sanitize_error(exc)
    repo.save(update_fields=["last_sync_error"])
```

### 4. JSON Parsing Safety

```python
import json
import logging

logger = logging.getLogger(__name__)

def safe_json(response):
    """Parse JSON response safely, returning None on failure."""
    try:
        return response.json()
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error(
            "Invalid JSON response from %s: %s",
            response.url,
            str(exc)[:100],
        )
        return None
```

---

## Testing Patterns

### Factory Usage

```python
from apps.integrations.factories import (
    GitHubIntegrationFactory,
    TrackedRepositoryFactory,
)
from apps.teams.factories import TeamFactory

class TestWebhookMultiTeam(TestCase):
    def setUp(self):
        self.team1 = TeamFactory()
        self.team2 = TeamFactory()
        self.integration1 = GitHubIntegrationFactory(team=self.team1)
        self.integration2 = GitHubIntegrationFactory(team=self.team2)
```

### Webhook Testing

```python
import hmac
import hashlib

def sign_payload(payload: bytes, secret: str) -> str:
    """Generate GitHub webhook signature."""
    sig = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={sig}"
```

---

## Environment Variables

No new environment variables required. Existing:

| Variable | Purpose |
|----------|---------|
| `INTEGRATION_ENCRYPTION_KEY` | Fernet key for token encryption |
| `AUTH_MODE` | `github_only` (prod) or `all` (dev) |
| `DEBUG` | Disables rate limits in dev |

---

## Migration Notes

### Webhook Secret Encryption Migration

```python
from django.db import migrations
from apps.integrations.services.encryption import encrypt

def encrypt_webhook_secrets(apps, schema_editor):
    GitHubIntegration = apps.get_model("integrations", "GitHubIntegration")
    for integration in GitHubIntegration.objects.all():
        # Only encrypt if not already encrypted
        if integration.webhook_secret and not integration.webhook_secret.startswith("gAAAA"):
            integration.webhook_secret = encrypt(integration.webhook_secret)
            integration.save(update_fields=["webhook_secret"])

class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "XXXX_previous_migration"),
    ]

    operations = [
        migrations.RunPython(encrypt_webhook_secrets, reverse_code=migrations.RunPython.noop),
    ]
```

**Note:** The `EncryptedTextField` handles encryption/decryption automatically after the field type change. The RunPython is only needed if we want to encrypt existing data in place.

---

## Related Documentation

- [PRD-MVP.md](../../../prd/PRD-MVP.md) - Product requirements
- [ARCHITECTURE.md](../../../prd/ARCHITECTURE.md) - System architecture
- [CLAUDE.md](../../../CLAUDE.md) - Coding guidelines (TDD, patterns)
- [Security Review Plan](../../../.claude/plans/generic-plotting-deer.md) - Original audit findings
