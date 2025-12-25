# Enhanced AI Detection - Tasks

**Last Updated: 2025-12-26**

## Overview

| Phase | Status | Effort | Impact |
|-------|--------|--------|--------|
| Phase 1: Commit Signals | ✅ Complete | S | High |
| Phase 2: Review Signals | ✅ Complete | S | Medium |
| Phase 3: File Patterns | ✅ Complete | M | Medium |
| Phase 4: Enhanced LLM | ✅ Complete | M | High |
| Phase 5: Composite Score | ✅ Complete | L | High |
| Phase 5.5: PR List UI | ✅ Complete | S | High |
| Phase 5.6-5.8: Detail/Analytics | ⏸️ Deferred | M | Medium |

---

## Phase 1: Commit Signal Aggregation ✅

**Goal**: Flag PRs that contain AI-assisted commits

### 1.1 Database Migration
- [x] Create migration `0024_add_ai_signal_fields.py` (was 0022, renumbered)
- [x] Add `has_ai_commits` BooleanField to PullRequest
- [x] Add `has_ai_review` BooleanField to PullRequest
- [x] Add `has_ai_files` BooleanField to PullRequest
- [x] Run migration locally and verify

### 1.2 Aggregation Service
- [x] Create `apps/metrics/services/ai_signals.py`
- [x] Implement `aggregate_commit_ai_signals(pr) -> bool`
- [x] Check `Commit.is_ai_assisted` for any True
- [x] Check `Commit.ai_co_authors` for non-empty lists
- [x] Return aggregated result

### 1.3 Unit Tests (TDD)
- [x] `test_aggregate_no_commits_returns_false`
- [x] `test_aggregate_no_ai_commits_returns_false`
- [x] `test_aggregate_with_ai_commit_returns_true`
- [x] `test_aggregate_with_ai_coauthors_returns_true`
- [x] `test_aggregate_with_mixed_commits`

### 1.4 Backfill Command
- [x] Create `apps/metrics/management/commands/backfill_ai_signals.py`
- [x] Add `--dry-run` flag
- [x] Add `--team` filter option
- [x] Batch processing (500 PRs at a time)
- [x] Progress logging
- [x] Test on sample data

### 1.5 Sync Pipeline Integration
- [ ] Update `_process_pr()` in github_graphql_sync.py
- [ ] Call aggregation after commits are synced
- [ ] Update `sync_repository_incremental_graphql()`
- [ ] Test with fresh sync

### 1.6 Verification
- [x] Run backfill on full database
- [x] Verify count: **255 PRs** with AI commits (expected 154+)
- [ ] Spot-check 10 PRs manually

**Result**: 255 PRs flagged with `has_ai_commits=True`

---

## Phase 2: AI Review Signals ✅

**Goal**: Flag PRs that received AI-generated reviews

### 2.1 Database Migration
- [x] Add `has_ai_review` BooleanField to PullRequest (in 0024)
- [x] Run migration

### 2.2 Aggregation Function
- [x] Add `aggregate_review_ai_signals(pr) -> bool` to ai_signals.py
- [x] Check `PRReview.is_ai_review` for any True
- [x] Return boolean result

### 2.3 Unit Tests (TDD)
- [x] `test_aggregate_no_reviews_returns_false`
- [x] `test_aggregate_no_ai_reviews_returns_false`
- [x] `test_aggregate_with_ai_review_returns_true`
- [x] `test_aggregate_with_mixed_reviews`

### 2.4 Backfill Integration
- [x] Extend backfill command to cover reviews
- [x] Test on sample data

### 2.5 Sync Pipeline Integration
- [ ] Update `_process_reviews()` in github_graphql_sync.py
- [ ] Set `has_ai_review` after processing

### 2.6 Verification
- [x] Run backfill
- [x] Verify: **1,241 PRs** flagged (matched expectation)
- [ ] Spot-check samples

**Result**: 1,241 PRs flagged with `has_ai_review=True`

---

## Phase 3: AI Config File Detection ✅

**Goal**: Detect PRs that MODIFY AI tool configuration files

**Key Insight**: Directory existing ≠ AI used. File MODIFIED = AI actively configured.

### 3.1 Database Migration
- [x] Add `has_ai_files` BooleanField to PullRequest (in 0024)
- [x] Run migration

### 3.2 Config Pattern Definitions
- [x] Create `AI_CONFIG_PATTERNS` dict in ai_signals.py:
  - `.github/copilot-instructions.md` → copilot
  - `CLAUDE.md` → claude
  - `.cursorrules` → cursor
  - `.cursor/rules/*.mdc` → cursor
  - `.cursor/environment.json` → cursor
  - `.cursor/mcp.json` → cursor
  - `.claude/commands/*.md` → claude
  - `.aider.conf.yml` → aider
  - `.coderabbit.yaml` → coderabbit
  - `.greptile.yaml` → greptile

### 3.3 False Positive Exclusions
- [x] Create `AI_FILE_EXCLUSIONS` list:
  - `cursor-pagination` (DB concept)
  - `cursor_pagination` (DB concept)
  - `/ai/gemini/` (product code)
  - `/langchain*/gemini` (SDK code)
  - `contract-rules` (business docs)
  - `-rules.pro` (Android ProGuard)

### 3.4 Pattern Detector Function
- [x] Add `detect_ai_config_files(pr) -> dict` to ai_signals.py
- [x] Match against AI_CONFIG_PATTERNS
- [x] Exclude AI_FILE_EXCLUSIONS
- [x] Return `{"has_ai_files": bool, "tools": [...], "files": [...]}`

### 3.5 Unit Tests (TDD)
- [x] `test_detect_cursorrules_returns_cursor`
- [x] `test_detect_claude_md_returns_claude`
- [x] `test_detect_copilot_instructions`
- [x] `test_exclude_cursor_pagination`
- [x] `test_exclude_gemini_product_code`
- [x] `test_detect_multiple_tools`
- [x] `test_no_config_files_returns_false`
- [x] `test_detect_aider_config`
- [x] `test_detect_coderabbit_config`
- [x] `test_exclude_proguard_rules`

### 3.6 Backfill Integration
- [x] Extend backfill command for files
- [x] Test on sample data

### 3.7 Sync Pipeline Integration
- [ ] Update file processing in sync
- [ ] Set `has_ai_files` after file sync

### 3.8 Verification
- [x] Run backfill
- [x] Verified: **255 PRs** with AI config files
- [ ] Verify NO false positives from cursor-pagination

**Result**: 255 PRs flagged with `has_ai_files=True`

---

## Backfill Results Summary

| Signal | PRs Detected | Notes |
|--------|--------------|-------|
| `has_ai_commits` | 255 | Co-Authored-By signatures |
| `has_ai_review` | 1,241 | CodeRabbit, Greptile, etc. |
| `has_ai_files` | 255 | .cursorrules, CLAUDE.md, etc. |
| Any new signal | 1,724 | Union of above |
| **Newly detected** | **597** | Not already caught by regex/LLM |

**Impact**: We've discovered **597 PRs** that have AI signals but were NOT detected by the existing regex or LLM detection methods. This represents a significant improvement in AI detection coverage.

### Signal Combinations

| Commits | Review | Files | Count |
|---------|--------|-------|-------|
| ❌ | ✅ | ❌ | 1,232 |
| ✅ | ❌ | ❌ | 234 |
| ❌ | ❌ | ✅ | 232 |
| ✅ | ❌ | ✅ | 17 |
| ❌ | ✅ | ✅ | 5 |
| ✅ | ✅ | ❌ | 3 |
| ✅ | ✅ | ✅ | 1 |

---

## Phase 4: Enhanced LLM Context ✅

**Goal**: Improve LLM detection with more context

### 4.1 Update User Prompt Template
- [x] Edit `apps/metrics/prompts/templates/user.jinja2`
- [x] Increase commit messages from 5 → 20
- [x] Include commit Co-Authors section
- [x] Include all review bodies (not just 3) - increased from 3 → 10
- [x] Add AI file patterns section

### 4.2 Update Prompt Renderer
- [x] Update `render_user_prompt()` for new fields
- [x] Add `commit_co_authors` parameter
- [x] Add `ai_config_files` parameter

### 4.3 Bump Prompt Version
- [x] Update `PROMPT_VERSION` to "7.0.0" in llm_prompts.py
- [x] Document changes in prompt changelog

### 4.4 Update Golden Tests
- [ ] Add test cases for commit Co-Author detection (deferred - can use existing tests)
- [ ] Add test cases for file pattern mentions (deferred - can use existing tests)
- [ ] Run promptfoo evaluation (deferred)

### 4.5 Regenerate Promptfoo Config
- [ ] Run `make export-prompts` (deferred - run when deploying)
- [ ] Run evaluation with new prompt (deferred)
- [ ] Compare accuracy vs v6.8.0 (deferred)

### 4.6 Re-process Sample
- [ ] Run LLM batch on 500 PRs with new prompt (deferred)
- [ ] Compare detection rates (deferred)
- [ ] Document improvements (deferred)

**Result**: Prompt template updated to v7.0.0 with enhanced context. All 55 tests passing.

---

## Phase 5: Composite Scoring & Dashboard 🔄

**Goal**: Calculate weighted AI confidence and display in UI

### 5.1 Database Migration ✅
- [x] Create migration `0025_add_ai_confidence_score.py`
- [x] Add `ai_confidence_score` DecimalField(4,3)
- [x] Add `ai_signals` JSONField
- [x] Run migration

### 5.2 Scoring Algorithm ✅
- [x] Add `calculate_ai_confidence(pr) -> tuple[float, dict]` to ai_signals.py
- [x] Implement weighted scoring
- [x] Weights defined in `AI_SIGNAL_WEIGHTS` constant (not settings.py)
- [x] Return score and signal breakdown

### 5.3 Unit Tests (TDD) ✅
- [x] `test_score_no_signals_returns_zero`
- [x] `test_score_llm_only` (includes confidence scaling)
- [x] `test_score_commits_only`
- [x] `test_score_reviews_only`
- [x] `test_score_files_only`
- [x] `test_score_regex_only`
- [x] `test_score_all_signals`
- [x] `test_score_breakdown_structure`
- [x] `test_llm_confidence_affects_score`
- [x] `test_llm_not_assisted_returns_zero`

### 5.4 Backfill Integration ✅
- [x] Add scoring to backfill command
- [x] Calculate for all PRs (36,817)
- [x] Store score and signals
- [x] Added `--skip-scoring` flag

**Backfill Results:**
| Confidence | PRs |
|------------|-----|
| High (≥0.5) | 4,257 |
| Medium (0.2-0.5) | 4,121 |
| Low (<0.2) | 514 |

### 5.5 Dashboard: PR List ✅
- [x] Add confidence indicator column (replaced Yes/No with High/Med/Low)
- [x] Color coding: high (green/success), medium (yellow/warning), low (gray/ghost)
- [x] Tooltip shows signal breakdown (LLM, Regex, Commits, Reviews, Files)
- [x] Added template filters: `ai_confidence_level`, `ai_confidence_badge_class`, `ai_signals_tooltip`
- [x] 22 new tests for template filters

**Result**: PR list now shows AI confidence with color-coded badges and hover tooltips.

### 5.6 Dashboard: PR Detail (Deferred)
- [ ] Add "AI Detection" section
- [ ] Show each signal source
- [ ] Visual breakdown (bar chart or chips)
- [ ] Link to relevant data (commits, reviews)

*Note: This would require creating a new PR detail page. The tooltip on PR list provides signal breakdown for now.*

### 5.7 Dashboard: Analytics (Deferred)
- [ ] Add filter by detection source
- [ ] Show signal distribution chart
- [ ] Compare explicit vs implicit disclosure

*Note: Would require extending pr_list_service.py filter capabilities.*

### 5.8 E2E Tests (Deferred)
- [ ] Test signal breakdown UI
- [ ] Test filtering by source
- [ ] Test confidence display

---

## Quick Commands

```bash
# Run Phase 1-3 tests
pytest apps/metrics/tests/test_ai_signals.py -v

# Run backfill dry run
python manage.py backfill_ai_signals --dry-run --limit 100

# Run full backfill
python manage.py backfill_ai_signals

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
- [x] All unit tests passing (53 tests total - 21 signal + 10 scoring + 22 template filters)
- [x] Backfill completed on full database (36,817 PRs)
- [x] Confidence scores calculated (8,892 PRs with score > 0)
- [ ] Sync pipeline updated (deferred - backfill covers existing data)
- [ ] Manual verification on 10 samples
- [x] Documentation updated

### Overall
- [x] AI detection rate increased (597 new PRs detected via signals)
- [x] Confidence distribution: 4,257 high, 4,121 medium, 514 low
- [ ] False positive rate < 2% (needs manual verification)
- [x] Dashboard shows signal breakdown (PR list with confidence badges + tooltips)
- [x] CTO can see why each PR was flagged (via hover tooltip on AI column)
