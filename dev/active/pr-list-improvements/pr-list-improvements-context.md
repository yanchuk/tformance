# PR List Page Improvements - Context

**Last Updated:** 2026-01-03

## Key Files

### Templates (to modify)

| File | Current State | Changes Needed |
|------|---------------|----------------|
| `templates/metrics/pull_requests/list_standalone.html` | Multi-line `if` in `@htmx:config-request.window` handler causes Alpine error | Move logic to `cleanRequestParams()` method in x-data |
| `templates/metrics/pull_requests/partials/table.html` | Each row has independent `expanded` state; faint visual feedback | Shared `expandedPrId` state; stronger visual highlighting |
| `templates/web/app/app_base.html` | `flex flex-row` container with no explicit gap | Add `gap-2 lg:gap-3` between sidebar and content |

### CSS (to modify)

| File | Current State | Changes Needed |
|------|---------------|----------------|
| `assets/styles/app/tailwind/app-components.css` | `.section { m-4 }`, `.app-card { p-4/p-8 }` | `.section { m-2 }`, `.app-card { p-3/p-5 }` |

### Tests (to create)

| File | Purpose |
|------|---------|
| `tests/e2e/pr-list-accordion.spec.ts` | E2E tests for accordion behavior and console errors |

---

## Architecture Decisions

### Decision 1: Method vs External Function for Alpine Handler

**Chosen:** Method in x-data object

**Rationale:**
- Keeps logic scoped to the component
- No global namespace pollution
- Follows Alpine.js best practices
- Easier to maintain alongside other x-data properties

**Alternative Considered:** External function in `assets/javascript/filters.js`
- Rejected: Would require additional import and doesn't benefit from Alpine's reactivity context

### Decision 2: Accordion Implementation Approach

**Chosen:** Shared `expandedPrId` state at table container level

**Rationale:**
- Simple comparison: `expandedPrId === {{ pr.id }}`
- Naturally enforces single-expand (setting one ID clears others)
- No need for event dispatch between rows

**Alternative Considered:** Alpine.js `$dispatch` events
- Rejected: More complex; requires event listeners on each row

### Decision 3: Preserve Per-Row State for Inline Notes

**Decision:** Keep `inlineOpen` state per-row while moving `expanded` to shared state

**Rationale:**
- Inline notes feature is independent of PR expansion
- Each row still needs its own tbody with x-data for `inlineOpen`
- Pattern: `<tbody x-data="{ inlineOpen: false }">`

### Decision 4: Visual Highlight Approach

**Chosen:** Left border accent + stronger background

**Implementation:**
- `border-l-4 border-l-primary` (4px orange left border)
- `bg-base-200/50` (50% opacity instead of 30%)
- Chevron color change to `text-primary` when expanded

**Rationale:**
- Clear visual hierarchy without being overwhelming
- Consistent with DaisyUI/Tailwind conventions
- Works in both light and dark themes

---

## Key Code Snippets

### Current Alpine Handler (BROKEN)
```html
@htmx:config-request.window="
  // Remove empty params from URL to keep it clean
  if ($event.detail.elt && $event.detail.elt.closest && $event.detail.elt.closest('[x-data]') === $el) {
    Object.keys($event.detail.parameters).forEach(key => {
      if ($event.detail.parameters[key] === '' || $event.detail.parameters[key] === null) {
        delete $event.detail.parameters[key];
      }
    });
  }
"
```

### Fixed Alpine Handler
```html
x-data="{
  // ... existing properties ...
  cleanRequestParams($event) {
    if ($event.detail.elt?.closest?.('[x-data]') === this.$el) {
      Object.keys($event.detail.parameters).forEach(key => {
        if ($event.detail.parameters[key] === '' || $event.detail.parameters[key] === null) {
          delete $event.detail.parameters[key];
        }
      });
    }
  }
}"
@htmx:config-request.window="cleanRequestParams($event)"
```

### Current PR Row Structure
```html
<tbody x-data="{ expanded: false, inlineOpen: false }">
  <tr @click="expanded = !expanded" :class="{ 'border-b-0': expanded }">
    ...
  </tr>
  <tr x-show="expanded" class="bg-base-200/30">
    ...
  </tr>
</tbody>
```

### New PR Table Structure (Accordion)
```html
<div x-data="{ expandedPrId: null }">
  <table>
    {% for pr in prs %}
    <tbody x-data="{ inlineOpen: false }">
      <tr @click="expandedPrId = (expandedPrId === {{ pr.id }}) ? null : {{ pr.id }}"
          :class="{
            'border-b-0': expandedPrId === {{ pr.id }},
            'border-l-4 border-l-primary bg-base-200/50': expandedPrId === {{ pr.id }}
          }">
        ...
      </tr>
      <tr x-show="expandedPrId === {{ pr.id }}"
          class="bg-base-200/50 border-l-4 border-l-primary">
        ...
      </tr>
    </tbody>
    {% endfor %}
  </table>
</div>
```

---

## Dependencies

### Internal Dependencies
- Alpine.js 3.x (already loaded globally)
- HTMX 2.0.8 (already loaded globally)
- Tailwind CSS 4.x (build step required if new classes used)
- DaisyUI (for `btn`, `table-zebra` classes)

### External Dependencies
- None

### Test Dependencies
- Playwright (for E2E tests)
- `tests/e2e/utils/test-helpers.ts` (login utilities)

---

## Related Files (Reference Only)

| File | Relevance |
|------|-----------|
| `templates/metrics/pull_requests/partials/expanded_row.html` | Content shown when PR expanded |
| `templates/notes/partials/note_icon.html` | Note icon in PR rows |
| `assets/javascript/htmx.js` | HTMX event handlers |
| `assets/javascript/alpine.js` | Alpine.js initialization |

---

## Testing Strategy

### E2E Tests (TDD - Write First)

1. **Console Error Test**
   - Navigate to PR list page
   - Check browser console for Alpine expression errors
   - Should find ZERO errors after fix

2. **Accordion Behavior Test**
   - Expand first PR row
   - Verify it shows expanded content
   - Expand second PR row
   - Verify first PR collapses automatically
   - Only one should be expanded at a time

3. **Visual Indicator Test**
   - Expand a PR row
   - Verify row has `border-l-primary` class
   - Verify chevron has `text-primary` class

### Manual Testing Checklist
- [ ] Load PR list page - no console errors
- [ ] Click PR row - expands with orange left border
- [ ] Click another PR row - first one collapses
- [ ] Verify spacing looks good at 1238px viewport width
- [ ] Test in both light and dark themes
- [ ] Test note icon still works (separate from expand)
