# AI Detection via PR Description Analysis - Context

**Last Updated: 2025-12-24 23:15 UTC**

## Session Summary (2025-12-24 - Pattern v1.7.0 + Enhanced Prompt Planning)

### What Was Accomplished This Session

1. **Pattern Improvement Loop v1.6.0 → v1.7.0**:
   - Ran LLM experiment on 100 PRs (96% agreement with regex)
   - Found 2 new tools: CodeRabbit text mentions, Mintlify agent
   - Added 6 new patterns, bumped to v1.7.0
   - Backfilled database: 459 PRs detected (20.2%)

2. **Detection Rate Progress**:
   - v1.5.0: 205 PRs (13.2%)
   - v1.6.0: 264 PRs (14.9%) - +59 PRs
   - v1.7.0: 459 PRs (20.2%) - +25 PRs (CodeRabbit: 22, Mintlify: 3)

3. **User Request for Enhanced LLM Prompt**:
   - Current prompt only sends: title, file_count, lines, comment_count, repo_languages
   - User wants FULL PR context for better AI detection AND PR summary generation
   - Goal: CTO-ready insights about PR health, issues, and what it's about

### Files Modified This Session

| File | Change |
|------|--------|
| `apps/metrics/services/ai_patterns.py` | v1.6.0 → v1.7.0 patterns |
| `apps/metrics/services/PATTERN_CHANGELOG.md` | Added v1.6.0 and v1.7.0 entries |
| `apps/metrics/tests/test_ai_detector.py` | Added 10 tests (107→117) |

### Uncommitted Changes

```bash
git status --short
# M apps/metrics/services/ai_patterns.py
# M apps/metrics/services/PATTERN_CHANGELOG.md
# M apps/metrics/tests/test_ai_detector.py
# M dev/active/ai-detection-pr-descriptions/*.md
# ?? dev/active/.../experiments/promptfoo-100.yaml
# ?? dev/active/.../experiments/test-cases-100-array.json
```

### Promptfoo 100 PR Dataset

Created `promptfoo-100.yaml` with 100 real PRs from database for comprehensive testing:
- 16 PRs currently AI-detected
- Teams: Cal.com (12), PostHog (22), Gumroad (11), Polar (9), etc.
- Run: `npx promptfoo eval -c promptfoo-100.yaml`

---

## NEXT SESSION: Enhanced LLM Prompt (v6.0.0)

### User Requirements

User wants the LLM to receive **ALL available PR data** to:
1. Detect AI usage more accurately (comments might mention AI tools)
2. Generate CTO-ready PR summary with insights
3. Identify issues/friction (many comments, back-and-forth, long review time)

### Data to Add to User Prompt

| Data | Field(s) in PullRequest | Purpose |
|------|-------------------------|---------|
| File paths | `files_changed` (JSONField) | Tech detection, scope understanding |
| Comment bodies | Need to fetch via API | AI mentions in discussions |
| Commit messages | `commits` relation | Co-Authored-By signatures |
| Cycle time | `cycle_time_hours` | PR health indicator |
| Review time | `review_time_hours` | Review friction indicator |
| First review at | `first_review_at` | Response time metric |
| State | `state` | open/merged/closed |
| Labels | `labels` (JSONField) | Categorization |
| Is draft | `is_draft` | Work in progress |
| Assignees | `assignees` (JSONField) | Who's responsible |
| Linked issues | `linked_issues` (JSONField) | Jira/issue context |
| Comment count | `comment_count` | Discussion level |
| Commits after review | Need calculation | Iteration indicator |

### Proposed System Prompt v6.0.0 Structure

```
## Your Task
1. AI Usage Detection (existing)
2. Technology Detection (existing)
3. PR Summary for CTO (existing)
4. **NEW: PR Health Assessment**
   - Review friction (comments, iterations)
   - Response time quality
   - Scope assessment (file count, lines)
   - Risk indicators (large PR, many iterations)

## PR Health Indicators (explain in system prompt)
- cycle_time_hours: Time from PR open to merge
- review_time_hours: Time from open to first review
- comment_count: Higher = more discussion/issues
- commits_after_review: Higher = more iterations needed
- file_count: >20 files = large scope
- lines_changed: >500 = needs careful review
```

### Proposed Response Schema v6.0.0

```json
{
  "ai": { /* existing */ },
  "tech": { /* existing */ },
  "summary": {
    "title": "Brief title",
    "description": "CTO-friendly summary",
    "type": "feature|bugfix|refactor|docs|test|chore|ci"
  },
  "health": {
    "review_friction": "low|medium|high",
    "scope": "small|medium|large|xlarge",
    "risk_level": "low|medium|high",
    "insights": ["Took 3 iterations to approve", "Large scope across 15 files"]
  }
}
```

---

## Previous Session Summary (2025-12-24 - Pattern v1.6.0 + Improvement Loop)

### What Was Accomplished This Session

1. **Pattern Improvement Loop**:
   - Analyzed PRs where LLM detected AI but regex missed
   - Found 3 new pattern categories to add:
     - **Cubic AI** (59 new detections) - PR description generator
     - **Cursor.com domain** (background-agent/dashboard links)
     - **Copilot Coding Agent** (6 new detections)

2. **Updated ai_patterns.py (v1.5.0 → v1.6.0)**:
   - Added 6 new patterns
   - Added "cubic" to AI_TOOL_DISPLAY_NAMES
   - Created `PATTERN_CHANGELOG.md` for version history tracking

3. **Detection Improvement Results**:
   - Before (v1.5.0): 205 PRs detected (13.2%)
   - After (v1.6.0): 259 PRs detected (16.7%)
   - **+26.3% improvement** (+54 PRs)

4. **Added 6 New Tests**:
   - test_detects_cubic_summary
   - test_detects_cubic_auto_generated
   - test_detects_cursor_com_background_agent
   - test_detects_cursor_com_dashboard
   - test_detects_copilot_coding_agent
   - test_detects_copilot_original_prompt

### Files Modified This Session

| File | Change |
|------|--------|
| `apps/metrics/services/ai_patterns.py` | Added v1.6.0 patterns |
| `apps/metrics/services/PATTERN_CHANGELOG.md` | NEW - Version history |
| `apps/metrics/tests/test_ai_detector.py` | Added 6 tests (107→113) |

---

## Previous Session Summary (2025-12-24 - Phase 2.6 COMPLETE)

### What Was Accomplished

1. **LLM Prompt v5.0.0 - Fully Implemented**:
   - Created `apps/metrics/services/llm_prompts.py` as **SOURCE OF TRUTH**
   - `get_user_prompt()` enhanced with: pr_title, additions, deletions, file_count, comment_count, repo_languages
   - 19 tests for llm_prompts.py - all passing

2. **GroqBatchProcessor Updated**:
   - Uses `PR_ANALYSIS_SYSTEM_PROMPT` from llm_prompts.py by default
   - Parses both v4 (flat) and v5 (nested) response formats
   - BatchResult includes: llm_summary dict, prompt_version, summary fields
   - 24 tests - all passing

3. **Database Fields (Migration 0019)**:
   - `llm_summary`: JSONField - Full LLM analysis response
   - `llm_summary_version`: CharField - Prompt version used

4. **Repository Languages Backfilled**:
   - polarsource/polar: Python primary, [Python, TypeScript, HCL, JavaScript, MDX]
   - Other seeded repos don't have TrackedRepository records

5. **LLM vs Regex Correlation Analysis**:
   - **+60% improvement** - LLM detects 16% vs Regex 10%
   - 92% agreement between methods
   - LLM catches 7% additional cases regex misses
   - Regex has 1% false positives LLM correctly rejects

6. **Promptfoo v5 Evaluation**:
   - 20/20 tests passing (100%)
   - Tests cover: AI detection, tech detection, summary/type classification

### Commit Made This Session

```
35a9264 Add LLM prompt v5 with PR summary and technology detection
```

### LLM vs Regex Correlation Results (100 PRs)

```
DETECTION RATES:
  Regex:   10 / 100 = 10.0%
  LLM:     16 / 100 = 16.0%

IMPROVEMENT:
  Absolute: +6 more detections
  Relative: +60% improvement

CORRELATION MATRIX:
                    LLM=Yes    LLM=No
  Regex=Yes           9          1
  Regex=No            7         83

AGREEMENT: 92% of cases
```

### Key Files Modified/Created

| File | Status | Purpose |
|------|--------|---------|
| `apps/metrics/services/llm_prompts.py` | NEW | Source of truth for prompts |
| `apps/metrics/tests/test_llm_prompts.py` | NEW | 19 tests |
| `apps/metrics/migrations/0019_add_llm_summary.py` | NEW | llm_summary fields |
| `apps/metrics/models/github.py` | MODIFIED | Added llm_summary, llm_summary_version |
| `apps/integrations/services/groq_batch.py` | MODIFIED | Uses v5 prompt, parses nested format |
| `apps/integrations/tests/test_groq_batch.py` | MODIFIED | 24 tests (added v5 format tests) |
| `apps/metrics/management/commands/export_prs_to_promptfoo.py` | NEW | Export PRs for testing |
| `apps/metrics/management/commands/run_llm_experiment.py` | NEW | Compare LLM vs regex |
| `prd/AI-DETECTION-TESTING.md` | NEW | Testing documentation |
| `dev/.../experiments/promptfoo.yaml` | MODIFIED | v5 prompt config |
| `dev/.../experiments/prompts/v5-system.txt` | NEW | v5 prompt for promptfoo |

### Prompt v5 Response Schema

```json
{
  "ai": {
    "is_assisted": true,
    "tools": ["cursor", "claude"],
    "usage_type": "authored",
    "confidence": 0.95
  },
  "tech": {
    "languages": ["python", "typescript"],
    "frameworks": ["django", "react"],
    "categories": ["backend", "frontend"]
  },
  "summary": {
    "title": "Add dark mode toggle",
    "description": "Adds user preference for dark/light theme in settings.",
    "type": "feature"
  }
}
```

---

## Next Steps on Restart

### Immediate (Phase 2.7)

1. **Create Celery tasks for nightly LLM batch**:
   ```python
   # In apps/integrations/tasks.py or new file
   @shared_task
   def queue_prs_for_llm_analysis():
       """Find PRs needing LLM analysis."""
       # Filter: llm_summary__isnull=True OR llm_summary_version != PROMPT_VERSION
       # Limit batch size (100-500)
       # Submit to GroqBatchProcessor

   @shared_task
   def apply_llm_analysis_results(batch_id: str):
       """Store LLM results in llm_summary field."""
       # Get results from GroqBatchProcessor
       # Update PullRequest.llm_summary, llm_summary_version
   ```

2. **Add to Celery beat schedule** (nightly, 2 AM UTC)

3. **Test end-to-end flow**:
   - Export PRs → Run through Groq → Verify results stored

### Future (Phase 3)

- Display `llm_summary` in PR list UI
- Show technology badges
- Use LLM confidence for AI detection display

---

## Commands to Verify

```bash
# Run all tests
make test

# Run specific test suites
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -v  # 19 tests
.venv/bin/pytest apps/integrations/tests/test_groq_batch.py -v  # 24 tests

# Check migrations
.venv/bin/python manage.py showmigrations metrics  # 0019 should be applied

# Run LLM experiment
GROQ_API_KEY=... .venv/bin/python manage.py run_llm_experiment --limit 50 --sample

# Run promptfoo eval
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=... npx promptfoo eval -c promptfoo.yaml
```

---

## Key Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Prompt source of truth | `llm_prompts.py` | Single location, versioned, importable |
| LLM summary storage | JSONField on PR | Flexible schema for v5+ responses |
| Response format | Nested (ai/tech/summary) | Clear separation, CTO dashboard ready |
| Repo languages refresh | Monthly Celery task | Languages change rarely |
| LLM provider | Groq (Llama 3.3 70B) | $0.08/1000 PRs, 60% better than regex |

---

## Database Schema

```sql
-- Key fields in metrics_pullrequest
body: TEXT                    -- PR description
is_ai_assisted: BOOLEAN       -- Regex detection result
ai_tools_detected: JSONB      -- List from regex ["cursor", "claude"]
ai_detection_version: VARCHAR -- Regex pattern version (e.g., "1.5.0")
llm_summary: JSONB            -- Full LLM analysis (ai, tech, summary)
llm_summary_version: VARCHAR  -- Prompt version (e.g., "5.0.0")

-- Key fields in integrations_trackedrepository
languages: JSONB              -- {"Python": 150000, "JavaScript": 25000}
primary_language: VARCHAR     -- "Python"
languages_updated_at: DATETIME
```

---

## Current Detection Stats (Dec 2024)

| Team | PRs | Regex | LLM (est.) |
|------|-----|-------|------------|
| Antiwork | 41 | 43.9% | ~70% |
| Cal.com | 199 | 32.7% | ~52% |
| Anthropic | 112 | 30.4% | ~49% |
| Gumroad | 221 | 29.9% | ~48% |
| PostHog | 637 | 2.7% | ~4% |
| Trigger.dev | 145 | 2.8% | ~4% |
| Polar.sh | 194 | 0.5% | ~1% |

LLM estimates based on +60% improvement factor.
