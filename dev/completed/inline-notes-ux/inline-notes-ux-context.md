# Inline Notes UX - Context & Dependencies

**Last Updated:** 2025-12-31

## Key Files

### Backend (Django)

| File | Purpose | Action |
|------|---------|--------|
| `apps/notes/views.py` | Note views | Add `inline_note` view |
| `apps/notes/urls.py` | URL patterns | Add inline URL |
| `apps/notes/models.py` | PRNote model | No changes |
| `apps/notes/forms.py` | PRNoteForm | No changes |
| `apps/notes/tests/test_views.py` | View tests | Add inline view tests |

### Templates

| File | Purpose | Action |
|------|---------|--------|
| `templates/notes/partials/note_icon.html` | Note icon component | CREATE |
| `templates/notes/partials/inline_note_row.html` | Inline form/preview row | CREATE |
| `templates/metrics/pull_requests/partials/table.html` | PR list table | Add note icon to Title cell |
| `templates/metrics/pull_requests/partials/expanded_row.html` | Expanded PR details | Remove modal link, keep read-only note display |

### JavaScript

| File | Purpose | Action |
|------|---------|--------|
| `assets/javascript/components/inline-notes.js` | Alpine component | CREATE |
| `assets/javascript/alpine.js` | Alpine setup | Register `inlineNote` component |

### Tests

| File | Purpose | Action |
|------|---------|--------|
| `apps/notes/tests/test_views.py` | Unit tests | Add inline view tests |
| `tests/e2e/notes.spec.ts` | E2E tests | Update for inline flow |

## Key Decisions

### 1. Note Icon Placement
**Decision:** Icon at START of Title cell content (leftmost element)
**Rationale:** User requested "left side of the list", integrates naturally with existing Title cell

### 2. Preview vs Direct Edit
**Decision:** Preview mode first for existing notes, [Edit] button to switch to form
**Rationale:** User confirmed this preference in planning session

### 3. Keyboard Shortcuts
**Decision:** Cmd/Ctrl+Enter to save, Escape to cancel
**Rationale:** Power-user friendly, confirmed by user

### 4. HTMX Row Insertion
**Decision:** Use `hx-swap="afterend"` on icon click to insert inline row
**Rationale:** Clean pattern for table row insertion without breaking structure

### 5. Alpine.js for Mode Toggle
**Decision:** Single `inlineNote()` component manages preview/edit modes
**Rationale:** Consistent with codebase patterns, avoids page reload

## Dependencies

### Existing Dependencies (No Changes)
- Django 5.2.x
- HTMX 2.0.x
- Alpine.js 3.x
- Font Awesome 6.x (icons)
- DaisyUI 4.x (components)
- Tailwind CSS 4.x

### Existing Code to Leverage
- `user_note_for_pr` template tag in `apps/metrics/templatetags/pr_list_tags.py`
- `PRNoteForm` in `apps/notes/forms.py`
- `@login_and_team_required` decorator

## Icon Color Mapping

```python
FLAG_COLORS = {
    '': 'text-base-content',           # No flag
    'false_positive': 'text-warning',   # Yellow
    'review_later': 'text-info',        # Blue
    'important': 'text-secondary',      # Purple
    'concern': 'text-error',            # Red
}
```

## URL Pattern

```python
# apps/notes/urls.py
path("pr/<int:pr_id>/inline/", views.inline_note, name="inline_note"),
```

## Test Coverage Requirements

### Unit Tests (pytest)
- `test_inline_note_get_returns_form_for_new_note`
- `test_inline_note_get_returns_preview_for_existing_note`
- `test_inline_note_post_creates_note`
- `test_inline_note_post_updates_existing_note`
- `test_inline_note_requires_authentication`
- `test_inline_note_delete_removes_note`

### E2E Tests (Playwright)
- `test_note_icon_visible_in_pr_list`
- `test_click_icon_shows_inline_form`
- `test_submit_form_creates_note`
- `test_existing_note_shows_preview`
- `test_edit_button_switches_to_form`
- `test_escape_closes_form`
- `test_cmd_enter_saves_note`
