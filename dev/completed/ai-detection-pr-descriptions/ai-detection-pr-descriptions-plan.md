# AI Detection via PR Description Analysis - Implementation Plan

**Last Updated: 2025-12-24**

## Executive Summary

Enhance AI-assisted PR detection by analyzing PR descriptions/bodies. Currently, 150 out of 224 Gumroad PRs contain structured "AI Disclosure" sections, but only 14 are correctly marked as AI-assisted. This represents a significant opportunity to improve detection accuracy from ~9% to potentially 80%+ through pattern matching and later LLM-based analysis.

## Current State Analysis

### What We Have
1. **PR Body Storage**: `body` field in `metrics_pullrequest` table stores PR descriptions
2. **Existing Detection**: `_detect_pr_ai_involvement()` in `github_graphql_sync.py` already calls `detect_ai_in_text()` on title + body
3. **Pattern Registry**: `ai_patterns.py` defines regex patterns for AI detection
4. **Rich Data**: Gumroad team has 221/224 PRs with body content, 150 with AI Disclosure sections

### Gap Analysis: Patterns Being Missed

| PR Example | AI Disclosure Content | Detected? | Issue |
|------------|----------------------|-----------|-------|
| #1635 | "Cursor (Claude 4.5 Sonnet) used for questions" | No | Cursor + Claude model names not matched |
| #1684 | "AI was used to extract related code" | No | "AI was used" pattern missing |
| #1709 | "Use Cursor(auto-mode) for initial setup" | No | "Use Cursor" pattern missing |
| #1656 | "IDE: Cursor, Model: Auto" | No | Structured format not parsed |
| #1626 | "Cursor (Claude 4.5 Sonnet) used for codebase queries" | No | Same as #1635 |
| #1627 | "Used cursor auto mode for doing similar pattern changes" | No | Lowercase "cursor" in context |
| #1673 | "AI prompt was generated with Claude Sonnet" | No | Indirect usage pattern |

### Negative Cases (Should NOT Match)
- "Devin added unnecessary tags" - mentions AI agent but not as author tool
- "Integrate Claude API" - about Claude as a product, not authoring tool
- "AI Disclosure: None" / "No AI was used" - explicit negative disclosures

## Proposed Future State

### Phase 1: Enhanced Keyword Detection (This Plan)
- Parse "AI Disclosure" sections specifically
- Add missing patterns for Cursor, Claude models, indirect usage
- Handle negative disclosure patterns
- Detect structured disclosure formats

### Phase 2: LLM-Based Analysis (Future)
- Use Claude API to parse complex disclosures
- Extract usage context (what AI was used for)
- Confidence scoring for ambiguous cases
- Learn from new disclosure patterns automatically

## Implementation Phases

---

## Phase 1: Expand Regex Pattern Coverage

**Goal**: Catch the obviously missed patterns without introducing false positives.

### 1.1 Add Cursor Detection Patterns

```python
# Cursor IDE patterns
(r"cursor\s*\(", "cursor"),  # "Cursor (" or "Cursor("
(r"cursor\s+ide", "cursor"),
(r"cursor\s+auto[- ]?mode", "cursor"),
(r"used\s+cursor", "cursor"),
(r"using\s+cursor", "cursor"),
(r"\bcursor\b.*used\s+for", "cursor"),
```

**Acceptance Criteria**:
- PRs #1626, #1627, #1635, #1655, #1656, #1668, #1696, #1709 correctly detected
- "cursor" alone (e.g., "move cursor to") NOT matched

### 1.2 Add Claude Model Name Patterns

```python
# Claude model names
(r"claude\s+(?:opus|sonnet|haiku)", "claude"),
(r"claude\s+\d+(?:\.\d+)?\s+(?:opus|sonnet|haiku)", "claude"),
(r"sonnet\s+\d+(?:\.\d+)?", "claude"),  # "Sonnet 4.5"
```

**Acceptance Criteria**:
- "Claude 4.5 Sonnet", "Claude (Sonnet 4.5)", "Sonnet 4.5" all detected
- Generic "sonnet" music term NOT matched (require digits)

### 1.3 Add Indirect AI Usage Patterns

```python
# Indirect usage indicators
(r"\bai\s+was\s+used", "ai_generic"),
(r"used\s+ai\s+(?:for|to)", "ai_generic"),
(r"\bwith\s+ai\s+assistance", "ai_generic"),
(r"ai\s+helped?\s+(?:with|to)", "ai_generic"),
```

**Effort**: Small (S)
**Dependencies**: None

---

## Phase 2: AI Disclosure Section Parser

**Goal**: Parse structured "AI Disclosure" sections common in Gumroad PRs.

### 2.1 Extract AI Disclosure Section

Create a new function to isolate the AI Disclosure section from PR body:

```python
def extract_ai_disclosure_section(body: str) -> str | None:
    """Extract AI Disclosure section from PR body if present."""
    # Match variations: "AI Disclosure", "### AI Disclosure", "## AI Disclosure:"
    pattern = r"(?:#*\s*)?AI\s+Disclosure[:\s]*\n?(.*?)(?=\n#|\n---|\Z)"
    match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None
```

### 2.2 Detect Negative Disclosures

Patterns that indicate NO AI was used:

```python
NEGATIVE_DISCLOSURE_PATTERNS = [
    r"no\s+ai\s+(?:was\s+)?used",
    r"none\.?\s*(?:all\s+code\s+written\s+by\s+me)?",
    r"no\s+ai\s+(?:was\s+)?used\s+for\s+any\s+part",
    r"not?\s+ai\s+used",
]
```

**Logic**: If AI Disclosure section exists AND matches negative pattern → skip further analysis of that section.

### 2.3 Parse Structured Disclosure Formats

Some PRs use structured formats:

```markdown
## AI Disclosure
- IDE: Cursor
- Model: Auto
- Used for: Hints and advice
```

Parse these with field extraction:
- `IDE:`, `Editor:` → extract tool name
- `Model:` → extract AI model
- `Used for:`, `Cursor used for:` → extract usage context (for future analytics)

**Effort**: Medium (M)
**Dependencies**: Phase 1 patterns

---

## Phase 3: Differentiate AI Types

**Goal**: Distinguish between types of AI involvement for better analytics.

### 3.1 Categorize AI Usage Types

| Category | Description | Example Patterns |
|----------|-------------|------------------|
| `ai_authored` | AI wrote the code | "Devin authored", bot authors |
| `ai_assisted` | AI helped write code | "Used Cursor for implementation" |
| `ai_reviewed` | AI reviewed the code | "CodeRabbit reviewed" |
| `ai_brainstorm` | AI for planning only | "Copilot used to brainstorm" |
| `ai_format` | AI for formatting only | "Copilot used to format PR" |

### 3.2 Update ai_tools_detected Schema

Currently stores `list[str]` of tool names. Extend to capture usage type:

```python
# Current: ["cursor", "claude"]
# Proposed: [{"tool": "cursor", "usage": "assisted"}, {"tool": "claude", "usage": "brainstorm"}]
```

**Migration**: Additive field `ai_usage_details: JSONField` alongside existing `ai_tools_detected`.

**Effort**: Large (L)
**Dependencies**: Phase 1 & 2

---

## Phase 4: Backfill Existing PRs

**Goal**: Apply improved detection to historical PRs.

### 4.1 Create Backfill Management Command

```python
# python manage.py backfill_ai_detection --team gumroad-demo --dry-run
```

Features:
- Filter by team
- Dry-run mode to preview changes
- Show before/after comparison
- Track patterns version for selective reprocessing

### 4.2 Validation Report

Generate report showing:
- PRs newly detected as AI-assisted
- PRs with changed tool detection
- Potential false positives (for manual review)

**Effort**: Medium (M)
**Dependencies**: Phase 1-3 complete

---

## Phase 5: LLM-Based Detection (Future Enhancement)

**Goal**: Use Claude API to parse complex disclosures and provide nuanced detection.

### 5.1 Design LLM Prompt

```
Given this PR description, identify:
1. Was AI used? (yes/no/unclear)
2. What AI tools were used? (list)
3. What was AI used for? (code writing, brainstorming, formatting, review, other)
4. Confidence level (high/medium/low)

Important:
- "Integrate Claude API" = using Claude as a product, NOT AI authoring
- "Devin added bugs" in context of fixing = referencing past PR, not current authoring

PR Description:
{body}
```

### 5.2 When to Use LLM

Only call LLM API when:
1. AI Disclosure section exists BUT
2. Regex patterns return ambiguous/no result
3. OR when reprocessing historical data (batch mode)

Cost optimization: Cache results, batch process during off-peak.

### 5.3 Implementation Options

| Option | Pros | Cons |
|--------|------|------|
| Sync (during sync) | Real-time detection | Latency, API costs |
| Async (Celery task) | No sync delay | Eventual consistency |
| Batch (management cmd) | Cost efficient | Manual trigger needed |

**Recommended**: Batch processing initially, async for new PRs later.

**Effort**: XL
**Dependencies**: All previous phases, Claude API integration

---

## Risk Assessment

### Risk 1: False Positives
**Concern**: Pattern matches incorrectly (e.g., "cursor" as mouse cursor)
**Mitigation**:
- Require context words ("used", "IDE", "for")
- Run on existing data first, validate manually
- Add word boundary markers `\b`

### Risk 2: Performance Impact
**Concern**: Complex regex slows down sync
**Mitigation**:
- Pre-compile all patterns (already done)
- Extract AI Disclosure section first (smaller text)
- Benchmark before/after

### Risk 3: Evolving Disclosure Formats
**Concern**: New tools, new disclosure styles
**Mitigation**:
- Pattern versioning (already exists)
- LLM phase provides adaptive detection
- Quarterly pattern review process

### Risk 4: LLM API Costs (Phase 5)
**Concern**: Per-call costs add up
**Mitigation**:
- Batch processing during off-peak
- Only call when regex is ambiguous
- Cache results

---

## Success Metrics

| Metric | Current | Target (Phase 1-4) | Target (Phase 5) |
|--------|---------|-------------------|------------------|
| Detection rate (Gumroad) | 9% (14/150 AI disclosures) | 75%+ | 90%+ |
| False positive rate | Unknown | <5% | <2% |
| Tool identification accuracy | Partial | 80%+ | 95%+ |
| Processing time impact | N/A | <10% increase | <5% increase |

---

## Required Resources and Dependencies

### Technical Dependencies
- `apps/metrics/services/ai_patterns.py` - Pattern definitions
- `apps/metrics/services/ai_detector.py` - Detection functions
- `apps/integrations/services/github_graphql_sync.py` - Sync integration

### External Dependencies (Phase 5)
- Claude API key (already used for Copilot metrics)
- Rate limit budget for LLM calls

### Testing Requirements
- Unit tests for new patterns (50+ test cases)
- Integration tests for sync flow
- E2E test for backfill command
- Manual validation on Gumroad data

---

## Implementation Order

1. **Phase 1** (S): Add regex patterns → immediate wins
2. **Phase 2** (M): AI Disclosure parser → structured detection
3. **Phase 4** (M): Backfill command → apply to historical data
4. **Phase 3** (L): Usage categorization → richer analytics
5. **Phase 5** (XL): LLM detection → adaptive, high-accuracy detection

**MVP = Phase 1 + 2 + 4** (~3 development cycles)

**Full feature = All phases** (~6-8 development cycles)
