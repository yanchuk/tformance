# Repository Name Display - Tasks

**Last Updated: 2025-12-24**

## Phase 1: Create Template Filter [S]

- [ ] Add `repo_name` filter to `apps/metrics/templatetags/pr_list_tags.py`
  - [ ] Handle empty/None values
  - [ ] Split on "/" and return last segment
  - [ ] Handle strings without "/" (return as-is)

## Phase 2: Update Templates [S]

- [ ] Update `templates/metrics/pull_requests/partials/table.html`
  - [ ] Add `|repo_name` filter to `{{ pr.github_repo }}`
- [ ] Update `templates/metrics/pull_requests/list.html`
  - [ ] Add `|repo_name` filter to `{{ repo }}` in option text
  - [ ] Keep `value="{{ repo }}"` unchanged (full name for filtering)

## Phase 3: Testing [S]

- [ ] Add unit tests in `apps/metrics/tests/test_pr_list_tags.py`
  - [ ] Test `"owner/repo"` -> `"repo"`
  - [ ] Test empty string
  - [ ] Test None
  - [ ] Test string without slash
- [ ] Manual verification on PR List page
  - [ ] Table shows short repo names
  - [ ] Dropdown shows short repo names
  - [ ] Filtering by repo still works

## Completion Criteria

- [ ] Repository column shows just repo name (e.g., "gumroad" not "antiwork/gumroad")
- [ ] Filter dropdown shows short names
- [ ] Filtering functionality unchanged
- [ ] All tests pass
