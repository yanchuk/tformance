# UI Review Context

**Last Updated:** 2025-12-12 (Session 3)
**Branch:** `feature/ui-consistency-review`
**Commit:** `ee03428`

---

## Current Implementation State

### Phase 1: Design System - COMPLETE
- Created `assets/styles/app/tailwind/design-system.css` (~400 lines)
- Updated `assets/styles/site-tailwind.css` to import design-system.css first

### Phase 2: Navigation Cleanup - COMPLETE
- Fixed broken Blog link (now conditional, only shows if blog page exists)
- Removed Pegasus demo items from sidebar
- Added Team Settings and Billing to sidebar
- Changed Dashboard icon

### Phase 3: UX Audit - COMPLETE
- Created `ux-audit.md` with full findings

### Phase 4: Error Pages - COMPLETE
- Updated all error pages (400, 403, 404, 429, 500) with dark theme

---

## Key Decisions Made

1. **Blog link handling**: Made conditional with `{% if blog_url %}` - only shows when Wagtail blog page exists
2. **Sidebar cleanup**: Removed all Pegasus demo items (Example App, Subscription Demo, Flowbite Demo, Examples Gallery)
3. **Navigation structure**:
   - Application: Dashboard, Integrations, Team Settings, Billing
   - My Account: Profile, Change Password, Sign out
   - Admin (superuser only): Project Dashboard, Impersonate a User
4. **Tailwind v4 CSS pattern**: Can't use `@apply` with classes defined in same file - use shared selector pattern instead
5. **Error page design**: Dark theme with color-coded error numbers (cyan 404, rose 500, amber for other 4xx)

---

## Files Modified

| File | Changes |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | **CREATED** - Comprehensive design system with ~50+ utility classes |
| `assets/styles/site-tailwind.css` | Added import for design-system.css |
| `templates/web/components/top_nav.html` | Fixed Blog link (conditional), removed Examples Gallery link for auth users |
| `templates/web/components/team_nav.html` | Removed Example App, Subscription Demo; Added Team Settings, renamed Subscription to Billing |
| `templates/web/components/app_nav_menu_items.html` | Removed Flowbite Demo link, updated Dashboard icon |
| `templates/error_base.html` | **REDESIGNED** - Dark theme with app-card, app-btn-* classes |
| `templates/404.html` | Cyan 404 code, clean messaging |
| `templates/500.html` | Rose 500 code for errors |
| `templates/403.html` | Amber 403 code for access denied |
| `templates/400.html` | Amber 400 code for bad request |
| `templates/429.html` | Amber 429 code for rate limiting |

---

## Git Worktree Info

**IMPORTANT**: This project uses git worktrees for feature development.

- Main worktree: `/Users/yanchuk/Documents/GitHub/tformance` (branch: main)
- Feature worktree: `/Users/yanchuk/Documents/GitHub/tformance/dev/active/ui-review` (branch: feature/ui-consistency-review)

To run Django from the feature worktree:
```bash
cd /Users/yanchuk/Documents/GitHub/tformance/dev/active/ui-review
DEBUG=True /Users/yanchuk/Documents/GitHub/tformance/.venv/bin/python manage.py runserver 8000
```

Note: The venv is shared from the main worktree.

---

## Next Session Steps

1. **Merge feature branch to main** (ready to merge)
2. Apply design system classes to remaining templates (onboarding, integrations, auth)
3. Create empty state component for tables/lists
4. Final consistency check across all pages

---

## Server Info

**To start dev environment from feature worktree:**
```bash
# From main directory
make start-bg  # Start Postgres, Redis

# From feature worktree
cd /Users/yanchuk/Documents/GitHub/tformance/dev/active/ui-review
DEBUG=True /Users/yanchuk/Documents/GitHub/tformance/.venv/bin/python manage.py runserver 8000 &
npm run dev &
```

**Test user:**
- Email: admin@example.com
- Password: admin123

---

## No Migrations Needed

All changes are template and CSS only - no Django model changes.
