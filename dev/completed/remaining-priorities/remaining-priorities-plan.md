# Remaining Priorities: Implementation Plan

**Last Updated:** 2025-12-21
**Status:** Ready for Implementation

## Executive Summary

With file splitting complete (Phase 1 of codebase improvements), this plan covers the remaining improvement priorities identified in the comprehensive codebase review. These are refinements rather than critical fixes - the codebase is MVP-ready.

## Priority Order

| Priority | Category | Effort | Impact |
|----------|----------|--------|--------|
| 1 | Bug Fixes | Low | High |
| 2 | Security Hardening | Low | Medium |
| 3 | Test Coverage Gaps | Medium | Medium |
| 4 | Complete Active Work | Varies | Varies |

---

## Priority 1: Bug Fixes (High Impact, Low Effort)

### 1.1 Quick Stats Display Bug

**Problem:** Dashboard quick stats not displaying correctly due to data structure mismatch.

**Root Cause:** Template expects nested dictionary structure, but service returns flat structure.

**Files:**
- `templates/web/components/quick_stats.html`
- `apps/dashboard/services/quick_stats.py`

**Fix:** Align template with service output format (flat dict).

**Effort:** 30 minutes

### 1.2 Survey Comment Dispatch

**Problem:** Survey comments not being posted to GitHub PRs after merge.

**Root Cause:** Missing task dispatch call in PR processor.

**Files:**
- `apps/metrics/processors.py`
- Add call to `post_survey_comment_task.delay(pr.id)` after PR merge detection

**Effort:** 1 hour

---

## Priority 2: Security Hardening (Medium Impact, Low Effort)

### 2.1 OAuth State Timestamp

**Problem:** OAuth state tokens have no expiration, allowing replay attacks.

**Files:**
- `apps/integrations/services/github_oauth.py`
- `apps/integrations/services/jira_oauth.py`

**Fix:** Add `iat` (issued at) timestamp to state, validate age < 10 minutes.

**Effort:** 30 minutes per provider

### 2.2 Webhook Payload Size Limits

**Problem:** GitHub webhook handler doesn't limit payload size (Slack does).

**Files:**
- `apps/web/views.py` (GitHub webhook handler)

**Fix:** Add 1MB payload size check before processing.

**Effort:** 15 minutes

### 2.3 Encryption Key Validation

**Problem:** No startup validation of Fernet encryption key format.

**Files:**
- `apps/integrations/services/encryption.py`

**Fix:** Add format validation at module load time.

**Effort:** 15 minutes

---

## Priority 3: Test Coverage Gaps (Medium Impact, Medium Effort)

### 3.1 Support App Tests

**Files to create:**
- `apps/support/tests/test_forms.py`
- `apps/support/tests/test_views.py`

**Effort:** 2 hours

### 3.2 Content App Tests

**Files to create:**
- `apps/content/tests/test_models.py`

**Effort:** 2 hours

### 3.3 AI Detector Tests

**Files to create:**
- `apps/metrics/tests/test_ai_detector.py`
- `apps/metrics/tests/test_ai_patterns.py`

**Effort:** 3 hours

### 3.4 Dashboard Services Tests

**Files to create:**
- `apps/dashboard/tests/test_services.py`

**Effort:** 1 hour

---

## Priority 4: Complete Active Work

### 4.1 Dashboard UX Improvements

**Location:** `dev/active/dashboard-ux-improvements/`
**Status:** Phase 0.2 incomplete (Quick Stats fix overlaps with Priority 1.1)

### 4.2 Skip Responded Reviewers

**Location:** `dev/active/skip-responded-reviewers/`
**Status:** TDD implementation incomplete

**Goal:** Prevent duplicate survey requests when reviewer already responded.

### 4.3 GitHub Surveys Phase 2

**Location:** `dev/active/github-surveys-phase2/`
**Status:** Partial implementation

---

## Implementation Approach

### Order of Operations

1. **Bug fixes first** - Immediate user-facing impact
2. **Security hardening** - Quick wins with lasting value
3. **Test coverage** - Improves confidence for future changes
4. **Active work completion** - Based on user priority

### TDD Workflow

All implementations should follow Red-Green-Refactor:
1. Write failing test
2. Implement minimum code to pass
3. Refactor while keeping tests green

---

## What NOT to Change

1. **Django → pytest migration** - Not worth the rewrite effort
2. **Team isolation patterns** - Already excellent
3. **Service layer structure** - Well-organized
4. **OAuth patterns** - Consistent across providers
5. **Theme colors** - Requires explicit approval

---

## Success Metrics

- [ ] All bug fixes verified in browser
- [ ] Security improvements have test coverage
- [ ] Test coverage gaps filled
- [ ] No regression in existing 1,942 tests
