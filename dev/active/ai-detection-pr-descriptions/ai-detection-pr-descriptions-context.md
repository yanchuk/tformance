# AI Detection via PR Description Analysis - Context

**Last Updated: 2025-12-24 22:00 UTC (Experiment Runner Complete)**

## Session Summary (2025-12-24 Evening)

### What Was Accomplished
1. **Groq Integration Decision**: Llama 3.3 70B at $0.08/1000 PRs (44x cheaper than Claude)
2. **Dependencies Added**: `groq`, `litellm`, `posthog` packages installed
3. **Promptfoo Setup**: Created YAML config with 18 test cases for prompt iteration
4. **Runbooks Created**: Context-free operation guides for experiments, prompts, repos
5. **Experiment Runner**: Full implementation with 21 tests
   - `ExperimentRunner` class for running LLM detection
   - `run_ai_detection_experiment` management command
   - Compares LLM vs regex, calculates metrics, exports results
6. **Tech Stack Finalized**:
   - Batch API → Groq SDK directly (50% cheaper)
   - Real-time API → LiteLLM (easy provider switching)
   - Prompt Testing → Promptfoo (fast iteration)
   - Analytics → PostHog LLM events

### Key Files Modified This Session
| File | Changes |
|------|---------|
| `pyproject.toml` | Added groq, litellm, posthog dependencies |
| `experiments/promptfoo.yaml` | NEW: 18 test cases (positive/negative/edge) |
| `experiments/prompts/v1.md` | Updated system prompt for JSON output |
| `experiments/default.yaml` | NEW: Default experiment config |
| `RUNBOOK-EXPERIMENTS.md` | Added Promptfoo workflow section |
| `llm-detection-architecture.md` | Updated for Groq (was Claude) |
| `apps/metrics/experiments/runner.py` | NEW: ExperimentRunner (500 lines) |
| `apps/metrics/experiments/tests/test_runner.py` | NEW: 21 tests |
| `apps/metrics/management/commands/run_ai_detection_experiment.py` | NEW: CLI |

### Next Step Required
**Add GROQ_API_KEY to .env:**
```bash
echo 'GROQ_API_KEY=your-key-here' >> .env
```
Get key from: https://console.groq.com/keys

Then test with:
```bash
cd dev/active/ai-detection-pr-descriptions/experiments
npx promptfoo eval
```

### No Migrations Needed
- No model changes in this session

## Previous Session Summary (2025-12-24 Morning)

### What Was Accomplished
1. **Phase 1 Regex Patterns**: Added 16 new patterns, version 1.4.0
2. **Validated Detection**: 54/221 PRs (24.4%) would be detected after backfill
3. **OSS Research**: Found 100 Claude Code PRs across 81 GitHub repos
4. **False Positive Discovery**: AI product repos (vercel/ai, langchain) match "Gemini" as product, not authoring

### Key Files From Morning Session
| File | Changes |
|------|---------|
| `apps/metrics/services/ai_patterns.py` | Added 6 new patterns (v1.3.0 → v1.4.0) |
| `apps/metrics/tests/test_ai_detector.py` | Added 8 new tests (88 → 96 total) |
| `apps/metrics/scripts/fetch_oss_prs.py` | NEW: OSS PR fetcher with tiered repos |
| `llm-detection-architecture.md` | NEW: Phase 5 LLM design document |

### New Patterns Added (Version 1.4.0)
```python
# Claude patterns
(r"\bclaude\s+code\b", "claude_code"),  # Without hyphen
(r"\bclaude[- ]?\d+(?:\.\d+)?\b", "claude"),  # claude-4, claude 4

# Cursor patterns
(r"\bcursor\s+for\b", "cursor"),  # cursor for understanding
(r"\bcursor\s+autocompletions?\b", "cursor"),  # cursor autocompletions
(r"\bwritten\s+by\s+cursor\b", "cursor"),  # written by Cursor
```

### No Migrations Needed
- No model changes in this session
- Backfill command needed but not yet created (Phase 4)

### Uncommitted Changes
Run `git status` to see current state. Key files to commit:
- `apps/metrics/services/ai_patterns.py`
- `apps/metrics/tests/test_ai_detector.py`
- `apps/metrics/scripts/fetch_oss_prs.py`
- `dev/active/ai-detection-pr-descriptions/*.md`

## Key Files

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `apps/metrics/services/ai_patterns.py` | Pattern definitions registry | 77-115 (AI_SIGNATURE_PATTERNS) |
| `apps/metrics/services/ai_detector.py` | Detection functions | 135-163 (detect_ai_in_text) |
| `apps/integrations/services/github_graphql_sync.py` | PR sync integration | 239-262 (_detect_pr_ai_involvement) |
| `apps/metrics/models/github.py` | PullRequest model | `body`, `is_ai_assisted`, `ai_tools_detected` fields |
| `apps/metrics/tests/test_ai_detector.py` | Existing AI detector tests | Full file |
| `apps/metrics/scripts/fetch_oss_prs.py` | OSS PR fetcher for training data | Full file |
| `dev/active/ai-detection-pr-descriptions/llm-detection-architecture.md` | Phase 5 LLM design | Full file |

## Database Schema

```sql
-- Key fields in metrics_pullrequest
body: TEXT                    -- PR description (already stored)
is_ai_assisted: BOOLEAN       -- Detection result
ai_tools_detected: JSONB      -- List of tools detected ["cursor", "claude"]
```

## Current Detection Flow

```
GitHub GraphQL API
       ↓
_process_pr() / _process_pr_incremental()
       ↓
_detect_pr_ai_involvement(author_login, title, body)
       ↓
detect_ai_author() + detect_ai_in_text()
       ↓
is_ai_assisted, ai_tools_detected stored on PR
```

## Pattern Analysis: Gumroad Data

### AI Disclosure Section Formats Found

**Type 1: Simple statement**
```
## AI Disclosure
No AI was used for any part of this contribution.
```

**Type 2: Tool mention**
```
## AI Disclosure
GitHub Copilot used to brainstorm
```

**Type 3: Model + Tool**
```
### AI Disclosure
Cursor (Claude 4.5 Sonnet) used for questions etc.
```

**Type 4: Structured list**
```
### AI Disclosure
- IDE: Cursor
- Model: Auto
- Used for: Hints and advice
```

**Type 5: Detailed explanation**
```
## AI Disclosure
Model: Claude(Sonnet 4.5) via Cursor IDE
Used for:
- Codebase exploration
- Writing test cases
- Addressing reviewer feedback
All AI-generated code was manually reviewed...
```

### Missed Pattern Examples (Actual PRs)

| PR # | Body Snippet | Why Missed |
|------|--------------|------------|
| 1635 | "Cursor (Claude 4.5 Sonnet) used for questions" | No pattern for "Cursor (" |
| 1709 | "Use Cursor(auto-mode) for the initial setup" | No pattern for "Use Cursor" |
| 1626 | "Cursor (Claude 4.5 Sonnet) used for codebase queries" | Same as 1635 |
| 1627 | "Used cursor auto mode" | Lowercase "cursor" in sentence |
| 1684 | "AI was used to extract related code" | No pattern for "AI was used" |
| 1673 | "AI prompt was generated with Claude Sonnet" | Model name without "Claude Code" |
| 1656 | "IDE: Cursor, Model: Auto" | Structured format not parsed |

### False Positive Risk Examples

| Text | Should Match? | Risk |
|------|--------------|------|
| "Devin added unnecessary tags" | NO | Mentioning past PR by AI agent |
| "Integrate Claude API" | NO | About product integration |
| "move cursor to the button" | NO | Mouse cursor, not IDE |
| "like a cursor in the database" | NO | Database cursor |

## Detection Statistics (Gumroad Team)

### Before Phase 1 (Version 1.1.0)
```
Total PRs with body: 221
Detected in DB: 14 (6.3%)
```

### After Phase 1 (Version 1.4.0)
```
Total PRs with body: 221
Currently in DB: 14 (6.3%)  # Needs backfill
Would be detected: 54 (24.4%)  # After backfill
Improvement: +40 PRs (3.9x increase)
```

### AI Disclosure Section Analysis
```
PRs with "AI Disclosure" section: 150
- Correctly detected as AI-assisted: 46
- Correctly NOT detected (negative): 94
- Ambiguous (need LLM): 10
```

## OSS Repository Analysis

### Search Results (2025-12-24)
```bash
# PRs with Claude Code signature across GitHub
gh search prs "Generated with Claude Code" --limit 100

# Results: 100 PRs from 81 unique repositories
Top repos:
  erimatnor/timescaledb: 5 PRs
  deeplearning4j/deeplearning4j: 4 PRs
  sailkit-dev/sailkit: 4 PRs
  mattermost/docs: 2 PRs
  mozilla/pdf.js: 1 PR
```

### False Positive Discovery
**AI Product Repos (vercel/ai, langchain) have high false positive risk:**
- "Gemini" pattern matches API product mentions, not AI authoring
- Need explicit signatures (Co-Authored-By, "Generated with") for these repos

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Store detection with PR | Keep current approach | Already storing ai_tools_detected on PR |
| Pattern versioning | Use PATTERNS_VERSION | Enables selective reprocessing |
| LLM detection | Phase 5 (future) | Start with improved regex first |
| Backfill approach | Management command | Gives control, dry-run capability |

## Testing Strategy

### Unit Test Cases Needed

1. **New Cursor patterns**: 10+ cases
2. **Claude model names**: 5+ cases
3. **Indirect usage**: 5+ cases
4. **Negative disclosures**: 10+ cases
5. **AI Disclosure section extraction**: 8+ cases
6. **False positive prevention**: 10+ cases

### Integration Tests

1. Test `_detect_pr_ai_involvement` with real PR body samples
2. Test sync flow correctly applies detection
3. Test backfill command updates existing PRs

### Validation Data

Use actual Gumroad PR bodies for testing:
- PRs 1626, 1627, 1635, 1655, 1656 → should detect Cursor
- PRs 1684, 1673 → should detect AI usage
- PRs with "No AI" → should NOT match

## Related Issues / PRs

- Previous AI detection work: Migration 0012_add_ai_tracking_fields
- Copilot metrics: apps/integrations/tests/test_copilot_sync.py
- Bot author detection: detect_ai_author() function

## External References

- [Gumroad AI Disclosure Template](https://github.com/antiwork/gumroad/pull/1673) - PR adding AI prompt template
- Cursor IDE: https://cursor.sh
- Claude models: opus, sonnet, haiku naming
