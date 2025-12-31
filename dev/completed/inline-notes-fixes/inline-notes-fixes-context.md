# Inline Notes Fixes - Context & Key Files

**Last Updated:** 2025-12-31

---

## Key Files to Modify

### Templates

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `templates/notes/partials/note_icon.html` | Note icon button | Replace music note SVG with filled star; update hx-target/hx-swap |
| `templates/notes/partials/inline_note_form.html` | Inline form row | Update close behavior to dispatch event |
| `templates/notes/partials/inline_note_preview.html` | Inline preview row | Update close behavior to dispatch event |
| `templates/metrics/pull_requests/partials/table.html` | PR table | Add Alpine state for inline row tracking |

### Backend

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/notes/models.py` | PRNote model | Make `content` field optional (blank=True) |
| `apps/notes/forms.py` | NoteForm | Remove required validation on content |
| `apps/notes/views.py` | inline_note view | Handle empty content gracefully |

### Tests

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/notes/tests/test_views.py` | View tests | Add tests for optional content |
| `apps/notes/tests/test_models.py` | Model tests | Add tests for blank content |

---

## Technical Decisions

### Decision 1: Row Insertion Strategy

**Chosen:** `hx-target="closest tr"` with `hx-swap="afterend"`

**Rationale:**
- `afterend` inserts immediately after the target element (the TR)
- Simpler than custom swap handling
- Works with existing table structure

**Alternative Considered:** Using `hx-swap-oob` for out-of-band swap
- Rejected: More complex, requires ID-based targeting

### Decision 2: Multiple Click Prevention

**Chosen:** Alpine.js state on tbody with `inlineOpen` flag

**Implementation:**
```html
<tbody x-data="{ expanded: false, inlineOpen: false }">
  <!-- Icon checks inlineOpen before triggering -->
  <button x-show="!inlineOpen" hx-get="...">

  <!-- OR use @click guard -->
  <button @click="if(inlineOpen) return; inlineOpen = true" hx-get="...">
```

**Close Event:**
```html
<!-- In inline_note_form.html -->
<button @click="$dispatch('inline-closed'); $el.closest('tr').remove()">Cancel</button>

<!-- In tbody -->
<tbody @inline-closed="inlineOpen = false">
```

### Decision 3: Content Optional Implementation

**Model Change:**
```python
content = models.TextField(
    max_length=2000,
    blank=True,
    default="",
    help_text="Optional note content",
)
```

**Migration:** Simple `AlterField` - no data migration needed since existing content stays.

**Form Change:**
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.fields["content"].required = False
```

---

## SVG Icons Reference

### Filled Star (for PRs with notes)
```html
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
</svg>
```

### Outline Star (for PRs without notes) - Already correct
```html
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
  <path stroke-linecap="round" stroke-linejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"/>
</svg>
```

---

## HTMX Swap Behavior Reference

| Swap Value | Behavior |
|------------|----------|
| `innerHTML` | Replace inner HTML of target |
| `outerHTML` | Replace entire target element |
| `afterbegin` | Insert at beginning inside target |
| `beforebegin` | Insert before target |
| `afterend` | Insert after target ← **We need this** |
| `beforeend` | Insert at end inside target |

---

## Testing Checklist

### Manual Testing
- [ ] Icon shows filled star for PRs with notes
- [ ] Icon shows outline star for PRs without notes
- [ ] Icon color matches flag (warning/info/secondary/error)
- [ ] Clicking icon opens inline row BELOW the PR
- [ ] Clicking icon multiple times does NOT create duplicates
- [ ] Can save note with only flag (no content)
- [ ] Can save note with only content (no flag)
- [ ] Can save note with both flag and content
- [ ] Edit/Delete/Close buttons work correctly
- [ ] Keyboard shortcuts still work (Cmd+Enter, Escape)

### Automated Testing (TDD)
- [ ] Test `inline_note` view accepts empty content with flag
- [ ] Test `inline_note` view rejects empty content AND empty flag
- [ ] Test model allows blank content
- [ ] Test form validation for optional content
