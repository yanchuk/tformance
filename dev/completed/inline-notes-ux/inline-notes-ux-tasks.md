# Inline Notes UX - Task Checklist

**Last Updated:** 2025-12-31
**Branch:** `feature/inline-notes-ux`
**Worktree:** `/Users/yanchuk/Documents/GitHub/tformance-inline-notes`

---

## Setup

- [x] Create feature branch from main
- [x] Create worktree for isolated development
- [ ] Verify dev server runs in worktree

---

## Phase 1: Backend - Inline Note View (TDD) ✅

### 1.1 RED: Write Failing Tests
- [x] `test_inline_note_requires_login`
- [x] `test_inline_note_get_returns_form_for_new_note`
- [x] `test_inline_note_get_returns_preview_for_existing_note`
- [x] `test_inline_note_post_creates_note`
- [x] `test_inline_note_post_updates_existing_note`
- [x] `test_inline_note_post_validates_content`
- [x] `test_inline_note_delete_removes_note`
- [x] `test_inline_note_htmx_returns_partial`
- [x] Run tests → Confirmed FAIL (8 tests, 404 errors)

### 1.2 GREEN: Implement View
- [x] Add `inline_note` view to `apps/notes/views.py`
- [x] Add URL pattern to `apps/notes/urls.py`
- [x] Create `templates/notes/partials/inline_note_form.html`
- [x] Create `templates/notes/partials/inline_note_preview.html`
- [x] Run tests → Confirmed PASS (43 tests)

### 1.3 REFACTOR
- [x] Extracted `_get_pr_and_note()` helper to reduce duplication
- [x] Run tests → Confirmed PASS (43 tests)

---

## Phase 2: Templates - Note Icon Component ✅

### 2.1 Create Note Icon Template
- [x] Create `templates/notes/partials/note_icon.html`
- [x] Icon states: empty (outline) vs filled (solid)
- [x] Color based on flag (warning/info/secondary/error)
- [x] HTMX attributes (`hx-get`, `hx-target`, `hx-swap`)
- [x] Tooltip on hover

### 2.2 Integrate into PR Table
- [x] Update `templates/metrics/pull_requests/partials/table.html`
- [x] Add note lookup via `{% user_note_for_pr pr as note %}`
- [x] Include note icon at START of Title cell (before expand button)
- [x] Remove old note badge from badge row
- [x] Run tests → Confirmed PASS (43 tests)

---

## Phase 3: Templates - Inline Note Row ✅

### 3.1 Create Inline Row Template
- [x] Updated `templates/notes/partials/inline_note_form.html` as table row
- [x] Updated `templates/notes/partials/inline_note_preview.html` as table row
- [x] Preview mode: flag badge + content + [Edit] + [Delete] + [Close]
- [x] Edit mode: textarea + flag select + [Save] + [Cancel]
- [x] Alpine `x-data` for mode toggle (editing state)
- [x] Keyboard shortcuts: Cmd/Ctrl+Enter to save, Escape to cancel

### 3.2 HTMX Integration
- [x] Icon click fetches inline row via `hx-get`
- [x] Row inserted with `hx-swap="afterbegin"` into tbody
- [x] Form POST updates note via `hx-post`, replaces row
- [x] Delete via `hx-delete` with confirmation

---

## Phase 4: JavaScript - Alpine Component

**NOTE:** Keyboard shortcuts implemented inline in templates using Alpine directives.
No separate JS component needed.

- [x] Cmd/Ctrl+Enter submits form (`@keydown.meta.enter`, `@keydown.ctrl.enter`)
- [x] Escape closes form (`@keydown.escape`)
- [x] Auto-focus textarea (`x-init="$el.focus()"`)

---

## Phase 5: Polish & Testing

### 5.1 CSS Transitions
- [ ] Add slide animation for row expand/collapse
- [ ] Subtle hover effects on icon
- [ ] Focus states for form elements

### 5.2 Update Expanded Row
- [ ] Remove modal "Add Note" / "Edit Note" link
- [ ] Keep read-only note display in expanded row (optional)

### 5.3 E2E Tests
- [ ] Update `tests/e2e/notes.spec.ts`
- [ ] Test note icon visibility in PR list
- [ ] Test click → inline form appears
- [ ] Test preview → edit flow
- [ ] Test keyboard shortcuts (Cmd+Enter, Escape)
- [ ] Test save/cancel/delete

### 5.4 Final Verification
- [x] Unit tests pass (43/43)
- [ ] E2E tests pass
- [ ] Manual testing in browser
- [ ] Pre-commit hooks pass

---

## Completion

- [ ] Commit changes with descriptive message
- [ ] Push to feature branch
- [ ] Create PR for review
- [ ] Merge to main after approval
- [ ] Clean up worktree

---

## Implementation Notes

### Decisions Made
1. **No separate Alpine component file** - Keyboard shortcuts work fine with inline Alpine directives
2. **Icon placement** - At very start of Title cell, before expand button
3. **Row insertion** - Uses `hx-swap="afterbegin"` to insert at start of tbody
4. **Templates as table rows** - `<tr>` with `colspan="11"` for full width

### Files Created/Modified
- `apps/notes/views.py` - Added `inline_note` view, `_get_pr_and_note` helper
- `apps/notes/urls.py` - Added inline_note URL pattern
- `templates/notes/partials/note_icon.html` - NEW
- `templates/notes/partials/inline_note_form.html` - Updated as table row
- `templates/notes/partials/inline_note_preview.html` - Updated as table row
- `templates/metrics/pull_requests/partials/table.html` - Added note icon
- `apps/notes/tests/test_views.py` - Added 8 tests for inline_note view
