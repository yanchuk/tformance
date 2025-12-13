# Security Hardening - Context Document

**Last Updated:** 2025-12-13 19:15 UTC
**Status:** Phase 1 & 2.1 COMPLETE - Ready for commit

---

## Current Implementation State

### COMPLETED This Session

1. **EncryptedTextField Implementation** (TDD: RED → GREEN → REFACTOR)
   - Created custom Django field with transparent encryption/decryption
   - Uses Fernet (AES-256) via existing `apps/integrations/services/encryption.py`
   - Lazy decryption pattern via descriptor for proper error handling

2. **IntegrationCredential Migration**
   - Changed `access_token` and `refresh_token` to EncryptedTextField
   - Migration `0013_alter_integrationcredential_access_token_and_more.py` applied
   - Removed 20+ explicit encrypt()/decrypt() calls across codebase

3. **STRICT_TEAM_CONTEXT Setting**
   - Added `STRICT_TEAM_CONTEXT = not DEBUG` to settings.py
   - Production raises `EmptyTeamContextException` on missing team context
   - Development allows silent `.none()` fallback

---

## Key Decisions Made

1. **Field-level vs Model.save() encryption**: Chose EncryptedTextField because:
   - Automatic - cannot be bypassed
   - Works with all ORM operations (QuerySet.update(), bulk operations)
   - Testable in isolation
   - Clear API for developers

2. **Lazy decryption via descriptor**: Required because:
   - Django's `from_db_value()` runs during query, not attribute access
   - Need to raise `InvalidToken` when attribute is accessed, not during filter()
   - `EncryptedValue` wrapper marks values as needing decryption

3. **Idempotency check**: `get_prep_value()` tries to decrypt first:
   - If success → value already encrypted, return as-is
   - If fail → encrypt the value
   - Handles re-saving without double-encryption

4. **Test file updates**: Changed from mocking `decrypt()` to using actual field:
   - Tests now verify real encryption behavior
   - Removed ~22 `@patch("apps.integrations.services.encryption.decrypt")` decorators
   - Changed expected tokens from `"decrypted_token"` to actual plaintext values

---

## Files Modified

### NEW Files
| File | Purpose |
|------|---------|
| `apps/utils/fields.py` | EncryptedTextField, EncryptedValue, EncryptedFieldDescriptor |
| `apps/utils/tests/test_fields.py` | 12 unit tests for field |
| `apps/integrations/migrations/0013_*.py` | Schema migration |

### MODIFIED Files - Production Code
| File | Changes |
|------|---------|
| `apps/integrations/models.py` | Use EncryptedTextField for tokens |
| `apps/integrations/views.py` | Remove encrypt/decrypt calls (6 places) |
| `apps/integrations/services/jira_oauth.py` | Remove encrypt/decrypt calls |
| `apps/integrations/services/github_sync.py` | Remove decrypt calls (2 places) |
| `apps/integrations/services/slack_client.py` | Remove decrypt import/call |
| `apps/integrations/factories.py` | Use plaintext tokens |
| `tformance/settings.py` | Add STRICT_TEAM_CONTEXT |

### MODIFIED Files - Tests
| File | Changes |
|------|---------|
| `apps/integrations/tests/test_views.py` | Updated encryption tests |
| `apps/integrations/tests/test_jira_views.py` | Updated encryption test |
| `apps/integrations/tests/test_jira_oauth.py` | Remove encrypt() calls |
| `apps/integrations/tests/test_jira_client.py` | Remove encrypt() calls (4 places) |
| `apps/integrations/tests/test_slack_client.py` | Remove decrypt mock |
| `apps/integrations/tests/test_slack_user_matching.py` | Remove encrypt() calls |
| `apps/integrations/tests/test_jira_user_matching.py` | Remove encrypt() calls |
| `apps/integrations/tests/test_github_sync.py` | Massive update - 22 mock removals |

---

## Tricky Bugs Fixed

1. **Double-decryption error**: After adding EncryptedTextField, views still called `decrypt()` on already-decrypted values → `InvalidToken` error. Fixed by removing explicit decrypt() calls.

2. **Test token mismatch**: Tests mocked decrypt to return `"decrypted_token"` but expected that value in assertions. Updated to use actual token from fixtures (`"encrypted_token_12345"`).

3. **github_sync tests with inline patches**: Tests used `with patch(...)` context manager pattern - couldn't use simple decorator removal. Required manual editing of each.

---

## Test Coverage

```bash
# All tests pass
make test ARGS='--keepdb'  # 1205 tests OK

# Field-specific tests
make test ARGS='apps.utils.tests.test_fields --keepdb'  # 12 tests OK

# Integration tests
make test ARGS='apps.integrations --keepdb'  # 634 tests OK
```

---

## Migrations Status

| App | Migration | Status |
|-----|-----------|--------|
| integrations | 0013_alter_integrationcredential_access_token_and_more | ✅ Applied |

No pending migrations. Run `make migrations` to verify.

---

## Remaining Work (Optional)

### Phase 2.2: Documentation (Low Priority)
- [ ] Document `for_team` vs `objects` patterns in CLAUDE.md
- [ ] Add PR checklist item for team-scoped queries

### Phase 3: Survey Verification (Deferred)
- [ ] Verify GitHub comment survey task enabled
- Already works - just needs documentation

---

## Handoff Notes

### What to Do on Session Resume

1. **Verify clean state**:
   ```bash
   make test ARGS='--keepdb'  # Should be 1205 tests OK
   make migrations ARGS='--check'  # Should be "No changes detected"
   ```

2. **Ready for commit** - All changes are complete and tested

3. **Uncommitted changes** (from git status):
   - Modified: `apps/integrations/` (models, views, services, tests, factories)
   - Modified: `apps/utils/` (new fields.py, tests)
   - Modified: `tformance/settings.py`
   - New: `dev/active/security-hardening/` docs

### Commit Message Suggestion
```
feat: Add EncryptedTextField for automatic token encryption

- Implement EncryptedTextField with Fernet encryption
- Migrate IntegrationCredential tokens to use encrypted field
- Remove explicit encrypt()/decrypt() calls
- Add STRICT_TEAM_CONTEXT for production safety
- 12 new tests for EncryptedTextField
- All 1205 tests passing
```

---

## Architecture Notes

### EncryptedTextField Design

```
┌─────────────────┐      ┌─────────────────┐
│   User Code     │      │    Database     │
│  (plaintext)    │      │  (encrypted)    │
└────────┬────────┘      └────────┬────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────┐
│         EncryptedTextField              │
│                                         │
│  get_prep_value() ───────► encrypt()    │
│                                         │
│  from_db_value() ◄─── EncryptedValue    │
│                            │            │
│  EncryptedFieldDescriptor  │            │
│  __get__() ───────────────►│ decrypt()  │
│                            │            │
└─────────────────────────────────────────┘
```

### Why Lazy Decryption?

Django calls `from_db_value()` during query execution, before attribute access.
If we decrypt there and the data is corrupted, the exception happens during
`Model.objects.get()` - hard to catch.

With lazy decryption:
- `from_db_value()` wraps value in `EncryptedValue`
- `EncryptedFieldDescriptor.__get__()` decrypts on access
- Exception raised at `model.access_token` - easy to catch
