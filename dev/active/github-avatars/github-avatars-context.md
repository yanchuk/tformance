# GitHub Avatars - Implementation Context

**Last Updated:** 2025-12-23

## Key Files

### Model (Already Updated)
```
apps/metrics/models/team.py
```
- `TeamMember.avatar_url` property - Returns GitHub avatar URL from github_id
- `TeamMember.initials` property - Returns 2-letter initials for fallback

### Service Layer
```
apps/metrics/services/dashboard_service.py
```
Functions that need avatar data added:
- Line 309: `get_ai_detective_leaderboard()`
- Line 351: `get_review_distribution()`
- Line 830: `get_copilot_by_member()`

Already updated:
- `get_team_breakdown()` - includes avatar_url, initials
- `get_recent_prs()` - includes author_avatar_url, author_initials

### Templates Needing Updates
```
templates/metrics/partials/recent_prs_table.html
templates/metrics/partials/copilot_members_table.html
templates/metrics/partials/review_distribution_chart.html
templates/metrics/partials/leaderboard_table.html
```

### Templates Already Updated
```
templates/metrics/partials/team_breakdown_table.html
apps/integrations/templates/integrations/components/member_row.html
```

## Key Decisions

### Avatar URL Construction
Using GitHub's avatar service:
```python
f"https://avatars.githubusercontent.com/u/{github_id}?s=80"
```
- `?s=80` requests 80px image (appropriate for UI)
- No authentication required
- CDN-backed, fast globally

### Fallback Strategy
When `github_id` is empty/null:
1. `avatar_url` property returns empty string
2. Template shows initials instead of image
3. DaisyUI `placeholder` class handles styling

### Service Layer Pattern
For functions using `.values()` aggregation:
```python
# Include github_id in values
.values("reviewer__display_name", "reviewer__github_id")

# Construct URL in result dict
{
    "reviewer_name": r["reviewer__display_name"],
    "avatar_url": f"https://avatars.githubusercontent.com/u/{r['reviewer__github_id']}?s=80"
                  if r["reviewer__github_id"] else "",
    "initials": _compute_initials(r["reviewer__display_name"]),
}
```

### Template Pattern
```html
<div class="avatar{% if not row.avatar_url %} placeholder{% endif %}">
  <div class="bg-neutral text-neutral-content rounded-full w-8 overflow-hidden">
    {% if row.avatar_url %}
    <img src="{{ row.avatar_url }}" alt="{{ row.name }}" class="w-full h-full object-cover">
    {% else %}
    <span class="text-xs">{{ row.initials }}</span>
    {% endif %}
  </div>
</div>
```

## Dependencies

### External
- GitHub Avatar Service: `avatars.githubusercontent.com`

### Internal
- `github_id` must be populated during team member sync
- Current Gumroad team has github_id for all 38 members

## Testing Approach

1. **Visual verification** via Playwright on `/app/metrics/overview/`
2. **Unit tests** for service functions (optional - avatar data is display-only)
3. **Check fallback** by testing with member without github_id

## Related PRs/Issues

- Part of Gumroad demo data seeding work
- Improves visual polish of analytics dashboard
