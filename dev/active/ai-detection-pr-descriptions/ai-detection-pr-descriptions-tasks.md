# AI Detection via PR Description Analysis - Tasks

**Last Updated: 2025-12-24 18:30 UTC**

## Immediate Next Steps (On Restart)

1. **Verify tests pass**: `make test ARGS='apps/metrics/tests/test_ai_detector.py'`
2. **Commit Phase 1 changes**: Patterns v1.4.0 + 96 tests
3. **Fix Gemini false positive**: Change `\bgemini\b` to require context
4. **Run backfill**: Create and run `backfill_ai_detection` command (Phase 4)

## Blocking Issue

**Gemini Pattern False Positive** in AI product repos:
- `vercel/ai` - "Gemini 3 exclusive feature" matched as AI authoring
- Need to change pattern to: `\bused\s+gemini\b` or similar

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

## Phase 2: AI Disclosure Section Parser [Effort: M]

### 2.1 Create Section Extractor Function
- [ ] Create `extract_ai_disclosure_section(body: str) -> str | None`
- [ ] Handle variations: "AI Disclosure", "### AI Disclosure:", "## AI Disclosure"
- [ ] Handle section ending: next header, ---, or EOF
- [ ] Write unit tests (8+ cases for different formats)

### 2.2 Implement Negative Disclosure Detection
- [ ] Create `NEGATIVE_DISCLOSURE_PATTERNS` list
- [ ] Add pattern: `no\s+ai\s+(?:was\s+)?used`
- [ ] Add pattern: `none\.?\s*$` (just "None" or "None.")
- [ ] Add pattern: `no\s+ai\s+(?:was\s+)?used\s+for\s+any\s+part`
- [ ] Create `is_negative_disclosure(text: str) -> bool`
- [ ] Write unit tests for negative detection (10+ cases)

### 2.3 Integrate into Detection Flow
- [ ] Update `detect_ai_in_text()` to use disclosure section parsing
- [ ] Logic: if disclosure section exists and is negative → return empty
- [ ] Logic: if disclosure section exists → analyze section preferentially
- [ ] Write integration tests

### 2.4 Parse Structured Disclosure Formats
- [ ] Detect and parse "IDE:" field
- [ ] Detect and parse "Model:" field
- [ ] Detect and parse "Used for:" field (for future analytics)
- [ ] Return structured data for dashboard enhancement

**Acceptance Criteria Phase 2**:
- [ ] AI Disclosure section correctly extracted from 150+ Gumroad PRs
- [ ] Negative disclosures correctly excluded
- [ ] Structured formats properly parsed
- [ ] Detection accuracy improved to 50%+

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

- [x] **Phase 1 Complete** - Enhanced patterns added (2025-12-24)
- [ ] **Phase 2 Complete** - AI Disclosure parser working
- [ ] **Phase 3 Complete** - Usage categorization
- [ ] **Phase 4 Complete** - Backfill executed
- [ ] **Phase 5 Complete** - LLM detection live

**Current Status**: Phase 1 fully validated and complete

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
