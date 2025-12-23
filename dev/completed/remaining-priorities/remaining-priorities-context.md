# Remaining Priorities: Context

**Last Updated:** 2025-12-21 (Session End)
**Status:** Priority 1-2 Complete, Priority 3-4 Remaining

## Background

This work follows the completion of the codebase file-splitting initiative which reorganized large files into modular structures. The remaining priorities are refinements to an already MVP-ready codebase.

---

## Completed Work (2025-12-21)

### Priority 1: Bug Fixes - Already Working
Both identified "bugs" were false positives in the original assessment:
- **Quick Stats Display**: Service and template structures match perfectly (nested dicts)
- **Survey Comment Dispatch**: Already dispatches `post_survey_comment_task.delay(pr.id)` in `processors.py:192`

### Priority 2: Security Hardening - Implemented

| Enhancement | File | Change |
|-------------|------|--------|
| OAuth state timestamps | `github_oauth.py`, `jira_oauth.py` | Added `iat` timestamp with 10-minute expiry validation |
| Webhook payload limit | `apps/web/views.py` | Already implemented at 5MB |
| Encryption key validation | `encryption.py` | Added format validation (32-byte URL-safe base64) |

**Tests Verified**: 729 integrations tests, 84 OAuth tests, 19 encryption tests - all passing

---

## Key Files by Priority

### Priority 1: Bug Fixes

| File | Purpose | Issue |
|------|---------|-------|
| `templates/web/components/quick_stats.html` | Dashboard stats display | Template structure mismatch |
| `apps/dashboard/services/quick_stats.py` | Stats calculation service | Returns flat dict |
| `apps/metrics/processors.py` | PR processing logic | Missing survey dispatch |

### Priority 2: Security

| File | Purpose | Enhancement |
|------|---------|-------------|
| `apps/integrations/services/github_oauth.py` | GitHub OAuth flow | Add state timestamp |
| `apps/integrations/services/jira_oauth.py` | Jira OAuth flow | Add state timestamp |
| `apps/web/views.py` | Webhook handlers | Add payload size limit |
| `apps/integrations/services/encryption.py` | Token encryption | Add key validation |

### Priority 3: Test Coverage

| Directory | Current State | Gap |
|-----------|---------------|-----|
| `apps/support/tests/` | Minimal | Forms and views untested |
| `apps/content/tests/` | Missing | Wagtail models untested |
| `apps/metrics/tests/` | Good | AI detector untested |
| `apps/dashboard/tests/` | Partial | Services untested |

---

## Related Active Work

| Directory | Status | Notes |
|-----------|--------|-------|
| `dev/active/dashboard-ux-improvements/` | Partial | Phase 0.2 overlaps bug fix |
| `dev/active/skip-responded-reviewers/` | Incomplete | TDD phases pending |
| `dev/active/github-surveys-phase2/` | Partial | Some features implemented |
| `dev/active/multi-token-github/` | Complete | Can be archived |
| `dev/active/real-project-seeding/` | Complete | Can be archived |

---

## Dependencies

### Bug Fixes
- None - can be done independently

### Security
- OAuth changes need integration testing
- Webhook changes need GitHub test payload

### Test Coverage
- Factory patterns already established
- Follow existing test structure in split directories

---

## Decisions Made

1. **Fix template, not service** - Quick stats service has correct flat structure; template should adapt
2. **10-minute state expiry** - Standard OAuth practice for state token validity
3. **1MB payload limit** - Matches Slack webhook limit already in place
4. **TDD for all new tests** - Follow project guidelines

---

## Verification Commands

```bash
# Run all tests
make test

# Run specific app tests
make test ARGS='apps.support'
make test ARGS='apps.content'
make test ARGS='apps.dashboard'

# Run security-related tests
make test ARGS='apps.integrations.tests.test_oauth'

# Check dev server
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

---

## Files Completed (Codebase Improvements Phase 1)

For reference, these splits are complete:

- `apps/metrics/models/` - 8 files (from 1,518 lines)
- `apps/integrations/views/` - 6 files (from 1,321 lines)
- `apps/integrations/tests/github_sync/` - 11 files (from 4,391 lines)
- `apps/metrics/tests/dashboard/` - 12 files (from 3,142 lines)
- `apps/metrics/tests/models/` - 13 files (from 2,847 lines)

All 1,942 tests passing.

---

## Session Handoff (2025-12-21)

### Files Modified This Session

| File | Change |
|------|--------|
| `apps/integrations/services/github_oauth.py` | Added `time` import, `OAUTH_STATE_MAX_AGE_SECONDS=600`, `iat` timestamp in `create_oauth_state()`, expiry validation in `verify_oauth_state()` |
| `apps/integrations/services/jira_oauth.py` | Same OAuth timestamp changes as GitHub |
| `apps/integrations/services/encryption.py` | Added `_reset_fernet_cache()`, `_validate_and_create_fernet()` with format validation, cached Fernet instance |
| `apps/integrations/tests/test_encryption.py` | Added `setUp()`/`tearDown()` to reset cache, updated wrong-key test |

### No Migrations Needed
All changes were to service layer code, no model changes.

### Uncommitted Changes
The security improvements are uncommitted. To commit:
```bash
git add apps/integrations/services/github_oauth.py apps/integrations/services/jira_oauth.py apps/integrations/services/encryption.py apps/integrations/tests/test_encryption.py
git commit -m "Add OAuth state timestamp validation and encryption key format validation"
```

### Next Steps (Priority 3: Test Coverage)
Was about to start writing tests for `apps/support/` app. Files to test:
- `apps/support/forms.py` - Support request form
- `apps/support/views.py` - Support form views

Create test file: `apps/support/tests/test_forms.py` and `apps/support/tests/test_views.py`

### Verification Commands
```bash
# Verify all tests still pass
make test ARGS='apps.integrations --keepdb'

# Check for uncommitted changes
git status

# Run full test suite
make test
```

### Key Discoveries
1. **False positives in plan**: Quick Stats and Survey Comment bugs didn't exist
2. **Webhook limit already exists**: 5MB limit at `apps/web/views.py:44`
3. **OAuth state uses Django Signer**: Already tamper-proof, just needed timestamp
4. **Encryption caching**: Required `_reset_fernet_cache()` for test isolation
