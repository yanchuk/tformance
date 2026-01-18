# Tasks: GitHub OAuth Name Population

**Last Updated:** 2026-01-18

## Progress Tracker

| Phase | Status | Tasks |
|-------|--------|-------|
| RED (Tests) | ✅ Complete | 2/2 |
| GREEN (Impl) | ✅ Complete | 2/2 |
| REFACTOR | ✅ Complete | 1/1 |

---

## Phase 1: RED - Write Failing Tests

### 1.1 Unit Tests for Name Parsing
**Effort:** S | **Status:** ✅ Complete

**File:** `apps/auth/tests/test_github_login.py`

Add test class for `_parse_github_name()`:
- [ ] Test two-word name: `"Ivan Yanchuk"` → `("Ivan", "Yanchuk")`
- [ ] Test single name: `"Ivan"` → `("Ivan", "")`
- [ ] Test multi-part last name: `"Ivan van Beethoven"` → `("Ivan", "van Beethoven")`
- [ ] Test None input: `None` → `("", "")`
- [ ] Test empty string: `""` → `("", "")`
- [ ] Test whitespace only: `"   "` → `("", "")`
- [ ] Test padded name: `"  Ivan  Yanchuk  "` → `("Ivan", "Yanchuk")`
- [ ] Test long name truncation: 200+ chars → 150 char limit

**Acceptance Criteria:**
- All tests fail with `ImportError` or `AssertionError` (function doesn't exist yet)
- Tests are in their own class `TestParseGitHubName`

---

### 1.2 Integration Test for User Creation with Name
**Effort:** S | **Status:** ✅ Complete

**File:** `apps/auth/tests/test_github_login.py`

Update existing `test_login_creates_new_user` or add new test:
- [ ] Mock GitHub response includes `"name": "Test User"`
- [ ] Assert `user.first_name == "Test"`
- [ ] Assert `user.last_name == "User"`

Add test for empty name scenario:
- [ ] Mock GitHub response with `"name": None`
- [ ] Assert `user.first_name == ""`
- [ ] Assert `user.last_name == ""`

**Acceptance Criteria:**
- Tests fail because user creation doesn't set first_name/last_name

---

## Phase 2: GREEN - Implement Feature

### 2.1 Add Name Parsing Helper
**Effort:** XS | **Status:** ✅ Complete

**File:** `apps/auth/views/github.py`

Add function after imports:
```python
def _parse_github_name(full_name: str | None) -> tuple[str, str]:
    """Split GitHub full name into (first_name, last_name)."""
    if not full_name:
        return ("", "")
    parts = full_name.strip().split(maxsplit=1)
    first_name = parts[0][:150] if parts else ""
    last_name = parts[1][:150] if len(parts) > 1 else ""
    return (first_name, last_name)
```

**Acceptance Criteria:**
- Unit tests for `_parse_github_name()` pass

---

### 2.2 Update User Creation
**Effort:** XS | **Status:** ✅ Complete

**File:** `apps/auth/views/github.py`
**Location:** `_handle_login_callback()`, lines 187-190

Update to:
```python
first_name, last_name = _parse_github_name(github_name)
user = CustomUser.objects.create(
    username=github_login_name,
    email=github_email or f"{github_login_name}@github.placeholder",
    first_name=first_name,
    last_name=last_name,
)
```

**Acceptance Criteria:**
- Integration tests pass
- All existing `test_github_login.py` tests still pass

---

## Phase 3: REFACTOR

### 3.1 Review and Polish
**Effort:** XS | **Status:** ✅ Complete

- [x] Run `make ruff` to format code
- [x] Run full test suite: `.venv/bin/pytest apps/auth/tests/ -v`
- [x] Review for any code duplication or improvements
- [x] Update docstrings if needed

**Acceptance Criteria:**
- Code passes linting
- All tests pass
- No regressions

---

## Verification Checklist

After all phases complete:
- [x] `.venv/bin/pytest apps/auth/tests/test_github_login.py -v` - All 27 tests pass
- [x] `make ruff` - No errors
- [ ] Manual test (optional): Sign up via GitHub, check `first_name` in admin

---

## Notes

- No database migrations needed (using existing AbstractUser fields)
- No backfill needed (no existing users)
