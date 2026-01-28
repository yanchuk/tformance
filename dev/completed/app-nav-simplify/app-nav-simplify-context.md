# Context: App Header & Footer Simplification

**Last Updated:** 2026-01-25

## Key Files

### Templates to Create

| File | Purpose |
|------|---------|
| `templates/web/components/top_nav_app_only.html` | Standalone app header (no marketing) |
| `templates/web/components/footer_app.html` | Simplified app footer (no comparisons) |

### Templates to Modify

| File | Change |
|------|--------|
| `templates/web/app/app_base.html` | Use new header/footer components |

### Templates to Delete

| File | Reason |
|------|--------|
| `templates/web/components/top_nav_app.html` | Becomes orphaned after change |

### Reference Files (Do Not Modify)

| File | Use For |
|------|---------|
| `templates/web/base.html` | Understanding block structure |
| `templates/web/components/top_nav.html` | Reference for logo styling |
| `templates/web/components/footer.html` | Reference for legal links, dark mode toggle |
| `templates/web/components/app_nav.html` | Sidebar nav (mobile toggle target) |

## Key Decisions

1. **Logo links to dashboard** - `{% url 'metrics:dashboard_redirect' %}` keeps users in app
2. **Mobile hamburger toggles sidebar** - Uses existing `app_nav.html` component
3. **Standalone templates** - No inheritance from marketing components
4. **Plain strings** - No `{% trans %}` per CLAUDE.md (i18n disabled)

## Dependencies

- No Django model changes
- No URL changes
- No Celery tasks
- Template-only changes

## URL Patterns Reference

```python
# Dashboard redirect URL
'metrics:dashboard_redirect'  # /app/ → redirects to team dashboard

# Legal pages (for footer links)
'web:terms'    # /terms/
'web:privacy'  # /privacy/
```

## Alpine.js Patterns

Mobile sidebar toggle uses Alpine.js. Reference existing pattern in `app_nav.html`:

```html
<div x-data="{ sidebarOpen: false }">
  <button @click="sidebarOpen = !sidebarOpen">
    <!-- hamburger icon -->
  </button>
  <div x-show="sidebarOpen">
    {% include "web/components/app_nav.html" %}
  </div>
</div>
```

## Test Locations

- Playwright E2E tests: `e2e/tests/`
- Create: `e2e/tests/test_app_navigation.py`
