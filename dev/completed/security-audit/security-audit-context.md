# Security Audit Context

**Last Updated:** 2025-12-13
**Session Status:** Active implementation - 53% complete (26/49 tasks)

---

## Current Implementation State

### Completed This Session

| Area | What Was Done | Files Modified |
|------|---------------|----------------|
| **Dependencies** | Fixed 4 CVEs (Django, urllib3) | `pyproject.toml`, `uv.lock` |
| **XSS Prevention** | Added bleach sanitization to mark_safe | `apps/content/blocks.py` |
| **Webhook Security** | Removed team_id leak, added replay protection | `apps/web/views.py` |
| **Webhook Rate Limiting** | Added 100/min per IP limits | `apps/web/views.py`, `apps/integrations/webhooks/slack_interactions.py` |
| **Webhook Payload Limits** | Added 5MB/1MB payload size checks | `apps/web/views.py`, `apps/integrations/webhooks/slack_interactions.py` |
| **CSRF Documentation** | Documented @csrf_exempt justifications | `apps/web/views.py`, `apps/integrations/webhooks/slack_interactions.py` |
| **HTTP Timeouts** | Added 30s timeout to OAuth requests | `apps/integrations/services/github_oauth.py`, `jira_oauth.py` |
| **Security Headers** | Created middleware with CSP, HSTS, etc. | `apps/utils/middleware.py`, `tformance/settings.py` |
| **Session Security** | Added session rotation on login | `apps/users/signals.py` |
| **IDOR Tests** | Created 18 cross-team isolation tests | `apps/metrics/tests/test_security_isolation.py` |
| **Template |safe Audit** | Documented |safe usage in form_tags.py | `apps/web/templatetags/form_tags.py` |
| **CI/CD** | Created Dependabot config | `.github/dependabot.yml` |
| **View Isolation Audit** | Verified all views filter by team | All views.py files |
| **Admin Decorator Audit** | Verified @team_admin_required coverage | `apps/integrations/views.py`, `apps/teams/views/` |
| **SQL Injection Audit** | Confirmed ORM-only, no raw SQL in app code | All apps |
| **Manager Usage Audit** | Verified team filtering in services/processors | `apps/metrics/services/`, `apps/metrics/processors.py` |

### Key Decisions Made

1. **Rate Limits**: Set to 100/min per IP for webhooks (generous for legitimate use, blocks attacks)
2. **CSP Policy**: Permissive for HTMX/Alpine.js compatibility (uses `unsafe-inline`)
3. **Replay Protection**: Uses Django cache with 1-hour TTL for webhook delivery IDs
4. **HTML Sanitization**: Whitelist approach - only `a, b, i, em, strong, br, span` tags allowed
5. **Payload Limits**: GitHub webhooks 5 MB, Slack webhooks 1 MB (based on typical payload sizes)
6. **|safe Filter**: Safe because help_text is developer-defined in form classes, not user input

### Files Modified (Uncommitted)

```bash
# Core security files
apps/utils/middleware.py              # NEW - SecurityHeadersMiddleware
apps/content/blocks.py                # Modified - bleach sanitization
apps/web/views.py                     # Modified - webhook security, payload limits, csrf docs
apps/integrations/webhooks/slack_interactions.py  # Modified - rate limiting, payload limits, csrf docs
apps/integrations/services/github_oauth.py        # Modified - timeout
apps/integrations/services/jira_oauth.py          # Modified - timeout
apps/users/signals.py                 # Modified - session rotation
tformance/settings.py                 # Modified - HSTS, production security
apps/web/templatetags/form_tags.py    # Modified - security documentation added

# Test files
apps/metrics/tests/test_security_isolation.py  # NEW - 18 IDOR tests
apps/web/tests/test_webhooks.py                # Modified - security tests

# Config files
.github/dependabot.yml                # NEW - automated dependency updates
pyproject.toml                        # Modified - Django, urllib3, bleach
uv.lock                               # Modified - dependency updates
```

### Next Immediate Steps

1. **Security changes committed**: Commit `3886dc5` contains all security implementations
2. **Remaining high-priority tasks** (Phase 2):
   - 2.1.4: Review Membership role escalation
   - 2.1.5: Audit API permission classes
   - 2.2.1: Audit all POST data handling
   - 2.3.3: Review admin panel team scoping
3. **Then Phase 3**:
   - 3.2.1-4: API security audit and rate limiting

### Session Handoff Notes

**Last Working On**: Completed Phase 2 audits (2.1.1, 2.1.2, 2.2.5, 2.3.2)

**Test Verification** (all pass):
```bash
make test ARGS='apps.web.tests.test_webhooks apps.metrics.tests.test_security_isolation --keepdb'
# Result: 31 tests passed
```

**No migrations needed** - all changes are code/config only, no model changes.

**Key Findings from Audits**:
- All views properly filter by `team=team` from request context
- 22 endpoints protected with `@team_admin_required` (all sensitive ops)
- Only 1 raw SQL usage (migration sequence reset) - completely safe
- dashboard_service.py and processors.py both receive team param and filter correctly
- dashboard/views.py is superuser-only admin dashboard (intentionally system-wide)

---

## Architecture Context

### Technology Stack
- **Backend:** Django 5.2.9, Python 3.12
- **Database:** PostgreSQL 17
- **Cache/Message Broker:** Redis
- **Frontend:** Django Templates, HTMX, Alpine.js, Tailwind CSS, DaisyUI
- **Authentication:** django-allauth (email + OAuth)
- **API Framework:** Django Rest Framework
- **Task Queue:** Celery with celery-beat

### Multi-tenancy Model
- **Isolation Level:** Application-level (shared database, team_id scoping)
- **Pattern:** All metric tables extend `BaseTeamModel` with `team` FK
- **Access Control:** `TeamScopedManager` filters queries by current team context
- **Enforcement:** Decorators (`@login_and_team_required`, `@team_admin_required`)
- **Test Coverage:** 18 tests in `test_security_isolation.py` verify isolation

### External Integrations
| Integration | Auth Method | Data Flow |
|-------------|-------------|-----------|
| GitHub | OAuth 2.0 | Pull repos, PRs, commits, reviews, org members |
| Jira | OAuth 2.0 (Atlassian) | Issues, sprints, story points |
| Slack | OAuth 2.0 | Bot messages, surveys, leaderboards |
| Stripe | API Keys | Billing, subscriptions |

---

## Critical Security Files (Updated)

### Webhook Handlers (SECURED)

```
apps/web/views.py
└── github_webhook() - @csrf_exempt @ratelimit(100/m)
    ├── Validates X-Hub-Signature-256 (timing-safe)
    ├── Validates X-GitHub-Delivery (required)
    ├── Replay protection via cache
    ├── Rate limited 100/min per IP
    └── Returns minimal response (no internal IDs) ✅ FIXED
```

```
apps/integrations/webhooks/slack_interactions.py
└── slack_interactions() - @csrf_exempt @ratelimit(100/m)
    ├── verify_slack_signature() using SignatureVerifier
    ├── Rate limited 100/min per IP ✅ ADDED
    └── Parses button click payloads
```

### Security Middleware (NEW)

```
apps/utils/middleware.py
└── SecurityHeadersMiddleware
    ├── Content-Security-Policy (permissive for HTMX/Alpine)
    ├── X-Content-Type-Options: nosniff
    ├── Referrer-Policy: strict-origin-when-cross-origin
    ├── Permissions-Policy (disabled camera, mic, etc.)
    └── Applied via settings.py MIDDLEWARE
```

### Session Security (SECURED)

```
apps/users/signals.py
└── rotate_session_on_login()
    ├── @receiver(user_logged_in)
    ├── request.session.cycle_key()
    └── Prevents session fixation attacks ✅ ADDED
```

### OAuth Services (SECURED)

```
apps/integrations/services/github_oauth.py
└── exchange_code_for_token()
    └── requests.post(..., timeout=30) ✅ FIXED

apps/integrations/services/jira_oauth.py
├── _make_token_request()
│   └── requests.post(..., timeout=30) ✅ FIXED
└── get_accessible_resources()
    └── requests.get(..., timeout=30) ✅ FIXED
```

### XSS Prevention (SECURED)

```
apps/content/blocks.py
└── CaptionBlock.render_basic()
    ├── bleach.clean(value, tags=ALLOWED_TAGS) ✅ FIXED
    └── Whitelist: a, b, i, em, strong, br, span
```

---

## Security Configuration (settings.py) - UPDATED

### Production Security Block (NEW)
```python
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = "DENY"
```

### Middleware Order (UPDATED)
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.utils.middleware.SecurityHeadersMiddleware",  # ✅ ADDED
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # ... rest unchanged
]
```

---

## Security-Relevant Dependencies (UPDATED)

| Package | Version | Purpose | Status |
|---------|---------|---------|--------|
| django | 5.2.9 | Framework | ✅ Updated from 5.2.8 |
| urllib3 | 2.6.2 | HTTP client | ✅ Updated from 2.5.0 |
| bleach | 6.3.0 | HTML sanitization | ✅ NEW |
| cryptography | - | Fernet encryption | Existing |
| django-ratelimit | - | Request rate limiting | Existing |

---

## Test Coverage for Security (UPDATED)

### New Security Tests
```
apps/metrics/tests/test_security_isolation.py (NEW - 18 tests)
├── TestTeamMemberIsolation (4 tests)
├── TestPullRequestIsolation (2 tests)
├── TestPRReviewIsolation (1 test)
├── TestCommitIsolation (1 test)
├── TestJiraIssueIsolation (1 test)
├── TestPRSurveyIsolation (1 test)
├── TestPRSurveyReviewIsolation (1 test)
├── TestWeeklyMetricsIsolation (1 test)
├── TestBulkOperationIsolation (3 tests)
└── TestDirectIDAccessPrevention (3 tests)

apps/web/tests/test_webhooks.py (UPDATED - 13 tests)
├── test_endpoint_returns_400_for_missing_delivery_id ✅ NEW
├── test_replay_protection_rejects_duplicate_delivery ✅ NEW
└── test_endpoint_looks_up_team_from_repository_in_payload ✅ UPDATED
```

### Test Commands
```bash
# Run all security tests (50 tests)
make test ARGS='apps.metrics.tests.test_security_isolation apps.web.tests.test_webhooks apps.integrations.tests.test_encryption'

# Verify no regressions
make test
```

---

## OWASP Top 10 Mapping (UPDATED)

| Category | Status | Notes |
|----------|--------|-------|
| A01 Broken Access Control | ✅ Good | 18 IDOR tests, team isolation verified |
| A02 Cryptographic Failures | ✅ Good | Fernet encryption for tokens |
| A03 Injection | ✅ Good | ORM used, bleach for HTML |
| A04 Insecure Design | Partial | Architecture review still needed |
| A05 Security Misconfiguration | ✅ Good | Security headers, HSTS added |
| A06 Vulnerable Components | ✅ Good | pip-audit clean, Dependabot configured |
| A07 Authentication Failures | ✅ Good | Session rotation, django-allauth |
| A08 Software/Data Integrity | ✅ Good | Webhook replay protection |
| A09 Logging Failures | Partial | Security logging audit still needed |
| A10 SSRF | Unknown | URL fetch audit still needed |

---

## Remaining High-Priority Work

### Phase 1 (P0) - ✅ COMPLETE
All webhook security tasks completed (info leak, replay, rate limit, csrf docs, payload limits)

### Phase 2 (P1) - ✅ MOSTLY COMPLETE (1 remaining)
- [x] 2.1.1-5 Authorization audit complete
- [x] 2.2.1-3, 2.2.5 Input validation audited
- [x] 2.3.1-3 Data isolation tested and verified
- [ ] 2.2.4 Add input sanitization utilities (optional - bleach already added)

### Phase 3 (P2) - 6 remaining
- [ ] 3.1.1 Review session timeout configuration
- [ ] 3.1.3-4 Concurrent session limits, hijack audit
- [ ] 3.2.1-4 API security audit and rate limiting

### Phase 4 (P3) - 5 remaining
- [ ] 4.1.1-4 Logging and monitoring
- [ ] 4.2.4 Review third-party package permissions
- [ ] 4.3.1-5 Production hardening

---

## Bandit Scan Results

**Remaining Medium+ Issues:**
- `apps/web/templatetags/form_tags.py:10` - mark_safe on joined rendered fields (acceptable - Django template rendering already escapes)
- `apps/content/blocks.py` - mark_safe after bleach.clean (acceptable - sanitized first)

**All High Issues:** Resolved
