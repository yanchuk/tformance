# UI Review Tasks

**Last Updated:** 2025-12-12 (Session 2)
**Status:** In Progress

---

## Phase 1: Design System Consolidation - COMPLETE

- [x] Create `assets/styles/app/tailwind/design-system.css`
- [x] Define `.app-bg` class (consistent dark background)
- [x] Define `.app-card` class (unified card styling)
- [x] Define `.app-sidebar` class (navigation styling)
- [x] Define `.app-stat-card` class (metric display)
- [x] Define button variant classes (`.app-btn-primary`, `.app-btn-secondary`, `.app-btn-ghost`)
- [x] Define form input classes (dark inputs with cyan focus)
- [x] Update `site-tailwind.css` to import design-system.css
- [x] Document design tokens in comments

**Note:** Tailwind v4 doesn't allow `@apply` with classes defined in same file. Used shared selector pattern instead.

---

## Phase 2: Navigation Cleanup - COMPLETE

- [x] Fix broken Blog link in `top_nav.html` (made conditional)
- [x] Remove Example App from `team_nav.html`
- [x] Remove Subscription Demo from `team_nav.html`
- [x] Remove Flowbite Demo from `app_nav_menu_items.html`
- [x] Remove Examples Gallery from `top_nav.html` (auth users)
- [x] Add Team Settings to `team_nav.html`
- [x] Rename Subscription to Billing in `team_nav.html`
- [x] Update Dashboard icon to chart-line

**Verified via Playwright:** Sidebar now shows only Dashboard, Integrations, Team Settings, Billing

---

## Phase 3: UX Audit - COMPLETE

- [x] Create comprehensive UX audit report
- [x] Document all user flows (new user, returning user, navigation)
- [x] Identify critical issues
- [x] Prioritize fixes

**Output:** `dev/active/ui-review/ux-audit.md`

---

## Phase 4: Onboarding Flow Polish - PENDING

- [ ] Update `templates/onboarding/base.html`
  - [ ] Apply app-bg class
  - [ ] Ensure progress steps use design system
- [ ] Polish `templates/onboarding/start.html`
  - [ ] Use app-card for content
  - [ ] Use app-btn-primary for CTA
- [ ] Polish `templates/onboarding/select_org.html`
  - [ ] Organization cards styling
- [ ] Polish `templates/onboarding/select_repos.html`
  - [ ] Repository checkboxes styling
- [ ] Polish `templates/onboarding/connect_jira.html`
  - [ ] Skip button styling
- [ ] Polish `templates/onboarding/connect_slack.html`
  - [ ] Skip button styling
- [ ] Polish `templates/onboarding/complete.html`
  - [ ] Celebration styling
  - [ ] Clear next steps CTA

---

## Phase 5: Dashboard Implementation - DEFERRED

**User requested to skip this phase for now.**

- [ ] Replace `templates/web/app_home.html` placeholder
- [ ] Create dashboard grid layout
- [ ] Add metric cards
- [ ] Add charts

---

## Phase 6: Integrations Pages Alignment - PENDING

- [ ] Review `apps/integrations/templates/integrations/home.html`
  - Already looks good, may need minor tweaks
- [ ] Ensure button styling uses app-btn-* classes
- [ ] Ensure card styling consistent

---

## Phase 7: Authentication Pages - PENDING

- [ ] Review `templates/account/login.html`
- [ ] Review `templates/account/signup.html`
- [ ] Ensure form inputs use app-input class
- [ ] Ensure buttons use app-btn-* classes

**Note:** Screenshots showed auth pages already have dark theme, may need minimal changes.

---

## Phase 8: Error Pages & Edge Cases - COMPLETE

- [x] Update `templates/error_base.html` - New dark theme with app-card, app-btn-* classes
- [x] Update `templates/404.html` - Cyan 404 code, clean messaging
- [x] Update `templates/500.html` - Rose 500 code for errors
- [x] Update `templates/403.html` - Amber 403 code for access denied
- [x] Update `templates/400.html` - Amber 400 code for bad request
- [x] Update `templates/429.html` - Amber 429 code for rate limiting
- [ ] Create empty state component (deferred)

---

## Session Summary

### Completed This Session:
1. Created comprehensive design system CSS (~400 lines)
2. Fixed navigation - removed all Pegasus demo items
3. Created UX audit documentation
4. Updated all error pages (404, 500, 403, 400, 429)
5. Verified changes with Playwright

### Screenshots Captured:
- `landing-page-check.png` - Landing page with terminal hero
- `signup-page-before.png` - Sign up page (dark theme already applied)
- `onboarding-step1.png` - GitHub connection step
- `app-dashboard-before.png` - Dashboard before nav cleanup
- `app-dashboard-after-cleanup.png` - Dashboard after nav cleanup
- `integrations-page.png` - Integrations hub
- `landing-page-nav-fixed.png` - Landing page without Blog link
- `error-404-page.png` - Updated 404 error page

### Key Files Created:
- `assets/styles/app/tailwind/design-system.css`
- `dev/active/ui-review/ux-audit.md`

### Key Files Modified:
- `assets/styles/site-tailwind.css`
- `templates/web/components/top_nav.html`
- `templates/web/components/team_nav.html`
- `templates/web/components/app_nav_menu_items.html`
- `templates/error_base.html`
- `templates/404.html`
- `templates/500.html`
- `templates/403.html`
- `templates/400.html`
- `templates/429.html`

---

## Next Session Priority

1. **Implement actual dashboard** (Phase 5 - deferred by user request)
2. **Apply design system classes to remaining templates** (ongoing polish)
3. **Create empty state component** for tables/lists
4. **Final consistency check across all pages**

---

## Commands to Verify Work

```bash
# Start dev environment
make start-bg
DEBUG=True .venv/bin/python manage.py runserver 8000 &
npm run dev &

# Run tests to ensure no regressions
make test

# Check for linting issues
make ruff

# No migrations needed - only template/CSS changes
```

---

## Notes

- No Django model changes - no migrations needed
- All changes are template and CSS only
- Test user: admin@example.com / admin123
- Screenshots saved to `.playwright-mcp/` directory
