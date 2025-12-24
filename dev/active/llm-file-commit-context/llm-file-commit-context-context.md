# LLM Full PR Context Enhancement - Context

**Last Updated: 2025-12-25**

## Status: ✅ COMPLETE

All phases implemented using TDD (Red-Green-Refactor cycle):
- **22 new tests** for `get_user_prompt()` v6.1.0 parameters
- **6 new tests** for Celery task data extraction
- **87 total tests** passing (73 prompts + 14 tasks)

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | `get_user_prompt()` - ADD new parameters |
| `apps/metrics/tasks.py` | Celery task `run_llm_analysis_batch()` - ADD data extraction |
| `apps/metrics/management/commands/run_llm_analysis.py` | Management command - ADD data extraction |
| `apps/metrics/models/github.py` | All PR-related models |
| `apps/metrics/tests/test_llm_prompts.py` | Prompt tests - ADD tests for new params |
| `apps/metrics/tests/test_llm_tasks.py` | Task tests - ADD tests for data extraction |

## All PR Data Available

### PullRequest Model Fields

```python
# apps/metrics/models/github.py:10-262

# ALREADY PASSED to get_user_prompt():
title: TextField
body: TextField
state: CharField (open, merged, closed)
additions: IntegerField
deletions: IntegerField
labels: JSONField (list of strings)
is_draft: BooleanField
is_hotfix: BooleanField
is_revert: BooleanField
cycle_time_hours: DecimalField
review_time_hours: DecimalField
total_comments: IntegerField
commits_after_first_review: IntegerField
review_rounds: IntegerField

# NOT YET PASSED (need to add):
milestone_title: CharField  # "Q1 Release", etc.
assignees: JSONField  # List of usernames
linked_issues: JSONField  # List of issue numbers
jira_key: CharField  # "PROJ-123"
author: ForeignKey(TeamMember)  # Need author.display_name
```

### Related Models (need prefetch)

```python
# PRFile - apps/metrics/models/github.py:442
class PRFile(BaseTeamModel):
    pull_request = ForeignKey(PullRequest, related_name="files")
    filename = CharField(max_length=500)  # Path like "apps/auth/views.py"
    status = CharField  # added, modified, removed, renamed
    file_category = CharField  # frontend, backend, test, docs, config

# Commit - apps/metrics/models/github.py:1068
class Commit(BaseTeamModel):
    pull_request = ForeignKey(PullRequest, related_name="commits")
    message = TextField  # Contains "Co-Authored-By: Claude"
    committed_at = DateTimeField
    author = ForeignKey(TeamMember)

# PRReview - apps/metrics/models/github.py:264
class PRReview(BaseTeamModel):
    pull_request = ForeignKey(PullRequest, related_name="reviews")
    reviewer = ForeignKey(TeamMember)
    state = CharField  # approved, changes_requested, commented
    review_submitted_at = DateTimeField

# PRComment - apps/metrics/models/github.py:910
class PRComment(BaseTeamModel):
    pull_request = ForeignKey(PullRequest, related_name="comments")
    body = TextField  # Comment text
    author = ForeignKey(TeamMember)
    comment_created_at = DateTimeField
```

## Current get_user_prompt() Signature

```python
# apps/metrics/services/llm_prompts.py:121-141
def get_user_prompt(
    pr_body: str,
    pr_title: str = "",
    file_count: int = 0,
    additions: int = 0,
    deletions: int = 0,
    comment_count: int = 0,
    repo_languages: list[str] | None = None,
    state: str = "",
    labels: list[str] | None = None,
    is_draft: bool = False,
    is_hotfix: bool = False,
    is_revert: bool = False,
    cycle_time_hours: float | None = None,
    review_time_hours: float | None = None,
    commits_after_first_review: int | None = None,
    review_rounds: int | None = None,
    file_paths: list[str] | None = None,      # EXISTS but not passed
    commit_messages: list[str] | None = None,  # EXISTS but not passed
) -> str:
```

## New Parameters to Add

```python
def get_user_prompt(
    # ... existing params ...
    # NEW - Additional PR metadata
    milestone: str | None = None,
    assignees: list[str] | None = None,
    linked_issues: list[str] | None = None,
    jira_key: str | None = None,
    author_name: str | None = None,
    # NEW - Related data
    reviewers: list[str] | None = None,
    review_comments: list[str] | None = None,
) -> str:
```

## Current Task Code Location

```python
# apps/metrics/tasks.py:152-167
user_prompt = get_user_prompt(
    pr_body=pr.body or "",
    pr_title=pr.title or "",
    additions=pr.additions or 0,
    deletions=pr.deletions or 0,
    comment_count=pr.total_comments or 0,
    state=pr.state or "",
    labels=pr.labels or [],
    is_draft=pr.is_draft or False,
    is_hotfix=pr.is_hotfix or False,
    is_revert=pr.is_revert or False,
    cycle_time_hours=pr.cycle_time_hours,
    review_time_hours=pr.review_time_hours,
    commits_after_first_review=pr.commits_after_first_review,
    review_rounds=pr.review_rounds,
    # MISSING: All new parameters
)
```

## Required Prefetch Pattern

```python
prs = list(
    qs.prefetch_related(
        'files',
        'commits',
        'reviews__reviewer',
        'comments__author',
    )
    .select_related('author')
    .order_by("-pr_created_at")[:limit]
)
```

## Data Extraction Pattern

```python
# Inside the for loop
file_paths = list(pr.files.values_list('filename', flat=True))
commit_messages = list(pr.commits.values_list('message', flat=True))
reviewers = list(set(
    r.reviewer.display_name
    for r in pr.reviews.all()
    if r.reviewer and r.reviewer.display_name
))
review_comments = [
    c.body[:200] + "..." if len(c.body) > 200 else c.body
    for c in list(pr.comments.all())[:3]
]

user_prompt = get_user_prompt(
    # ... existing params ...
    # New params
    milestone=pr.milestone_title or None,
    assignees=pr.assignees or [],
    linked_issues=[str(i) for i in pr.linked_issues] if pr.linked_issues else [],
    jira_key=pr.jira_key or None,
    author_name=pr.author.display_name if pr.author else None,
    file_paths=file_paths,
    commit_messages=commit_messages,
    reviewers=reviewers,
    review_comments=review_comments,
)
```

## Key Decisions

1. **Limit files to 20** - Prevent token overflow
2. **Limit commits to 5** - Focus on recent commits
3. **Limit review comments to 3** - Sample of discussion
4. **Truncate comment bodies to 200 chars** - Keep concise
5. **Use prefetch_related** - Avoid N+1 queries
6. **Handle empty/None gracefully** - All params optional
7. **Increment PROMPT_VERSION to 6.1.0** - Track schema changes
