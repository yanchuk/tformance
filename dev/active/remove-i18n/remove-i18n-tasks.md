# Remove i18n - Task Checklist

**Last Updated: 2026-01-02**

## Pre-Implementation

- [ ] Run `make test` to confirm baseline passes
- [ ] Create git branch `chore/remove-i18n`

## Phase 1: Template Cleanup

### 1.1 Remove `{% load i18n %}` lines
- [ ] Remove from `templates/` (161 files)
- [ ] Remove from `apps/integrations/templates/` (7 files)
- [ ] Verify no syntax errors with `python manage.py check --deploy`

### 1.2 Replace `{% trans "..." %}` with plain strings
- [ ] Replace in `templates/metrics/` (largest concentration)
- [ ] Replace in `templates/account/`
- [ ] Replace in `templates/teams/`
- [ ] Replace in `templates/web/`
- [ ] Replace in `templates/onboarding/`
- [ ] Replace in `templates/subscriptions/`
- [ ] Replace in `templates/feedback/`
- [ ] Replace in `templates/insights/`
- [ ] Replace in `templates/notes/`
- [ ] Replace in `templates/socialaccount/`
- [ ] Replace in `templates/content/`
- [ ] Replace in `templates/dashboard/`
- [ ] Replace in error templates (400, 403, 404, 429, 500)
- [ ] Replace in `apps/integrations/templates/`

### 1.3 Verify template changes
- [ ] Run `python manage.py check`
- [ ] Run `make test` for template-related tests

## Phase 2: Python Code Cleanup

### 2.1 Teams app
- [ ] `apps/teams/views/invitation_views.py` - remove gettext
- [ ] `apps/teams/views/manage_team_views.py` - remove gettext
- [ ] `apps/teams/views/membership_views.py` - remove gettext
- [ ] `apps/teams/views/api_views.py` - remove gettext
- [ ] `apps/teams/models.py` - remove gettext
- [ ] `apps/teams/helpers.py` - remove gettext
- [ ] `apps/teams/forms.py` - remove gettext
- [ ] `apps/teams/signals.py` - remove gettext
- [ ] `apps/teams/invitations.py` - remove gettext

### 2.2 Users app
- [ ] `apps/users/views.py` - remove gettext
- [ ] `apps/users/adapter.py` - remove gettext
- [ ] `apps/users/forms.py` - remove gettext
- [ ] `apps/users/helpers.py` - remove gettext

### 2.3 Subscriptions app
- [ ] `apps/subscriptions/views/views.py` - remove gettext
- [ ] `apps/subscriptions/helpers.py` - remove gettext
- [ ] `apps/subscriptions/decorators.py` - remove gettext
- [ ] `apps/subscriptions/wrappers.py` - remove gettext
- [ ] `apps/subscriptions/metadata.py` - remove gettext
- [ ] `apps/subscriptions/models.py` - remove gettext
- [ ] `apps/subscriptions/feature_gating.py` - remove gettext
- [ ] `apps/subscriptions/forms.py` - remove gettext

### 2.4 Other apps
- [ ] `apps/auth/views.py` - remove gettext
- [ ] `apps/onboarding/views.py` - remove gettext
- [ ] `apps/web/views.py` - remove gettext

### 2.5 Verify Python changes
- [ ] Run `make ruff` to fix formatting/linting
- [ ] Run `make test` for all tests

## Phase 3: Documentation & Verification

- [ ] Update CLAUDE.md to note i18n is not used
- [ ] Run full test suite: `make test`
- [ ] Start dev server: `make dev`
- [ ] Spot-check key pages:
  - [ ] Login page
  - [ ] Dashboard
  - [ ] PR list
  - [ ] Settings/account
- [ ] Commit with message: `chore: remove unused i18n infrastructure`

## Post-Implementation

- [ ] Merge to main
- [ ] Delete branch

## Rollback Plan

If issues arise:
```bash
git checkout main -- templates/ apps/
```

## Automation Scripts

### Remove `{% load i18n %}` lines:
```bash
find templates apps -name "*.html" -exec sed -i '' '/{% load i18n %}/d' {} \;
```

### Replace `{% trans "string" %}` with `string`:
```bash
# Pattern: {% trans "text" %} -> text
# Pattern: {% trans 'text' %} -> text
find templates apps -name "*.html" -exec sed -i '' \
  -e "s/{% trans \"\([^\"]*\)\" %}/\1/g" \
  -e "s/{% trans '\([^']*\)' %}/\1/g" {} \;
```

### Find remaining gettext in Python:
```bash
grep -rn "gettext" apps/ --include="*.py"
```
