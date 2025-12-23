# GitHub Avatars - Task Checklist

**Last Updated:** 2025-12-23

## Phase 1: Model Layer
- [x] Add `avatar_url` property to TeamMember model
- [x] Add `initials` property to TeamMember model

## Phase 2: Service Layer Updates

### Already Done
- [x] Update `get_team_breakdown()` to include avatar_url, initials
- [x] Update `get_recent_prs()` to include author_avatar_url, author_initials
- [x] Update `get_ai_detective_leaderboard()` to include avatar_url, initials
- [x] Update `get_review_distribution()` to include avatar_url, initials
- [x] Update `get_copilot_by_member()` to include avatar_url, initials

### Helper Functions Added
- [x] `_compute_initials()` - Compute 2-letter initials from display name
- [x] `_avatar_url_from_github_id()` - Construct GitHub avatar URL from user ID

## Phase 3: Template Updates

### Completed
- [x] Update `team_breakdown_table.html` with conditional avatar
- [x] Update `member_row.html` (integrations) with conditional avatar
- [x] Update `recent_prs_table.html` with conditional avatar
- [x] Update `leaderboard_table.html` with conditional avatar
- [x] Update `review_distribution_chart.html` with conditional avatar
- [x] Update `copilot_members_table.html` with conditional avatar

## Phase 4: Testing & Verification

- [x] Test avatars display on `/app/metrics/overview/` page
- [x] Verify Team Breakdown section shows GitHub photos
- [x] Verify Copilot Usage by Member shows GitHub photos
- [x] Test fallback initials for members without github_id
- [x] Check no visual regressions in existing components

## Notes

- Avatar images are 80px, appropriate for all current UI sizes
- GitHub CDN is fast, no need for caching
- Initials use DaisyUI `placeholder` class for consistent styling
- Reviewer Workload section uses inline template (not a partial) - could be enhanced separately
