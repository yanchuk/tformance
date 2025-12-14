# Security Hardening Tasks

**Last Updated:** 2025-12-13
**Status:** Completed (Phase 1 & 2.1)
**Total Tasks:** 12 | **Completed:** 9 | **Remaining:** 3

---

## Phase 1: EncryptedTextField Implementation ✅ COMPLETE

### Section 1.1: Create EncryptedTextField ✅
- [x] 1.1.1 Create `apps/utils/fields.py` with EncryptedTextField class
  - Implemented `from_db_value()` for automatic decryption
  - Implemented `get_prep_value()` for automatic encryption
  - Handle None and empty string values
  - Added idempotency check (don't double-encrypt)
  - Added `deconstruct()` for migrations
  - **Completed:** 2025-12-13 via TDD RED-GREEN-REFACTOR cycle

- [x] 1.1.2 Write comprehensive unit tests for EncryptedTextField
  - Created `apps/utils/tests/test_fields.py`
  - 12 tests covering all edge cases
  - **Completed:** 2025-12-13

### Section 1.2: Migrate IntegrationCredential Model ✅
- [x] 1.2.1 Update IntegrationCredential to use EncryptedTextField
  - Replaced `access_token = models.TextField()` with EncryptedTextField
  - Replaced `refresh_token = models.TextField()` with EncryptedTextField
  - **Completed:** 2025-12-13

- [x] 1.2.2 Create and run migration
  - Created `apps/integrations/migrations/0013_alter_integrationcredential_access_token_and_more.py`
  - Schema-only migration applied cleanly
  - **Completed:** 2025-12-13

- [x] 1.2.3 Verify existing data still works
  - All 634 integration tests pass
  - **Completed:** 2025-12-13

### Section 1.3: Code Cleanup ✅
- [x] 1.3.1 Remove explicit encrypt()/decrypt() calls from code
  - Updated `apps/integrations/views.py` - removed encrypt/decrypt calls
  - Updated `apps/integrations/services/jira_oauth.py` - removed encrypt/decrypt
  - Updated `apps/integrations/services/github_sync.py` - removed decrypt
  - Updated `apps/integrations/services/slack_client.py` - removed decrypt
  - **Completed:** 2025-12-13

- [x] 1.3.2 Update test fixtures to use plaintext values
  - Updated `apps/integrations/factories.py`
  - Updated all test files using explicit encrypt() calls
  - All 1205 tests pass
  - **Completed:** 2025-12-13

---

## Phase 2: Tenant Isolation Hardening ✅ PARTIAL

### Section 2.1: Enable Strict Context ✅
- [x] 2.1.1 Add STRICT_TEAM_CONTEXT to production settings
  - Added `STRICT_TEAM_CONTEXT = not DEBUG` to `tformance/settings.py`
  - Raises exception on missing team context in production
  - Allows silent fallback in development
  - **Completed:** 2025-12-13

- [x] 2.1.2 Verify no breaking changes
  - Full test suite passes (1205 tests)
  - **Completed:** 2025-12-13

### Section 2.2: Documentation and Prevention (Optional)
- [ ] 2.2.1 Document team isolation patterns in CLAUDE.md
  - Add section on when to use `for_team` vs `objects`
  - Document `STRICT_TEAM_CONTEXT` setting
  - Add warning about IDOR risks
  - Effort: S

- [ ] 2.2.2 Add code review checklist item
  - Add to PR template or .github/PULL_REQUEST_TEMPLATE.md
  - Checklist item: "Team-scoped models use `team=team` filter or `for_team` manager"
  - Effort: S

---

## Phase 3: Survey Channel Verification (Low Priority)

- [ ] 3.1.1 Verify GitHub comment survey task is auto-enabled
  - Check `post_survey_comment_task` task configuration
  - Ensure teams can collect AI data without Slack
  - Effort: S
  - Status: Deferred (existing implementation already works)

---

## Summary

### Implemented Features
1. **EncryptedTextField** - Custom Django field that transparently encrypts/decrypts data
2. **Automatic token encryption** - IntegrationCredential tokens now auto-encrypt
3. **Strict team context** - Production raises exceptions on missing team context

### Key Files Modified
- `apps/utils/fields.py` (NEW) - EncryptedTextField implementation
- `apps/utils/tests/test_fields.py` (NEW) - 12 unit tests
- `apps/integrations/models.py` - Use EncryptedTextField
- `apps/integrations/migrations/0013_*.py` (NEW) - Migration
- `apps/integrations/views.py` - Removed explicit encrypt/decrypt
- `apps/integrations/services/*.py` - Removed explicit decrypt
- `apps/integrations/factories.py` - Use plaintext tokens
- `apps/integrations/tests/*.py` - Updated for transparent encryption
- `tformance/settings.py` - Added STRICT_TEAM_CONTEXT
