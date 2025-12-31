# Personal PR Notes - Context & Dependencies

**Last Updated:** 2025-12-31

---

## Key Files to Reference

### PRD & Requirements
| File | Purpose |
|------|---------|
| `prd/PERSONAL-NOTES.md` | Full PRD with user stories, acceptance criteria |

### Pattern Templates (Feedback App)
| File | Purpose |
|------|---------|
| `apps/feedback/models.py` | Model pattern (but use BaseModel, not BaseTeamModel) |
| `apps/feedback/views.py` | HTMX modal pattern, form handling |
| `apps/feedback/forms.py` | DaisyUI form widgets |
| `apps/feedback/urls.py` | URL structure with team_urlpatterns |
| `apps/feedback/factories.py` | Factory Boy pattern |
| `apps/feedback/tests/test_views.py` | Test patterns with team setup |
| `templates/feedback/partials/feedback_form.html` | Modal dialog template |

### Base Classes
| File | Purpose |
|------|---------|
| `apps/utils/models.py` | BaseModel with timestamps |
| `apps/users/models.py` | CustomUser model |
| `apps/teams/decorators.py` | `@login_and_team_required` decorator |

### Integration Points
| File | Purpose |
|------|---------|
| `templates/metrics/pull_requests/partials/expanded_row.html` | Add "Add Note" button here |
| `templates/metrics/pull_requests/partials/table.html` | Add note indicator badge |
| `apps/metrics/views/pr_list_views.py` | May need to annotate queryset |
| `tformance/urls.py` | Register notes app URLs |
| `templates/web/sidebar.html` | Add "My Notes" navigation link |

---

## Key Decisions (From PRD Review)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data ownership | User-scoped (CustomUser FK) | Personal annotations, not team data |
| Uniqueness | One note per user per PR | Update model, not comment thread |
| Flag categories | 4 types | False Positive, Review Later, Important, Concern |
| PR deletion | CASCADE deletes notes | Notes without PR context are useless |
| Team access loss | Notes persist | Personal data survives access changes |
| Resolve action | My Notes cards only | Not in edit modal - list-review action |
| Card actions | Edit + Resolve + View PR | Delete only via modal |
| False Positive flag | Personal annotation only | Does NOT change PR's AI status |
| Filter logic | AND | Status + Flag filters combine |
| View PR link | Opens new tab | User stays in My Notes |

---

## Flag Color Mapping

| Flag | Value | DaisyUI Badge | Tailwind |
|------|-------|---------------|----------|
| False Positive | `false_positive` | `badge-error` | `text-error` |
| Review Later | `review_later` | `badge-warning` | `text-warning` |
| Important | `important` | `badge-info` | `text-info` |
| Concern | `concern` | `badge-accent` | `text-accent` |

---

## URL Patterns

```python
# apps/notes/urls.py
app_name = "notes"

team_urlpatterns = (
    [
        path("", views.my_notes, name="my_notes"),
        path("pr/<int:pr_id>/", views.note_form, name="note_form"),
        path("pr/<int:pr_id>/delete/", views.delete_note, name="delete_note"),
        path("pr/<int:pr_id>/resolve/", views.toggle_resolve, name="toggle_resolve"),
    ],
    "notes",
)

# In tformance/urls.py, add:
path("notes/", include("apps.notes.urls")),  # under team_urlpatterns
```

---

## Query Parameters (My Notes)

| Parameter | Values | Default |
|-----------|--------|---------|
| `status` | `active`, `resolved`, `all` | `active` |
| `flag` | `false_positive`, `review_later`, `important`, `concern`, or omit | all |
| `page` | integer | 1 |

---

## Dependencies

### Python Packages (Already Installed)
- Django 5.x
- django-htmx
- Factory Boy (testing)

### No New Dependencies Required

---

## Test Fixtures

```python
# apps/notes/factories.py
import factory
from apps.notes.models import PRNote
from apps.metrics.factories import PullRequestFactory
from apps.users.factories import UserFactory

class PRNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PRNote

    user = factory.SubFactory(UserFactory)
    pull_request = factory.SubFactory(PullRequestFactory)
    content = factory.Faker("paragraph", nb_sentences=2)
    flag = factory.Iterator(["", "", "false_positive", "review_later", "important", "concern"])
    is_resolved = False
```

---

## Migration Checklist

Before merging:
- [ ] Migration created: `python manage.py makemigrations notes`
- [ ] Migration applied: `python manage.py migrate`
- [ ] No migration conflicts with main branch
- [ ] Indexes created for (user, is_resolved, created_at) and (user, flag)

---

## E2E Test Environment

```bash
# Start dev server (required for E2E)
make dev

# Run E2E tests
npx playwright test tests/e2e/personal-notes.spec.ts

# Debug mode
npx playwright test tests/e2e/personal-notes.spec.ts --debug

# Test credentials
# Email: admin@example.com
# Password: admin123
```

---

## Rollback Plan

If issues arise:
1. Remove URL registration from `tformance/urls.py`
2. Revert template changes in expanded_row.html
3. Migration can be reversed: `python manage.py migrate notes zero`
4. Remove `apps/notes/` directory
5. Remove `templates/notes/` directory

---

## Related Tasks (Not in Scope)

These are explicitly out of scope for v1:
- Team-shared notes
- General notes (not attached to PR)
- Markdown preview/rendering
- Full-text search
- Export functionality
- Bulk delete/archive
