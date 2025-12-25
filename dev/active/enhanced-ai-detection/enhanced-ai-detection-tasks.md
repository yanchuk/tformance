# Enhanced AI Detection - Tasks

**Last Updated: 2025-12-25**

## Overview

| Phase | Status | Effort | Impact |
|-------|--------|--------|--------|
| Phase 1: Commit Signals | 🔲 Pending | S | High |
| Phase 2: Review Signals | 🔲 Pending | S | Medium |
| Phase 3: File Patterns | 🔲 Pending | M | Medium |
| Phase 4: Enhanced LLM | 🔲 Pending | M | High |
| Phase 5: Composite Score | 🔲 Pending | L | High |

---

## Phase 1: Commit Signal Aggregation

**Goal**: Flag PRs that contain AI-assisted commits

### 1.1 Database Migration
- [ ] Create migration `0022_add_ai_signal_fields.py`
- [ ] Add `has_ai_commits` BooleanField to PullRequest
- [ ] Add index on (team, has_ai_commits)
- [ ] Run migration locally and verify

### 1.2 Aggregation Service
- [ ] Create `apps/metrics/services/ai_signals.py`
- [ ] Implement `aggregate_commit_ai_signals(pr_id) -> bool`
- [ ] Check `Commit.is_ai_assisted` for any True
- [ ] Check `Commit.ai_co_authors` for non-empty lists
- [ ] Return aggregated result

### 1.3 Unit Tests (TDD)
- [ ] `test_aggregate_no_commits_returns_false`
- [ ] `test_aggregate_no_ai_commits_returns_false`
- [ ] `test_aggregate_with_ai_commit_returns_true`
- [ ] `test_aggregate_with_ai_coauthors_returns_true`
- [ ] `test_aggregate_with_mixed_commits`

### 1.4 Backfill Command
- [ ] Create `apps/metrics/management/commands/backfill_ai_signals.py`
- [ ] Add `--dry-run` flag
- [ ] Add `--team` filter option
- [ ] Batch processing (500 PRs at a time)
- [ ] Progress logging
- [ ] Test on sample data

### 1.5 Sync Pipeline Integration
- [ ] Update `_process_pr()` in github_graphql_sync.py
- [ ] Call aggregation after commits are synced
- [ ] Update `sync_repository_incremental_graphql()`
- [ ] Test with fresh sync

### 1.6 Verification
- [ ] Run backfill on full database
- [ ] Verify count matches expected (154+ PRs)
- [ ] Spot-check 10 PRs manually

---

## Phase 2: AI Review Signals

**Goal**: Flag PRs that received AI-generated reviews

### 2.1 Database Migration
- [ ] Add `has_ai_review` BooleanField to PullRequest (in 0022)
- [ ] Run migration

### 2.2 Aggregation Function
- [ ] Add `aggregate_review_ai_signals(pr_id) -> bool` to ai_signals.py
- [ ] Check `PRReview.is_ai_review` for any True
- [ ] Return list of AI reviewer types

### 2.3 Unit Tests (TDD)
- [ ] `test_aggregate_no_reviews_returns_false`
- [ ] `test_aggregate_no_ai_reviews_returns_false`
- [ ] `test_aggregate_with_ai_review_returns_true`
- [ ] `test_aggregate_returns_reviewer_types`

### 2.4 Backfill Integration
- [ ] Extend backfill command to cover reviews
- [ ] Test on sample data

### 2.5 Sync Pipeline Integration
- [ ] Update `_process_reviews()` in github_graphql_sync.py
- [ ] Set `has_ai_review` after processing

### 2.6 Verification
- [ ] Run backfill
- [ ] Verify 1,241+ PRs flagged
- [ ] Spot-check samples

---

## Phase 3: File Pattern Detection

**Goal**: Detect AI tool artifacts from file paths

### 3.1 Database Migration
- [ ] Add `has_ai_files` BooleanField to PullRequest (in 0022)
- [ ] Run migration

### 3.2 Pattern Detector
- [ ] Add `AI_FILE_PATTERNS` to ai_patterns.py
- [ ] Patterns: `.cursor/`, `.claude/`, `aider.chat/`, `.copilot/`
- [ ] Add `detect_ai_file_patterns(file_paths) -> dict`
- [ ] Return matched patterns and file counts

### 3.3 Aggregation Function
- [ ] Add `aggregate_file_ai_signals(pr_id) -> bool` to ai_signals.py
- [ ] Query PRFile.filename for PR
- [ ] Call pattern detector
- [ ] Return result

### 3.4 Unit Tests (TDD)
- [ ] `test_detect_cursor_files`
- [ ] `test_detect_claude_files`
- [ ] `test_detect_aider_files`
- [ ] `test_detect_multiple_patterns`
- [ ] `test_no_patterns_returns_empty`

### 3.5 Backfill Integration
- [ ] Extend backfill command for files
- [ ] Test on sample data

### 3.6 Sync Pipeline Integration
- [ ] Update file processing in sync
- [ ] Set `has_ai_files` after file sync

### 3.7 Verification
- [ ] Run backfill
- [ ] Verify 215+ PRs flagged
- [ ] Spot-check samples

---

## Phase 4: Enhanced LLM Context

**Goal**: Improve LLM detection with more context

### 4.1 Update User Prompt Template
- [ ] Edit `apps/metrics/prompts/templates/user.jinja2`
- [ ] Increase commit messages from 5 → 20
- [ ] Include commit Co-Authors section
- [ ] Include all review bodies (not just 3)
- [ ] Add AI file patterns section

### 4.2 Update Prompt Renderer
- [ ] Update `render_user_prompt()` for new fields
- [ ] Add `commit_co_authors` parameter
- [ ] Add `ai_file_patterns` parameter

### 4.3 Bump Prompt Version
- [ ] Update `PROMPT_VERSION` to "7.0.0" in llm_prompts.py
- [ ] Document changes in prompt changelog

### 4.4 Update Golden Tests
- [ ] Add test cases for commit Co-Author detection
- [ ] Add test cases for file pattern mentions
- [ ] Run promptfoo evaluation

### 4.5 Regenerate Promptfoo Config
- [ ] Run `make export-prompts`
- [ ] Run evaluation with new prompt
- [ ] Compare accuracy vs v6.8.0

### 4.6 Re-process Sample
- [ ] Run LLM batch on 500 PRs with new prompt
- [ ] Compare detection rates
- [ ] Document improvements

---

## Phase 5: Composite Scoring & Dashboard

**Goal**: Calculate weighted AI confidence and display in UI

### 5.1 Database Migration
- [ ] Create migration `0023_add_ai_confidence_score.py`
- [ ] Add `ai_confidence_score` DecimalField(4,3)
- [ ] Add `ai_signals` JSONField
- [ ] Run migration

### 5.2 Scoring Algorithm
- [ ] Add `calculate_ai_confidence(pr) -> tuple[float, dict]` to ai_signals.py
- [ ] Implement weighted scoring
- [ ] Configure weights in settings.py
- [ ] Return score and signal breakdown

### 5.3 Unit Tests (TDD)
- [ ] `test_score_no_signals_returns_zero`
- [ ] `test_score_llm_only`
- [ ] `test_score_commits_only`
- [ ] `test_score_all_signals`
- [ ] `test_score_breakdown_structure`

### 5.4 Backfill Integration
- [ ] Add scoring to backfill command
- [ ] Calculate for all PRs
- [ ] Store score and signals

### 5.5 Dashboard: PR List
- [ ] Add confidence indicator column
- [ ] Color coding: high (green), medium (yellow), low (gray)
- [ ] Tooltip shows signal breakdown

### 5.6 Dashboard: PR Detail
- [ ] Add "AI Detection" section
- [ ] Show each signal source
- [ ] Visual breakdown (bar chart or chips)
- [ ] Link to relevant data (commits, reviews)

### 5.7 Dashboard: Analytics
- [ ] Add filter by detection source
- [ ] Show signal distribution chart
- [ ] Compare explicit vs implicit disclosure

### 5.8 E2E Tests
- [ ] Test signal breakdown UI
- [ ] Test filtering by source
- [ ] Test confidence display

---

## Quick Commands

```bash
# Run Phase 1 tests
pytest apps/metrics/tests/test_ai_signals.py -v -k commit

# Run backfill dry run
python manage.py backfill_ai_signals --dry-run --limit 100

# Check results
python manage.py shell -c "
from apps.metrics.models import PullRequest
print(f'has_ai_commits: {PullRequest.objects.filter(has_ai_commits=True).count()}')
print(f'has_ai_review: {PullRequest.objects.filter(has_ai_review=True).count()}')
print(f'has_ai_files: {PullRequest.objects.filter(has_ai_files=True).count()}')
"

# Export prompts after Phase 4
make export-prompts

# Run full test suite
make test
```

---

## Definition of Done

### Per Phase
- [ ] All unit tests passing
- [ ] Backfill completed on full database
- [ ] Sync pipeline updated
- [ ] Manual verification on 10 samples
- [ ] Documentation updated

### Overall
- [ ] AI detection rate increased by 15%+
- [ ] False positive rate < 2%
- [ ] Dashboard shows signal breakdown
- [ ] CTO can see why each PR was flagged
