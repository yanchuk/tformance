# Investigation: LLM Misclassifying Go Repo as Rails + Missing Files Sync

**Last Updated:** 2026-01-03

## Executive Summary

PR #2408 from `railsware/mailtrap-halon-scripts` (a Go repository) was incorrectly classified as Ruby/Rails by the LLM. Investigation revealed two related issues:

1. **LLM Bias**: The LLM inferred "Rails" from the organization name "railsware" when no file evidence was available
2. **Missing Files**: All 14 PRs from this repo had 0 files, 0 commits, 0 reviews in the database despite having code changes

## Current State Analysis

### Test Data (Team ID 149: railsware)

```
Repo: railsware/mailtrap-halon-scripts
Last sync: 2026-01-03 19:23:54 UTC
Sync status: completed
PRs synced: 14
```

### Database State (Before Re-test)

| PR # | Files | Commits | Reviews | additions | deletions |
|------|-------|---------|---------|-----------|-----------|
| 2410 | 2 | 0 | 0 | 5 | 0 |
| 2409 | 9 | 0 | 0 | 100 | 25 |
| 2408 | 0 | 0 | 0 | 5 | 0 |
| 2407 | 0 | 0 | 0 | 40 | 2 |
| 2406 | 0 | 0 | 0 | 100 | 25 |

**Note**: PRs 2410 and 2409 have files because they were synced during my investigation test at 20:37:06. The original sync at 19:17:00 saved 0 files.

### PR #2408 LLM Classification (WRONG)

```json
{
  "tech": {
    "languages": ["ruby"],      // WRONG - should be "go" or empty
    "frameworks": ["rails"]     // WRONG - inferred from org name "railsware"
  }
}
```

### Actual Files in PR #2408 (from GitHub API)

```
- src/lib/bounces/mailtrap/classifications.csv
- src/lib/bounces/mailtrap/classifier_test.go  ← Go file!
```

## Root Cause Analysis

### Issue 1: LLM Tech Detection Bias

**Finding**: When no file evidence is provided to the LLM, it falls back to inferring technology from:
- Organization names (e.g., "railsware" → Rails)
- Repository names that sound like frameworks
- Company branding

**Evidence**: The LLM prompt context only contained:
```
Repository: railsware/mailtrap-halon-scripts
Files: (none)
Repo languages: (none)
```

### Issue 2: Files Not Saved During Original Sync

**Timeline**:
- 19:17:00 - Original onboarding sync created PRs (0 files saved)
- 19:36:45 - Commit f30a1ad added structured logging
- 20:37:06 - Test sync updated PRs #2410, #2409 (files saved correctly)

**Verified Working Components**:
1. OAuth scopes are correct (`repo` provides full access)
2. GraphQL query includes `files(first: 50)`
3. App OAuth token returns files when tested directly
4. Current `_process_files()` code works correctly

**Possible Root Causes** (to verify with fresh sync):
1. Celery worker running stale code during original sync
2. Silent exception during file processing
3. Database transaction issue
4. Race condition in async processing

### Issue 3: Languages Not Fetched During Onboarding

**Finding**: `refresh_all_repo_languages_task` only runs monthly (1st of month, 3 AM UTC).
New repos added after the 1st won't have languages until next month.

**Location**: `tformance/settings.py:662-666`
```python
"refresh-repo-languages-monthly": {
    "task": "apps.integrations.tasks.refresh_all_repo_languages_task",
    "schedule": schedules.crontab(minute=0, hour=3, day_of_month=1),
}
```

## Proposed Fixes

### Fix 1: Add Anti-Bias Rules to LLM Prompt

**File**: `apps/metrics/prompts/templates/sections/tech_detection.jinja2`

Add explicit rules:
```markdown
### Critical Rules for Tech Detection

**DO NOT infer technology from:**
- Organization names (e.g., "railsware" ≠ Rails, "godev" ≠ Go)
- Repository names that sound like frameworks
- Company branding or naming conventions

**When file paths are missing or empty:**
- Return empty arrays: `languages: [], frameworks: []`
- Only detect technology if you have FILE EXTENSION evidence
```

### Fix 2: Add Language Fetch to Onboarding Pipeline

**File**: `apps/integrations/onboarding_pipeline.py`

Add `refresh_repo_languages_task` to Phase 1 pipeline after sync completes.

### Fix 3: Add Logging for Empty Nested Data

**File**: `apps/integrations/services/github_graphql_sync.py`

Log warning when files array is empty but additions/deletions > 0:
```python
if not files_nodes and (additions + deletions) > 0:
    logger.warning(f"PR #{pr_number}: has {additions}+{deletions} changes but 0 files")
```

## Implementation Phases

### Phase 1: Investigation Verification (NOW)
- User will delete team 149 data and re-run onboarding
- Monitor sync to see if files are saved correctly
- Check for any errors or exceptions

### Phase 2: Prompt Fix
1. Edit `tech_detection.jinja2` - add anti-bias rules
2. Update `PROMPT_VERSION` to `8.2.0`
3. Add golden test case for org name bias
4. Run: `make export-prompts && npx promptfoo eval`

### Phase 3: Pipeline Improvements
1. Add language fetch to onboarding pipeline
2. Add logging for empty nested data
3. Update tests

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing LLM analysis | High | Version bump, run promptfoo eval |
| Onboarding pipeline slowdown | Low | Language fetch is async, runs after sync |
| Missing real bugs in file sync | Medium | Add comprehensive logging |

## Success Metrics

- [ ] Fresh sync saves files correctly for all PRs
- [ ] PR #2408 classified correctly after re-analysis
- [ ] Repo languages available immediately after onboarding
- [ ] No more false tech classifications from org names

## Files to Modify

| File | Change |
|------|--------|
| `apps/metrics/prompts/templates/sections/tech_detection.jinja2` | Add anti-bias rules |
| `apps/metrics/services/llm_prompts.py` | Bump PROMPT_VERSION to 8.2.0 |
| `apps/metrics/prompts/golden_tests.py` | Add test for org name bias |
| `apps/integrations/onboarding_pipeline.py` | Add language fetch |
| `apps/integrations/services/github_graphql_sync.py` | Add logging for empty files |

## Validation Commands

```bash
# Test prompt changes
make export-prompts && npx promptfoo eval

# Run integration tests
.venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py -v
.venv/bin/pytest apps/integrations/tests/test_onboarding_pipeline.py -v

# Run prompt tests
.venv/bin/pytest apps/metrics/prompts/tests/ -v
```
