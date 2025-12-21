# Remaining Priorities: Task Checklist

**Last Updated:** 2025-12-21 (Session End)

## Overview

- **Total Tasks:** 15
- **Completed:** 10
- **In Progress:** 0
- **Remaining:** 5

### ⚠️ UNCOMMITTED CHANGES
Security improvements need to be committed:
```bash
git add apps/integrations/services/github_oauth.py apps/integrations/services/jira_oauth.py apps/integrations/services/encryption.py apps/integrations/tests/test_encryption.py
git commit -m "Add OAuth state timestamp validation and encryption key format validation"
```

---

## Priority 1: Bug Fixes [2/2] ✅ COMPLETE (Already Working)

### 1.1 Quick Stats Display [1/1]
- [x] ~~Fix template/service mismatch~~ **Already correct** - service returns nested dict, template expects nested dict

### 1.2 Survey Comment Dispatch [1/1]
- [x] ~~Add task dispatch after PR merge~~ **Already implemented** - `post_survey_comment_task.delay(pr.id)` in `processors.py:192`

---

## Priority 2: Security Hardening [4/4] ✅ COMPLETE

### 2.1 OAuth State Timestamps [2/2]
- [x] Add `iat` timestamp to GitHub OAuth state (`apps/integrations/services/github_oauth.py`)
- [x] Add `iat` timestamp to Jira OAuth state (`apps/integrations/services/jira_oauth.py`)

### 2.2 Webhook Security [1/1]
- [x] ~~Add payload size limit~~ **Already implemented** - `MAX_WEBHOOK_PAYLOAD_SIZE = 5MB` in `apps/web/views.py:44`

### 2.3 Encryption Validation [1/1]
- [x] Add Fernet key format validation at first use (`apps/integrations/services/encryption.py`)

---

## Priority 3: Test Coverage [4/4] ✅ COMPLETE

### 3.1 Support App [1/1]
- [x] Create `apps/support/tests/test_forms.py` and `test_views.py` (13 tests)

### 3.2 Content App [SKIPPED]
- [x] ~~Create content tests~~ **Skipped** - Wagtail CMS not critical for MVP

### 3.3 AI Detection [1/1]
- [x] ~~Create AI detector tests~~ **Already existed** - 38 tests in `test_ai_detector.py`

### 3.4 Dashboard Services [1/1]
- [x] Create `apps/dashboard/tests/test_services.py` (7 tests)

---

## Priority 4: Active Work Completion [0/4]

### 4.1 Dashboard UX [0/1]
- [ ] Complete Phase 0.2 in `dev/active/dashboard-ux-improvements/`

### 4.2 Skip Responded Reviewers [0/1]
- [ ] Complete TDD implementation in `dev/active/skip-responded-reviewers/`

### 4.3 GitHub Surveys Phase 2 [0/1]
- [ ] Review and complete `dev/active/github-surveys-phase2/`

### 4.4 Archive Completed Work [0/1]
- [ ] Move `multi-token-github/` and `real-project-seeding/` to `dev/completed/`

---

## Verification [0/2]

- [ ] All 1,942+ tests passing after changes
- [ ] Dev server running and responsive

---

## Notes

### Blockers
- None identified

### Decisions Made
- Fix template structure, not service output
- Use 10-minute OAuth state expiry
- Follow existing TDD patterns

### Quick Reference

```bash
# Run tests
make test

# Check specific apps
make test ARGS='apps.support'
make test ARGS='apps.dashboard'

# Verify dev server
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```
