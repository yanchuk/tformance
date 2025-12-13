# Security Hardening Plan

**Last Updated:** 2025-12-13
**Status:** Planning
**Priority:** High

---

## Executive Summary

This plan addresses three verified security concerns identified during the security audit:

1. **Tenant Isolation** - `objects` manager exposes all tenant data; relies on developer diligence
2. **Token Encryption** - Plain `TextField` allows plaintext tokens; encryption is caller-dependent
3. **AI Metrics Capture** - GitHub survey alternative exists but may not be consistently enabled

### Estimated Total Effort: 2-3 days

---

## Current State Analysis

### 1. Tenant Isolation Architecture

**Current Implementation:**
```python
# apps/teams/models.py:112-131
class BaseTeamModel(BaseModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    objects = models.Manager()      # DEFAULT - returns ALL tenants
    for_team = TeamScopedManager()  # Must be explicitly used
```

**Risks:**
- Default `objects` manager bypasses team filtering
- `TeamScopedManager` silently returns `.none()` when no context (vs failing closed)
- PostgreSQL has no Row-Level Security (RLS) as defense-in-depth
- New views/serializers could accidentally expose cross-tenant data

**Current Mitigations:**
- All production code manually filters by `team=team` or `team=request.team`
- 18 cross-team isolation tests pass
- Security audit verified no IDOR vulnerabilities in current code

### 2. Token Encryption Architecture

**Current Implementation:**
```python
# apps/integrations/models.py:39-47
access_token = models.TextField()   # Plain TextField
refresh_token = models.TextField()  # Plain TextField
```

**Risks:**
- Encryption depends on caller using `encrypt()` before save
- Django Admin could potentially edit tokens (though currently hidden)
- Data migrations or management commands could persist plaintext
- Some test fixtures use plaintext tokens

**Current Mitigations:**
- All production views call `encrypt()` before saving
- Admin shows `token_masked` readonly field, hides actual tokens
- Factory properly encrypts test data

### 3. AI Metrics Without Slack

**Current Implementation:**
- Slack survey task skips if no Slack integration
- GitHub PR comment surveys exist as alternative
- Web-based survey forms work with token links

**Actual Status:** GitHub comment surveys provide alternative capture channel

---

## Proposed Future State

### Phase 1: Token Encryption Enforcement (High Priority)

Replace caller-dependent encryption with field-level enforcement:

```python
# apps/utils/fields.py (NEW)
class EncryptedTextField(models.TextField):
    """TextField that automatically encrypts/decrypts values."""

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return decrypt(value)

    def get_prep_value(self, value):
        if value is None:
            return value
        return encrypt(value)
```

### Phase 2: Tenant Isolation Hardening (Medium Priority)

Option A: Enable `STRICT_TEAM_CONTEXT=True` in production
- Raises exception instead of silent `.none()` when context missing
- Catches developer errors during development/testing

Option B: Make scoped manager the default (more invasive)
- Requires updating Django Admin configurations
- May break existing code patterns

### Phase 3: Survey Channel Redundancy (Low Priority)

Ensure teams without Slack still get AI metrics:
- Verify GitHub comment surveys are auto-enabled
- Add fallback logic if neither channel is available

---

## Implementation Phases

### Phase 1: EncryptedTextField Implementation

**Duration:** 1 day
**Risk Level:** Medium (data migration required)

#### Tasks:

1.1 **Create EncryptedTextField** (Size: M)
- Create `apps/utils/fields.py` with custom field class
- Implement `from_db_value()` and `get_prep_value()` methods
- Handle None values gracefully
- Add comprehensive docstring

1.2 **Write EncryptedTextField Tests** (Size: M)
- Test encryption on save
- Test decryption on read
- Test None handling
- Test with Django ORM operations (filter, update, etc.)
- Test with Django migrations

1.3 **Migrate IntegrationCredential Model** (Size: L)
- Replace `TextField` with `EncryptedTextField` for `access_token`
- Replace `TextField` with `EncryptedTextField` for `refresh_token`
- Data migration: existing encrypted values remain valid
- Remove explicit `encrypt()` calls from views (optional, for cleanup)

1.4 **Update Test Fixtures** (Size: S)
- Update tests that use plaintext tokens to use encrypted or let field handle it
- Verify factory still works correctly

1.5 **Verify Integration Tests** (Size: S)
- Run full test suite
- Verify OAuth flows work end-to-end

### Phase 2: Tenant Isolation Hardening

**Duration:** 0.5 day
**Risk Level:** Low

#### Tasks:

2.1 **Enable STRICT_TEAM_CONTEXT** (Size: S)
- Add `STRICT_TEAM_CONTEXT = True` to production settings
- Keep `False` in development for now (or `True` for strict testing)
- Update error handling to provide helpful messages

2.2 **Add Linting Rule** (Size: M)
- Create custom ruff/bandit rule to flag `.objects.` on BaseTeamModel subclasses
- Or add to code review checklist

2.3 **Document Team Isolation Pattern** (Size: S)
- Add section to CLAUDE.md about when to use `for_team` vs `objects`
- Document the `STRICT_TEAM_CONTEXT` setting

### Phase 3: Survey Channel Verification

**Duration:** 0.5 day
**Risk Level:** Low

#### Tasks:

3.1 **Audit GitHub Comment Survey Trigger** (Size: S)
- Verify `post_survey_comment_task` is called for all merged PRs
- Check task orchestration (which tasks call it)

3.2 **Add Fallback Documentation** (Size: S)
- Document how AI metrics are captured without Slack
- Update onboarding docs if needed

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Data migration breaks existing tokens | High | Low | No-op migration; encrypted values remain valid |
| EncryptedTextField breaks ORM queries | Medium | Medium | Extensive testing; filter by encrypted value works |
| STRICT_TEAM_CONTEXT breaks code | Medium | Low | Enable in production only; test in CI first |
| Admin access to raw tokens | Low | Low | Field already hidden in admin |

---

## Success Metrics

1. **Token Encryption:**
   - All token storage goes through EncryptedTextField
   - No plaintext tokens in database
   - All 50+ existing tests pass

2. **Tenant Isolation:**
   - `STRICT_TEAM_CONTEXT=True` in production settings
   - Exception raised on missing team context
   - Cross-team isolation tests remain green

3. **Survey Coverage:**
   - Documented survey flow for teams without Slack
   - GitHub comment surveys verified working

---

## Dependencies

- `cryptography` package (already installed for Fernet)
- Django 5.2.9 (already in use)
- No new package dependencies required

---

## Files to Create/Modify

### New Files:
- `apps/utils/fields.py` - EncryptedTextField class
- `apps/utils/tests/test_fields.py` - Field tests
- `apps/integrations/migrations/XXXX_encrypted_token_fields.py` - Migration

### Modified Files:
- `apps/integrations/models.py` - Use EncryptedTextField
- `tformance/settings.py` - Add STRICT_TEAM_CONTEXT
- `CLAUDE.md` - Document team isolation patterns

---

## Rollback Plan

### Phase 1 Rollback:
- Revert to TextField (migration is reversible)
- Existing encrypted values can be read by EncryptedTextField OR manually decrypted

### Phase 2 Rollback:
- Set `STRICT_TEAM_CONTEXT=False` in settings
- No data changes involved

---

## Testing Requirements

### Unit Tests:
- EncryptedTextField encryption/decryption
- EncryptedTextField with None values
- EncryptedTextField with empty strings

### Integration Tests:
- OAuth token storage with new field
- OAuth token retrieval with new field
- Cross-team isolation with STRICT_TEAM_CONTEXT

### Manual Tests:
- Connect new GitHub integration
- Verify token stored encrypted
- Verify token decrypted on use
