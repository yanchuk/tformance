# Personal PR Notes - Product Requirements Document

**Document Version:** 1.0
**Date:** December 2025
**Status:** Draft for Review
**Author:** Product Team

---

## Related Documents

| Document | Description |
|----------|-------------|
| [PRD-MVP.md](PRD-MVP.md) | Main product specification |
| [DASHBOARDS.md](DASHBOARDS.md) | Dashboard views and metrics |
| [AI-DETECTION-TESTING.md](AI-DETECTION-TESTING.md) | AI detection patterns and testing |

---

## 1. Executive Summary

A lightweight personal annotation layer allowing CTOs to capture observations during PR reviews. Notes are private, attached to specific PRs, and reviewable in a dedicated "My Notes" view.

**Core value:** Bridge the gap between weekly PR review sessions and monthly synthesis by preserving context and flagging items for follow-up.

---

## 2. Problem Statement

### The Context Loss Problem

During weekly PR reviews, CTOs often notice patterns, issues, or items requiring follow-up. Currently:

1. **Observations are forgotten** before monthly synthesis
2. **External tools** (Notion, Google Docs) are disconnected from PR data
3. **No structured flagging** to mark PRs needing attention

### User Quotes

> "I review 50+ PRs a week. By month-end, I can't remember which ones had issues."

> "When AI detection seems wrong, I have nowhere to note it for later."

---

## 3. Solution Overview

### Features

| Feature | Description |
|---------|-------------|
| **Add Note to PR** | Modal from PR expanded row to capture observations |
| **Flag Categories** | Mark notes as: False Positive, Review Later, Important, Concern |
| **My Notes Page** | Dedicated view to review all notes with filtering |
| **Note Indicators** | Visual badges on PR rows showing notes exist |

### Out of Scope (v1)

| Feature | Reason |
|---------|--------|
| Team-shared notes | Adds permission complexity; private is simpler for MVP |
| General notes | Focus on PR-attached context; general notes can use external tools |
| Markdown preview | Plain text sufficient for MVP |
| Full-text search | Flag filtering covers primary use case |
| Export functionality | Not needed for internal review workflow |

---

## 4. User Stories

### US-1: Add Note to PR

**As a** CTO reviewing the PR list
**I want to** add a personal note to a specific PR
**So that** I can capture my observations for later review

**Acceptance Criteria:**
- [ ] "Add Note" button visible in PR expanded row
- [ ] Modal opens with textarea and flag dropdown
- [ ] Note saved on submit, modal closes
- [ ] Confirmation message shown
- [ ] Note persisted to database, linked to user and PR

### US-2: Edit Existing Note

**As a** CTO who previously added a note
**I want to** edit my existing note on a PR
**So that** I can update observations over time

**Acceptance Criteria:**
- [ ] "Edit Note" button shown if note exists (replaces "Add Note")
- [ ] Modal pre-filled with existing content and flag
- [ ] Changes saved as update (not new note)
- [ ] One note per user per PR enforced

### US-3: Delete Note

**As a** CTO who no longer needs a note
**I want to** delete my note from a PR
**So that** my notes list stays relevant

**Acceptance Criteria:**
- [ ] Delete button in modal (edit mode only)
- [ ] Confirmation required before deletion
- [ ] Note removed from database
- [ ] PR row indicator removed

### US-4: View All My Notes

**As a** CTO doing monthly synthesis
**I want to** see all my notes in one place
**So that** I can review patterns and follow up

**Acceptance Criteria:**
- [ ] "My Notes" accessible from navigation menu
- [ ] Notes sorted by most recent first
- [ ] Each card shows: PR title, repo, note preview, flag badge, date
- [ ] Each card has actions: Edit (opens modal), Resolve/Unresolve, View PR (new tab)
- [ ] Pagination at 50 notes
- [ ] Empty state shown when no notes exist

### US-5: Filter Notes by Flag

**As a** CTO reviewing flagged items
**I want to** filter notes by flag type
**So that** I can focus on specific categories

**Acceptance Criteria:**
- [ ] Dropdown filter: All, False Positive, Review Later, Important, Concern
- [ ] HTMX-based filtering (no full page reload)
- [ ] Empty state message when no matches
- [ ] Filter state persisted in URL

### US-6: Mark Note as Resolved

**As a** CTO who has addressed a noted item
**I want to** mark the note as resolved (done)
**So that** I can track what's been handled while keeping history

**Acceptance Criteria:**
- [ ] "Mark as Resolved" button available on note cards **in My Notes page only**
- [ ] Resolved notes show visual distinction (muted style, checkmark icon)
- [ ] Resolved notes kept in database (not deleted)
- [ ] Can filter My Notes by: All, Active (unresolved), Resolved
- [ ] Can "unresolve" a resolved note to reopen it
- [ ] `resolved_at` timestamp captured when resolved

**Note:** Resolve action is NOT available in the edit modal - it's a list-review action only.

### US-7: See Note Indicator on PR Row

**As a** CTO browsing the PR list
**I want to** see which PRs have notes
**So that** I can identify reviewed items

**Acceptance Criteria:**
- [ ] Small icon/badge on PR rows with notes
- [ ] Badge color reflects flag type (if flagged)
- [ ] Resolved notes show different indicator (e.g., checkmark)
- [ ] Tooltip shows note preview on hover (optional)

---

## 5. Data Model

```
PRNote
├── id (PK, auto)
├── user (FK → CustomUser) - Note owner
├── pull_request (FK → PullRequest) - Associated PR
├── content (TextField, max 2000 chars) - Note text
├── flag (CharField, optional) - Category flag
├── is_resolved (BooleanField, default=False) - Marked as done
├── resolved_at (DateTimeField, nullable) - When marked resolved
├── created_at (DateTimeField, auto)
└── updated_at (DateTimeField, auto)

Constraints:
- UNIQUE(user, pull_request) - One note per user per PR
- CASCADE delete when PR deleted
- CASCADE delete when User deleted

Indexes:
- (user, is_resolved, created_at) - For My Notes listing with status filter
- (user, flag) - For flag filtering
```

### Flag Options

| Value | Display Label | Color | Use Case |
|-------|---------------|-------|----------|
| (empty) | No Flag | — | General observation |
| `false_positive` | False Positive | Red | AI detection was incorrect (personal annotation only - does NOT change PR's AI status) |
| `review_later` | Review Later | Yellow | Needs follow-up |
| `important` | Important | Blue | High priority observation |
| `concern` | Concern | Orange | Issue to address with team |

---

## 6. UI/UX Specifications

### Entry Point: PR Expanded Row

Location: Bottom of expanded row content, after AI & Tech section

```
┌─────────────────────────────────────────────────────┐
│ PR #123: Add user authentication                    │
├─────────────────────────────────────────────────────┤
│ Summary    │    Health    │    AI & Tech            │
│ ...        │    ...       │    ...                  │
├─────────────────────────────────────────────────────┤
│ My Note                                             │
│ [Add Note]  ← or [Edit Note 📝] if exists           │
└─────────────────────────────────────────────────────┘
```

### Note Modal

DaisyUI dialog, following existing feedback modal pattern.

```
┌─────────────────────────────────────────────────────┐
│ Note for PR #123                              [×]   │
├─────────────────────────────────────────────────────┤
│                                                     │
│ Note                                                │
│ ┌─────────────────────────────────────────────────┐ │
│ │ This PR seems to use Copilot but detection     │ │
│ │ missed it. Check commit messages for patterns. │ │
│ │                                                │ │
│ └─────────────────────────────────────────────────┘ │
│ Max 2000 characters                                 │
│                                                     │
│ Flag (optional)                                     │
│ [False Positive ▾]                                  │
│                                                     │
│         [Delete]  [Cancel]  [Save Note]             │
│         (edit only)                                 │
└─────────────────────────────────────────────────────┘
```

### My Notes Page

Accessible from main navigation.

```
┌─────────────────────────────────────────────────────┐
│ My Notes                                            │
│                                                     │
│ Status: [Active ▾]    Flag: [All ▾]                 │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📝 backend-api / PR #456                        │ │
│ │ Refactor auth module                            │ │
│ │ ┌────────────┐                         2 days   │ │
│ │ │Review Later│                                  │ │
│ │ └────────────┘                                  │ │
│ │ "Need to check if this impacts the login..."   │ │
│ │                     [Edit] [Resolve] [View PR ↗] │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ ┌─────────────────────────────────────────────────┐ │
│ │ 📝 frontend-app / PR #123                       │ │
│ │ Add user authentication                         │ │
│ │ ┌──────────────┐                       5 days   │ │
│ │ │False Positive│                                │ │
│ │ └──────────────┘                                │ │
│ │ "This PR seems to use Copilot but detection..." │ │
│ │                     [Edit] [Resolve] [View PR ↗] │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ Showing 1-2 of 2 notes                              │
│                                                     │
│ ─────────────────────────────────────────────────── │
│ Empty State (when no notes):                        │
│ "No notes yet. Add notes to PRs during your review  │
│  to capture observations for later."                │
└─────────────────────────────────────────────────────┘
```

### PR Row Indicator

Small badge in PR table row when note exists:

```
│ PR #456 📝 │ Refactor auth │ merged │ 2d ago │
```

Badge uses flag color if flagged.

---

## 7. Technical Requirements

### Privacy & Security

| Requirement | Implementation |
|-------------|----------------|
| User isolation | Query: `PRNote.objects.filter(user=request.user)` |
| No cross-user access | Views reject access to other users' notes |
| Cascade on delete | Note deleted when PR or User deleted |
| No API exposure | Notes not exposed in public/team APIs |
| Team access loss | Notes persist even if user loses team access (personal data) |

### Performance

| Requirement | Implementation |
|-------------|----------------|
| Efficient listing | Index on `(user, created_at)` |
| PR list badge | Single annotated query to check note existence |
| Pagination | Default 50 per page on My Notes |

### HTMX Integration

| Pattern | Usage |
|---------|-------|
| Modal loading | `hx-get` to load form, `hx-target="body"`, `hx-swap="beforeend"` |
| Form submission | `hx-post`, `hx-target="closest dialog"`, `hx-swap="outerHTML"` |
| Filter updates | `hx-get` with `hx-push-url="true"` |

---

## 8. User Journeys

### Weekly Review Flow

```
1. CTO opens PR list
2. Scans through PRs, expands interesting ones
3. Notices something worth noting (pattern, issue, question)
4. Clicks "Add Note"
5. Types quick observation: "AI detection seems off here"
6. Selects flag: "False Positive"
7. Clicks "Save Note"
8. Modal closes, continues review
9. Repeats for 5-10 PRs
```

### Monthly Synthesis Flow

```
1. CTO opens "My Notes" page
2. Filters by "Active" to see unresolved notes (23 items)
3. Filters by flag "Review Later" → 8 items to follow up
4. Reviews each, clicks "View PR" (opens new tab) for context
5. Takes action, then marks note as "Resolved"
6. Filters by flag "False Positive" → 5 detection issues
7. Identifies pattern: AI detection misses certain commit formats
8. Creates internal task to improve detection patterns
9. Marks processed notes as "Resolved" (keeps history)
10. Optionally deletes notes no longer needed
```

---

## 9. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Adoption | 50% of active CTOs create ≥1 note within 30 days | Distinct users with notes |
| Engagement | Avg 5+ notes per active user per month | Notes created / users |
| Review Usage | 70% of note creators visit My Notes weekly | Page views per user |
| Retention | Notes feature used in consecutive months | Monthly active users |

---

## 10. Implementation Phases

### Phase 1: Core Model & CRUD

- Create `apps/notes/` Django app
- PRNote model with migrations
- Note form modal (add/edit)
- Delete functionality
- Unit tests (TDD)

**Deliverables:** Model, views, form template, tests

### Phase 2: My Notes Page

- List view with pagination
- Status filter (Active/Resolved/All)
- Flag filtering (HTMX)
- Note cards with: PR link, Edit button, Resolve toggle
- Mark as Resolved / Unresolve functionality
- Integration tests

**Deliverables:** My Notes page, filter UI, resolve action, navigation link

### Phase 3: PR List Integration

- "Add Note" button in expanded row
- Note indicator badge on PR rows
- E2E tests

**Deliverables:** PR list integration, visual indicators

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope creep to team notes | Delays MVP, adds complexity | Strict private-only scope; team visibility is Phase 2 |
| Low adoption | Feature unused | Track metrics, iterate on discoverability |
| Too many notes | Performance issues | Pagination from day 1, 50-note limit |
| Note content too long | Storage, display issues | 2000 char limit |

---

## 12. Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Markdown rendering? | No - plain text for MVP |
| Bulk delete? | No - single delete only |
| Note length limit? | Yes - 2000 characters |
| Date filtering? | No - flag filtering is primary |
| PR link behavior? | Opens in new tab |
| Flag categories? | 4 flags: False Positive, Review Later, Important, Concern |

---

## Appendix A: Flag Color Mapping

| Flag | Tailwind Class | DaisyUI Badge |
|------|---------------|---------------|
| False Positive | `text-error` | `badge-error` |
| Review Later | `text-warning` | `badge-warning` |
| Important | `text-info` | `badge-info` |
| Concern | `text-accent` | `badge-accent` |

---

## Appendix B: URL Structure

```
/app/notes/                        → My Notes list
/app/notes/pr/<pr_id>/             → Note form modal (GET/POST)
/app/notes/pr/<pr_id>/delete/      → Delete note (POST)
/app/notes/pr/<pr_id>/resolve/     → Toggle resolve status (POST)
```

**Query Parameters (My Notes list):**
- `status=active|resolved|all` (default: active)
- `flag=false_positive|review_later|important|concern` (default: all)
- Filters combine with AND logic (e.g., `?status=active&flag=review_later`)

---

## Appendix C: Edge Cases

| Scenario | Behavior |
|----------|----------|
| PR deleted | Note cascade deleted (user loses note) |
| User loses team access | Notes still visible in My Notes, but "View PR" link may 404 |
| Click "View PR" on deleted PR | Show error toast "PR no longer available" |
| Multiple filters applied | AND logic: Active + Review Later = only unresolved Review Later notes |
| Note on PR user can't access | Note card shows PR info, "View PR" returns 403 |
