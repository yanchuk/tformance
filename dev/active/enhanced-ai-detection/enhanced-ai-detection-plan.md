# Enhanced AI Detection: Multi-Signal Intelligence

**Last Updated: 2025-12-25**
**Status: Planning**
**Priority: High - Core Product Differentiator**

---

## Executive Summary

### The Opportunity

Our platform currently detects AI assistance using only **PR description text** (title + body), leaving significant signal on the table. Analysis of 18,712 PRs reveals:

| Untapped Signal | Data Available | PRs Affected |
|-----------------|----------------|--------------|
| AI commits in PRs | 525 commits detected | 154 PRs not flagged |
| AI reviewer activity | 2,556 AI reviews | 1,241 PRs |
| AI file patterns | `.cursor/`, `.claude/` | 215+ PRs |
| Full commit history | 156K commits | 99% unused |

**Business Impact**: By aggregating all signals, we can increase AI detection accuracy by 15-25%, providing CTOs with the most accurate picture of AI adoption in their organization.

### ICP Value Proposition

**For CTOs asking "Is AI actually helping my team?"**

| Current State | Enhanced State |
|---------------|----------------|
| Only sees PRs with explicit AI disclosure | Sees ALL AI usage, including undisclosed |
| Misses commits signed by AI | Catches Co-Authored-By signatures |
| Ignores AI code review tools | Shows CodeRabbit, Copilot reviews |
| No file-level AI signals | Detects `.cursor/`, `.claude/` configs |

**Key Insight for CTOs**: "Your team's actual AI adoption is likely 25-40% higher than what's explicitly disclosed in PRs."

---

## Current State Analysis

### Detection Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT DETECTION                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   PR Title + Body ──► Regex Patterns ──► is_ai_assisted     │
│         │                                                    │
│         └──────────► LLM Analysis ──► llm_summary.ai        │
│                                                              │
│   ⚠️ UNUSED DATA:                                           │
│   • 156K commit messages (only 5 sent to LLM)               │
│   • 525 commit Co-Author signatures (not aggregated)        │
│   • 2,556 AI reviews (not linked to PR)                     │
│   • 321K file paths (not checked for AI patterns)           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Detection Accuracy (Current)

| Metric | Regex v1.9.0 | LLM v6.8.0 |
|--------|--------------|------------|
| Detection Rate | 23.4% | 26.4% |
| Agreement | 96.6% | 96.6% |
| Known FPs | 10 | ~5 |
| Known FNs | Unknown | ~150 (from commit analysis) |

---

## Proposed Future State

### Multi-Signal Detection Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENHANCED DETECTION                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│   │  PR Body    │   │  Commits    │   │  Reviews    │          │
│   │  + Title    │   │  Messages   │   │  + Bots     │          │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘          │
│          │                 │                 │                  │
│          ▼                 ▼                 ▼                  │
│   ┌─────────────────────────────────────────────────┐          │
│   │           SIGNAL AGGREGATION ENGINE             │          │
│   │                                                 │          │
│   │  • Commit Co-Authors → PR.has_ai_commits        │          │
│   │  • AI Reviews → PR.has_ai_review                │          │
│   │  • File Patterns → PR.has_ai_files              │          │
│   │  • Regex Detection → PR.is_ai_assisted          │          │
│   │  • LLM Analysis → PR.llm_summary.ai             │          │
│   └──────────────────────┬──────────────────────────┘          │
│                          │                                      │
│                          ▼                                      │
│   ┌─────────────────────────────────────────────────┐          │
│   │          COMPOSITE AI SCORE                     │          │
│   │                                                 │          │
│   │  ai_confidence = weighted_sum(                  │          │
│   │    llm_detection * 0.40,      # Most accurate   │          │
│   │    commit_signals * 0.25,     # Hard evidence   │          │
│   │    regex_patterns * 0.20,     # Fast fallback   │          │
│   │    review_signals * 0.10,     # Supplementary   │          │
│   │    file_patterns * 0.05       # Weak signal     │          │
│   │  )                                              │          │
│   └─────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### New Model Fields

```python
# PullRequest model additions
class PullRequest(BaseTeamModel):
    # ... existing fields ...

    # NEW: Aggregated signals
    has_ai_commits = models.BooleanField(default=False)
    has_ai_review = models.BooleanField(default=False)
    has_ai_files = models.BooleanField(default=False)

    # NEW: Composite score
    ai_confidence_score = models.DecimalField(
        max_digits=4, decimal_places=3, null=True,
        help_text="Weighted AI detection confidence 0.000-1.000"
    )
    ai_signals = models.JSONField(
        default=dict,
        help_text="Breakdown of detection signals for transparency"
    )
```

---

## Implementation Phases

### Phase 1: Commit Signal Aggregation (Quick Win)
**Effort: Small | Impact: High | No API calls**

Aggregate existing `Commit.is_ai_assisted` and `Commit.ai_co_authors` to PR level.

**ICP Benefit**: "See which PRs contain AI-assisted commits, even when the PR description doesn't mention AI."

### Phase 2: AI Review Linking
**Effort: Small | Impact: Medium | No API calls**

Link `PRReview.is_ai_review` to parent PR for holistic view.

**ICP Benefit**: "Know which PRs were reviewed by AI tools like CodeRabbit, Copilot, or Greptile."

### Phase 3: AI Config File Detection
**Effort: Medium | Impact: Medium | No API calls**

Detect when PRs **modify** AI tool configuration files (not just exist in repo).

**Key Distinction**:
- `.cursor/` directory exists → Tool is **set up** (weak signal)
- PR modifies `.cursorrules` → Tool is **actively configured** (strong signal)

**Strong Signal Files** (from actual data):
| File | PRs | Tool |
|------|-----|------|
| `.github/copilot-instructions.md` | 46 | Copilot |
| `CLAUDE.md` | 36 | Claude Code |
| `.cursorrules` | 36 | Cursor |
| `.cursor/rules/*.mdc` | 15-8 | Cursor |
| `.cursor/mcp.json` | 7 | Cursor |
| `.claude/commands/*.md` | 7 | Claude Code |

**ICP Benefit**: "See which PRs actively configure AI tools - proof the team is investing in AI workflows."

### Phase 4: Enhanced LLM Context
**Effort: Medium | Impact: High | Uses existing LLM quota**

Send more commit messages and all review text to LLM for better analysis.

**ICP Benefit**: "More accurate AI detection with context from the full PR history."

### Phase 5: Composite Scoring & Dashboard
**Effort: Large | Impact: High**

Create weighted AI confidence score and display signals in dashboard.

**ICP Benefit**: "See exactly why a PR was flagged as AI-assisted with signal breakdown."

---

## Detailed Task Breakdown

### Phase 1: Commit Signal Aggregation

#### 1.1 Add `has_ai_commits` field to PullRequest
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] Migration adds `has_ai_commits` BooleanField
  - [ ] Field defaults to False
  - [ ] Index on (team, has_ai_commits) for queries

#### 1.2 Create aggregation function
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] `aggregate_commit_ai_signals(pr)` function
  - [ ] Returns True if any commit has `is_ai_assisted=True`
  - [ ] Returns True if any commit has non-empty `ai_co_authors`
  - [ ] Unit tests with 100% coverage

#### 1.3 Backfill existing PRs
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] Management command `backfill_pr_ai_commits`
  - [ ] Processes all 18K PRs efficiently (batch updates)
  - [ ] Logs progress and results
  - [ ] Dry-run mode available

#### 1.4 Add to sync pipeline
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] `sync_repository_history_graphql()` sets `has_ai_commits`
  - [ ] Incremental sync updates the field
  - [ ] Webhook handlers update on new commits

### Phase 2: AI Review Linking

#### 2.1 Add `has_ai_review` field to PullRequest
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] Migration adds `has_ai_review` BooleanField
  - [ ] Field defaults to False

#### 2.2 Create review aggregation function
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] `aggregate_review_ai_signals(pr)` function
  - [ ] Returns True if any PRReview has `is_ai_review=True`
  - [ ] Includes `ai_reviewer_type` in signals dict
  - [ ] Unit tests

#### 2.3 Backfill and integrate
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] Management command covers reviews
  - [ ] Sync pipeline updated
  - [ ] Webhook handlers updated

### Phase 3: File Pattern Detection

#### 3.1 Add `has_ai_files` field to PullRequest
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] Migration adds `has_ai_files` BooleanField

#### 3.2 Create AI file pattern detector
- **Effort**: M
- **Acceptance Criteria**:
  - [ ] `detect_ai_file_patterns(file_paths)` function
  - [ ] Patterns: `.cursor/`, `.claude/`, `aider.chat/`, `.copilot/`
  - [ ] Returns dict with matched patterns
  - [ ] Configurable pattern list (not hardcoded)

#### 3.3 Integrate with sync and backfill
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] Backfill command extended
  - [ ] Sync pipeline checks files on PR sync

### Phase 4: Enhanced LLM Context

#### 4.1 Expand commit message context
- **Effort**: M
- **Acceptance Criteria**:
  - [ ] Send up to 20 commit messages (was 5)
  - [ ] Include commit Co-Author info in context
  - [ ] Summarize if > 20 commits

#### 4.2 Expand review context
- **Effort**: M
- **Acceptance Criteria**:
  - [ ] Send all review bodies (was 3)
  - [ ] Include reviewer names
  - [ ] Flag known AI reviewers

#### 4.3 Update prompt template
- **Effort**: M
- **Acceptance Criteria**:
  - [ ] user.jinja2 updated with new sections
  - [ ] Bump PROMPT_VERSION to 7.0.0
  - [ ] Re-run promptfoo evaluation
  - [ ] Document expected improvements

### Phase 5: Composite Scoring & Dashboard

#### 5.1 Add composite score fields
- **Effort**: S
- **Acceptance Criteria**:
  - [ ] `ai_confidence_score` DecimalField (0.000-1.000)
  - [ ] `ai_signals` JSONField for breakdown

#### 5.2 Implement scoring algorithm
- **Effort**: M
- **Acceptance Criteria**:
  - [ ] Weighted scoring function
  - [ ] Configurable weights in settings
  - [ ] Returns score + signal breakdown
  - [ ] Unit tests for edge cases

#### 5.3 Dashboard signal breakdown UI
- **Effort**: L
- **Acceptance Criteria**:
  - [ ] PR detail shows signal breakdown
  - [ ] Visual indicator of confidence level
  - [ ] Tooltip explains each signal source
  - [ ] Filter by detection source

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Migration on large table | Low | Medium | Run during off-hours, batch updates |
| LLM context too large | Medium | Low | Truncate/summarize long content |
| Scoring weights wrong | Medium | Medium | A/B test with manual review sample |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Users confused by multiple signals | Low | Medium | Clear UI explanations |
| Over-detection (more FPs) | Medium | High | Conservative weights, confidence threshold |
| Under-detection expectations | Low | Low | Document methodology |

---

## Success Metrics

### Detection Accuracy
- **Target**: Increase AI detection rate from 26% to 32%+ (true positives)
- **Measure**: Sample 100 PRs, manual review

### False Positive Rate
- **Target**: Maintain <2% FP rate
- **Measure**: Weekly review of flagged PRs

### Signal Coverage
- **Target**: 90%+ of AI-assisted PRs detected by 2+ signals
- **Measure**: Query `ai_signals` for multi-signal confirmation

### User Understanding
- **Target**: 80% of users understand why a PR was flagged
- **Measure**: Survey/feedback on signal breakdown UI

---

## Resource Requirements

### Development
- **Backend**: 3-4 days (Phases 1-3)
- **LLM Integration**: 2 days (Phase 4)
- **Frontend/Dashboard**: 3 days (Phase 5)
- **Testing**: 2 days (throughout)

### Infrastructure
- No new services required
- LLM costs: ~$0.08/1000 PRs (existing)
- Database: 3 new fields per PR (~50KB/1000 PRs)

### Dependencies
- Existing commit sync working ✅
- Existing review sync working ✅
- File sync working ✅
- LLM batch processing working ✅

---

## How This Helps CTOs (ICP)

### 1. **Complete AI Adoption Picture**
> "I thought only 20% of our PRs used AI. Turns out it's 35% when you count commits and file patterns."

CTOs can see the full scope of AI tool adoption, not just explicit disclosures.

### 2. **Tool Attribution**
> "I can see that 60% of our AI usage is Claude, 30% is Copilot, and 10% is CodeRabbit reviews."

The `ai_signals` breakdown shows which tools are actually being used.

### 3. **Team Comparison**
> "Team A explicitly discloses AI usage. Team B doesn't, but their commits show AI co-authors. Both are ~40% AI."

Normalize comparison across teams with different disclosure habits.

### 4. **ROI Calculation**
> "We're paying for Cursor seats, but I can see it's actually being used based on .cursor/ files in PRs."

Validate tool adoption against license costs.

### 5. **Quality Correlation**
> "PRs with AI reviews from CodeRabbit have 15% fewer review rounds. Worth keeping."

Connect AI tool usage to delivery outcomes.

---

## Appendix: Detection Signal Details

### Commit Co-Author Patterns
```
Co-authored-by: Claude <noreply@anthropic.com>
Co-authored-by: Cursor <hello@cursor.sh>
Co-authored-by: GitHub Copilot <copilot@github.com>
Co-authored-by: aider <aider@aider.chat>
```

### AI Reviewer Patterns
```
coderabbitai[bot]
github-actions[bot] (with copilot context)
greptile[bot]
sourcery-ai[bot]
```

### AI File Patterns (MODIFIED in PR = Strong Signal)

**Strong Signals** - Developer actively configuring AI tools:
```
# Copilot
.github/copilot-instructions.md    # 46 PRs - Copilot customization

# Claude Code
CLAUDE.md                          # 36 PRs - Project rules for Claude
.claude/                           # Claude commands & config
.github/workflows/claude*.yml      # Claude automation

# Cursor IDE
.cursorrules                       # 36 PRs - Cursor project rules
.cursor/rules/*.mdc                # Custom Cursor rules
.cursor/environment.json           # Cursor environment
.cursor/mcp.json                   # Cursor MCP servers

# Other AI Tools
.aider.conf.yml                    # Aider configuration
.coderabbit.yaml                   # CodeRabbit config
.greptile.yaml                     # Greptile config
```

**False Positives to Exclude** (keyword matches, not AI config):
```
# Database pagination (not AI)
*cursor-pagination*
*cursor_pagination*

# Business/Android rules (not AI)
*contract-rules*
*consumer-rules.pro
*proguard-rules.pro

# AI product code (building AI features, not using AI to code)
*/ai/gemini/*
*/langchain*/gemini*
*_sdk/ai/*
```

**Detection Logic**:
1. Check if file is in "Strong Signals" list
2. Exclude if matches "False Positives" patterns
3. PR modified AI config file = `has_ai_files = True`
