# Comparison Pages: Context

Last Updated: 2026-01-24

## Key Files

### Data & Logic
- `apps/web/compare_data.py` - Competitor data, pricing, features, helper functions
- `apps/web/views.py` - `compare_hub()` and `compare_competitor()` views (lines 577-655)
- `apps/web/sitemaps.py` - `ComparisonSitemap` class (lines 26-51)
- `apps/web/urls.py` - URL patterns for `/compare/` routes (lines 10-11)

### Templates
- `templates/web/compare/base_compare.html` - Base template with schema markup
- `templates/web/compare/hub.html` - Hub page with feature matrix, competitor grid
- `templates/web/compare/competitor.html` - Individual competitor comparison

### Configuration
- `tformance/urls.py` - Main sitemap config includes `ComparisonSitemap`
- `apps/web/templatetags/number_filters.py` - `get_item` and `intcomma` filters

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data storage | Python dict in `compare_data.py` | Simple, no DB overhead, easy to update |
| Templates | DaisyUI + Tailwind | Consistent with landing page |
| SEO | Schema.org FAQPage + BreadcrumbList | Rich snippets in search results |
| Honesty | Show "where they're ahead" section | Builds trust, differentiates from competitors |

---

## Dependencies

### Internal
- `apps/web/meta.py` - `get_protocol()` for sitemap URLs
- DaisyUI components (table, collapse, card)
- `number_filters` templatetag (`intcomma`, `get_item`)

### External
- None (static data, no API calls)

---

## Patterns Used

### View Pattern
Function-based views (per CLAUDE.md). No authentication required—public pages.

```python
def compare_hub(request):
    # Build context with all competitors
    # Return render(request, "web/compare/hub.html", context)
```

### Data Pattern
Single source of truth in `compare_data.py`. Competitors stored as dict with slug as key.

```python
COMPETITORS = {
    "linearb": {
        "name": "LinearB",
        "slug": "linearb",
        "pricing_range": "$35-46/seat/mo",
        "features": {...},
        "faqs": [...],
        ...
    },
    ...
}
```

### Sitemap Pattern
Custom `Sitemap` subclass. Returns list of identifiers, `location()` maps to URLs.

```python
class ComparisonSitemap(sitemaps.Sitemap):
    def items(self):
        return ["hub"] + list(COMPETITORS.keys())

    def location(self, item):
        if item == "hub":
            return reverse("web:compare")
        return reverse("web:compare_competitor", kwargs={"competitor": item})
```

---

## Test Locations

Tests should go in `apps/web/tests/test_compare.py` (create new file).

### What to Test
1. `compare_data.py` helper functions
2. View responses (200, context, templates)
3. Sitemap URL generation
4. 404 on invalid competitor slug
