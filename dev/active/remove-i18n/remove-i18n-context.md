# Remove i18n - Context

**Last Updated: 2026-01-02**

## Key Files

### Settings
- `tformance/settings.py:444` - `USE_I18N = False` (already disabled)

### Template Directories
- `templates/` - 161 files with `{% load i18n %}`
- `apps/integrations/templates/` - 7 HTML files with i18n
- `apps/notes/tests/` - 1 test file references i18n

### Python Files with gettext (24 files)

**Teams App:**
- `apps/teams/views/invitation_views.py`
- `apps/teams/views/manage_team_views.py`
- `apps/teams/views/membership_views.py`
- `apps/teams/views/api_views.py`
- `apps/teams/models.py`
- `apps/teams/helpers.py`
- `apps/teams/forms.py`
- `apps/teams/signals.py`
- `apps/teams/invitations.py`

**Users App:**
- `apps/users/views.py`
- `apps/users/adapter.py`
- `apps/users/forms.py`
- `apps/users/helpers.py`

**Subscriptions App:**
- `apps/subscriptions/views/views.py`
- `apps/subscriptions/helpers.py`
- `apps/subscriptions/decorators.py`
- `apps/subscriptions/wrappers.py`
- `apps/subscriptions/metadata.py`
- `apps/subscriptions/models.py`
- `apps/subscriptions/feature_gating.py`
- `apps/subscriptions/forms.py`

**Other:**
- `apps/auth/views.py`
- `apps/onboarding/views.py`
- `apps/web/views.py`

## Translation Tag Patterns Found

### Simple translation
```html
{% trans "Pull Requests" %}
```

### In attributes
```html
title="{% trans 'Send Feedback' %}"
```

### With variables (none found)
```html
{% blocktrans %}...{% endblocktrans %}
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Remove vs Keep | Remove | No i18n plans, simplifies code |
| Automated vs Manual | Automated | 757 occurrences, consistent patterns |
| All at once vs Incremental | All at once | Low risk, settings already disabled |

## Dependencies

- None - i18n is already disabled in settings
- Templates will work identically after removal

## Testing Strategy

1. Run `make test` before changes
2. Apply changes with automated scripts
3. Run `make test` after changes
4. Verify dev server starts
5. Spot-check key pages in browser
