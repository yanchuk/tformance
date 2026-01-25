# Features Dropdown Menu - Context

**Last Updated:** 2025-01-25

---

## Key Files

### To Create
- `apps/web/tests/test_features.py` - TDD tests
- `templates/web/features.html` - Features page

### To Modify
- `apps/web/urls.py` - Add route
- `apps/web/views.py` - Add view
- `templates/web/components/top_nav.html` - Add dropdown
- `assets/styles/site-tailwind.css` - Add smooth scroll

### Reference Files
- `prd/NAVIGATION-RESEARCH.md` - Competitor research
- `templates/web/components/feature_showcase.html` - Reuse component
- `templates/web/components/what_you_get.html` - Reuse component
- `templates/web/components/cta_terminal.html` - Reuse component
- `templates/web/landing_page.html` - Current homepage structure
- `apps/web/tests/test_pricing.py` - Test pattern reference

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Dropdown library | Alpine.js | Already used, accessible with ARIA |
| Link targets | Dedicated `/features/` page | User preference (not homepage anchors) |
| Mobile nav | Flat list | Simpler UX, no nested dropdowns |
| Feature items | 3 + footer link | AI Impact, Team Perf, Integrations + Compare |
| SEO | Unique hero content | Avoid duplicate content issues |

---

## URL Structure

```
/features/              → Features page (new)
/features/#ai-impact    → AI Impact section
/features/#team-perf    → Team Performance section
/features/#integrations → Integrations section
/compare/               → Compare Tools (existing)
```

---

## View Pattern (from `apps/web/views.py`)

```python
def features(request):
    return render(
        request,
        "web/features.html",
        {
            "page_title": "Platform Features",
            "page_description": "AI impact analytics, team performance metrics, and integrations...",
        },
    )
```

---

## Test Pattern (from `apps/web/tests/`)

```python
from django.test import TestCase
from django.urls import reverse

class FeaturesPageTests(TestCase):
    def test_features_page_returns_200(self):
        response = self.client.get(reverse("web:features"))
        self.assertEqual(response.status_code, 200)
```

---

## Alpine.js Dropdown Pattern

```html
<div x-data="{ open: false }"
     @mouseenter="open = true"
     @mouseleave="open = false"
     @keydown.escape="open = false">
  <button @click="open = !open"
          :aria-expanded="open"
          aria-haspopup="true">
    Features
  </button>
  <div x-show="open"
       x-transition
       @click.outside="open = false"
       role="menu">
    <!-- items -->
  </div>
</div>
```

---

## Component Reuse

The Features page reuses existing landing page components:

1. **`feature_showcase.html`** → #ai-impact section
   - Interactive carousel with 4 features
   - Already has AI adoption, team performance content

2. **`what_you_get.html`** → #team-performance section
   - Dashboard preview cards
   - Shows actual product screenshots

3. **`cta_terminal.html`** → Bottom CTA
   - Terminal-style signup prompt

---

## Styling Notes

### Scroll Behavior
```css
html {
  scroll-behavior: smooth;
}
```

### Scroll Offset (for fixed nav)
```html
<section id="ai-impact" class="scroll-mt-20">
```

### Dropdown Z-Index
```html
class="... z-50"  /* Above nav shadow */
```

---

## Dependencies

- Alpine.js (loaded via base template)
- DaisyUI menu/dropdown classes
- Font Awesome icons (`fa-robot`, `fa-chart-line`, `fa-plug`)
- Tailwind v4 utilities
