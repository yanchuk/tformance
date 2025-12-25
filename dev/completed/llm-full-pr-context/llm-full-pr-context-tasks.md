# LLM Full PR Context - Task Checklist

**Last Updated: 2025-12-25 (Session 3 - Final)**

## Status: COMPLETE ✅

All phases completed. Ready to move to `dev/completed/`.

## Phase 1: Audit & Documentation ✅

- [x] Document all PullRequest model fields
- [x] Document all related model fields (PRFile, Commit, PRReview, PRComment, PRCheckRun)
- [x] Identify what each code path sends
- [x] Create gap analysis table
- [x] Create example payloads (current vs proposed)

## Phase 2: Unified Context Builder ✅

- [x] Create `build_llm_pr_context(pr: PullRequest) -> str` in llm_prompts.py
  - [x] Add all PullRequest fields to output
  - [x] Add PRFile data with categories
  - [x] Add Commit data (messages, AI co-authors)
  - [x] Add PRReview data (state, body, reviewer)
  - [x] Add PRComment data (NEW - currently not sent)
  - [x] ~~Add PRCheckRun data~~ - SKIPPED (low value, high token cost)
  - [x] Add TrackedRepository languages
  - [x] Handle missing/None values gracefully
  - [x] Truncate long sections to respect token limits
- [x] Add type hints and docstring
- [x] Write unit tests for new function (28 tests, all passing)

## Phase 3: Update Callers ✅

- [x] Update `groq_batch.py` to use `build_llm_pr_context()`
  - [x] Import `build_llm_pr_context` from llm_prompts
  - [x] Replace `_format_pr_context()` call with `build_llm_pr_context(pr)`
  - [x] Remove helper methods: `_format_files_section`, `_format_commits_section`, `_format_reviews_section`, `_format_repo_languages_section`
  - [x] Update tests to use unified function directly
  - [x] Test batch processing still works (27 tests passing)
- [x] Update `run_llm_analysis.py` to use `build_llm_pr_context()`
  - [x] Import `build_llm_pr_context` from llm_prompts
  - [x] Replace lines 123-154 (manual field extraction) with single function call
  - [x] Update prefetch to include `comments__author`
- [x] Ensure backward compatibility with existing prompts

## Phase 4: Promptfoo Updates ✅

- [x] Update promptfoo-v6.yaml with new context format → Created `promptfoo-v6.2.yaml`
- [x] Add test cases for new fields (comments) → 3 new comment-based tests
- [x] Run promptfoo evaluation to verify no regression → 13/13 tests pass (100%)
- [x] Document any prompt version bump needed → v6.2.0
- [x] Update to use `v6.2.0-system.txt` as latest prompt file

## Phase 5: Testing & Validation ✅

- [x] Run unit tests: 101 tests in test_llm_prompts.py passing
- [x] Run groq_batch tests: 27 tests passing
- [x] Full test suite: 2958 passed (2 failures unrelated to this work)
- [x] Promptfoo tests: 13/13 passing

## Acceptance Criteria - All Met ✅

### For Phase 2 ✅
- [x] Single function handles ALL PR context formatting
- [x] All 30+ PullRequest fields are included
- [x] All 4 related models contribute data (files, commits, reviews, comments)
- [x] Function has 100% test coverage
- [x] Docstring documents all sections of output

### For Phase 3 ✅
- [x] Both callers use the same function
- [x] No duplicate formatting code remains
- [x] Performance is not degraded (prefetch_related used)
- [x] Existing functionality preserved

### For Phase 4 ✅
- [x] All promptfoo tests pass (13/13 = 100%)
- [x] New fields have test coverage (3 comment-based tests)
- [x] AI detection accuracy >= current baseline (maintained)

## Summary

- **PROMPT_VERSION**: 6.2.0
- **Function**: `build_llm_pr_context()` in `apps/metrics/services/llm_prompts.py`
- **Test file**: `promptfoo-v6.2.yaml` using `v6.2.0-system.txt`
- **Lines removed**: ~100 lines of duplicate formatting code
- **No migrations needed**

## Next Steps (Optional Future Work)

- Consider moving this task to `dev/completed/`
- Monitor AI detection accuracy in production
- Add more comment-based test cases as edge cases discovered
