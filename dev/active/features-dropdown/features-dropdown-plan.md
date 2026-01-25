# Features Dropdown Menu - Implementation Plan

**Last Updated:** 2025-01-25
**Status:** Implementation Complete - Ready for Manual Testing
**TDD Phase:** GREEN Complete ✅

---

## Executive Summary

Add a "Features" dropdown to the public marketing navigation with a dedicated `/features/` page. This is Phase 2 of the navigation evolution (from research in `prd/NAVIGATION-RESEARCH.md`).

**Deliverables:**
1. New `/features/` page with anchor sections
2. Alpine.js-powered dropdown in top nav (accessible)
3. Mobile menu updates with flat feature list
4. TDD test coverage

---

## Current State

**Navigation:**
```
[Logo]    [Blog]    Pricing [Sign Up] [Sign In]
```

**Issues:**
- No way to discover features before signing up
- Homepage is long scroll with all content
- No dedicated features landing page

---

## Proposed Future State

**Navigation:**
```
[Logo]    Features ▼ | Blog    Pricing    [Sign Up] [Sign In]
```

**Dropdown Content:**
- AI Impact Analytics → `/features/#ai-impact`
- Team Performance → `/features/#team-performance`
- Integrations → `/features/#integrations`
- Compare Tools → `/compare/`

---

## Implementation Phases

### Phase 1: TDD Setup (RED)
Write failing tests before implementation.

| Task | Effort | Status |
|------|--------|--------|
| Create test file `apps/web/tests/test_features.py` | S | ⬜ |
| Write test for 200 response | S | ⬜ |
| Write test for SEO metadata | S | ⬜ |
| Write test for anchor sections | S | ⬜ |
| Verify tests fail | S | ⬜ |

### Phase 2: Features Page (GREEN)
Minimal implementation to pass tests.

| Task | Effort | Status |
|------|--------|--------|
| Add URL route in `apps/web/urls.py` | S | ⬜ |
| Add view in `apps/web/views.py` with SEO metadata | S | ⬜ |
| Create template `templates/web/features.html` | M | ⬜ |
| Add anchor wrapper sections | S | ⬜ |
| Include existing components | S | ⬜ |
| Verify tests pass | S | ⬜ |

### Phase 3: Navigation Dropdown
Add dropdown to top nav.

| Task | Effort | Status |
|------|--------|--------|
| Add Alpine.js dropdown to `top_nav.html` (desktop) | M | ⬜ |
| Add feature items to mobile menu | S | ⬜ |
| Add active state for Features page | S | ⬜ |
| Add smooth scroll CSS | S | ⬜ |

### Phase 4: Polish & Verify
Final touches and manual testing.

| Task | Effort | Status |
|------|--------|--------|
| Test dropdown keyboard navigation | S | ⬜ |
| Test mobile menu | S | ⬜ |
| Test anchor scroll behavior | S | ⬜ |
| Test responsive breakpoints | S | ⬜ |

---

## Technical Details

### Files to Create

| File | Purpose |
|------|---------|
| `apps/web/tests/test_features.py` | TDD tests |
| `templates/web/features.html` | Features page |

### Files to Modify

| File | Changes |
|------|---------|
| `apps/web/urls.py` | Add `/features/` route |
| `apps/web/views.py` | Add `features()` view |
| `templates/web/components/top_nav.html` | Add dropdown + mobile items |
| `assets/styles/site-tailwind.css` | Add smooth scroll |

### Key Patterns

**Alpine.js Dropdown (accessible):**
- `x-data="{ open: false }"` for state
- `@mouseenter`/`@mouseleave` for hover
- `@click.outside` to close
- `@keydown.escape` to close
- ARIA: `aria-haspopup`, `aria-expanded`, `role="menu"`, `role="menuitem"`

**Django URL Tags:**
- Use `{% url 'web:features' %}#anchor` not hardcoded paths

**Scroll Offset:**
- `scroll-mt-20` class on anchor sections (80px offset for fixed nav)

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| SEO duplicate content | Unique hero on Features page |
| Anchor scroll jumps | Add `scroll-behavior: smooth` CSS |
| Dropdown accessibility | Use Alpine.js with ARIA roles |
| Mobile UX complexity | Keep flat list, no nested dropdown |

---

## Success Metrics

1. All tests pass: `.venv/bin/pytest apps/web/tests/test_features.py -v`
2. Features page loads at `/features/`
3. Dropdown works on desktop (hover + click)
4. Mobile menu shows feature links
5. Anchor links scroll smoothly to sections

---

## Dependencies

- Existing components: `feature_showcase.html`, `what_you_get.html`, `cta_terminal.html`
- Compare page exists at `/compare/`
- Alpine.js already loaded
- DaisyUI + Tailwind CSS available
