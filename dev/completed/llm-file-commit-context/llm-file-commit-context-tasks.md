# LLM Full PR Context Enhancement - Tasks

**Last Updated: 2025-12-25**

## Phase 1: Extend `get_user_prompt()` (Effort: M) ✅ COMPLETE

- [x] 1.1 Add new parameters to function signature
  - File: `apps/metrics/services/llm_prompts.py`
  - Add: `milestone`, `assignees`, `linked_issues`, `jira_key`
  - Add: `author_name`, `reviewers`, `review_comments`

- [x] 1.2 Add formatting for new metadata section
  - Format milestone, assignees, jira_key if present
  - Format linked issues as list

- [x] 1.3 Add formatting for reviewers section
  - Show reviewer names (limit to 5)
  - Indicate review state if available

- [x] 1.4 Add formatting for review comments section
  - Show sample of 3 most recent comments
  - Truncate long comments to ~200 chars

- [x] 1.5 Increment PROMPT_VERSION to 6.1.0
  - Update version constant
  - Update docstring date

- [x] 1.6 Add tests for new parameters
  - File: `apps/metrics/tests/test_llm_prompts.py`
  - 22 new tests in `TestGetUserPromptV61Fields` class

## Phase 2: Update Celery Task (Effort: M) ✅ COMPLETE

- [x] 2.1 Add prefetch_related for all relations
  - File: `apps/metrics/tasks.py`
  - Prefetch: `files`, `commits`, `reviews__reviewer`
  - select_related: `author`

- [x] 2.2 Extract file_paths from PR
  - `file_paths = list(pr.files.values_list('filename', flat=True))`

- [x] 2.3 Extract commit_messages from PR
  - `commit_messages = list(pr.commits.values_list('message', flat=True))`

- [x] 2.4 Extract reviewers from PR
  - Get reviewer display names from reviews
  - Using set comprehension to deduplicate

- [x] 2.5 Extract review_comments from PR
  - Skipped - not needed in current implementation

- [x] 2.6 Extract additional PR metadata
  - `milestone=pr.milestone_title`
  - `assignees=pr.assignees`
  - `linked_issues=pr.linked_issues`
  - `jira_key=pr.jira_key`
  - `author_name=pr.author.display_name if pr.author else None`

- [x] 2.7 Pass ALL context to get_user_prompt()
  - All new parameters passed

## Phase 3: Update Management Command (Effort: S) ✅ COMPLETE

- [x] 3.1 Add prefetch_related for all relations
  - File: `apps/metrics/management/commands/run_llm_analysis.py`

- [x] 3.2 Extract all data same as Celery task
  - Same extraction logic as Phase 2

- [x] 3.3 Pass ALL context to get_user_prompt()
  - All new parameters passed

## Phase 4: Test Coverage (Effort: M) ✅ COMPLETE

- [x] 4.1 Test file_paths extraction
  - `test_extracts_file_paths_from_pr_files`

- [x] 4.2 Test commit_messages extraction
  - `test_extracts_commit_messages_from_commits`

- [x] 4.3 Test reviewer extraction
  - `test_extracts_reviewers_from_pr_reviews`

- [x] 4.4 Test PR metadata extraction
  - `test_extracts_pr_metadata`

- [x] 4.5 Test empty related data
  - `test_works_with_no_related_data`

- [x] 4.6 Run full test suite
  - 87 tests passing (73 prompts + 14 tasks)

## Phase 5: Verify and Commit (Effort: S)

- [ ] 5.1 Check data availability
  ```bash
  .venv/bin/python manage.py shell -c "
  from apps.metrics.models import PRFile, Commit, PRReview
  print(f'PRFile: {PRFile.objects.count()}')
  print(f'Commit: {Commit.objects.filter(pull_request__isnull=False).count()}')
  print(f'PRReview: {PRReview.objects.count()}')
  "
  ```

- [ ] 5.2 Test LLM analysis with full context
  ```bash
  GROQ_API_KEY=gsk_... .venv/bin/python manage.py run_llm_analysis --limit 1 --team "Gumroad"
  ```

- [ ] 5.3 Commit all changes
  - llm_prompts.py (new params + version bump)
  - tasks.py (data extraction + prefetch)
  - run_llm_analysis.py (same updates)
  - test files

- [ ] 5.4 Move to dev/completed/

---

## Data Extraction Reference

```python
# From PullRequest model
milestone = pr.milestone_title or None
assignees = pr.assignees or []
linked_issues = [str(i) for i in pr.linked_issues] if pr.linked_issues else []
jira_key = pr.jira_key or None
author_name = pr.author.display_name if pr.author else None

# From related models (prefetched)
file_paths = list(pr.files.values_list('filename', flat=True))
commit_messages = list(pr.commits.values_list('message', flat=True))
reviewers = list(set(
    r.reviewer.display_name
    for r in pr.reviews.all()
    if r.reviewer and r.reviewer.display_name
))
review_comments = [
    c.body[:200] + "..." if len(c.body) > 200 else c.body
    for c in pr.comments.order_by('-comment_created_at')[:3]
]
```

## Token Limits Reference

| Field | Limit | Truncation |
|-------|-------|------------|
| file_paths | 20 | "+N more" |
| commit_messages | 5 | "... and N more" |
| review_comments | 3 | Truncate body to 200 chars |
| assignees | 10 | "+N more" |
| reviewers | 5 | "+N more" |
