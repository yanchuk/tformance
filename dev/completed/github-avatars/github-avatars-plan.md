# GitHub Avatars Implementation Plan

**Last Updated:** 2025-12-23

## Executive Summary

Add GitHub profile pictures (avatars) to all team member displays throughout the application. Currently, member avatars show initials only. This enhancement will display actual GitHub profile photos where available, with initials as a graceful fallback.

## Current State Analysis

### What Exists
- `TeamMember` model stores `github_id` for each member
- GitHub's avatar service provides profile pictures via: `https://avatars.githubusercontent.com/u/{github_id}?s=80`
- Multiple templates display member information with placeholder initials

### Templates Using Initials (Need Updates)
| Template | Variable | Service Function |
|----------|----------|------------------|
| `templates/metrics/partials/recent_prs_table.html` | `row.author` | `get_recent_prs()` |
| `templates/metrics/partials/copilot_members_table.html` | `row.member_name` | `get_copilot_by_member()` |
| `templates/metrics/partials/review_distribution_chart.html` | `row.reviewer_name` | `get_review_distribution()` |
| `templates/metrics/partials/leaderboard_table.html` | `row.member_name` | `get_ai_detective_leaderboard()` |

### Already Completed
| Component | Status |
|-----------|--------|
| `TeamMember.avatar_url` property | ✅ Done |
| `TeamMember.initials` property | ✅ Done |
| `member_row.html` (integrations) | ✅ Done |
| `team_breakdown_table.html` | ✅ Done |
| `get_team_breakdown()` service | ✅ Done |
| `get_recent_prs()` service | ✅ Done |

## Proposed Future State

All member displays will:
1. Show GitHub profile picture if `github_id` exists
2. Fall back to initials if no GitHub ID
3. Use consistent styling across all components
4. Load images efficiently with proper sizing

## Implementation Phases

### Phase 1: Service Layer Updates (Effort: S)

Update remaining dashboard service functions to include avatar data:

1. **`get_ai_detective_leaderboard()`** - Currently uses `.values()` aggregation
2. **`get_review_distribution()`** - Currently uses `.values()` aggregation
3. **`get_copilot_by_member()`** - Need to check implementation

**Challenge**: Functions using Django `.values()` don't have access to model properties. Options:
- A) Refactor to iterate over queryset (more queries, cleaner code)
- B) Add `github_id` to values and construct URL in Python
- C) Use annotations with Concat (complex)

**Recommended**: Option B - Add `reviewer__github_id` to values, construct URL in service

### Phase 2: Template Updates (Effort: S)

Update 4 templates with conditional avatar display:

```html
<!-- Pattern to use -->
<div class="avatar{% if not row.avatar_url %} placeholder{% endif %}">
  <div class="bg-neutral text-neutral-content rounded-full w-8 overflow-hidden">
    {% if row.avatar_url %}
    <img src="{{ row.avatar_url }}" alt="{{ row.member_name }}" class="w-full h-full object-cover">
    {% else %}
    <span class="text-xs">{{ row.initials }}</span>
    {% endif %}
  </div>
</div>
```

### Phase 3: Testing (Effort: S)

1. Test avatars render for members with GitHub IDs
2. Test fallback initials for members without GitHub IDs
3. Verify no visual regressions in existing components

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub avatar service unavailable | Low | Low | Initials fallback handles gracefully |
| Performance impact from image loading | Low | Low | GitHub CDN is fast, images are small (80px) |
| Broken images for invalid github_ids | Low | Low | Browser shows broken image or initials |

## Success Metrics

- [ ] All 4 remaining templates show GitHub avatars
- [ ] Initials fallback works for members without GitHub IDs
- [ ] No visual regressions in existing avatar displays
- [ ] Page load times not noticeably impacted

## Dependencies

- GitHub avatar service availability (external)
- `github_id` populated for team members (from sync)

## Files to Modify

### Services
- `apps/metrics/services/dashboard_service.py`
  - `get_ai_detective_leaderboard()` (~line 309)
  - `get_review_distribution()` (~line 351)
  - `get_copilot_by_member()` (~line 830)

### Templates
- `templates/metrics/partials/recent_prs_table.html`
- `templates/metrics/partials/copilot_members_table.html`
- `templates/metrics/partials/review_distribution_chart.html`
- `templates/metrics/partials/leaderboard_table.html`
