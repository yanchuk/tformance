# UI Polish (December 23, 2025) - Tasks

**Last Updated: 2025-12-23**

## Completed Tasks

- [x] Rename "Team ID" to "Account ID" in Team Settings
- [x] Make Account ID field read-only (not editable)
- [x] Display Account ID separately from Team Name form
- [x] Improve input border visibility in light theme (darker base-300)
- [x] Remove GitHub icon from "GitHub Copilot" section divider
- [x] Remove icon from "AI Detection" section divider
- [x] Rename `/app/metrics/dashboard/cto/` URL to `/app/metrics/overview/`
- [x] Update page title from "CTO Overview" to "Analytics Overview"

## Pending Tasks

- [ ] Run full test suite to verify no regressions
- [ ] Commit changes with appropriate message
- [ ] Update any E2E tests that reference old `/cto/` URL (if any)

## Notes

### No Migrations Needed
All changes were to forms, templates, and CSS - no model changes.

### URL Change Impact
The `/cto/` → `/overview/` URL change may affect:
- E2E tests in `tests/e2e/dashboard.spec.ts`
- Any internal links referencing the old URL
- The `dashboard_redirect` view still redirects admins to `metrics:cto_overview` (name unchanged)

### Design System Colors
Light theme `base-300` changed from `#E5E7EB` to `#C5C8CE` for better border visibility.
