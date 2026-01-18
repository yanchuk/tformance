# Plan: Populate User Profile from GitHub OAuth

**Last Updated:** 2026-01-18

## Executive Summary

Enable personalized user communication by extracting and storing `first_name`/`last_name` from GitHub OAuth during user signup. This supports the weekly insights email feature which needs to address users by name.

## Current State Analysis

### What Exists
- Custom GitHub OAuth flow in `apps/auth/views/github.py`
- GitHub name fetched at line 155: `github_name = github_user.get("name")`
- Name stored in `SocialAccount.extra_data["name"]` — NOT in `CustomUser.first_name`/`last_name`
- `CustomUser` extends `AbstractUser` which has `first_name`/`last_name` fields (max_length=150)

### The Gap
When a user signs up via GitHub, their `first_name` and `last_name` remain empty despite GitHub providing this information.

## Proposed Future State

- New users via GitHub OAuth have `first_name`/`last_name` populated automatically
- Name parsing handles edge cases (single names, multi-part last names, empty names)
- Field length validated to prevent database errors
- Comprehensive test coverage following TDD

## Implementation Phases

### Phase 1: RED - Write Failing Tests
**Effort: S** | **Priority: P0**

Write tests FIRST that define the expected behavior:
1. Unit tests for name parsing helper
2. Integration tests for user creation with name

### Phase 2: GREEN - Implement Feature
**Effort: S** | **Priority: P0**

Minimal implementation to make tests pass:
1. Add `_parse_github_name()` helper function
2. Update user creation to use parsed names

### Phase 3: REFACTOR - Polish
**Effort: XS** | **Priority: P1**

Clean up and optimize if needed (likely minimal for this feature).

## Technical Details

### Files to Modify
| File | Change |
|------|--------|
| `apps/auth/views/github.py` | Add helper, update user creation |
| `apps/auth/tests/test_github_login.py` | Add name-related tests |

### Name Parsing Logic
```python
def _parse_github_name(full_name: str | None) -> tuple[str, str]:
    """Split GitHub full name into (first_name, last_name).

    Handles:
    - "Ivan" → ("Ivan", "")
    - "Ivan Yanchuk" → ("Ivan", "Yanchuk")
    - "Ivan van Yanchuk" → ("Ivan", "van Yanchuk")
    - None/empty → ("", "")
    - Long names → truncated to 150 chars (Django field limit)
    """
    if not full_name:
        return ("", "")
    parts = full_name.strip().split(maxsplit=1)
    first_name = parts[0][:150] if parts else ""
    last_name = parts[1][:150] if len(parts) > 1 else ""
    return (first_name, last_name)
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub returns None for name | Medium | Low | Handle gracefully with empty strings |
| Name exceeds field length | Low | Medium | Truncate to 150 chars |
| Existing tests break | Low | Medium | Run full test suite before/after |

## Success Metrics

- [ ] All new tests pass
- [ ] Existing `test_github_login.py` tests still pass
- [ ] New GitHub signups have `first_name` populated
- [ ] `user.get_display_name()` returns first name instead of email

## Out of Scope

- Backfilling existing users (none exist)
- Storing location/company fields (future enhancement)
- Modifying allauth social account adapter (using custom flow)
