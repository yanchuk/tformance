# Team Slug Fix - Context

**Last Updated:** 2024-12-24

## Summary

Fixed a bug where teams created via `/teams/create/` had empty slugs, causing `NoReverseMatch` errors when accessing `team.dashboard_url`.

## Problem

When creating a new team (e.g., "Posthog") via the create team form, the team was saved with an empty `slug` field because:
1. `TeamChangeForm` only includes the `name` field
2. The `create_team` view saved the form directly without generating a slug
3. Empty slug caused `NoReverseMatch` on any page using `team.dashboard_url`

## Root Cause

`apps/teams/views/manage_team_views.py:65-72` - The `create_team` view used `form.save()` directly without setting the `slug` field.

## Solution

1. **Database fix**: Updated existing "Posthog" team with empty slug:
   ```sql
   UPDATE teams_team SET slug = 'posthog' WHERE id = 44 AND slug = ''
   ```

2. **Code fix**: Modified `create_team` view to use existing `get_next_unique_team_slug()` helper:
   ```python
   team = form.save(commit=False)
   team.slug = get_next_unique_team_slug(team.name)
   team.save()
   ```

## Files Modified

| File | Change |
|------|--------|
| `apps/teams/views/manage_team_views.py` | Added slug generation in `create_team` view |
| `apps/teams/tests/test_creation.py` | Added 4 TDD tests for slug generation |

## TDD Approach

This fix was implemented using strict TDD:

1. **RED**: Wrote 4 failing tests
   - `test_create_team_via_view_generates_slug`
   - `test_create_team_via_view_slug_is_unique`
   - `test_create_team_via_view_handles_special_characters`
   - `test_created_team_dashboard_url_works`

2. **GREEN**: Implemented minimal fix using existing `get_next_unique_team_slug()` helper

3. **REFACTOR**: Evaluated - no refactoring needed (implementation is clean and minimal)

## Key Decisions

- Used existing `get_next_unique_team_slug()` helper instead of writing new slug logic
- This helper is already used by `create_default_team_for_user()` in the same codebase
- Ensures consistent slug generation across all team creation paths

## Test Results

All 76 team tests passing after fix.

## No Migrations Needed

This was a view-only fix. No model changes, no migrations required.
