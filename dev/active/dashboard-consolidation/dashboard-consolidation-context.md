# Dashboard Consolidation - Context

**Last Updated:** 2025-01-25

## Key Files Reference

### Views to Modify
```
apps/metrics/views/dashboard_views.py
├── cto_overview()        # Line ~150 - Convert to redirect
└── dashboard_redirect()  # Already points to analytics_overview ✓
```

### Templates to Modify
```
templates/metrics/analytics/
├── overview.html         # Add Team Health card, remove Full Dashboard link
├── ai_adoption.html      # Add Copilot Engagement card
├── quality.html          # Remove Full Dashboard link only
└── team.html             # Remove Full Dashboard link only

templates/metrics/
└── cto_overview.html     # DELETE (624 lines)
```

### Templates Already Created (DX Features)
```
templates/metrics/partials/
├── copilot_engagement_card.html     # Ready ✓
└── team_health_indicators_card.html  # Ready ✓
```

### Python Tests to Update
```
apps/metrics/tests/
├── test_dashboard_views.py              # Remove TestCTOOverview class (lines 67-209)
├── test_insight_dashboard.py            # Check for cto_overview references
└── test_copilot_graceful_degradation.py # Update 8 test methods
```

### E2E Tests to Update
```
tests/e2e/
├── insights.spec.ts         # ~16 references
├── copilot.spec.ts          # ~8 references
├── feedback.spec.ts         # ~3 references
├── llm-feedback.spec.ts     # ~3 references
├── analytics.spec.ts        # ~2 references
├── dashboard.spec.ts        # ~1 reference
├── error-states.spec.ts     # ~1 reference
├── interactive.spec.ts      # ~1 reference
└── fixtures/test-fixtures.ts # ~1 reference
```

### Documentation to Update
```
# Claude Skills (HIGH PRIORITY)
.claude/skills/django-dev-guidelines/SKILL.md         # Lines 113, 196
.claude/skills/django-dev-guidelines/resources/drf-guide.md
.claude/agents/documentation-architect.md              # Lines 97-98

# Dev Guides
dev/guides/CODE-GUIDELINES.md                         # Line 57

# PRDs
prd/DASHBOARDS.md                                     # Lines 38, 381, 463
prd/DATA-MODEL.md                                     # Line 316
prd/PERSONAL-NOTES.md                                 # Lines 440-443
```

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Redirect vs Delete | Redirect (302) | Preserves bookmarks, graceful deprecation |
| Test order | Tests first | Prevents CI breakage during implementation |
| DX feature placement | Analytics tabs | Existing infrastructure, no new pages needed |
| Documentation scope | All /a/<slug>/ refs | Prevents Claude behavior issues |

## URL Patterns

### Current (WRONG - in docs)
```
/a/<team_slug>/metrics/...
```

### Correct (in code)
```
/app/metrics/...?team=<team_id>
```

Team resolution happens via:
1. Session storage (`selected_team_id`)
2. Query parameter (`?team=47`)
3. User's primary team (default)

## HTMX Patterns for Integration

### Copilot Engagement Card (AI Adoption tab)
```html
{% if copilot_enabled %}
<div class="card bg-base-100 shadow-sm">
  <div class="card-body">
    <h3 class="card-title text-base">Copilot Engagement</h3>
    <div hx-get="{% url 'metrics:cards_copilot_engagement' %}?days={{ days }}"
         hx-trigger="load" hx-swap="innerHTML">
      <span class="loading loading-spinner"></span>
    </div>
  </div>
</div>
{% endif %}
```

### Team Health Indicators Card (Overview tab)
```html
<div class="card bg-base-100 shadow-sm">
  <div class="card-body">
    <h3 class="card-title text-base">Team Health</h3>
    <div hx-get="{% url 'metrics:cards_team_health' %}?days={{ days }}"
         hx-trigger="load" hx-swap="innerHTML">
      <span class="loading loading-spinner"></span>
    </div>
  </div>
</div>
```

## Related PRs and Issues

- DX Features implementation: In progress (47 tests passing)
- P1 Review Experience Survey: Pending (blocked on this cleanup)

## Verification URLs

After implementation, verify at:
```
http://localhost:8000/app/metrics/overview/?team=47
→ Should redirect (302) to /app/metrics/analytics/?team=47

http://localhost:8000/app/metrics/analytics/?team=47
→ Should show Team Health Indicators card

http://localhost:8000/app/metrics/analytics/ai-adoption/?team=47
→ Should show Copilot Engagement card (if Copilot enabled)
```

## Test Data

Use Supabase Demo team (ID: 47) for testing:
- Has Copilot data
- Has PR data for Team Health indicators
- Has survey data
