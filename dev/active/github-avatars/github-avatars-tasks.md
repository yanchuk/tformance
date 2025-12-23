# GitHub Avatars - Task Checklist

**Last Updated:** 2025-12-23

## Phase 1: Model Layer
- [x] Add `avatar_url` property to TeamMember model
- [x] Add `initials` property to TeamMember model

## Phase 2: Service Layer Updates

### Already Done
- [x] Update `get_team_breakdown()` to include avatar_url, initials
- [x] Update `get_recent_prs()` to include author_avatar_url, author_initials

### Remaining
- [ ] Update `get_ai_detective_leaderboard()` to include avatar_url, initials
  - File: `apps/metrics/services/dashboard_service.py` line 309
  - Add `reviewer__github_id` to values query
  - Construct avatar_url from github_id
  - Add initials helper

- [ ] Update `get_review_distribution()` to include avatar_url, initials
  - File: `apps/metrics/services/dashboard_service.py` line 351
  - Add `reviewer__github_id` to values query
  - Construct avatar_url from github_id
  - Add initials helper

- [ ] Update `get_copilot_by_member()` to include avatar_url, initials
  - File: `apps/metrics/services/dashboard_service.py` line 830
  - Check current implementation approach
  - Add avatar data to return dict

## Phase 3: Template Updates

### Already Done
- [x] Update `team_breakdown_table.html` with conditional avatar
- [x] Update `member_row.html` (integrations) with conditional avatar

### Remaining
- [ ] Update `recent_prs_table.html`
  - File: `templates/metrics/partials/recent_prs_table.html`
  - Line 25-27: Replace placeholder with conditional avatar
  - Use `row.author_avatar_url` and `row.author_initials`

- [ ] Update `leaderboard_table.html`
  - File: `templates/metrics/partials/leaderboard_table.html`
  - Line 30-32: Replace placeholder with conditional avatar
  - Use `row.avatar_url` and `row.initials`

- [ ] Update `review_distribution_chart.html`
  - File: `templates/metrics/partials/review_distribution_chart.html`
  - Line 7-9: Replace placeholder with conditional avatar
  - Use `row.avatar_url` and `row.initials`

- [ ] Update `copilot_members_table.html`
  - File: `templates/metrics/partials/copilot_members_table.html`
  - Line 17-19: Replace placeholder with conditional avatar
  - Use `row.avatar_url` and `row.initials`

## Phase 4: Testing & Verification

- [ ] Test avatars display on `/app/metrics/overview/` page
- [ ] Verify Team Breakdown section shows GitHub photos
- [ ] Verify Leaderboard section shows GitHub photos
- [ ] Verify Recent PRs table shows GitHub photos
- [ ] Verify Reviewer Workload shows GitHub photos
- [ ] Test fallback initials for members without github_id
- [ ] Check no visual regressions in existing components

## Helper Function Needed

Add to `dashboard_service.py`:
```python
def _compute_initials(name: str) -> str:
    """Compute 2-letter initials from a display name."""
    if not name:
        return "??"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return name[:2].upper()

def _avatar_url_from_github_id(github_id: str | None) -> str:
    """Construct GitHub avatar URL from user ID."""
    if github_id:
        return f"https://avatars.githubusercontent.com/u/{github_id}?s=80"
    return ""
```

## Notes

- Avatar images are 80px, appropriate for all current UI sizes
- GitHub CDN is fast, no need for caching
- Initials use DaisyUI `placeholder` class for consistent styling
