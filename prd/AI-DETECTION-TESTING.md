# AI Detection Testing & Experimentation

## Overview

This document covers the tools and approaches for testing and evaluating AI detection in PR descriptions.

## Prompt Source of Truth

**IMPORTANT**: The canonical prompt lives in code, not in experiment files.

| What | Location | Purpose |
|------|----------|---------|
| **Production Prompt** | `apps/metrics/services/llm_prompts.py` | Source of truth |
| **Version** | `PROMPT_VERSION` constant | Track changes |
| **Promptfoo Testing** | `dev/active/.../experiments/prompts/` | Copy for testing |

When updating prompts:
1. Edit `llm_prompts.py` first
2. Increment `PROMPT_VERSION`
3. Copy to `prompts/v{N}-system.txt` for promptfoo testing
4. Run `npx promptfoo eval` to validate

## LLM Response Schema (v5.0.0)

The LLM returns comprehensive PR analysis:

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

Stored in `PullRequest.llm_summary` JSONField.

## Detection Approaches

### 1. Regex-Based Detection (Current Production)
- **Location**: `apps/metrics/services/ai_detector.py`, `apps/metrics/services/ai_patterns.py`
- **Version tracking**: `ai_detection_version` field on PullRequest model
- **Patterns**: 100+ regex patterns covering Cursor, Claude, Copilot, etc.

### 2. LLM-Based Detection (In Development)
- **Provider**: Groq (llama-3.3-70b-versatile) - $0.08/1000 PRs
- **Prompt**: `apps/metrics/services/llm_prompts.py`
- **Batch API**: `apps/integrations/services/groq_batch.py`
- **Experiment Runner**: `apps/metrics/experiments/runner.py`
- **Stored in**: `PullRequest.llm_summary`, `llm_summary_version`

## Testing Tools

### Promptfoo (Prompt Evaluation)

```bash
# Navigate to experiments directory
cd dev/active/ai-detection-pr-descriptions/experiments

# Set API key (required for each terminal session)
export GROQ_API_KEY="your-key-here"

# Run evaluation
npx promptfoo eval

# View results in browser
npx promptfoo view
```

**Config file**: `promptfoo.yaml`
**Prompt versions**: `prompts/v5-system.txt` (current)

### Export PRs for Testing

```bash
# Export random sample of 50 PRs to JSON
python manage.py export_prs_to_promptfoo --limit 50 --sample --format json

# Export from specific team
python manage.py export_prs_to_promptfoo --team "PostHog" --limit 100

# Export as YAML (for promptfoo)
python manage.py export_prs_to_promptfoo --format yaml
```

### Run LLM Experiment

```bash
# Compare LLM vs regex on 30 random PRs
export GROQ_API_KEY="your-key-here"
python manage.py run_llm_experiment --limit 30 --sample

# Run on specific team
python manage.py run_llm_experiment --team "Gumroad" --limit 50
```

**Results saved to**: `dev/active/ai-detection-pr-descriptions/experiments/results/`

### Backfill AI Detection

```bash
# Dry run - see what would change
python manage.py backfill_ai_detection --dry-run

# Backfill specific team
python manage.py backfill_ai_detection --team "PostHog Analytics"

# Force re-detection on all PRs
python manage.py backfill_ai_detection --force
```

## Database Fields

### PullRequest Model

| Field | Type | Purpose |
|-------|------|---------|
| `is_ai_assisted` | Boolean | Regex detection result |
| `ai_tools_detected` | JSONField | List of tools from regex |
| `ai_detection_version` | CharField | Regex pattern version |
| `llm_summary` | JSONField | Full LLM analysis (ai, tech, summary) |
| `llm_summary_version` | CharField | Prompt version used |

## Metrics Tracking

### PostHog Integration
LLM calls are automatically logged to PostHog via LiteLLM callbacks:
- Event: `$ai_generation`
- Metadata: `pr_id`, `experiment_name`, `model`

## Current Detection Rates (Dec 2024)

| Team              | PRs | AI Detected | Rate  |
|-------------------|-----|-------------|-------|
| Antiwork          | 41  | 18          | 43.9% |
| Cal.com           | 199 | 65          | 32.7% |
| Anthropic         | 112 | 34          | 30.4% |
| Gumroad           | 221 | 66          | 29.9% |
| PostHog Analytics | 637 | 17          | 2.7%  |
| Trigger.dev       | 145 | 4           | 2.8%  |
| Polar.sh          | 194 | 1           | 0.5%  |

Low rates for PostHog/Polar/Trigger.dev suggest:
- Teams don't disclose AI usage in PRs
- AI usage without explicit mention
- Patterns we're missing (LLM would catch more)

## Experiment Workflow

1. **Edit prompt** → `apps/metrics/services/llm_prompts.py`
2. **Increment version** → `PROMPT_VERSION`
3. **Copy to experiments** → `prompts/v{N}-system.txt`
4. **Export test PRs** → `python manage.py export_prs_to_promptfoo`
5. **Run evaluation** → `npx promptfoo eval`
6. **Analyze results** → `npx promptfoo view`
7. **Update patterns** → `ai_patterns.py` (for regex)
8. **Backfill** → `python manage.py backfill_ai_detection`

## Files

```
apps/metrics/
├── services/
│   ├── llm_prompts.py         # SOURCE OF TRUTH for prompts
│   ├── ai_detector.py          # detect_ai_in_text()
│   └── ai_patterns.py          # AI_PATTERNS dict
├── experiments/
│   └── runner.py               # ExperimentRunner class
└── management/commands/
    ├── export_prs_to_promptfoo.py
    ├── run_llm_experiment.py
    └── backfill_ai_detection.py

dev/active/ai-detection-pr-descriptions/
├── experiments/
│   ├── promptfoo.yaml          # Promptfoo config
│   ├── prompts/
│   │   └── v5-system.txt       # Copy of current prompt
│   ├── results/                # Experiment outputs
│   └── test-cases-real.json    # Exported PRs
├── ai-detection-pr-descriptions-context.md
└── ai-detection-pr-descriptions-tasks.md
```

## Environment Variables

```bash
GROQ_API_KEY=gsk_...           # Required for LLM detection
POSTHOG_API_KEY=...            # Optional, for tracking LLM calls
```
