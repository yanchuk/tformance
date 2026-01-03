# Remove i18n from Tformance

**Last Updated: 2026-01-02**

## Executive Summary

Remove Django internationalization (i18n) infrastructure from Tformance since there are no plans for multi-language support. This will simplify templates, reduce cognitive overhead, and eliminate unused infrastructure.

## Current State Analysis

### i18n Usage Inventory

| Component | Files | Details |
|-----------|-------|---------|
| `{% load i18n %}` in templates | 161 | In `templates/` directory |
| `{% load i18n %}` in apps | 9 | In `apps/` templates |
| `{% trans "..." %}` tags | 757 | Actual translation tags in templates |
| Files using `{% trans %}` | 86 | Templates with translation tags |
| Python `gettext` usage | 24 | Files importing translation functions |

### Settings Configuration

```python
# tformance/settings.py:444
USE_I18N = WAGTAIL_I18N_ENABLED = False
```

i18n is already **disabled** in settings, but the template infrastructure remains.

### Template Pattern

Templates follow this pattern inherited from SaaS Pegasus:
```html
{% extends "web/base.html" %}
{% load i18n %}
...
{% trans "Pull Requests" %}
```

### Python Code Pattern

Python files use `gettext_lazy`:
```python
from django.utils.translation import gettext_lazy as _
error_message = _("Invalid invitation")
```

## Proposed Future State

1. Remove all `{% load i18n %}` template tags
2. Replace all `{% trans "..." %}` with plain strings
3. Remove Python `gettext_lazy` usage (replace with plain strings)
4. Keep `USE_I18N = False` in settings
5. Document decision in CLAUDE.md

## Implementation Phases

### Phase 1: Template Cleanup (S)
Remove i18n from Django templates - the bulk of the work.

### Phase 2: Python Code Cleanup (S)
Remove gettext from Python files.

### Phase 3: Documentation & Verification (S)
Update docs and verify no regressions.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking template syntax | Low | High | Test after each batch of changes |
| Missing translations | N/A | None | i18n is already disabled |
| Editor/IDE warnings | Low | Low | Templates will be simpler |

## Success Metrics

- [ ] Zero `{% load i18n %}` in codebase
- [ ] Zero `{% trans %}` or `{% blocktrans %}` tags
- [ ] Zero `gettext` imports in app code
- [ ] All tests pass
- [ ] Dev server starts successfully

## Effort Estimate

**Total: Small (S)** - Mechanical find-and-replace operations

- Phase 1: ~1-2 hours (automated with sed/scripts)
- Phase 2: ~30 minutes
- Phase 3: ~15 minutes

## Implementation Approach

Use automated text replacement:

```bash
# Remove {% load i18n %} lines
find templates apps -name "*.html" -exec sed -i '' '/{% load i18n %}/d' {} \;

# Replace {% trans "string" %} with string
# This requires careful regex to handle various patterns
```

## Dependencies

- None - this is standalone cleanup work
- Can be done incrementally by directory

## Notes

- SaaS Pegasus includes i18n by default for multi-language support
- Since Tformance is English-only, this is dead code
- Removing it simplifies templates and reduces confusion
