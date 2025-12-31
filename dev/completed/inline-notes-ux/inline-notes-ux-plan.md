# Inline Notes UX Redesign - Implementation Plan

**Last Updated:** 2025-12-31

## Executive Summary

Redesign the PR notes feature to enable rapid inline note-taking during CTO weekly reviews. Replace the current modal-based approach with an inline form that appears directly in the PR list, with a note icon on the left side of each row.

## Current State Analysis

### Pain Points
1. **Modal interrupts flow** - Current workflow requires: Expand row → Click "Add Note" → Modal opens → Fill form → Submit → Close modal
2. **Hidden action** - Note button only visible after expanding PR row (2 clicks minimum)
3. **No visual status** - Can't scan which PRs have notes without expanding each row

### Existing Implementation
- `apps/notes/` - Django app with PRNote model, forms, views
- Modal form at `/app/notes/pr/{id}/`
- Note badge in expanded row section
- HTMX-based form submission

## Proposed Future State

### UX Improvements
1. **Note icon in Title cell** - Visible without expanding row
2. **Color-coded status** - Icon color indicates flag type
3. **Inline form** - Slides in below PR row (no modal)
4. **Preview first** - Existing notes show preview, then [Edit] to modify
5. **Keyboard shortcuts** - Cmd+Enter to save, Escape to cancel

### Visual Design
```
┌────────────────────────────────────────────────────────────────────────┐
│  Title                    │ Repo │ Author │ ... │ Merged              │
├────────────────────────────────────────────────────────────────────────┤
│  ○  Fix auth bug #123     │ api  │ alice  │ ... │ 2d ago              │  ← No note
├────────────────────────────────────────────────────────────────────────┤
│  ●  Add payments #456     │ web  │ bob    │ ... │ 3d ago              │  ← Has note (blue)
├────────────────────────────────────────────────────────────────────────┤
│  ↳ "Need to follow up..." [Edit] [Delete]                             │  ← Preview row
└────────────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Backend - Inline Note View (TDD)
**Effort:** M

1. Write tests for `inline_note` view
   - GET returns inline row partial
   - POST saves note and returns success response
   - Handles create vs update
   - Requires authentication

2. Implement `inline_note` view in `apps/notes/views.py`

3. Add URL pattern in `apps/notes/urls.py`

### Phase 2: Templates - Note Icon Component (TDD)
**Effort:** S

1. Create `templates/notes/partials/note_icon.html`
   - Empty icon for no note
   - Filled icon with flag color for existing note
   - HTMX trigger to fetch inline row

2. Update `templates/metrics/pull_requests/partials/table.html`
   - Add note icon at start of Title cell
   - Include note lookup via template tag

### Phase 3: Templates - Inline Note Row (TDD)
**Effort:** M

1. Create `templates/notes/partials/inline_note_row.html`
   - Preview mode: note text + flag badge + [Edit] + [Delete]
   - Edit mode: textarea + flag select + [Save] + [Cancel]
   - Alpine.js component for mode switching

2. HTMX attributes for form submission

### Phase 4: JavaScript - Alpine Component
**Effort:** S

1. Create `assets/javascript/components/inline-notes.js`
   - `inlineNote()` Alpine component
   - Keyboard shortcuts (Cmd+Enter, Escape)
   - Auto-focus on edit mode

2. Register component in `assets/javascript/alpine.js`

### Phase 5: Polish & E2E Tests
**Effort:** M

1. CSS transitions for slide animation
2. Update E2E tests in `tests/e2e/notes.spec.ts`
3. Remove modal approach from expanded row

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| HTMX row insertion complexity | Medium | Use `hx-swap="afterend"` pattern |
| Keyboard shortcuts conflict | Low | Use `@keydown.meta.enter` (platform-aware) |
| Breaking existing My Notes page | Low | Keep existing views, only add new inline view |

## Success Metrics

- [ ] Note icon visible in Title cell for every PR
- [ ] One click to add note (icon → form appears inline)
- [ ] One click to view existing note (icon → preview appears)
- [ ] Cmd+Enter saves, Escape cancels
- [ ] No modal dialogs for note CRUD
- [ ] Smooth slide animation for inline row
- [ ] All existing tests pass
- [ ] New E2E tests for inline flow
