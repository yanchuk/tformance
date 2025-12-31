# Inline Notes Fixes - Task Checklist

**Last Updated:** 2025-12-31
**Branch:** `feature/inline-notes-fixes`
**Worktree:** `/Users/yanchuk/Documents/GitHub/tformance-inline-notes-fixes`

---

## Setup

- [ ] Create feature branch from main
- [ ] Create worktree for isolated development
- [ ] Verify dev server runs in worktree

---

## Phase 1: Icon Fix (TDD)

### 1.1 RED: Write Failing Test
- [ ] Test that note icon uses star SVG (not music note)
- [ ] Run test → Confirm FAIL

### 1.2 GREEN: Fix Icon
- [ ] Replace music note SVG with filled star SVG in `note_icon.html`
- [ ] Keep color logic (warning/info/secondary/error based on flag)
- [ ] Run test → Confirm PASS

### 1.3 REFACTOR
- [ ] Verify icon displays correctly in browser
- [ ] Run all tests → Confirm PASS

---

## Phase 2: Row Position Fix (TDD)

### 2.1 RED: Write Failing Test
- [ ] Test that inline row renders AFTER current PR row (not at top of tbody)
- [ ] Run test → Confirm FAIL

### 2.2 GREEN: Fix Row Position
- [ ] Update `note_icon.html`:
  - Change `hx-target="closest tbody"` to `hx-target="closest tr"`
  - Change `hx-swap="afterbegin"` to `hx-swap="afterend"`
- [ ] Run test → Confirm PASS

### 2.3 REFACTOR
- [ ] Verify inline row appears below clicked PR in browser
- [ ] Run all tests → Confirm PASS

---

## Phase 3: Multiple Render Prevention (TDD)

### 3.1 RED: Write Failing Test
- [ ] Test that clicking icon twice does not create duplicate rows
- [ ] Run test → Confirm FAIL

### 3.2 GREEN: Implement Prevention
- [ ] Add `inlineOpen` state to tbody in `table.html`:
  ```html
  <tbody x-data="{ expanded: false, inlineOpen: false }"
         @inline-closed.window="inlineOpen = false">
  ```
- [ ] Update note icon in `note_icon.html`:
  ```html
  <button ... @click.stop="if(inlineOpen) { $event.preventDefault(); return; } inlineOpen = true">
  ```
- [ ] Add close event dispatch in `inline_note_form.html`:
  ```html
  <button @click="$dispatch('inline-closed'); $el.closest('tr').remove()">Cancel</button>
  ```
- [ ] Add close event dispatch in `inline_note_preview.html`:
  ```html
  <button @click="$dispatch('inline-closed'); $el.closest('tr').remove()">Close</button>
  ```
- [ ] Run test → Confirm PASS

### 3.3 REFACTOR
- [ ] Verify clicking icon twice does not create duplicates in browser
- [ ] Verify closing inline row allows reopening
- [ ] Run all tests → Confirm PASS

---

## Phase 4: Optional Content (TDD)

### 4.1 RED: Write Failing Tests
- [ ] `test_inline_note_post_creates_note_with_flag_only`
- [ ] `test_inline_note_post_requires_flag_if_no_content`
- [ ] `test_model_allows_blank_content`
- [ ] Run tests → Confirm FAIL

### 4.2 GREEN: Implement Optional Content

#### 4.2.1 Model Change
- [ ] Update `apps/notes/models.py`:
  ```python
  content = models.TextField(
      max_length=2000,
      blank=True,
      default="",
      help_text="Optional note content",
  )
  ```
- [ ] Create migration: `python manage.py makemigrations notes`
- [ ] Apply migration: `python manage.py migrate`

#### 4.2.2 Form Change
- [ ] Update `apps/notes/forms.py`:
  ```python
  def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      self.fields["content"].required = False
  ```

#### 4.2.3 View Change
- [ ] Update `apps/notes/views.py` to validate:
  - Either content OR flag must be provided
  - Empty content + empty flag = validation error

#### 4.2.4 Template Changes
- [ ] Update `inline_note_form.html`:
  - Remove `required` attribute from textarea
  - Update placeholder: "Optional: Add your observations..."
- [ ] Update `inline_note_preview.html`:
  - Handle empty content display gracefully

- [ ] Run tests → Confirm PASS

### 4.3 REFACTOR
- [ ] Verify can save note with flag only (no content) in browser
- [ ] Verify validation error when both empty
- [ ] Run all tests → Confirm PASS

---

## Phase 5: Final Verification

- [ ] All unit tests pass
- [ ] Manual browser testing complete
- [ ] Pre-commit hooks pass

---

## Completion

- [ ] Commit changes with descriptive message
- [ ] Merge to main
- [ ] Delete feature branch
- [ ] Clean up worktree

---

## Implementation Notes

### Decisions Made
*(To be filled during implementation)*

### Files Created/Modified
*(To be filled during implementation)*

### Issues Encountered
*(To be filled during implementation)*
