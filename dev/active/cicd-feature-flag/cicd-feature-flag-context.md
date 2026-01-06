# CI/CD Feature Flag - Context

**Last Updated: 2026-01-06**

## Key Files

### Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `apps/integrations/services/integration_flags.py` | Flag definitions | Add `FLAG_CICD` constant and `is_cicd_enabled()` helper |
| `apps/integrations/tests/test_integration_flags.py` | Flag tests | Add tests for `is_cicd_enabled()` |
| `apps/metrics/views/dashboard_views.py` | CTO dashboard view | Pass `cicd_enabled` to context |
| `apps/metrics/views/analytics_views.py` | Analytics views | Pass `cicd_enabled` via `_get_analytics_context()` |
| `templates/metrics/cto_overview.html` | CTO dashboard template | Wrap CI/CD row (lines 461-500) |
| `templates/metrics/analytics/quality.html` | Quality analytics template | Wrap CI/CD card (lines 76-92) |
| `templates/metrics/analytics/delivery.html` | Delivery analytics template | Wrap deployment card (lines 85-101) |

### Reference Files (Read-Only)

| File | Why Referenced |
|------|----------------|
| `apps/teams/models.py` | Custom Flag model definition |
| `apps/integrations/services/integration_flags.py` | Existing flag patterns |
| `apps/integrations/tests/test_integration_flags.py` | Test patterns with `override_flag` |

## Key Decisions

### 1. Global vs Team-Scoped Flag
**Decision:** Global flag (not team-scoped)
**Rationale:** CI/CD is a product feature decision, not per-team customization. Using global flag means same visibility for all teams.

### 2. Default State
**Decision:** Disabled by default (CI/CD hidden)
**Rationale:** User requested hiding CI/CD for now. Enabling requires explicit admin action.

### 3. Implementation Approach
**Decision:** Pass flag via view context, not Waffle template tags
**Rationale:** Consistent with existing patterns in `_get_onboarding_flags_context()`. More explicit control in views.

### 4. Test Strategy
**Decision:** Use `waffle.testutils.override_flag` decorator
**Rationale:** Thread-safe for parallel test execution (pytest-xdist). Matches existing test patterns.

## Code Patterns to Follow

### Flag Definition Pattern
```python
# From integration_flags.py
FLAG_JIRA = "integration_jira_enabled"

def is_integration_enabled(request: HttpRequest, integration_slug: str) -> bool:
    flag_name = INTEGRATION_FLAGS.get(integration_slug)
    if not flag_name:
        return False
    return waffle.flag_is_active(request, flag_name)
```

### Test Pattern
```python
# From test_integration_flags.py
from waffle.testutils import override_flag
from apps.teams.models import Flag

def setUp(self):
    Flag.objects.get_or_create(name="cicd_enabled")

def test_example(self):
    with override_flag("cicd_enabled", active=True):
        self.assertTrue(is_cicd_enabled(request))
```

### View Context Pattern
```python
# From dashboard_views.py
def cto_overview(request: HttpRequest) -> HttpResponse:
    context = _get_date_range_context(request)
    context["cicd_enabled"] = is_cicd_enabled(request)  # Add this
    return TemplateResponse(request, template, context)
```

### Template Pattern
```html
{% if cicd_enabled %}
<!-- CI/CD content -->
{% endif %}
```

## Dependencies

### Internal Dependencies
- `apps.teams.models.Flag` - Custom Waffle flag model
- `waffle.flag_is_active()` - Flag checking function

### External Dependencies
- `django-waffle` - Already in requirements

## Flag Administration

To enable CI/CD after implementation:
1. Go to Django Admin → Waffle → Flags
2. Create flag with name `cicd_enabled`
3. Set `Everyone` to `Yes` (or assign specific teams)
4. Save

To disable: Set `Everyone` to `No` or delete the flag.
