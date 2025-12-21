# Phase 11: AI Agent Feedback System - Plan

**Created:** 2025-12-21
**Status:** 🔴 PLANNING

## Overview

Help teams improve their AI coding assistants by collecting actionable feedback and generating configuration improvements.

**Value Proposition:** "We help improve your AI agent's performance"

## Why This Feature (Key Differentiator)

1. **Captures real friction** - When devs hit issues with AI-generated code, capture what went wrong
2. **Aggregates patterns** - Identify common failure modes across the team
3. **Generates improvements** - Suggest updates to agent.md, .cursorrules, etc.
4. **Closes the loop** - Track if suggested improvements actually help

> "Your AI coding assistant is only as good as its rules. We analyze your team's AI interactions to surface what's working, what's not, and suggest specific improvements to your agent configuration."

## Implementation Phases

### MVP Scope (Phase 11a) - Focus on core feedback loop

1. **Feedback Model** - Store feedback linked to PRs
2. **Feedback Button** - "Report AI Issue" on PR detail pages
3. **Feedback Form** - Quick categorization + description
4. **Feedback Dashboard** - View and filter feedback
5. **Basic Patterns** - Show top categories and trends

### Future Scope (Phase 11b)

6. **Slack Integration** - Reaction-based feedback
7. **Rule Suggestions** - AI-generated config improvements
8. **Improvement Tracking** - Before/after metrics
9. **Export** - Config file generation

## Data Model

### AIFeedback Model
```python
class AIFeedback(BaseTeamModel):
    """Feedback about AI-generated code issues."""

    # What was the issue?
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)

    # Where did it happen?
    pull_request = models.ForeignKey(PullRequest, null=True, blank=True)
    commit = models.ForeignKey(Commit, null=True, blank=True)
    file_path = models.CharField(max_length=500, blank=True)
    language = models.CharField(max_length=50, blank=True)

    # Who reported it?
    reported_by = models.ForeignKey(TeamMember)

    # Status
    status = models.CharField(max_length=20, default='open')
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
```

### Category Choices
```python
CATEGORY_CHOICES = [
    ('wrong_code', 'Generated wrong code'),
    ('missed_context', 'Missed project context'),
    ('style_issue', 'Style/formatting issue'),
    ('missing_tests', 'Forgot tests'),
    ('security', 'Security concern'),
    ('performance', 'Performance issue'),
    ('other', 'Other'),
]
```

## UI Components

### 1. Feedback Button (on PR pages)
- Floating action button or menu item
- Opens modal with feedback form
- Pre-fills PR context

### 2. Feedback Form Modal
- Category dropdown
- Description textarea
- Optional: file path, line numbers
- Submit button

### 3. Feedback Dashboard
- List of all feedback for team
- Filter by category, status, date
- Trend charts
- Top issues summary

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/app/feedback/` | GET | Feedback dashboard |
| `/app/feedback/create/` | POST | Submit new feedback |
| `/app/feedback/<id>/` | GET | Feedback detail |
| `/app/feedback/<id>/resolve/` | POST | Mark as resolved |

## Files to Create

```
apps/feedback/
├── __init__.py
├── models.py              # AIFeedback model
├── views.py               # Dashboard and CRUD views
├── urls.py                # URL patterns
├── forms.py               # FeedbackForm
├── admin.py               # Admin interface
└── tests/
    ├── __init__.py
    ├── test_models.py
    └── test_views.py

templates/feedback/
├── dashboard.html         # Main feedback list
├── detail.html            # Single feedback view
├── partials/
│   ├── feedback_form.html # Modal form
│   ├── feedback_card.html # List item
│   └── stats_cards.html   # Dashboard stats
```

## Integration Points

1. **PR Detail Page** - Add "Report AI Issue" button
2. **CTO Dashboard** - Add feedback summary card
3. **Team Dashboard** - Add feedback link in nav
4. **Slack (future)** - Add reaction handler to PR surveys

## Success Metrics

- Feedback submissions per week
- Categories distribution
- Resolution rate
- Time to resolution
- User engagement (who reports most)

## Technical Decisions

1. **Separate App** - Create `apps/feedback/` for clean separation
2. **TDD Approach** - Write tests first
3. **HTMX Integration** - Modal forms and dynamic updates
4. **Team-Scoped** - All data filtered by team
