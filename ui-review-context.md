# UI Review Context

**Last Updated:** 2025-12-12 (Session 2)

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

### UX Audit - COMPLETE
- Created `dev/active/ui-review/ux-audit.md` with full findings

---

## Key Decisions Made This Session

1. **Blog link handling**: Made conditional with `{% if blog_url %}` - only shows when Wagtail blog page exists
2. **Sidebar cleanup**: Removed all Pegasus demo items (Example App, Subscription Demo, Flowbite Demo, Examples Gallery)
3. **Navigation structure**:
   - Application: Dashboard, Integrations, Team Settings, Billing
   - My Account: Profile, Change Password, Sign out
   - Admin (superuser only): Project Dashboard, Impersonate a User
4. **Tailwind v4 CSS pattern**: Can't use `@apply` with classes defined in same file - use shared selector pattern instead

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | **CREATED** - Comprehensive design system with ~50+ utility classes |
| `assets/styles/site-tailwind.css` | Added import for design-system.css |
| `templates/web/components/top_nav.html` | Fixed Blog link (conditional), removed Examples Gallery link for auth users |
| `templates/web/components/team_nav.html` | Removed Example App, Subscription Demo; Added Team Settings, renamed Subscription to Billing |
| `templates/web/components/app_nav_menu_items.html` | Removed Flowbite Demo link, updated Dashboard icon |
| `dev/active/ui-review/ux-audit.md` | **CREATED** - Full UX audit report |

---

## Blockers/Issues Discovered

1. **Tailwind CSS v4 @apply limitation**: Cannot use `@apply custom-class` where custom-class is defined in the same CSS file
   - Solution: Use shared selector pattern like `.btn, .btn-primary, .btn-secondary { @apply ... }`

2. **Dev server startup**: `./scripts/dev.sh` requires DEBUG=True or fails with ALLOWED_HOSTS error
   - Workaround: `DEBUG=True .venv/bin/python manage.py runserver 8000`
   - Vite must be started separately: `npm run dev`

---

## Next Immediate Steps

1. **Dashboard implementation** - Replace placeholder `templates/web/app_home.html` with real dashboard
   - Need to create dashboard view with metrics data
   - Reference `prd/DASHBOARDS.md` for widget specs

2. **Onboarding polish** - Apply design system classes to onboarding templates

3. **Component consistency** - Apply `.app-*` classes across remaining templates

---

## Key Files

### CSS Files (Updated)

| File | Purpose |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | **NEW** - Main design system with all app-* classes |
| `assets/styles/site-tailwind.css` | Imports design-system.css first |
| `assets/styles/app/tailwind/landing-page.css` | Landing page specific (terminal-*, stat-*, feature-card) |

### Navigation Components (Updated)

| File | Purpose | Status |
|------|---------|--------|
| `templates/web/components/top_nav.html` | Public page navigation | Updated - Blog conditional |
| `templates/web/components/team_nav.html` | Team-specific nav items | Updated - Demo items removed |
| `templates/web/components/app_nav_menu_items.html` | Sidebar menu items | Updated - Flowbite Demo removed |

### Base Templates

| File | Purpose | Priority |
|------|---------|----------|
| `templates/web/base.html` | Root template for public pages | High |
| `templates/web/app/app_base.html` | Root template for authenticated app | High |
| `templates/web/landing_page.html` | Landing page structure | Reference |

### Onboarding Flow

| File | Step |
|------|------|
| `templates/onboarding/base.html` | Base layout with progress indicator |
| `templates/onboarding/start.html` | Step 1: GitHub connection |
| `templates/onboarding/select_org.html` | Step 1b: Organization selection |
| `templates/onboarding/select_repos.html` | Step 2: Repository selection |
| `templates/onboarding/connect_jira.html` | Step 3: Jira (optional) |
| `templates/onboarding/connect_slack.html` | Step 4: Slack (optional) |
| `templates/onboarding/complete.html` | Step 5: Completion |

### App Pages

| File | Purpose |
|------|---------|
| `templates/web/app_home.html` | Main dashboard (**PLACEHOLDER - NEEDS REPLACEMENT**) |
| `apps/integrations/templates/integrations/home.html` | Integrations hub |

---

## Design System Reference

### New Design System Classes (design-system.css)

```css
/* Page backgrounds */
.app-bg, .app-bg-surface, .app-bg-grid

/* Cards */
.app-card, .app-card-interactive, .app-card-header, .app-card-title, .app-card-body, .app-card-footer

/* Stat cards */
.app-stat-card, .app-stat-value, .app-stat-value-positive/-negative/-neutral, .app-stat-label, .app-stat-change

/* Buttons */
.app-btn-primary, .app-btn-secondary, .app-btn-ghost, .app-btn-danger, .app-btn-sm, .app-btn-lg, .app-btn-icon

/* Forms */
.app-input, .app-select, .app-textarea, .app-checkbox, .app-label, .app-helper, .app-error, .app-form-group

/* Navigation */
.app-sidebar, .app-sidebar-item, .app-sidebar-item-active, .app-sidebar-heading, .app-navbar

/* Badges */
.app-badge-default/-primary/-success/-warning/-danger

/* Tables */
.app-table (with thead, th, td, tbody tr styling)

/* Alerts */
.app-alert-info/-success/-warning/-error

/* Progress */
.app-progress, .app-progress-bar, .app-steps, .app-step-indicator/-active/-complete

/* Loading */
.app-skeleton, .app-spinner

/* Empty states */
.app-empty-state, .app-empty-state-icon/-title/-description

/* Text */
.app-text-muted/-secondary/-primary/-accent/-mono/-gradient

/* Layout */
.app-layout, .app-main, .app-page-header/-title/-subtitle, .app-grid-2/-3/-4

/* Misc */
.app-divider, .app-divider-vertical, .app-scrollbar, .app-tooltip
```

### Color Palette

```css
deep: '#0f172a'      /* Slate 900 - deepest background */
surface: '#1e293b'   /* Slate 800 - card backgrounds */
elevated: '#334155'  /* Slate 700 - elevated elements/borders */
muted: '#64748b'     /* Slate 500 - muted text */
cyan: '#06b6d4'      /* Primary accent */
cyan-light: '#22d3ee'
cyan-dark: '#0891b2'
```

### Typography

```css
font-sans: 'DM Sans', system-ui, sans-serif
font-mono: 'JetBrains Mono', monospace
```

---

## Server Info

**To start dev environment:**
```bash
make start-bg  # Start Postgres, Redis
DEBUG=True .venv/bin/python manage.py runserver 8000 &  # Django
npm run dev &  # Vite
```

**Test user:**
- Email: admin@example.com
- Password: admin123

---

## Related PRD Documents

- `prd/DASHBOARDS.md` - Dashboard widget specifications
- `prd/ONBOARDING.md` - Onboarding flow requirements
- `prd/SLACK-BOT.md` - Slack integration UI
