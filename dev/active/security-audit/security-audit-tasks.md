# Security Audit Tasks Checklist

**Last Updated:** 2025-12-13
**Status:** In Progress (Phase 1 Partial, Phase 2 Partial, Phase 3 Partial, Phase 4 Complete)

---

## Phase 1: Critical Security (P0)

### Section 1.1: OAuth Token Security Audit
- [ ] 1.1.1 Audit token storage encryption
  - Verify Fernet key is properly secured
  - Check for key rotation capability
  - Review key storage mechanism
- [ ] 1.1.2 Implement token refresh handling
  - Add auto-refresh for Jira tokens (expiring)
  - Add auto-refresh for Slack tokens (if applicable)
  - Handle refresh failures gracefully
- [ ] 1.1.3 Add token expiration monitoring
  - Log warning when tokens approach expiration
  - Add admin notification for expiring tokens
- [ ] 1.1.4 Review token scope minimization
  - Verify GitHub scopes are minimal for requirements
  - Verify Jira scopes are minimal for requirements
  - Verify Slack scopes are minimal for requirements
- [ ] 1.1.5 Secure state parameter validation
  - Verify HMAC signing on OAuth state
  - Add timestamp to state parameter
  - Validate state age (reject old states)

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
- [ ] 2.1.1 Audit team isolation in all views
  - Review `apps/integrations/views.py` - all views use team from request
  - Review `apps/metrics/` views
  - Review `apps/dashboard/` views
  - Review `apps/subscriptions/` views
- [ ] 2.1.2 Review `@team_admin_required` usage
  - Verify all admin-only actions are protected
  - Check disconnect endpoints
  - Check settings modification endpoints
- [x] 2.1.3 Add IDOR (Insecure Direct Object Reference) tests ✅ COMPLETED
  - Created `apps/metrics/tests/test_security_isolation.py`
  - 18 tests covering all team-scoped models
  - Tests TeamMember, PullRequest, PRReview, Commit, JiraIssue isolation
  - Tests PRSurvey, PRSurveyReview, WeeklyMetrics isolation
  - Tests direct ID access prevention (IDOR)
- [ ] 2.1.4 Review Membership role escalation
  - Verify role can only be changed by admin
  - Verify invitation role assignment is validated
  - Check for self-promotion vulnerabilities
- [ ] 2.1.5 Audit API permission classes
  - Review DRF viewsets
  - Verify team scoping on API endpoints
  - Check API key team association

### Section 2.2: Input Validation & Injection Prevention
- [ ] 2.2.1 Audit all POST data handling
  - Review `request.POST.get()` usage in views
  - Add validation for integer conversions
  - Add validation for string inputs
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
- [ ] 2.2.4 Add input sanitization utilities
  - Create `apps/utils/sanitization.py`
  - Add HTML sanitization function
  - Add SQL-safe string validation
- [ ] 2.2.5 Review SQL query construction
  - Audit `apps/web/migrations/` for raw SQL
  - Check for any raw() or extra() usage
  - Verify parameterized queries

### Section 2.3: Data Isolation Testing
- [x] 2.3.1 Create cross-team access test suite ✅ COMPLETED
  - Created `apps/metrics/tests/test_security_isolation.py`
  - Tests TeamMember, PullRequest, PRReview, Commit model isolation
  - Tests JiraIssue, PRSurvey, PRSurveyReview, WeeklyMetrics isolation
  - Tests bulk operations and filter chaining
  - Tests direct ID access prevention (IDOR)
- [ ] 2.3.2 Audit `objects` vs `for_team` manager usage
  - Search for `.objects.` in views
  - Verify team filtering for each case
  - Document exceptions (admin panel)
- [ ] 2.3.3 Review admin panel team scoping
  - Verify admin users see only their teams
  - Check for data leakage in admin

---

## Phase 3: Session & API Security (P2)

### Section 3.1: Session Security
- [ ] 3.1.1 Review session timeout configuration
  - Check `SESSION_COOKIE_AGE` setting
  - Implement appropriate timeout for SaaS
- [x] 3.1.2 Implement session rotation on login ✅ COMPLETED
  - Added `rotate_session_on_login` signal in `apps/users/signals.py`
  - Uses `request.session.cycle_key()` on user_logged_in signal
  - Prevents session fixation attacks
- [ ] 3.1.3 Add concurrent session limits
  - Implement max sessions per user
  - Add session invalidation on password change
- [ ] 3.1.4 Review hijack functionality security
  - Audit django-hijack configuration
  - Verify admin-only access
  - Add audit logging for impersonation

### Section 3.2: API Security
- [ ] 3.2.1 Audit DRF permission classes
  - Review `IsAuthenticatedOrHasUserAPIKey`
  - Check all API views have permissions
  - Verify team scoping on responses
- [ ] 3.2.2 Review API key security
  - Verify keys are hashed in database
  - Add key rotation capability
  - Document key management
- [ ] 3.2.3 Add API rate limiting
  - Implement per-user rate limits
  - Implement per-API-key rate limits
  - Configure appropriate limits
- [ ] 3.2.4 Review API error responses
  - Check for sensitive data in errors
  - Standardize error format
  - Remove stack traces in production

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
- [ ] 4.1.1 Audit logging for sensitive data
  - Search logs for token patterns
  - Check exception logging configuration
  - Add sensitive data filtering
- [ ] 4.1.2 Implement security event logging
  - Log authentication failures
  - Log privilege changes
  - Log OAuth connections/disconnections
- [ ] 4.1.3 Add anomaly detection alerts
  - Alert on multiple failed logins
  - Alert on unusual OAuth patterns
  - Alert on cross-team access attempts
- [ ] 4.1.4 Review Sentry configuration
  - Enable PII filtering
  - Review data scrubbing rules
  - Test sensitive data exclusion

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
- [ ] 4.2.4 Review third-party package permissions
  - Document django-allauth access
  - Document django-hijack access
  - Document external API libraries

### Section 4.3: Production Hardening
- [ ] 4.3.1 Review Django DEBUG setting
  - Verify `DEBUG=False` in production
  - Check for debug-only code paths
- [ ] 4.3.2 Audit ALLOWED_HOSTS
  - Verify no wildcard `*` in production
  - Configure specific domains only
- [ ] 4.3.3 Review admin URL security
  - Consider changing `/admin/` path
  - Add IP restriction in production
  - Require 2FA for admin access
- [ ] 4.3.4 Implement secrets rotation procedure
  - Document key rotation process
  - Create rotation runbook
  - Test rotation without downtime
- [ ] 4.3.5 Review database connection security
  - Verify SSL/TLS for database
  - Check connection credentials
  - Review database permissions

---

## Progress Summary

| Phase | Section | Progress | Notes |
|-------|---------|----------|-------|
| 1 | 1.1 OAuth Tokens | 0/5 | |
| 1 | 1.2 Webhooks | 5/5 | ✅ COMPLETE - Info leak, replay, rate limit, csrf docs, payload limits |
| 2 | 2.1 Authorization | 1/5 | IDOR tests created |
| 2 | 2.2 Input Validation | 2/5 | XSS fixed, |safe filter audited |
| 2 | 2.3 Data Isolation | 1/3 | Cross-team test suite created |
| 3 | 3.1 Sessions | 1/4 | Session rotation added |
| 3 | 3.2 API | 0/4 | |
| 3 | 3.3 Headers | 5/5 | ✅ COMPLETE |
| 4 | 4.1 Logging | 0/4 | |
| 4 | 4.2 Dependencies | 3/4 | ✅ Vulnerabilities fixed, Dependabot |
| 4 | 4.3 Production | 0/5 | HSTS settings added |

**Total:** 18/49 tasks completed (37%)

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
