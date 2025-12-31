# Personal PR Notes - Task Checklist

**Last Updated:** 2025-12-31
**Branch:** `feature/personal-notes`

---

## Pre-Implementation Setup

- [ ] Create git worktree: `git worktree add ../tformance-personal-notes feature/personal-notes`
- [ ] Navigate to worktree: `cd ../tformance-personal-notes`
- [ ] Install dependencies: `make init`
- [ ] Start background services: `make start`
- [ ] Verify dev server: `make dev`
- [ ] Create `apps/notes/` app: `python manage.py startapp notes apps/notes`

---

## Phase 1: Foundation (Core Model & CRUD)

### 1.1 Model Layer

- [ ] **RED:** Write `test_models.py::TestPRNote::test_create_note`
- [ ] **RED:** Write `test_models.py::TestPRNote::test_unique_constraint`
- [ ] **RED:** Write `test_models.py::TestPRNote::test_cascade_delete_on_pr`
- [ ] **RED:** Write `test_models.py::TestPRNote::test_cascade_delete_on_user`
- [ ] **RED:** Write `test_models.py::TestPRNote::test_flag_choices`
- [ ] **GREEN:** Implement `PRNote` model in `models.py`
- [ ] **GREEN:** Create migration: `python manage.py makemigrations notes`
- [ ] **GREEN:** Apply migration: `python manage.py migrate`
- [ ] **REFACTOR:** Create `PRNoteFactory` in `factories.py`
- [ ] Verify: All model tests pass

### 1.2 Form Layer

- [ ] **RED:** Write form validation tests (content max length, flag choices)
- [ ] **GREEN:** Implement `NoteForm` in `forms.py`
- [ ] **REFACTOR:** Add DaisyUI widget classes
- [ ] Verify: Form tests pass

### 1.3 Note Form View (Add/Edit)

- [ ] **RED:** Write `test_views.py::TestNoteForm::test_form_requires_login`
- [ ] **RED:** Write `test_views.py::TestNoteForm::test_form_returns_empty_for_new`
- [ ] **RED:** Write `test_views.py::TestNoteForm::test_form_returns_filled_for_existing`
- [ ] **RED:** Write `test_views.py::TestNoteForm::test_cannot_see_other_users_notes`
- [ ] **RED:** Write `test_views.py::TestNoteForm::test_create_new_note`
- [ ] **RED:** Write `test_views.py::TestNoteForm::test_update_existing_note`
- [ ] **RED:** Write `test_views.py::TestNoteForm::test_htmx_returns_modal`
- [ ] **GREEN:** Implement `note_form` view in `views.py`
- [ ] **GREEN:** Create `templates/notes/partials/note_form.html`
- [ ] **GREEN:** Create `templates/notes/partials/note_success.html`
- [ ] **REFACTOR:** Clean up, add docstrings
- [ ] Verify: All note form tests pass

### 1.4 URL Registration (Partial)

- [ ] Create `urls.py` with team_urlpatterns
- [ ] Register in `tformance/urls.py`
- [ ] Add `notes` to `INSTALLED_APPS`

### 1.5 Playwright Check #1

- [ ] Start dev server
- [ ] **Manual/Playwright:** Navigate to PR list, expand row
- [ ] **Manual/Playwright:** Trigger note_form endpoint directly (modal loads)
- [ ] **Manual/Playwright:** Submit form, verify save works

---

## Phase 2: Delete & My Notes Page

### 2.1 Delete View

- [ ] **RED:** Write `test_views.py::TestDeleteNote::test_delete_requires_login`
- [ ] **RED:** Write `test_views.py::TestDeleteNote::test_delete_note`
- [ ] **RED:** Write `test_views.py::TestDeleteNote::test_cannot_delete_other_users_note`
- [ ] **RED:** Write `test_views.py::TestDeleteNote::test_delete_nonexistent_returns_404`
- [ ] **GREEN:** Implement `delete_note` view
- [ ] **GREEN:** Add delete button to modal (edit mode)
- [ ] **REFACTOR:** Add confirmation dialog
- [ ] Verify: Delete tests pass

### 2.2 My Notes View

- [ ] **RED:** Write `test_views.py::TestMyNotes::test_requires_login`
- [ ] **RED:** Write `test_views.py::TestMyNotes::test_list_shows_only_own_notes`
- [ ] **RED:** Write `test_views.py::TestMyNotes::test_filter_by_status_active`
- [ ] **RED:** Write `test_views.py::TestMyNotes::test_filter_by_status_resolved`
- [ ] **RED:** Write `test_views.py::TestMyNotes::test_filter_by_flag`
- [ ] **RED:** Write `test_views.py::TestMyNotes::test_combined_filters`
- [ ] **RED:** Write `test_views.py::TestMyNotes::test_pagination`
- [ ] **RED:** Write `test_views.py::TestMyNotes::test_empty_state`
- [ ] **GREEN:** Implement `my_notes` view
- [ ] **GREEN:** Create `templates/notes/my_notes.html`
- [ ] **GREEN:** Create `templates/notes/partials/note_card.html`
- [ ] **GREEN:** Create `templates/notes/partials/notes_list.html` (HTMX partial)
- [ ] **REFACTOR:** Add filter dropdowns, pagination UI
- [ ] Verify: My Notes tests pass

### 2.3 Toggle Resolve View

- [ ] **RED:** Write `test_views.py::TestToggleResolve::test_resolve_note`
- [ ] **RED:** Write `test_views.py::TestToggleResolve::test_unresolve_note`
- [ ] **RED:** Write `test_views.py::TestToggleResolve::test_sets_resolved_at`
- [ ] **RED:** Write `test_views.py::TestToggleResolve::test_cannot_resolve_other_users_note`
- [ ] **GREEN:** Implement `toggle_resolve` view
- [ ] **GREEN:** Add Resolve/Unresolve buttons to note cards
- [ ] **REFACTOR:** Update card styling for resolved state
- [ ] Verify: Resolve tests pass

### 2.4 Playwright Check #2

- [ ] **Manual/Playwright:** Navigate to My Notes page (empty state)
- [ ] **Manual/Playwright:** Create a note from PR list
- [ ] **Manual/Playwright:** Navigate to My Notes (note visible)
- [ ] **Manual/Playwright:** Test status filter (Active/Resolved)
- [ ] **Manual/Playwright:** Test flag filter
- [ ] **Manual/Playwright:** Resolve a note
- [ ] **Manual/Playwright:** Verify resolved state persists

---

## Phase 3: PR List Integration

### 3.1 Add Note Button

- [ ] Add "Add Note" button section to `expanded_row.html`
- [ ] Conditionally show "Edit Note" if note exists
- [ ] Wire up HTMX to load modal

### 3.2 PR Queryset Annotation

- [ ] Modify `pr_list_views.py` to annotate `has_note`, `note_flag`, `note_resolved`
- [ ] Pass annotation to template context

### 3.3 Note Indicator Badge

- [ ] Add badge to PR row in `table.html`
- [ ] Style badge based on flag color
- [ ] Show checkmark for resolved notes

### 3.4 Navigation Link

- [ ] Add "My Notes" link to sidebar
- [ ] Highlight active state

### 3.5 Playwright Check #3

- [ ] **Manual/Playwright:** Full flow - Add note from PR list
- [ ] **Manual/Playwright:** Verify badge appears on PR row
- [ ] **Manual/Playwright:** Click "Edit Note" from PR list
- [ ] **Manual/Playwright:** Navigate to My Notes from sidebar
- [ ] **Manual/Playwright:** Click "View PR" (opens new tab)

---

## Phase 4: Polish & E2E

### 4.1 Edge Cases

- [ ] Handle deleted PR gracefully (404 on View PR)
- [ ] Handle team access loss (notes still visible)
- [ ] Add toast notifications for success/error

### 4.2 Admin Registration

- [ ] Register PRNote in `admin.py`
- [ ] Add list_display, list_filter, search_fields

### 4.3 E2E Test

- [ ] Write `tests/e2e/personal-notes.spec.ts`
- [ ] Test: Create note from PR expanded row
- [ ] Test: Edit existing note
- [ ] Test: Resolve/Unresolve from My Notes
- [ ] Test: Delete note
- [ ] Test: Filter by status and flag
- [ ] Test: View PR link opens new tab
- [ ] Test: Empty state displays correctly
- [ ] Run: `npx playwright test tests/e2e/personal-notes.spec.ts`

### 4.4 Final Verification

- [ ] Run full test suite: `make test`
- [ ] Run E2E suite: `make e2e`
- [ ] Check no regressions on PR list performance
- [ ] Review code with `make ruff`

---

## Post-Implementation

- [ ] Update PRD status to "Implemented"
- [ ] Create PR from worktree branch to main
- [ ] Request code review
- [ ] Merge after approval
- [ ] Clean up worktree: `git worktree remove ../tformance-personal-notes`
- [ ] Archive this task folder to `dev/completed/`

---

## Quick Commands Reference

```bash
# Run notes app tests only
pytest apps/notes/ -v

# Run with coverage
pytest apps/notes/ --cov=apps/notes --cov-report=term-missing

# Run specific test class
pytest apps/notes/tests/test_views.py::TestNoteForm -v

# Run E2E test
npx playwright test tests/e2e/personal-notes.spec.ts --headed

# Check for ruff issues
make ruff-lint

# Start dev server with debug
DEBUG=True python manage.py runserver
```

---

## Notes & Blockers

*(Add notes during implementation)*

-

---

## Time Tracking

| Phase | Estimated | Actual |
|-------|-----------|--------|
| Phase 1: Foundation | 2-3 hours | |
| Phase 2: Delete & My Notes | 2-3 hours | |
| Phase 3: PR Integration | 1-2 hours | |
| Phase 4: Polish & E2E | 1-2 hours | |
| **Total** | 6-10 hours | |
