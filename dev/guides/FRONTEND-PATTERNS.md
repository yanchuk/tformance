# Frontend Patterns (HTMX + Alpine.js)

> Back to [CLAUDE.md](../../CLAUDE.md)

This project uses HTMX for server-driven partial page updates and Alpine.js for client-side reactivity.

## Critical Rules

1. **NEVER use inline `<script>` tags in HTMX partials** - They won't execute after HTMX swaps content
2. **Use Alpine.store() for state that must persist** across HTMX navigation
3. **Use ChartManager for all chart initialization** - Prevents duplicate instances

## Alpine.js Stores

Use `Alpine.store()` for state that needs to survive HTMX content swaps:

```javascript
// In assets/javascript/alpine.js
Alpine.store('dateRange', {
  days: 30,
  preset: '',
  setDays(d) { this.days = d; this.preset = ''; },
  setPreset(p) { this.preset = p; this.days = 0; },
  isActive(d) { return this.days === d && !this.preset; }
});

// In templates - access via $store
<button @click="$store.dateRange.setDays(7)"
        :class="{'btn-primary': $store.dateRange.isActive(7)}">
  7d
</button>
```

**Available stores:**
- `$store.dateRange` - Time range selection (days, preset, granularity)
- `$store.metrics` - Selected metrics for comparison views

## Alpine Component Registration

Extract reusable components to JS modules instead of inline scripts:

```javascript
// In assets/javascript/components/my-component.js
export function registerMyComponent() {
  Alpine.data('myComponent', () => ({
    open: false,
    toggle() { this.open = !this.open; }
  }));
}

// In alpine.js - register during alpine:init
import { registerMyComponent } from './components/my-component.js';
document.addEventListener('alpine:init', () => {
  registerMyComponent();
});
```

## ChartManager Usage

All charts should be registered with ChartManager for proper lifecycle management:

```javascript
// Register a chart factory
chartManager.register('my-chart', (canvas, data) => {
  if (!data) return null;
  return new Chart(canvas.getContext('2d'), { /* config */ });
}, { dataId: 'my-chart-data' });

// Charts auto-initialize on htmx:afterSwap via chartManager.initAll()
```

**Registered charts:** ai-adoption-chart, cycle-time-chart, review-time-chart, copilot-trend-chart, pr-type-chart, tech-chart, trend-chart

## HTMX Event Handlers

Key handlers in `assets/javascript/htmx.js`:

```javascript
// Error handling - shows user-friendly message on 4xx/5xx
htmx.on('htmx:afterRequest', (evt) => {
  if (evt.detail.failed) {
    // Display error in target element
  }
});

// Alpine re-initialization after content swap
htmx.on('htmx:afterSwap', (evt) => {
  if (window.Alpine) {
    Alpine.initTree(evt.detail.target);
  }
});
```

## Template Best Practices

```html
<!-- DO: Use data attributes for chart config -->
<canvas id="my-chart"
        data-chart-type="stacked-bar"
        data-chart-data-id="my-chart-data">
</canvas>
{{ chart_data|json_script:"my-chart-data" }}

<!-- DO: Use Alpine store for persistent state -->
<div x-data>
  <button @click="$store.dateRange.setDays(30)">30d</button>
</div>

<!-- DON'T: Inline scripts in partials -->
<script>
  // This won't execute after HTMX swap!
  new Chart(...)
</script>
```

## Django Template Guidelines

- Indent templates with two spaces
- Use standard Django template syntax
- JavaScript and CSS files built with vite: use `{% vite_asset %}` tag (requires `{% load django_vite %}`)
- React components also need `{% vite_react_refresh %}` for HMR
- Use `{% static %}` for images and external JS/CSS not managed by vite
- Prefer Alpine.js for page-level JavaScript over inline `<script>` tags
- Break re-usable components into separate templates with `{% include %}`
- Use DaisyUI styling, fall back to TailwindCSS when needed

## Testing HTMX Flows

E2E tests for HTMX integration are in `tests/e2e/`:
- `htmx-error-handling.spec.ts` - Error display
- `htmx-navigation.spec.ts` - State persistence
- `alpine-htmx-integration.spec.ts` - Store + component behavior

```bash
npx playwright test tests/e2e/htmx --reporter=list
```
