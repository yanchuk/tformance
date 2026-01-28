# Plan: Simplify App Header & Footer

**Last Updated:** 2026-01-25

## Executive Summary

Remove marketing content (Features, Pricing, competitor comparisons) from the authenticated app section (`/app/`) to provide a cleaner, focused experience for logged-in users. This separates the marketing website from the product experience.

## Current State Analysis

### Template Inheritance Problem

```
base.html
├── {% block top_nav %} → top_nav.html (marketing links)
├── {% block footer %} → footer.html (competitor comparisons)
└── app_base.html (extends base.html)
    └── {% block top_nav %} → top_nav_app.html (extends top_nav.html, INHERITS marketing)
    └── {% block footer %} → NOT OVERRIDDEN (INHERITS marketing footer)
```

**Issue:** `top_nav_app.html` extends `top_nav.html` and calls `{{ block.super }}`, causing all marketing links to leak into the authenticated app experience.

### What Users Currently See in `/app/`

**Header (unwanted marketing content):**
- Features dropdown (AI Impact, Team Performance, Integrations)
- Pricing link
- Blog link
- Compare Tools link

**Footer (unwanted marketing content):**
- vs LinearB, vs Jellyfish, vs Swarmia, vs Span, etc.
- "All Comparisons" link

## Proposed Future State

### App Header (`top_nav_app_only.html`)
- Logo → links to dashboard (`metrics:dashboard_redirect`)
- Mobile hamburger → toggles sidebar visibility
- NO marketing links (Features, Pricing, Blog, Compare)
- NO Sign Up/Sign In (user already authenticated)

### App Footer (`footer_app.html`)
- Dark mode toggle
- Legal links (Terms, Privacy, Contact)
- Copyright
- NO competitor comparisons

### Template Structure After

```
base.html
├── {% block top_nav %} → top_nav.html (marketing)
├── {% block footer %} → footer.html (marketing)
└── app_base.html (extends base.html)
    └── {% block top_nav %} → top_nav_app_only.html (STANDALONE, no marketing)
    └── {% block footer %} → footer_app.html (STANDALONE, no marketing)
```

## Implementation Phases

### Phase 1: TDD - Write Failing Tests
Write Playwright tests that verify:
1. App header does NOT contain marketing links
2. App footer does NOT contain competitor comparisons
3. Marketing pages still have full navigation

### Phase 2: Create New Templates
1. Create `top_nav_app_only.html` - standalone app header
2. Create `footer_app.html` - simplified app footer

### Phase 3: Update App Base Template
1. Modify `app_base.html` to use new components
2. Override `{% block footer %}` block

### Phase 4: Cleanup
1. Delete orphaned `top_nav_app.html`
2. Verify no template references remain

### Phase 5: Verification
1. Run Playwright tests
2. Manual verification of key pages

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Mobile nav breaks | Low | Medium | Test hamburger menu toggles sidebar |
| Marketing pages affected | Low | High | Test public pages independently |
| Missing legal links | Low | Medium | Copy from existing footer.html |

## Success Metrics

- [ ] App pages show NO marketing links in header
- [ ] App pages show NO competitor comparisons in footer
- [ ] Public pages retain full marketing nav/footer
- [ ] Mobile hamburger toggles sidebar correctly
- [ ] All Playwright tests pass
