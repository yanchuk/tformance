# AI Detection via PR Description Analysis - Tasks

**Last Updated: 2025-12-24 20:00 UTC**

## Immediate Next Steps (On Restart)

1. ✅ **Verify tests pass**: 96 tests passing
2. ✅ **Commit Phase 1 changes**: Committed as `8723f22`
3. ✅ **Plan Groq integration**: Architecture doc updated with Llama 3.3 70B + full payload
4. **Add groq package**: `uv add groq`
5. **Create Groq service**: `apps/integrations/services/groq_ai_detector.py`
6. **Create backfill command**: With `--use-llm` option

## Known Issue (Low Priority)

**Gemini Pattern False Positive** in AI product repos:
- `vercel/ai` - "Gemini 3 exclusive feature" matched as AI authoring
- Workaround: LLM handles this correctly, regex is just first pass
- Fix if needed: Change `\bgemini\b` to `\bused\s+gemini\b`

## Phase 1: Expand Regex Pattern Coverage [Effort: S]

### 1.1 Add Cursor Detection Patterns ✅
- [x] Add pattern: `cursor\s*\(` (Cursor with parenthesis)
- [x] Add pattern: `cursor\s+ide` (Cursor IDE)
- [x] Add pattern: `cursor\s+auto[- ]?mode` (Cursor auto mode)
- [x] Add pattern: `used\s+cursor` (used Cursor)
- [x] Add pattern: `using\s+cursor` (using Cursor)
- [x] Add pattern: `\bcursor\b.*used\s+for` (Cursor used for)
- [x] Write unit tests for all Cursor patterns (10+ cases)
- [x] Add negative test: "move cursor" should NOT match
- [x] Add negative test: "database cursor" should NOT match

### 1.2 Add Claude Model Name Patterns ✅
- [x] Add pattern: `claude\s+(?:opus|sonnet|haiku)` (Claude Opus/Sonnet/Haiku)
- [x] Add pattern: `claude\s+\d+(?:\.\d+)?\s+(?:opus|sonnet|haiku)` (Claude 4.5 Sonnet)
- [x] Add pattern: `sonnet\s+\d+(?:\.\d+)?` (Sonnet 4.5)
- [x] Add pattern: `opus\s+\d+(?:\.\d+)?` (Opus 4.5)
- [x] Write unit tests for model name patterns (5+ cases)
- [x] Verify: "Claude API integration" should NOT match

### 1.3 Add Indirect AI Usage Patterns ✅
- [x] Add pattern: `\bai\s+was\s+used` (AI was used)
- [x] Add pattern: `used\s+ai\s+(?:for|to)` (used AI for/to)
- [x] Add pattern: `\bwith\s+ai\s+assistance` (with AI assistance)
- [x] Add pattern: `ai\s+helped?\s+(?:with|to)` (AI helped with)
- [x] Write unit tests for indirect usage (5+ cases)

### 1.4 Increment Pattern Version ✅
- [x] Update PATTERNS_VERSION in ai_patterns.py to "1.4.0"

**Acceptance Criteria Phase 1**: ✅
- [x] All new patterns added to AI_SIGNATURE_PATTERNS in ai_patterns.py
- [x] 20+ new unit tests passing (96 total)
- [x] No regressions in existing tests
- [x] PRs #1626, #1627, #1635, #1655, #1656 would be detected

---

## Phase 2: Groq LLM Integration [Effort: M] ⟵ CURRENT

**Decision**: Skip complex section parser - Groq LLM handles all cases at $0.08/1000 PRs

### 2.1 Setup Groq Integration
- [ ] Add groq package: `uv add groq`
- [ ] Add `GROQ_API_KEY` to environment/secrets
- [ ] Create migration for `llm_detection_at` field on PullRequest

### 2.2 Implement Groq Service (TDD)
- [ ] Create `apps/integrations/services/groq_ai_detector.py`
- [ ] Implement `detect_ai_with_groq(pr_body: str) -> AIDetectionResult`
- [ ] Implement `create_batch_file(prs, output_path)` for batch API
- [ ] Implement `submit_batch_job(file_path)` → batch_id
- [ ] Implement `get_batch_results(batch_id)` → results dict
- [ ] Write unit tests (mock Groq responses)
- [ ] Write integration test with real API call (1 PR)

### 2.3 Create Backfill Management Command ✅
- [x] Create `apps/metrics/management/commands/backfill_ai_detection.py`
- [x] Add `--team` filter option
- [x] Add `--dry-run` option (preview changes)
- [x] Add `--use-llm` option (use Groq vs regex-only)
- [x] Add `--limit` option (max PRs to process)
- [x] Show before/after comparison for each changed PR
- [x] Add `--only-undetected` option
- [x] Add `--verbose` option
- [x] Categorize changes: new detections, removed, tool-only

### 2.4 Run Backfill Validation
- [ ] Run `--dry-run --limit 50` on Gumroad team
- [ ] Manually verify 20 detections
- [ ] Compare regex vs LLM results
- [ ] Run actual backfill if results look good

### 2.5 Experiment Framework + PostHog Logging
- [x] Add dependencies: `uv add groq litellm posthog`
- [x] Create experiment runner: `apps/metrics/experiments/runner.py`
- [ ] Create analysis utils: `apps/metrics/experiments/analysis.py`
- [ ] Integrate PostHog LLM analytics for automatic logging
- [x] Create management command: `run_ai_detection_experiment`

### 2.5.1 Promptfoo Integration (Fast Prompt Iteration)
- [x] Create `experiments/promptfoo.yaml` with test cases
- [x] Update runbook with Promptfoo workflow
- [x] Add 18 test cases covering positive/negative/edge cases
- [ ] Run initial evaluation: `npx promptfoo eval` (requires GROQ_API_KEY)

### 2.6 Runbooks (Documentation for Context-Free Operation)
- [x] Create `RUNBOOK-EXPERIMENTS.md` - How to run experiments
- [x] Create `RUNBOOK-PROMPTS.md` - How to modify prompts
- [x] Create `RUNBOOK-REPOS.md` - How to manage target repos
- [x] Create `experiments/default.yaml` - Default config
- [x] Create `experiments/prompts/v1.md` - Initial prompt

### 2.7 Add Celery Task for Nightly Batch
- [ ] Create `queue_prs_for_llm_detection` task
- [ ] Create `poll_llm_detection_batch` task
- [ ] Add to Celery beat schedule (nightly)
- [ ] Test full batch flow

**Acceptance Criteria Phase 2**:
- [ ] Groq service working with tests
- [ ] Experiment framework operational
- [ ] All LLM calls logged to PostHog
- [ ] Runbooks enable context-free operation
- [ ] Detection rate on Gumroad: 24% → 70%+
- [ ] Cost confirmed at ~$0.08/1000 PRs

---

## Phase 3: AI Usage Categorization [Effort: L]

### 3.1 Define Usage Categories
- [ ] Document categories: authored, assisted, reviewed, brainstorm, format
- [ ] Add category patterns to ai_patterns.py
- [ ] Create `categorize_ai_usage(text: str) -> str`

### 3.2 Extend Data Model
- [ ] Add `ai_usage_details: JSONField` to PullRequest model
- [ ] Create migration
- [ ] Update factories for testing
- [ ] Backward compatible with existing ai_tools_detected

### 3.3 Update Sync Logic
- [ ] Modify _detect_pr_ai_involvement to return usage details
- [ ] Store usage details in new field
- [ ] Update existing detection calls

### 3.4 Dashboard Enhancement
- [ ] Show usage category in PR list tooltip
- [ ] Add filter by usage type
- [ ] Create AI usage breakdown chart

**Acceptance Criteria Phase 3**:
- [ ] PRs categorized by AI usage type
- [ ] Dashboard shows usage breakdown
- [ ] "Copilot used to brainstorm" → brainstorm category
- [ ] "Cursor for implementation" → assisted category

---

## Phase 4: Backfill Existing PRs [Effort: M]

### 4.1 Create Management Command
- [ ] Create `backfill_ai_detection` command in apps/metrics/management/commands/
- [ ] Add `--team` filter option
- [ ] Add `--dry-run` option
- [ ] Add `--verbose` option for detailed output
- [ ] Show before/after comparison for each PR

### 4.2 Implement Backfill Logic
- [ ] Query PRs with body content
- [ ] Apply new detection logic
- [ ] Use bulk_update for performance
- [ ] Track changes for reporting

### 4.3 Generate Validation Report
- [ ] List PRs newly detected as AI-assisted
- [ ] List PRs with changed tool detection
- [ ] Highlight potential false positives
- [ ] Export to CSV for manual review

### 4.4 Run Backfill on Gumroad Data
- [ ] Run in dry-run mode first
- [ ] Review changes manually
- [ ] Run actual backfill
- [ ] Verify detection rate improved

**Acceptance Criteria Phase 4**:
- [ ] Command works with --dry-run
- [ ] Gumroad detection rate: 9% → 70%+
- [ ] No false positives on manual review
- [ ] Backfill completes in <1 minute

---

## Phase 5: LLM-Based Detection [Effort: XL]

### 5.1 Design LLM Integration
- [ ] Design prompt template for AI disclosure parsing
- [ ] Define response schema (tool, usage, confidence)
- [ ] Plan cost optimization (batching, caching)

### 5.2 Create LLM Service
- [ ] Create `ai_disclosure_llm_parser.py` service
- [ ] Implement Claude API call with structured output
- [ ] Add caching layer (Redis)
- [ ] Add rate limiting

### 5.3 Async Processing
- [ ] Create Celery task for LLM detection
- [ ] Queue PRs with ambiguous detection
- [ ] Update PR when LLM result returns

### 5.4 Batch Processing Command
- [ ] Create `llm_detect_ai` management command
- [ ] Process historical PRs in batches
- [ ] Cost tracking and limits

### 5.5 Integration
- [ ] Trigger LLM for new PRs (when regex ambiguous)
- [ ] Dashboard shows LLM confidence score
- [ ] A/B comparison: regex vs LLM accuracy

**Acceptance Criteria Phase 5**:
- [ ] LLM correctly parses complex disclosures
- [ ] Detection rate: 70% → 90%+
- [ ] False positive rate <2%
- [ ] API costs monitored and within budget

---

## Validation Checklist

### Test with Real Gumroad PRs

| PR # | Expected Detection | Phase 1 | Phase 2 | Phase 4 |
|------|-------------------|---------|---------|---------|
| 1635 | cursor, claude | [ ] | [ ] | [ ] |
| 1709 | cursor | [ ] | [ ] | [ ] |
| 1626 | cursor, claude | [ ] | [ ] | [ ] |
| 1627 | cursor | [ ] | [ ] | [ ] |
| 1684 | ai_generic | [ ] | [ ] | [ ] |
| 1673 | claude | [ ] | [ ] | [ ] |
| 1656 | cursor | [ ] | [ ] | [ ] |
| 1711 | (none - negative) | [ ] | [ ] | [ ] |
| 1419 | (none - "None") | [ ] | [ ] | [ ] |
| 1500 | copilot | [ ] | [ ] | [ ] |

### False Positive Prevention

| Text | Should NOT Match | Verified |
|------|-----------------|----------|
| "Devin added unnecessary tags" | [ ] |
| "Integrate Claude API" | [ ] |
| "move cursor to button" | [ ] |
| "database cursor" | [ ] |
| "AI Disclosure: None" | [ ] |

---

## Progress Tracking

- [x] **Phase 1 Complete** - Enhanced regex patterns (2025-12-24) - Commit `8723f22`
- [ ] **Phase 2 In Progress** - Groq LLM integration
- [ ] **Phase 3 Pending** - Usage categorization + dashboard
- [ ] **Phase 4 Pending** - Production deployment

**Current Status**: Phase 2 starting - Groq integration

## Revised Plan Summary

| Phase | Description | Effort | Detection Rate |
|-------|-------------|--------|----------------|
| 1 ✅ | Regex patterns | S | 24.4% |
| 2 ⟵ | Groq LLM (Llama 3.3 70B) | M | 70-90% |
| 3 | Usage categorization | S | +analytics |
| 4 | Dashboard + production | M | shipped |

**Key Decision**: Skip complex section parser - Groq handles everything at $0.08/1000 PRs

## Phase 1 Results (2025-12-24)

### Patterns Added (Version 1.4.0)
- **Cursor patterns**: 12 new patterns for Cursor IDE usage
  - `cursor (`, `cursor ide`, `cursor auto mode`, `used cursor`, `using cursor`
  - `with cursor`, `cursor in auto`, `cursor used for`, `ide: cursor`
  - `cursor for`, `cursor autocompletions`, `written by cursor`
- **Claude patterns**: 9 new patterns for Claude models
  - `claude opus/sonnet/haiku`, `claude 4.5 sonnet`, `claude-code`
  - `claude code` (without hyphen), `with claude`, `and claude`
  - `claude-4`, `claude 4` (version numbers)
- **Indirect AI patterns**: 4 patterns for "AI was used", "used AI for", etc.
- **Gemini patterns**: Added Google Gemini detection
- **Copilot patterns**: Added "Copilot used" detection
- **Negative disclosure handling**: Strip "No AI was used" to prevent false positives

### Detection Improvement (Gumroad Team)
```
Total PRs with body: 221
Currently in DB:      14 detected (6.3%)
After backfill:       54 detected (24.4%)
Improvement: +40 PRs (3.9x increase)

AI Disclosure Section Analysis:
- 150 PRs have "AI Disclosure" section
- 46 correctly detected as AI-assisted
- 94 correctly NOT detected (negative disclosures)
- 10 ambiguous (need Phase 5 LLM for context)
```

### Tests Added
- 96 total tests in test_ai_detector.py (all passing)
- +16 new tests since initial Phase 1
- 8 test classes covering all pattern categories

### Remaining Ambiguous Cases (for Phase 5 LLM)
These disclosures say "Used for X" without specifying the tool:
- "Used for brainstorming the cause of the issue"
- "Used to identify all usages"
- "Used mainly for test coverage"

These require LLM to infer from context that an AI tool was used.
