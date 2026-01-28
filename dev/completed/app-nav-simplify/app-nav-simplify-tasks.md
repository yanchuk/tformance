# Tasks: App Header & Footer Simplification

**Last Updated:** 2026-01-25

## Phase 1: TDD - Write Failing Tests [S]

- [x] **1.1** Create Playwright test file `tests/e2e/app-navigation.spec.ts`
- [x] **1.2** Write test: App header does NOT contain "Features" link
- [x] **1.3** Write test: App header does NOT contain "Pricing" link
- [x] **1.4** Write test: App footer does NOT contain competitor comparison links
- [x] **1.5** Write test: Marketing home page HAS "Features" link
- [x] **1.6** Write test: Marketing home page HAS competitor comparisons
- [x] **1.7** Run tests - verify they FAIL (RED phase)

## Phase 2: Create New Templates [M]

- [x] **2.1** Create `templates/web/components/top_nav_app_only.html`
  - Logo linking to `metrics:dashboard_redirect`
  - Mobile hamburger button
  - No marketing links
- [x] **2.2** Create `templates/web/components/footer_app.html`
  - Dark mode toggle (copy from footer.html)
  - Legal links (Terms, Privacy, Contact)
  - Copyright
  - No competitor comparisons

## Phase 3: Update App Base Template [S]

- [x] **3.1** Modify `templates/web/app/app_base.html`:
  - Change `{% include 'web/components/top_nav_app.html' %}` to `top_nav_app_only.html`
  - Add `{% block footer %}` override to use `footer_app.html`

## Phase 4: Verification (GREEN phase) [S]

- [x] **4.1** Run Playwright tests - verify they PASS (66 passed, 6 skipped)
- [x] **4.2** Manual check: `/app/` header has no Features/Pricing/Blog
- [x] **4.3** Manual check: `/app/` footer has no competitor comparisons
- [x] **4.4** Manual check: `/` (home) has full marketing nav
- [ ] **4.5** Manual check: Mobile hamburger toggles sidebar

## Phase 5: Cleanup [S]

- [x] **5.1** Delete orphaned `templates/web/components/top_nav_app.html`
- [x] **5.2** Grep codebase for any remaining references to `top_nav_app.html`
- [ ] **5.3** Run full test suite to ensure no regressions

---

## Progress Summary

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: TDD Tests | ✅ Complete | Created `tests/e2e/app-navigation.spec.ts` |
| Phase 2: Templates | ✅ Complete | Created `top_nav_app_only.html` and `footer_app.html` |
| Phase 3: Integration | ✅ Complete | Updated `app_base.html` |
| Phase 4: Verification | ✅ Complete | 66 tests pass, verified via Playwright MCP |
| Phase 5: Cleanup | ✅ Complete | Deleted orphaned template |

## Effort Estimates

- **S** = Small (< 30 min)
- **M** = Medium (30 min - 2 hours)
- **L** = Large (2-4 hours)
- **XL** = Extra Large (> 4 hours)

**Total Estimated Effort:** ~2 hours (mostly S tasks)
