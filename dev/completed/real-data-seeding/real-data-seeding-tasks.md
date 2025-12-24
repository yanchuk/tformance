# Real Data Seeding Tasks

**Last Updated:** 2025-12-24
**Status:** COMPLETE

## Completed Tasks

- [x] Add anthropic, calcom, trigger configs to real_projects.py
- [x] Add `--no-check-runs` flag for faster seeding
- [x] Apply migration 0018_add_ai_detection_version
- [x] Run full seeding for PostHog, Anthropic, Cal.com, Trigger.dev
- [x] **Fix: Teams not visible in admin@example.com account**
  - Root cause: Seeder wasn't adding admin user as team member
  - Fix: Added `_add_admin_to_team()` method to `RealProjectSeeder`
  - Manually added admin to existing teams via Django shell

## Seeding Results

| Org | PRs Seeded | Team Members | Notes |
|-----|-----------|--------------|-------|
| PostHog | 130 | 101 | From cache |
| Anthropic | 13 | 38 | 3 repos |
| Cal.com | 6 | 56 | 1 retry on timeout |
| Trigger.dev | 5 | 31 | From cache |

## Code Changes

- `apps/metrics/seeding/real_project_seeder.py`:
  - Added `_add_admin_to_team()` method
  - Called after team creation in `_get_or_create_team()`
  - Auto-adds admin@example.com as team admin (if exists)
