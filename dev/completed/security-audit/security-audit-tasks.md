# Security Audit Tasks Checklist

**Last Updated:** 2025-12-21
**Status:** ✅ COMPLETE (49/49 tasks - 100%)

---

## Phase 1: Critical Security (P0)

### Section 1.1: OAuth Token Security Audit
- [x] 1.1.1 Audit token storage encryption ✅ COMPLETED
  - Fernet (AES-256-CBC + HMAC-SHA256) encryption implemented
  - 25+ encryption tests covering edge cases
  - Key from INTEGRATION_ENCRYPTION_KEY setting
  - Raises ValueError if key not configured
- [x] 1.1.2 Review token refresh handling ✅ COMPLETED
  - Jira: `ensure_valid_jira_token()` with 5-min buffer refresh
  - New tokens re-encrypted before storage
  - Atomic save with update_fields
- [x] 1.1.3 Check token expiration handling ✅ COMPLETED
  - `token_expires_at` tracked for all credentials
  - TOKEN_REFRESH_BUFFER (5 mins) for proactive refresh
  - GitHub tokens don't expire (no refresh needed)
- [x] 1.1.4 Review token scope minimization ✅ COMPLETED
  - GitHub: `read:org repo read:user` (needed for PRs, commits, org members)
  - Jira: `read:jira-work read:jira-user offline_access` (read-only + refresh)
  - Slack: `chat:write users:read users:read.email` (minimal for surveys)
- [x] 1.1.5 Secure state parameter validation ✅ COMPLETED
  - State signed with Django's Signer (HMAC with SECRET_KEY)
  - Contains team_id to prevent cross-team attacks
  - Validation on all callbacks (GitHub, Jira, Slack)
  - Callbacks rate-limited 10/min per IP

### Section 1.2: Webhook Security Hardening
- [x] 1.2.1 Remove `team_id` from webhook responses ✅ COMPLETED
  - Updated `apps/web/views.py:github_webhook`
  - Now returns only `status` and `event` type
- [x] 1.2.2 Add webhook replay protection ✅ COMPLETED
  - Validates `X-GitHub-Delivery` header (required)
  - Rejects duplicate webhook IDs using cache
  - Cache timeout: 1 hour for replay protection
- [x] 1.2.3 Add webhook rate limiting ✅ COMPLETED
  - Added @ratelimit decorator to GitHub webhook (100/min per IP)
  - Added @ratelimit decorator to Slack webhook (100/min per IP)
  - Uses django-ratelimit with block=True
- [x] 1.2.4 Audit `@csrf_exempt` endpoints ✅ COMPLETED
  - Documented `/webhooks/github/` justification with SECURITY comment
  - Documented `/integrations/slack/interactions/` justification with SECURITY comment
  - Verified only 2 csrf_exempt endpoints exist (both webhooks with signature validation)
- [x] 1.2.5 Add webhook payload size limits ✅ COMPLETED
  - GitHub webhook: 5 MB max (MAX_WEBHOOK_PAYLOAD_SIZE)
  - Slack webhook: 1 MB max (MAX_SLACK_PAYLOAD_SIZE)
  - Returns 413 Payload Too Large for oversized requests

---

## Phase 2: Access Control & Data Protection (P1)

### Section 2.1: Authorization Audit
- [x] 2.1.1 Audit team isolation in all views ✅ COMPLETED
  - Reviewed `apps/integrations/views.py` - all queries filter by `team=team`
  - `apps/metrics/` has no views.py (uses service layer with team param)
  - `apps/dashboard/views.py` - superuser-only admin dashboard (intentionally system-wide)
  - `apps/subscriptions/views/views.py` - no direct .objects. calls
  - All team-scoped queries properly filter by team
- [x] 2.1.2 Review `@team_admin_required` usage ✅ COMPLETED
  - All disconnect endpoints protected: github_disconnect, jira_disconnect, slack_disconnect
  - All settings endpoints protected: slack_settings
  - All toggle/modification endpoints protected (member toggle, repo toggle, project toggle)
  - Team delete and invitation management protected
  - Dashboard/metrics admin views protected
- [x] 2.1.3 Add IDOR (Insecure Direct Object Reference) tests ✅ COMPLETED
  - Created `apps/metrics/tests/test_security_isolation.py`
  - 18 tests covering all team-scoped models
  - Tests TeamMember, PullRequest, PRReview, Commit, JiraIssue isolation
  - Tests PRSurvey, PRSurveyReview, WeeklyMetrics isolation
  - Tests direct ID access prevention (IDOR)
- [x] 2.1.4 Review Membership role escalation ✅ COMPLETED
  - Role changes require admin permission (is_admin check)
  - Users cannot change their own role (editing_self check)
  - Invitation roles constrained to ROLE_CHOICES (admin/member)
  - Last admin cannot be removed (admin_count check)
- [x] 2.1.5 Audit API permission classes ✅ COMPLETED
  - TeamViewSet: IsAuthenticatedOrHasUserAPIKey + TeamAccessPermissions
  - InvitationViewSet: Admin check for create, member check for read
  - get_queryset() filters to user's teams or team context
  - HasUserAPIKey validates API key and populates request.user

### Section 2.2: Input Validation & Injection Prevention
- [x] 2.2.1 Audit all POST data handling ✅ COMPLETED
  - Reviewed all request.POST.get() usage in views
  - Fixed integer conversion in slack_settings (added try/except)
  - Fixed missing validation in CreateCheckoutSession API (added 400 response)
  - All views use Django forms or explicit validation
- [x] 2.2.2 Review `mark_safe` usage ✅ COMPLETED
  - Fixed `apps/content/blocks.py` XSS vulnerability
  - Added `bleach` library for HTML sanitization
  - Whitelist approach: only safe tags (a, b, i, em, strong, br, span)
  - Sanitized before mark_safe to prevent XSS
- [x] 2.2.3 Audit template `|safe` filter usage ✅ COMPLETED
  - Reviewed `apps/web/templatetags/form_tags.py` - only 3 uses on form help_text
  - Added Security Note docstring explaining justification (developer-defined, not user input)
  - No templates use |safe - all uses are in template tags
  - Low risk: help_text comes from Python form definitions
- [x] 2.2.4 Add input sanitization utilities ✅ COMPLETED
  - Created `apps/utils/sanitization.py` with bleach-based HTML sanitization
  - `sanitize_html()` function with configurable allowed tags/attributes
  - `sanitize_plain_text()` for stripping all HTML
  - SQL-safe validation not needed (Django ORM handles parameterized queries)
- [x] 2.2.5 Review SQL query construction ✅ COMPLETED
  - Only one raw SQL in migrations (sequence reset in 0001_initial.py) - safe
  - No .raw() or .extra() usage in application code
  - No cursor.execute() or connection.execute() calls
  - All queries use Django ORM with parameterized queries

### Section 2.3: Data Isolation Testing
- [x] 2.3.1 Create cross-team access test suite ✅ COMPLETED
  - Created `apps/metrics/tests/test_security_isolation.py`
  - Tests TeamMember, PullRequest, PRReview, Commit model isolation
  - Tests JiraIssue, PRSurvey, PRSurveyReview, WeeklyMetrics isolation
  - Tests bulk operations and filter chaining
  - Tests direct ID access prevention (IDOR)
- [x] 2.3.2 Audit `objects` vs `for_team` manager usage ✅ COMPLETED
  - Views: All team-scoped queries use `team=team` filter from request.team
  - Services: dashboard_service.py receives team param, filters all queries
  - Processors: All webhook handlers filter by team from tracked repository
  - Management commands: Admin-only tools (not exposed to users)
- [x] 2.3.3 Review admin panel team scoping ✅ COMPLETED
  - Django admin is for platform superusers only (not team admins)
  - All models have list_filter=["team"] for filtering
  - Team admins manage teams via application UI
  - Appropriate for multi-tenant SaaS - superusers need full visibility

---

## Phase 3: Session & API Security (P2)

### Section 3.1: Session Security
- [x] 3.1.1 Review session timeout configuration ✅ COMPLETED
  - Uses Django default (2 weeks) - appropriate for SaaS with remember-me
  - SESSION_COOKIE_HTTPONLY = True (JS can't access)
  - SESSION_COOKIE_SECURE = not DEBUG (HTTPS in production)
  - SESSION_COOKIE_SAMESITE = "Lax" (CSRF protection)
- [x] 3.1.2 Implement session rotation on login ✅ COMPLETED
  - Added `rotate_session_on_login` signal in `apps/users/signals.py`
  - Uses `request.session.cycle_key()` on user_logged_in signal
  - Prevents session fixation attacks
- [x] 3.1.3 Review concurrent session handling ✅ COMPLETED
  - No max session limit (acceptable for SaaS - multiple devices common)
  - Password change via django-allauth triggers re-auth
  - Session database backend allows manual invalidation if needed
- [x] 3.1.4 Review hijack functionality security ✅ COMPLETED
  - `apps/support/views.py:hijack_user` requires `is_superuser` AND `staff_member`
  - Double protection: `@user_passes_test(lambda u: u.is_superuser)` + `@staff_member_required`
  - Redirects unauthorized to 404 (no info leakage)
  - Appropriate for support/debugging use case

### Section 3.2: API Security
- [x] 3.2.1 Audit DRF permission classes ✅ COMPLETED (see 2.1.5)
  - `IsAuthenticatedOrHasUserAPIKey` properly enforces auth
  - `TeamAccessPermissions` validates team membership for safe/unsafe methods
  - All API views have proper permissions (TeamViewSet, InvitationViewSet)
  - Queryset filtering ensures team scoping
- [x] 3.2.2 Review API key security ✅ COMPLETED
  - Uses `rest_framework_api_key` which hashes keys (SHA-512)
  - Keys stored as hashed prefix + hashed key (not plaintext)
  - `HasUserAPIKey.has_permission()` checks `user.is_active`
  - Key rotation: delete old key, create new (manual process)
- [x] 3.2.3 Review API rate limiting ✅ COMPLETED
  - NOTE: DRF throttling NOT enabled for API endpoints
  - Webhooks: 100/min per IP via django-ratelimit
  - OAuth callbacks: 10/min per IP via django-ratelimit
  - RECOMMENDATION: Add DRF throttle classes for API abuse prevention
- [x] 3.2.4 Review API error responses ✅ COMPLETED
  - DEBUG=False in production disables stack traces
  - DRF uses standardized error responses (detail, code)
  - No token/key values exposed in errors

### Section 3.3: Security Headers
- [x] 3.3.1 Implement Content-Security-Policy ✅ COMPLETED
  - Created `apps/utils/middleware.py:SecurityHeadersMiddleware`
  - Configured permissive CSP for HTMX/Alpine.js compatibility
  - Includes: default-src, script-src, style-src, img-src, connect-src, frame-ancestors, form-action
- [x] 3.3.2 Add X-Content-Type-Options ✅ COMPLETED
  - Added `X-Content-Type-Options: nosniff` header
  - Middleware applied to all responses
- [x] 3.3.3 Add Referrer-Policy ✅ COMPLETED
  - Configured `strict-origin-when-cross-origin`
  - Middleware applied to all responses
- [x] 3.3.4 Add Permissions-Policy ✅ COMPLETED
  - Disabled: camera, microphone, geolocation, payment, usb, accelerometer, gyroscope, magnetometer
  - Middleware applied to all responses
- [x] 3.3.5 Review HSTS configuration ✅ COMPLETED
  - Added HSTS in production (when DEBUG=False)
  - SECURE_HSTS_SECONDS = 31536000 (1 year)
  - SECURE_HSTS_INCLUDE_SUBDOMAINS = True
  - SECURE_HSTS_PRELOAD = True
  - SECURE_SSL_REDIRECT = True

---

## Phase 4: Monitoring & Dependencies (P3)

### Section 4.1: Logging & Monitoring
- [x] 4.1.1 Audit logging for sensitive data ✅ COMPLETED
  - Logging uses Django's built-in formatters
  - No token values logged (decrypt() only at use time)
  - logger.info/warning for security events (duplicate webhooks, replay)
- [x] 4.1.2 Review security event logging ✅ COMPLETED
  - OAuth connections logged in views.py (connect/disconnect messages)
  - Webhook signature failures logged as warnings
  - Session rotation logged in signals.py
  - RECOMMENDATION: Add structured security audit log for SOC2 compliance
- [x] 4.1.3 Review anomaly detection ✅ COMPLETED
  - Rate limiting blocks repeated attempts (10/min OAuth, 100/min webhooks)
  - Cross-team access returns 404 (no logging of attempts)
  - RECOMMENDATION: Add failed auth logging for security monitoring
- [x] 4.1.4 Review Sentry configuration ✅ COMPLETED
  - Sentry DSN configurable via env var (not hardcoded)
  - Uses DjangoIntegration for automatic error capture
  - RECOMMENDATION: Configure send_default_pii=False for PII protection

### Section 4.2: Dependency Security
- [x] 4.2.1 Run `pip-audit` on dependencies ✅ COMPLETED
  - Ran pip-audit, found 4 vulnerabilities
  - Fixed: Django 5.2.8 → 5.2.9 (CVE-2025-13372, CVE-2025-64460)
  - Fixed: urllib3 2.5.0 → 2.6.2 (CVE-2025-66418, CVE-2025-66471)
  - No known vulnerabilities remaining
- [x] 4.2.2 Set up Dependabot/Renovate ✅ COMPLETED
  - Created `.github/dependabot.yml`
  - Configured Python (pip) dependency updates - weekly
  - Configured npm dependency updates - weekly
  - Configured GitHub Actions updates - weekly
  - Groups minor/patch updates, reviews major separately
- [x] 4.2.3 Audit npm dependencies ✅ COMPLETED
  - Ran `npm audit` - found 0 vulnerabilities
  - No action required
- [x] 4.2.4 Review third-party package permissions ✅ COMPLETED
  - django-allauth: Auth only, no data access
  - django-hijack: Superuser-only impersonation (verified in 3.1.4)
  - PyGithub/jira/slack-sdk: Scopes documented in 1.1.4

### Section 4.3: Production Hardening
- [x] 4.3.1 Review Django DEBUG setting ✅ COMPLETED
  - `DEBUG = env.bool("DEBUG", default=False)` - secure default
  - Production settings block at line 667 activates when DEBUG=False
  - HSTS, SSL redirect, secure cookies all enabled in production
- [x] 4.3.2 Audit ALLOWED_HOSTS ✅ COMPLETED
  - `ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])` - no wildcard
  - Must explicitly set in environment - empty list is secure default
  - Django will reject requests to unlisted hosts
- [x] 4.3.3 Review admin URL security ✅ COMPLETED
  - Admin at `/admin/` (standard path)
  - Admin login redirects to main login page (line 57 in urls.py)
  - Admin requires is_superuser + is_staff
  - RECOMMENDATION: Consider IP restriction or custom admin URL for defense in depth
- [x] 4.3.4 Review secrets management ✅ COMPLETED
  - All secrets via environment variables (not hardcoded)
  - INTEGRATION_ENCRYPTION_KEY for token encryption
  - RECOMMENDATION: Document key rotation procedure in runbook
  - Test rotation without downtime
- [x] 4.3.5 Review database connection security ✅ COMPLETED
  - DATABASE_URL or individual env vars for connection (not hardcoded)
  - Default password shown as *** in settings (placeholder)
  - RECOMMENDATION: Enable sslmode=require for production DATABASE_URL

---

## Progress Summary

| Phase | Section | Progress | Notes |
|-------|---------|----------|-------|
| 1 | 1.1 OAuth Tokens | 5/5 | ✅ COMPLETE - Encryption, refresh, expiry, scopes, state validation |
| 1 | 1.2 Webhooks | 5/5 | ✅ COMPLETE - Info leak, replay, rate limit, csrf docs, payload limits |
| 2 | 2.1 Authorization | 5/5 | ✅ COMPLETE - IDOR tests, view audit, decorator review, role escalation, API perms |
| 2 | 2.2 Input Validation | 5/5 | ✅ COMPLETE - XSS fixed, |safe audited, SQL reviewed, POST handling fixed, sanitization utils |
| 2 | 2.3 Data Isolation | 3/3 | ✅ COMPLETE - Cross-team tests, manager audit, admin scoping |
| 3 | 3.1 Sessions | 4/4 | ✅ COMPLETE - Timeout, rotation, concurrent, hijack |
| 3 | 3.2 API Security | 4/4 | ✅ COMPLETE - Permissions, API keys, rate limiting, errors |
| 3 | 3.3 Security Headers | 5/5 | ✅ COMPLETE - CSP, X-Content-Type, Referrer, Permissions, HSTS |
| 4 | 4.1 Logging | 4/4 | ✅ COMPLETE - Sensitive data, events, anomaly, Sentry |
| 4 | 4.2 Dependencies | 4/4 | ✅ COMPLETE - pip-audit, dependabot, npm audit, packages |
| 4 | 4.3 Production | 5/5 | ✅ COMPLETE - DEBUG, ALLOWED_HOSTS, admin, secrets, database |

**Total:** 49/49 tasks completed (100%) ✅ ALL COMPLETE

### Additional Fixes Applied
- Added HTTP request timeouts (30s) to prevent DoS
- Ran bandit security linter - fixed identified issues
- Added bleach library for HTML sanitization
- Session rotation on login (session fixation prevention)
- Webhook payload size limits (5 MB for GitHub, 1 MB for Slack)
- Security documentation comments on @csrf_exempt endpoints

---

## Quick Commands

### Dependency Scanning
```bash
# Python vulnerabilities
pip install pip-audit
pip-audit

# Bandit security linting
pip install bandit
bandit -r apps/

# NPM vulnerabilities
npm audit
```

### Security Header Testing
```bash
# Test locally
curl -I http://localhost:8000/

# Online tools
# https://securityheaders.com
# https://observatory.mozilla.org
```

### Search for Security Issues
```bash
# Find mark_safe usage
grep -r "mark_safe" apps/

# Find |safe filter
grep -r "|safe" templates/

# Find raw SQL
grep -r "\.raw(" apps/
grep -r "\.extra(" apps/

# Find csrf_exempt
grep -r "csrf_exempt" apps/
```
