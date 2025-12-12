# Security Audit Plan: AI Impact Analytics Platform

**Last Updated:** 2025-12-13
**Status:** Planning
**Risk Level:** High Priority (handles OAuth tokens, PII, external API integrations)

---

## Executive Summary

This document outlines a comprehensive security audit plan for the tformance AI Impact Analytics Platform. The platform handles sensitive data including OAuth tokens for GitHub/Jira/Slack, team metrics, and developer information. Given the SaaS nature and external integrations, a thorough security review is critical before production deployment.

### Key Security Domains

| Domain | Risk Level | Priority |
|--------|------------|----------|
| OAuth Token Management | Critical | P0 |
| Webhook Security | High | P0 |
| Authentication & Authorization | High | P1 |
| Data Isolation (Multi-tenancy) | High | P1 |
| Input Validation & Injection | Medium | P1 |
| Session & Cookie Security | Medium | P2 |
| API Security | Medium | P2 |
| Logging & Monitoring | Medium | P2 |
| Dependency Vulnerabilities | Medium | P3 |
| Production Hardening | High | P3 |

---

## Current State Analysis

### Existing Security Measures (Strengths)

1. **OAuth Token Encryption**
   - Fernet encryption (AES-256) for OAuth tokens (`apps/integrations/services/encryption.py`)
   - Encryption key required via `INTEGRATION_ENCRYPTION_KEY` environment variable

2. **Cookie Security**
   - `SESSION_COOKIE_HTTPONLY = True`
   - `SESSION_COOKIE_SECURE = not DEBUG` (secure in production)
   - `CSRF_COOKIE_HTTPONLY = True`
   - `CSRF_COOKIE_SECURE = not DEBUG`
   - `SameSite=Lax` for both session and CSRF cookies

3. **Webhook Signature Validation**
   - GitHub webhooks validate `X-Hub-Signature-256` with timing-safe comparison (`apps/web/views.py:96`)
   - Slack webhooks verify signature using `SignatureVerifier` (`apps/integrations/webhooks/slack_interactions.py:37`)

4. **Rate Limiting**
   - OAuth callbacks rate-limited to 10/min per IP (`@ratelimit(key="ip", rate="10/m")`)

5. **Team Isolation**
   - `BaseTeamModel` with `team` foreign key on all metrics tables
   - `TeamScopedManager` for automatic team filtering
   - `@login_and_team_required` and `@team_admin_required` decorators

6. **Password Validation**
   - Django's standard password validators enabled

7. **CSRF Protection**
   - Django CSRF middleware enabled
   - Trusted origins configurable via `CSRF_TRUSTED_ORIGINS`

### Identified Security Gaps (Weaknesses)

1. **Missing Security Headers**
   - No Content-Security-Policy (CSP)
   - No X-Content-Type-Options
   - No Referrer-Policy
   - No Permissions-Policy

2. **Potential Template Injection**
   - `mark_safe` usage in `apps/content/blocks.py:13`
   - `|safe` filter usage in template tags

3. **Missing Input Validation**
   - Form POST data in views used directly without sanitization
   - Integer conversion from POST data without validation (`int(request.POST.get(...)`)

4. **Logging Sensitive Data**
   - Error logging may include tokens or secrets in exception traces

5. **Webhook Response Leakage**
   - GitHub webhook returns `team_id` in response body (information disclosure)

6. **Session/Token Lifecycle**
   - No OAuth token refresh implementation visible
   - Token expiration handling unclear

7. **Admin Panel Security**
   - Admin accessible at predictable `/admin/` path
   - No additional 2FA enforcement for admin

---

## Implementation Phases

### Phase 1: Critical Security (P0)

**Focus:** OAuth token security, webhook hardening, critical vulnerabilities

#### Section 1.1: OAuth Token Security Audit

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 1.1.1 | Audit token storage encryption | S | Verify Fernet key is properly secured, rotation strategy exists |
| 1.1.2 | Implement token refresh handling | M | Auto-refresh tokens before expiration for Jira/Slack |
| 1.1.3 | Add token expiration monitoring | M | Alert/log when tokens approach expiration |
| 1.1.4 | Review token scope minimization | S | Verify minimal OAuth scopes requested |
| 1.1.5 | Secure state parameter validation | S | Verify HMAC-signed state prevents CSRF on OAuth flows |

#### Section 1.2: Webhook Security Hardening

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 1.2.1 | Remove `team_id` from webhook responses | S | No internal IDs exposed in responses |
| 1.2.2 | Add webhook replay protection | M | Implement timestamp validation (reject >5min old) |
| 1.2.3 | Add webhook rate limiting | M | Per-source IP rate limits on webhook endpoints |
| 1.2.4 | Audit `@csrf_exempt` endpoints | S | Document all exempt endpoints, verify necessity |
| 1.2.5 | Add webhook payload size limits | S | Reject payloads >1MB |

---

### Phase 2: Access Control & Data Protection (P1)

**Focus:** Authorization, multi-tenancy, injection prevention

#### Section 2.1: Authorization Audit

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 2.1.1 | Audit team isolation in all views | L | All views properly scoped to team |
| 2.1.2 | Review `@team_admin_required` usage | M | Admin-only actions properly protected |
| 2.1.3 | Add IDOR (Insecure Direct Object Reference) tests | L | Tests verify cross-team access blocked |
| 2.1.4 | Review Membership role escalation | M | No path for member to become admin without proper auth |
| 2.1.5 | Audit API permission classes | M | All API endpoints have proper permission checks |

#### Section 2.2: Input Validation & Injection Prevention

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 2.2.1 | Audit all POST data handling | L | All inputs validated before use |
| 2.2.2 | Review `mark_safe` usage | S | Replace with `format_html` or sanitize inputs |
| 2.2.3 | Audit template `|safe` filter usage | M | Remove or justify each usage |
| 2.2.4 | Add input sanitization utilities | M | Centralized validation helpers |
| 2.2.5 | Review SQL query construction | S | No raw SQL with user input |

#### Section 2.3: Data Isolation Testing

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 2.3.1 | Create cross-team access test suite | L | Tests cover all team-scoped models |
| 2.3.2 | Audit `objects` vs `for_team` manager usage | M | Identify unintended use of unfiltered manager |
| 2.3.3 | Review admin panel team scoping | M | Admin users can only see authorized teams |

---

### Phase 3: Session & API Security (P2)

**Focus:** Session management, API hardening, cookies

#### Section 3.1: Session Security

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 3.1.1 | Review session timeout configuration | S | Appropriate session timeout for SaaS |
| 3.1.2 | Implement session rotation on login | M | New session ID after authentication |
| 3.1.3 | Add concurrent session limits | M | Option to limit active sessions per user |
| 3.1.4 | Review hijack functionality security | M | Proper audit trail for impersonation |

#### Section 3.2: API Security

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 3.2.1 | Audit DRF permission classes | M | All endpoints properly protected |
| 3.2.2 | Review API key security | S | Keys hashed, rotation supported |
| 3.2.3 | Add API rate limiting | M | Per-user/per-key rate limits |
| 3.2.4 | Review API error responses | S | No sensitive data in error messages |

#### Section 3.3: Security Headers

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 3.3.1 | Implement Content-Security-Policy | M | CSP header with appropriate directives |
| 3.3.2 | Add X-Content-Type-Options | S | `nosniff` header on all responses |
| 3.3.3 | Add Referrer-Policy | S | `strict-origin-when-cross-origin` |
| 3.3.4 | Add Permissions-Policy | S | Disable unnecessary browser features |
| 3.3.5 | Review HSTS configuration | S | HSTS enabled in production |

---

### Phase 4: Monitoring & Dependencies (P3)

**Focus:** Logging, monitoring, dependency security, production hardening

#### Section 4.1: Logging & Monitoring

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 4.1.1 | Audit logging for sensitive data | M | No tokens/passwords in logs |
| 4.1.2 | Implement security event logging | M | Log auth failures, privilege changes |
| 4.1.3 | Add anomaly detection alerts | L | Alert on suspicious patterns |
| 4.1.4 | Review Sentry configuration | S | Ensure PII filtering enabled |

#### Section 4.2: Dependency Security

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 4.2.1 | Run `pip-audit` on dependencies | S | No critical vulnerabilities |
| 4.2.2 | Set up Dependabot/Renovate | M | Automated dependency updates |
| 4.2.3 | Audit npm dependencies | S | No known vulnerabilities in frontend |
| 4.2.4 | Review third-party package permissions | M | Document what each package accesses |

#### Section 4.3: Production Hardening

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 4.3.1 | Review Django DEBUG setting | S | Ensure DEBUG=False in production |
| 4.3.2 | Audit ALLOWED_HOSTS | S | No wildcard in production |
| 4.3.3 | Review admin URL security | M | Consider admin URL obfuscation or IP restriction |
| 4.3.4 | Implement secrets rotation procedure | M | Documented process for key rotation |
| 4.3.5 | Review database connection security | S | SSL/TLS for database connections |

---

## Risk Assessment & Mitigation

### Critical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| OAuth token theft | Medium | Critical | Encryption at rest, minimize scope, audit access |
| Webhook spoofing | Low | High | Signature validation, replay protection |
| Cross-team data leak | Medium | Critical | Team isolation tests, audit `for_team` usage |
| SQL injection | Low | Critical | ORM usage, raw SQL audit |

### High Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| XSS via templates | Medium | High | Audit `mark_safe`, CSP headers |
| Session hijacking | Low | High | Secure cookies, session rotation |
| Privilege escalation | Low | High | Role validation, audit admin endpoints |
| Unpatched vulnerabilities | Medium | High | Dependency scanning, regular updates |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Critical vulnerabilities | 0 | SAST/DAST scanning |
| High vulnerabilities | 0 | Security review completion |
| OAuth token exposure incidents | 0 | Security monitoring |
| Cross-team data access attempts blocked | 100% | Unit/integration tests |
| Security headers compliance | A+ grade | securityheaders.com |
| Dependency vulnerabilities | 0 critical, <5 high | pip-audit, npm audit |

---

## Required Resources & Dependencies

### Tools Required

- **SAST:** Bandit (Python), Semgrep
- **DAST:** OWASP ZAP (manual testing)
- **Dependency Scanning:** pip-audit, npm audit
- **Secrets Scanning:** truffleHog, git-secrets
- **Header Analysis:** securityheaders.com, Mozilla Observatory

### External Dependencies

- Security headers middleware (django-csp or custom)
- Rate limiting expansion (django-ratelimit already in use)
- Audit logging package consideration

### Timeline Estimates

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1 (P0) | 1-2 weeks | None |
| Phase 2 (P1) | 2-3 weeks | Phase 1 complete |
| Phase 3 (P2) | 1-2 weeks | Phase 2 partial |
| Phase 4 (P3) | 1 week | Before production |

---

## Appendix: Files to Review

### Critical Security Files
- `apps/integrations/services/encryption.py` - Token encryption
- `apps/integrations/views.py` - OAuth flows
- `apps/web/views.py` - GitHub webhook handler
- `apps/integrations/webhooks/slack_interactions.py` - Slack webhook handler
- `tformance/settings.py` - Security configuration
- `apps/teams/decorators.py` - Authorization decorators
- `apps/teams/middleware.py` - Team context middleware
- `apps/teams/models.py` - BaseTeamModel and TeamScopedManager

### Template Files with Security Implications
- `apps/content/blocks.py` - `mark_safe` usage
- `apps/web/templatetags/form_tags.py` - Template helpers

### Webhook Endpoints (csrf_exempt)
- `/webhooks/github/` - GitHub webhooks
- `/integrations/slack/interactions/` - Slack interactions
