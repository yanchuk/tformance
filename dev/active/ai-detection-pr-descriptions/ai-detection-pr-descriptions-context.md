# AI Detection via PR Description Analysis - Context

**Last Updated: 2025-12-25 12:00 UTC**

## Session Summary (2025-12-25 - Prompt v5 + LLM Summary Field)

### What Was Accomplished

1. **Prompt v5.0.0 - Comprehensive PR Analysis**:
   - Created `apps/metrics/services/llm_prompts.py` as **SOURCE OF TRUTH**
   - Three outputs: AI detection, Technology detection, PR summary
   - Response schema designed for CTO dashboard display

2. **New Database Fields (Migration 0019)**:
   - `llm_summary`: JSONField - Full LLM analysis response
   - `llm_summary_version`: CharField - Prompt version used

3. **Repository Languages Feature Complete**:
   - Added `languages`, `primary_language`, `languages_updated_at` to TrackedRepository
   - Created `github_repo_languages.py` service
   - Added Celery tasks: `refresh_repo_languages_task`, `refresh_all_repo_languages_task`
   - Monthly refresh schedule configured
   - 16 tests passing

4. **Testing Infrastructure**:
   - `export_prs_to_promptfoo.py` - Export real PRs to promptfoo format
   - `run_llm_experiment.py` - Compare LLM vs regex detection
   - Documentation moved to `prd/AI-DETECTION-TESTING.md`

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

### IMPORTANT: User Prompt Data

**Current**: Only PR body is passed
**Required**: Need to pass ALL available PR data to LLM:

```python
# apps/metrics/services/llm_prompts.py - get_user_prompt() needs enhancement

# Data to pass:
- pr_title: str               # PR title
- pr_body: str                # PR description
- file_count: int             # Number of files changed
- additions: int              # Lines added
- deletions: int              # Lines deleted
- comment_count: int          # Total comments
- repo_languages: list[str]   # Top 3-5 languages from TrackedRepository
```

The system prompt already explains how to interpret this data. The user prompt just needs to include it.

### Files Modified This Session

| File | Changes |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | NEW: Source of truth for prompts |
| `apps/metrics/models/github.py` | Added llm_summary, llm_summary_version |
| `apps/metrics/migrations/0019_add_llm_summary.py` | NEW |
| `apps/integrations/models.py` | Added languages fields (migration 0015) |
| `apps/integrations/services/github_repo_languages.py` | NEW |
| `apps/integrations/tasks.py` | Added refresh language tasks |
| `apps/integrations/tests/test_github_repo_languages.py` | NEW: 16 tests |
| `apps/metrics/management/commands/export_prs_to_promptfoo.py` | NEW |
| `apps/metrics/management/commands/run_llm_experiment.py` | NEW |
| `prd/AI-DETECTION-TESTING.md` | Moved from dev/active |
| `CLAUDE.md` | Added reference to testing docs |

### Files Already Committed (Previous Sessions)

- `apps/metrics/services/ai_patterns.py` - v1.5.0
- `apps/metrics/models/github.py` - ai_detection_version field
- `apps/metrics/migrations/0018_add_ai_detection_version.py`
- `apps/integrations/services/groq_batch.py` - Prompt v4
- `dev/active/.../experiments/prompts/v4.md` - Tech detection prompt

### Next Steps on Restart

1. **Enhance user prompt with ALL PR data**:
   ```python
   # In llm_prompts.py, update get_user_prompt() to include:
   # - additions/deletions (PR size)
   # - repo languages from TrackedRepository.languages
   # - comments count
   ```

2. **Update GroqBatchProcessor to use new prompts**:
   ```python
   # In groq_batch.py, import from llm_prompts.py:
   from apps.metrics.services.llm_prompts import (
       PR_ANALYSIS_SYSTEM_PROMPT,
       PROMPT_VERSION,
       get_user_prompt,
   )
   ```

3. **Add Celery task for nightly LLM batch**:
   - Create `queue_prs_for_llm_analysis` task
   - Create `apply_llm_analysis_results` task
   - Store results in `llm_summary` field

4. **Update promptfoo tests for v5 schema**

5. **Commit all uncommitted changes**

### Commands to Run

```bash
# Check uncommitted changes
git status

# Run language service tests
.venv/bin/pytest apps/integrations/tests/test_github_repo_languages.py -v

# Check migrations
make migrations  # Should show no changes

# Run Groq batch tests
.venv/bin/pytest apps/integrations/tests/test_groq_batch.py -v
```

### Prompt Source of Truth

| What | Location | Purpose |
|------|----------|---------|
| **Production Prompt** | `apps/metrics/services/llm_prompts.py` | Canonical source |
| **Version** | `PROMPT_VERSION = "5.0.0"` | Track changes |
| **Promptfoo Testing** | `experiments/prompts/v5-system.txt` | Copy for testing |

When updating prompts:
1. Edit `llm_prompts.py` first
2. Increment `PROMPT_VERSION`
3. Copy to `prompts/v{N}-system.txt` for promptfoo
4. Run `npx promptfoo eval`

---

## Previous Session (2025-12-25 08:30 - Technology Detection v4)

### What Was Accomplished
1. Pattern Version 1.5.0 Committed (99789a5)
2. Prompt v4 - Technology Detection added
3. Versioning system extended with tech patterns
4. 22 Groq batch tests passing

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | **SOURCE OF TRUTH** for LLM prompts |
| `apps/metrics/services/ai_patterns.py` | Regex patterns (v1.5.0) |
| `apps/metrics/services/ai_detector.py` | detect_ai_in_text() |
| `apps/integrations/services/groq_batch.py` | Groq Batch API service |
| `apps/integrations/services/github_repo_languages.py` | Language fetching |
| `apps/metrics/experiments/runner.py` | ExperimentRunner class |
| `prd/AI-DETECTION-TESTING.md` | Testing documentation |

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

## Current Detection Flow

```
GitHub GraphQL API
       ↓
_process_pr() / _process_pr_incremental()
       ↓
Regex: _detect_pr_ai_involvement(author_login, title, body)
       ↓
detect_ai_author() + detect_ai_in_text()
       ↓
is_ai_assisted, ai_tools_detected stored

[Future: Nightly Celery Task]
       ↓
Groq Batch API with v5 prompt
       ↓
llm_summary, llm_summary_version stored
```

## Detection Statistics (Dec 2024)

| Team | PRs | AI Detected | Rate |
|------|-----|-------------|------|
| Antiwork | 41 | 18 | 43.9% |
| Cal.com | 199 | 65 | 32.7% |
| Anthropic | 112 | 34 | 30.4% |
| Gumroad | 221 | 66 | 29.9% |
| PostHog | 637 | 17 | 2.7% |
| Trigger.dev | 145 | 4 | 2.8% |
| Polar.sh | 194 | 1 | 0.5% |

Low rates for PostHog/Polar/Trigger.dev suggest teams don't disclose AI usage.
LLM detection should catch more nuanced cases.
