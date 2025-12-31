# Personal PR Notes - Implementation Plan

**Last Updated:** 2025-12-31
**PRD:** [prd/PERSONAL-NOTES.md](../../../prd/PERSONAL-NOTES.md)
**Status:** Ready for Implementation
**Worktree Branch:** `feature/personal-notes`

---

## Executive Summary

Implement a lightweight personal annotation system allowing CTOs to add private notes to PRs. Notes support flagging (False Positive, Review Later, Important, Concern), resolution tracking, and a dedicated "My Notes" review page.

### Key Deliverables
1. `apps/notes/` Django app with PRNote model
2. HTMX modal for add/edit/delete notes from PR list
3. My Notes page with status/flag filtering
4. PR row indicators for notes
5. Full test coverage (TDD) + E2E tests

---

## Current State Analysis

### Existing Patterns to Follow
- **Feedback app** (`apps/feedback/`) - HTMX modal pattern, view structure, test patterns
- **BaseModel** (`apps/utils/models.py`) - Created/updated timestamps
- **Team decorators** (`apps/teams/decorators.py`) - `@login_and_team_required`
- **PR expanded row** (`templates/metrics/pull_requests/partials/expanded_row.html`) - Integration point

### Key Differences from Feedback
| Aspect | Feedback (AIFeedback) | Notes (PRNote) |
|--------|----------------------|----------------|
| Scope | Team-scoped (`BaseTeamModel`) | User-scoped (FK to `CustomUser`) |
| Visibility | Team members can see | Only owner can see |
| PR relation | Optional | Required |
| Uniqueness | Multiple per PR | One per user per PR |

---

## Proposed Architecture

### Data Model
```python
class PRNote(BaseModel):
    user = FK(CustomUser, CASCADE)           # Owner (not TeamMember)
    pull_request = FK(PullRequest, CASCADE)  # Required
    content = TextField(max_length=2000)     # Note text
    flag = CharField(choices, blank=True)    # Optional category
    is_resolved = BooleanField(default=False)
    resolved_at = DateTimeField(null=True)

    class Meta:
        constraints = [UniqueConstraint(["user", "pull_request"])]
        indexes = [(user, is_resolved, created_at), (user, flag)]
```

### URL Structure
```
/a/<team_slug>/notes/                    → my_notes (list)
/a/<team_slug>/notes/pr/<pr_id>/         → note_form (GET: modal, POST: save)
/a/<team_slug>/notes/pr/<pr_id>/delete/  → delete_note (POST)
/a/<team_slug>/notes/pr/<pr_id>/resolve/ → toggle_resolve (POST)
```

### View Functions
1. `my_notes(request)` - List with pagination + filters
2. `note_form(request, pr_id)` - GET: modal form, POST: create/update
3. `delete_note(request, pr_id)` - Delete with confirmation
4. `toggle_resolve(request, pr_id)` - Toggle resolved status

---

## Implementation Phases

### Phase 1: Foundation (TDD)
**Goal:** Core model, factory, basic CRUD views

1. Create `apps/notes/` app structure
2. Write model tests (RED)
3. Implement PRNote model (GREEN)
4. Create migration
5. Write factory (REFACTOR)
6. Write form tests (RED)
7. Implement NoteForm (GREEN)
8. Write view tests for note_form (RED)
9. Implement note_form view (GREEN)
10. Create modal template
11. **Playwright check:** Modal opens, form submits

### Phase 2: Delete & My Notes Page
**Goal:** Delete functionality + list view with filters

1. Write delete view tests (RED)
2. Implement delete_note view (GREEN)
3. Write my_notes view tests (RED)
4. Implement my_notes view with filters (GREEN)
5. Create my_notes template with cards
6. Write resolve toggle tests (RED)
7. Implement toggle_resolve view (GREEN)
8. **Playwright check:** My Notes page loads, filters work

### Phase 3: PR List Integration
**Goal:** Connect to PR list, visual indicators

1. Add "Add Note" button to expanded_row.html
2. Annotate PR queryset with note existence
3. Add note indicator badge to PR rows
4. Register URLs in tformance/urls.py
5. Add navigation link to sidebar
6. **Playwright check:** Full user flow works

### Phase 4: Polish & E2E
**Goal:** Edge cases, final testing

1. Handle PR access edge cases (team access loss)
2. Admin registration
3. Write comprehensive E2E test
4. Run full test suite

---

## Technical Decisions

### Why User-Scoped (not Team-Scoped)?
Notes are personal annotations, not team resources. Using `CustomUser` FK instead of `BaseTeamModel` because:
- Simpler permission model (user.pr_notes vs team-scoped managers)
- Notes persist if user loses team access (personal data)
- No need for team context in queries

### Query Pattern
```python
# User isolation - simple FK filter
PRNote.objects.filter(user=request.user)

# For PR list annotation
PullRequest.objects.annotate(
    has_note=Exists(PRNote.objects.filter(
        user=request.user,
        pull_request=OuterRef('pk')
    ))
)
```

### HTMX Modal Pattern (from Feedback)
```html
<!-- Trigger in expanded_row.html -->
<button hx-get="{% url 'notes:note_form' pr.id %}"
        hx-target="body"
        hx-swap="beforeend">
  Add Note
</button>

<!-- Modal response -->
<dialog class="modal modal-open">
  <form hx-post="..." hx-target="closest dialog" hx-swap="outerHTML">
    ...
  </form>
</dialog>
```

---

## Worktree Setup

```bash
# Create worktree for isolated development
git worktree add ../tformance-personal-notes feature/personal-notes

# Navigate to worktree
cd ../tformance-personal-notes

# Install dependencies
make init

# Start services
make start

# Run dev server
make dev

# In another terminal, run tests continuously
pytest apps/notes/ -v --tb=short
```

---

## Testing Strategy

### Unit Tests (TDD - Write First)
- `apps/notes/tests/test_models.py` - Model creation, uniqueness, cascades
- `apps/notes/tests/test_views.py` - All view functions with permissions

### Integration Tests
- Cross-user isolation (User A cannot see User B's notes)
- HTMX responses return correct partials
- Filter combinations work correctly

### E2E Test (Playwright)
```typescript
// tests/e2e/personal-notes.spec.ts
test('CTO can create, edit, resolve, and delete note', async ({ page }) => {
  // 1. Login as CTO
  // 2. Navigate to PR list
  // 3. Expand a PR row
  // 4. Click "Add Note"
  // 5. Fill form, select flag, submit
  // 6. Verify modal closes, badge appears
  // 7. Navigate to "My Notes"
  // 8. Verify note card visible
  // 9. Click "Resolve"
  // 10. Verify resolved state
  // 11. Click "Edit", modify, save
  // 12. Delete note
  // 13. Verify removal
});
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Scope creep to team notes | Strictly private for v1; team visibility is v2 |
| Breaking PR list performance | Single annotated query, index on (user, pr) |
| HTMX state sync issues | Follow established feedback modal pattern |
| Test flakiness | Use factories consistently, avoid time-dependent tests |

---

## Success Criteria

1. All unit tests pass (100% coverage on notes app)
2. E2E test passes consistently
3. PRD acceptance criteria met for all 7 user stories
4. No performance regression on PR list page
5. Code follows existing patterns (feedback app as template)

---

## File Structure (After Implementation)

```
apps/notes/
├── __init__.py
├── admin.py
├── apps.py
├── factories.py
├── forms.py
├── models.py
├── urls.py
├── views.py
└── tests/
    ├── __init__.py
    ├── test_models.py
    └── test_views.py

templates/notes/
├── my_notes.html
└── partials/
    ├── note_form.html
    ├── note_card.html
    ├── note_success.html
    └── notes_list.html

tests/e2e/
└── personal-notes.spec.ts
```
