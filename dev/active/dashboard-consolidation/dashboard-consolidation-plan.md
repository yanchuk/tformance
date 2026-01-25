# Dashboard Consolidation Plan

**Last Updated:** 2025-01-25

## Executive Summary

Remove the legacy CTO Dashboard (`/app/metrics/overview/`) and consolidate all functionality into the Analytics Dashboard (`/app/metrics/analytics/`). This includes integrating newly implemented DX features (Copilot Engagement, Team Health Indicators) and cleaning up documentation with outdated URL patterns.

## Current State Analysis

### Legacy System
- **CTO Overview page** at `/app/metrics/overview/` - 624-line template with duplicate functionality
- **Analytics Dashboard** at `/app/metrics/analytics/` - Active, maintained dashboard with tabs
- **Redundant navigation** - "Full Dashboard" links in analytics templates point back to legacy page

### Completed DX Features (Ready for Integration)
| Feature | Service | View | Template | Tests |
|---------|---------|------|----------|-------|
| Copilot Engagement | `get_copilot_engagement_summary()` | `copilot_engagement_card()` | `copilot_engagement_card.html` | 13 passing |
| Cost Visibility | `get_copilot_seat_price()` | N/A (property) | N/A | 13 passing |
| Team Health | `get_team_health_indicators()` | `team_health_indicators_card()` | `team_health_indicators_card.html` | 21 passing |

### Documentation Issues
- **Team slug URLs**: Multiple docs reference `/a/<team_slug>/` pattern (deprecated)
- **CTO Dashboard references**: PRDs and guides mention legacy page
- **Claude Skills**: Outdated examples affect AI behavior

## Proposed Future State

### URL Structure
```
/app/metrics/overview/  →  302 redirect to /app/metrics/analytics/
/app/metrics/analytics/  →  Primary dashboard (unchanged)
  ├── /analytics/          →  Overview tab + Team Health Indicators
  ├── /analytics/ai-adoption/  →  AI Adoption tab + Copilot Engagement
  ├── /analytics/delivery/     →  Delivery tab (unchanged)
  ├── /analytics/quality/      →  Quality tab (unchanged)
  └── /analytics/team/         →  Team tab (unchanged)
```

### DX Feature Placement
- **Team Health Indicators**: Analytics Overview tab (new section)
- **Copilot Engagement**: AI Adoption tab (after Copilot Delivery Impact)

## Implementation Phases

### Phase A: Update Tests First (Prevents CI Breakage)
Update all tests to expect new URL structure before changing code.

**Python Tests:**
1. Remove `TestCTOOverview` class from `test_dashboard_views.py`
2. Update `test_insight_dashboard.py` references
3. Update `test_copilot_graceful_degradation.py` (8 methods)

**E2E Tests:**
Replace `/app/metrics/overview/` → `/app/metrics/analytics/` in 9 files (~36 references)

### Phase B: Code Changes
1. Convert `cto_overview()` to redirect (graceful deprecation)
2. Remove "Full Dashboard" navigation links from analytics templates
3. Integrate DX feature cards into analytics templates
4. Delete `cto_overview.html` template

### Phase C: Documentation Cleanup
1. Fix Claude skills (HIGH PRIORITY - affects AI behavior)
2. Fix PRD documents (CTO dashboard references)
3. Fix dev guides (team slug URLs)

### Phase D: Verification
Run full test suite and manual verification.

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Broken bookmarks | Low | Redirect preserves URLs for 30+ days |
| CI failures | High | Update tests BEFORE code changes |
| Broken docs | Medium | Comprehensive grep search for patterns |
| Missing features | Low | DX features already tested (47 tests) |

## Success Metrics

- [ ] All tests pass: `make test` (target: 0 failures)
- [ ] All E2E pass: `make e2e` (target: 0 failures)
- [ ] `/app/metrics/overview/` returns 302 redirect
- [ ] No grep hits for `/a/<team_slug>/` in documentation
- [ ] No grep hits for `cto_overview` in PRDs (except as redirect reference)
- [ ] DX feature cards render on analytics pages

## Required Resources

- **Django view changes**: 1 file (`dashboard_views.py`)
- **Template changes**: 5 files (4 analytics + 1 delete)
- **Test updates**: 12 files (3 Python + 9 E2E)
- **Documentation**: 7+ files
- **Estimated effort**: M (half day with TDD)

## Dependencies

- DX features implemented: ✅ Complete (47 tests passing)
- URL routes exist: ✅ `cards/copilot-engagement/` and `cards/team-health/`
- Analytics dashboard stable: ✅ No recent changes

## Command Reference

```bash
# Run specific test files
make test ARGS='apps.metrics.tests.test_dashboard_views'
make test ARGS='apps.metrics.tests.test_copilot_graceful_degradation'

# Run E2E tests
make e2e

# Search for patterns
grep -r "/a/<team_slug>" --include="*.md" .
grep -r "cto_overview" --include="*.md" prd/
grep -r "/app/metrics/overview" tests/e2e/
```
