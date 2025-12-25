# LLM Full PR Context Enhancement - Plan

**Last Updated: 2025-12-24**

## Executive Summary

Enhance the LLM analysis pipeline to pass ALL available PR data to the prompt. This provides maximum context for:
- **Technology detection** - File extensions reveal languages (`.py` → Python, `.tsx` → React)
- **AI co-author detection** - Commit messages contain "Co-Authored-By" signatures
- **Better summaries** - Milestone, assignees, linked issues provide business context
- **Review insights** - Reviewer names and states show collaboration patterns

## Current State Analysis

### All PullRequest Fields

| Field | Type | Currently Passed? |
|-------|------|-------------------|
| `title` | TextField | ✅ Yes |
| `body` | TextField | ✅ Yes |
| `state` | CharField | ✅ Yes |
| `additions` | IntegerField | ✅ Yes |
| `deletions` | IntegerField | ✅ Yes |
| `labels` | JSONField | ✅ Yes |
| `is_draft` | BooleanField | ✅ Yes |
| `is_hotfix` | BooleanField | ✅ Yes |
| `is_revert` | BooleanField | ✅ Yes |
| `cycle_time_hours` | DecimalField | ✅ Yes |
| `review_time_hours` | DecimalField | ✅ Yes |
| `total_comments` | IntegerField | ✅ Yes |
| `commits_after_first_review` | IntegerField | ✅ Yes |
| `review_rounds` | IntegerField | ✅ Yes |
| `milestone_title` | CharField | ❌ **NOT PASSED** |
| `assignees` | JSONField | ❌ **NOT PASSED** |
| `linked_issues` | JSONField | ❌ **NOT PASSED** |
| `jira_key` | CharField | ❌ **NOT PASSED** |
| `author.display_name` | CharField | ❌ **NOT PASSED** |

### Related Models NOT Passed

| Model | Related Name | Key Field | Purpose |
|-------|--------------|-----------|---------|
| `PRFile` | `files` | `filename` | Tech detection from file extensions |
| `Commit` | `commits` | `message` | AI co-author detection |
| `PRReview` | `reviews` | `reviewer.display_name`, `state` | Review patterns |
| `PRComment` | `comments` | `body` | Discussion context |

## Proposed Future State

### New Parameters for `get_user_prompt()`

Add these new parameters:
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
    file_paths: list[str] | None = None,      # Already exists
    commit_messages: list[str] | None = None,  # Already exists
    reviewers: list[str] | None = None,        # NEW
    review_comments: list[str] | None = None,  # NEW - sample of comments
) -> str:
```

### Benefits

- **File paths** → Definitive tech detection from extensions
- **Commit messages** → "Co-Authored-By: Claude" detection
- **Milestone** → Business context (e.g., "Q1 Release")
- **Linked issues** → Feature scope understanding
- **Jira key** → Cross-reference with project management
- **Reviewers** → Collaboration pattern insights
- **Review comments** → Discussion context for health assessment

## Implementation Phases

### Phase 1: Extend `get_user_prompt()` (Effort: M)

Add new parameters and formatting for:
- `milestone`, `assignees`, `linked_issues`, `jira_key`
- `author_name`, `reviewers`, `review_comments`
- Increment `PROMPT_VERSION` to 6.1.0

### Phase 2: Update Celery Task (Effort: M)

Modify `run_llm_analysis_batch()` to:
1. Prefetch related data: `files`, `commits`, `reviews`, `comments`
2. Extract all new fields from PR and related models
3. Pass ALL context to `get_user_prompt()`

### Phase 3: Update Management Command (Effort: S)

Apply same changes to `run_llm_analysis.py` management command.

### Phase 4: Test Coverage (Effort: M)

Add tests for all new parameters and data extraction.

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Token limit exceeded | Medium | Medium | Limit files to 20, commits to 5, comments to 3 |
| N+1 query performance | Low | Medium | Use `prefetch_related()` for all relations |
| Missing data | Low | Low | Handle None/empty gracefully |
| Prompt too long | Medium | Low | Truncate long fields (already done) |

## Success Metrics

1. All PR fields passed to LLM prompt
2. Related data (files, commits, reviews) included
3. No query count increase (via prefetch)
4. All existing tests pass
5. New tests cover enhanced context

## Token Budget Limits

To avoid exceeding LLM token limits:
- **File paths**: Max 20 files (truncate with "+N more")
- **Commit messages**: Max 5 commits (truncate with "... and N more")
- **Review comments**: Max 3 comments (sample most relevant)
- **PR body**: Already truncated to ~2000 chars in promptfoo export

## Dependencies

- All related models must have data (populated during GitHub sync)
- No new packages required
