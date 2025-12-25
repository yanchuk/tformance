# LLM Full PR Context - Implementation Plan

**Last Updated: 2025-12-25**

## Executive Summary

Audit the PR data we send to LLM for analysis and ensure we're sending ALL available information from the PullRequest model and related models. Currently there's a gap between what `get_user_prompt()` in llm_prompts.py supports vs what `_format_pr_context()` in groq_batch.py actually sends.

## Current State Analysis

### What We Have in the Database (PullRequest Model)

| Field | Type | Currently Sent? | Notes |
|-------|------|-----------------|-------|
| `title` | TextField | ✅ Yes | Both paths |
| `body` | TextField | ✅ Yes | Both paths |
| `state` | CharField | ⚠️ Partial | run_llm_analysis only |
| `additions` | IntegerField | ✅ Yes | Both paths |
| `deletions` | IntegerField | ✅ Yes | Both paths |
| `labels` | JSONField | ⚠️ Partial | run_llm_analysis only |
| `is_draft` | BooleanField | ⚠️ Partial | run_llm_analysis only |
| `is_hotfix` | BooleanField | ⚠️ Partial | run_llm_analysis only |
| `is_revert` | BooleanField | ⚠️ Partial | run_llm_analysis only |
| `cycle_time_hours` | DecimalField | ⚠️ Partial | run_llm_analysis only |
| `review_time_hours` | DecimalField | ⚠️ Partial | run_llm_analysis only |
| `review_rounds` | IntegerField | ⚠️ Partial | run_llm_analysis only |
| `commits_after_first_review` | IntegerField | ⚠️ Partial | run_llm_analysis only |
| `total_comments` | IntegerField | ⚠️ Partial | run_llm_analysis only |
| `milestone_title` | CharField | ⚠️ Partial | run_llm_analysis only |
| `assignees` | JSONField | ⚠️ Partial | run_llm_analysis only |
| `linked_issues` | JSONField | ⚠️ Partial | run_llm_analysis only |
| `jira_key` | CharField | ⚠️ Partial | run_llm_analysis only |
| `github_repo` | CharField | ✅ Yes | groq_batch only |
| `github_pr_id` | BigIntegerField | ❌ No | Not sent |
| `pr_created_at` | DateTimeField | ❌ No | Not sent |
| `merged_at` | DateTimeField | ❌ No | Not sent |
| `first_review_at` | DateTimeField | ❌ No | Not sent |
| `avg_fix_response_hours` | DecimalField | ❌ No | Not sent |

### Related Models Data

| Model | Currently Sent? | Notes |
|-------|-----------------|-------|
| `PRFile` (files) | ⚠️ Partial | groq_batch sends, run_llm_analysis sends paths only |
| `Commit` (commits) | ⚠️ Partial | Both send messages, but limited |
| `PRReview` (reviews) | ⚠️ Partial | groq_batch sends bodies, run_llm_analysis sends reviewer names |
| `PRComment` (comments) | ❌ No | Not sent at all |
| `PRCheckRun` (check_runs) | ❌ Skip | Low value - merged PRs have passing CI |
| `TeamMember` (author) | ⚠️ Partial | Name only, no GitHub username context |
| `TrackedRepository` | ⚠️ Partial | groq_batch gets languages |

## Gap Analysis

### Two Code Paths - Not Aligned

1. **`groq_batch.py:_format_pr_context()`** - Used for batch processing
   - Has: repo, author, labels, linked_issues, files with categories, commits, reviews, repo languages
   - Missing: state, flags, timing metrics, milestone, assignees, jira_key, comments

2. **`run_llm_analysis.py`** - Uses `get_user_prompt()` from llm_prompts.py
   - Has: All timing metrics, flags, labels, milestone, assignees, linked_issues, jira_key
   - Missing: repo name, repo languages, file categories, review states

### Critical Missing Data

1. **PRComment** - Never sent, but may contain AI discussion
2. **PRCheckRun** - CI/CD context useful for health assessment
3. **Branch name** - Often contains Jira keys or feature context
4. **PR URL/number** - For debugging/verification

## Proposed Future State

### Unified PR Context Builder

Create a single `build_llm_pr_context()` function that:
1. Lives in `apps/metrics/services/llm_prompts.py` (source of truth)
2. Takes a `PullRequest` object with prefetched relations
3. Returns formatted context string with ALL available data
4. Is used by BOTH groq_batch.py AND run_llm_analysis.py

### Complete Data Mapping

```
# PR Metadata
- PR Number: {github_pr_id}
- Title: {title}
- Repository: {github_repo}
- Author: {author.display_name} (@{author.github_username})
- State: {state}
- Created: {pr_created_at}
- Merged: {merged_at}

# Flags
- Draft: {is_draft}
- Hotfix: {is_hotfix}
- Revert: {is_revert}

# Organization
- Labels: {labels}
- Milestone: {milestone_title}
- Assignees: {assignees}
- Jira: {jira_key}
- Linked Issues: {linked_issues}

# Code Changes
- Size: +{additions}/-{deletions} lines
- Files: {files count}
  - [category] filename (+add/-del)

# Timing Metrics
- Cycle time: {cycle_time_hours}h
- Time to first review: {review_time_hours}h
- Commits after review: {commits_after_first_review}
- Review rounds: {review_rounds}
- Total comments: {total_comments}
- Avg fix response: {avg_fix_response_hours}h

# Commits (last 10)
- {message} (by {author}, may contain Co-Authored-By)

# Reviews (last 5)
- [{state}] {reviewer}: {body}

# Comments (last 5) - NEW
- {author}: {body}

# Repository Languages
- Primary: {primary_language}
- All: {languages}

# Description
{body}
```

## Implementation Phases

### Phase 1: Audit & Align (This Task)
- Document current state (DONE above)
- Identify gaps (DONE above)
- Create plan files

### Phase 2: Unified Context Builder
- Create `build_llm_pr_context(pr: PullRequest) -> str` in llm_prompts.py
- Include ALL fields from PullRequest model
- Include ALL related model data (files, commits, reviews, comments)
- Add tests

### Phase 3: Add Missing Data
- Add PRComment to context (may contain AI discussion)
- ~~Add PRCheckRun~~ - SKIPPED (low value, high token cost)
- Add branch name if available
- Add PR URL

### Phase 4: Update Callers
- Update groq_batch.py to use new unified function
- Update run_llm_analysis.py to use new unified function
- Remove duplicate formatting code

### Phase 5: Update Promptfoo Tests
- Update test cases with new context format
- Verify LLM still produces correct outputs
- Run evaluation suite

## Example Payloads

### Example 1: Current State (run_llm_analysis.py)

```
Analyze this pull request:

Title: Add user authentication endpoint
Author: John Doe
State: merged

Lines: +250/-50
Files: apps/auth/views.py, apps/auth/tests.py, apps/auth/models.py

Cycle time: 24.5 hours
Time to first review: 2.0 hours
Comments: 8
Commits after first review: 3
Review rounds: 2

Reviewers: Jane Smith, Bob Wilson

Milestone: Q1 2025 Release
Assignees: jdoe
Linked issues: 123, 456
Jira: AUTH-1234

Recent commits:
- Add JWT token validation
- Fix token expiry handling
- Add tests for auth flow

Description:
Added Django REST Framework authentication endpoints with JWT tokens.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Example 2: Proposed Future State (Complete)

```
Analyze this pull request:

# PR Metadata
- PR Number: #1234
- Title: Add user authentication endpoint
- Repository: acme/backend
- Author: John Doe (@johndoe)
- State: merged
- Created: 2025-01-15 09:30:00 UTC
- Merged: 2025-01-16 10:00:00 UTC
- URL: https://github.com/acme/backend/pull/1234

# Flags
- Draft: No
- Hotfix: No
- Revert: No

# Organization
- Labels: feature, auth, backend
- Milestone: Q1 2025 Release
- Assignees: johndoe, janesmith
- Jira: AUTH-1234
- Linked Issues: #123, #456

# Code Changes
- Size: +250/-50 lines (Medium)
- Files changed: 5
  - [backend] apps/auth/views.py (+120/-20)
  - [backend] apps/auth/models.py (+50/-10)
  - [backend] apps/auth/serializers.py (+30/-5)
  - [test] apps/auth/tests/test_views.py (+40/-10)
  - [config] apps/auth/urls.py (+10/-5)

# Timing Metrics
- Cycle time: 24.5 hours
- Time to first review: 2.0 hours
- Commits after first review: 3
- Review rounds: 2
- Total comments: 8
- Avg fix response: 1.5 hours

# Commits (last 10)
- Add JWT token validation

  🤖 Generated with [Claude Code](https://claude.com/claude-code)

  Co-Authored-By: Claude <noreply@anthropic.com>
- Fix token expiry handling
- Add tests for auth flow

# Reviews
- [APPROVED] Jane Smith (@janesmith): LGTM! Nice clean implementation.
- [CHANGES_REQUESTED] Bob Wilson (@bwilson): Can we add rate limiting?
- [APPROVED] Bob Wilson (@bwilson): Rate limiting looks good now.

# Comments
- Jane Smith: Should we use refresh tokens here?
- John Doe: Good point, added in latest commit.
- Bot (coderabbit): AI Code Review: Looks good overall...

# Repository Languages
- Primary: Python
- All: Python (85%), TypeScript (10%), Shell (5%)

# Description
Added Django REST Framework authentication endpoints with JWT tokens.

## What
- New `/api/auth/login/` endpoint
- New `/api/auth/refresh/` endpoint
- JWT token validation middleware

## Why
Needed for mobile app authentication.

## AI Disclosure
Used Cursor with Claude for initial scaffolding.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Token limit exceeded | High | Medium | Truncate sections, prioritize most important data |
| LLM output quality degrades | Medium | Low | Test with promptfoo before deploying |
| Performance regression | Low | Medium | Use prefetch_related, limit related records |
| Breaking existing detection | High | Low | Keep backward compatible, run regression tests |

## Success Metrics

1. **Completeness**: 100% of PullRequest fields included in context
2. **Unified Code**: Single function used by all callers
3. **Test Coverage**: All fields tested in promptfoo suite
4. **No Regression**: AI detection accuracy maintained or improved

## Required Resources

- Update llm_prompts.py with unified builder
- Update groq_batch.py to use new function
- Update run_llm_analysis.py to use new function
- Update promptfoo test cases
- Run evaluation to verify no regression
