# Comparison Pages: Plan

Last Updated: 2026-01-24

## Summary

SEO-optimized competitor comparison pages. Hub page at `/compare/` links to individual pages like `/compare/linearb/`. Each page shows honest feature and pricing comparison.

Code is built. Tests are missing. This plan covers testing and shipping.

---

## What Exists

| Component | File | Status |
|-----------|------|--------|
| Data layer | `apps/web/compare_data.py` | Done |
| Views | `apps/web/views.py` | Done |
| URLs | `apps/web/urls.py` | Done |
| Templates | `templates/web/compare/` | Done |
| Sitemap | `apps/web/sitemaps.py` | Done |

### Competitors

7 competitors with pricing, features, FAQs:
- LinearB, Jellyfish, Swarmia (high priority)
- Span, Workweave (medium priority)
- Mesmer, Nivara (low priority)

### URL Structure

```
/compare/              → Hub page (all competitors)
/compare/<slug>/       → Individual comparison (e.g., /compare/linearb/)
/sitemap.xml           → Includes comparison section
```

---

## Implementation Phases

### Phase 1: Tests (TDD Retrofit)

Write tests for existing code. Run tests first to confirm they fail or pass as expected.

**Tasks:**
1. Test `compare_data.py` functions
2. Test views return 200 and correct context
3. Test sitemap generates correct URLs
4. Test 404 for invalid competitor slugs

**Effort:** M (2-3 hours)

### Phase 2: Commit & Verify

Stage, commit, verify locally.

**Tasks:**
1. Run test suite
2. Commit all changes
3. Verify pages load locally
4. Verify sitemap.xml includes comparison URLs

**Effort:** S (30 min)

### Phase 3: Deploy & Monitor

Push to staging, verify, then production.

**Tasks:**
1. Push branch to origin
2. Merge to main (or PR)
3. Verify on staging
4. Monitor for 404s or errors

**Effort:** S (30 min)

---

## Technical Details

### compare_data.py Functions

```python
get_competitor(slug: str) -> dict | None
get_all_competitors() -> dict
get_competitors_by_priority(priority: str) -> list[dict]
calculate_savings(team_size: int, competitor_slug: str) -> dict | None
get_feature_status_display(value) -> dict
```

### Views

```python
def compare_hub(request):
    """Returns hub.html with all competitors, feature matrix, pricing."""

def compare_competitor(request, competitor: str):
    """Returns competitor.html with single competitor details, savings table, FAQs."""
```

### Sitemap

`ComparisonSitemap` generates:
- `hub` → `/compare/`
- 7 competitor slugs → `/compare/<slug>/`

---

## Success Criteria

1. All tests pass
2. `/compare/` loads with all 7 competitors
3. Each `/compare/<slug>/` page loads
4. `/sitemap.xml` includes 8 comparison URLs
5. SEO meta tags render correctly (title, description)
6. Schema.org FAQPage markup present on competitor pages

---

## Risks

| Risk | Mitigation |
|------|------------|
| Competitor data outdated | Data is static in Python; update `compare_data.py` when needed |
| SEO not indexed | Sitemap + schema markup should help; monitor Search Console |
| Pricing changes | Single source of truth in `compare_data.py` |
