# AI Detection Testing & Experimentation

## Overview

This document covers the tools and approaches for testing and evaluating AI detection in PR descriptions.

## Prompt Source of Truth

**IMPORTANT**: The canonical prompt lives in **Jinja2 templates**, not in experiment files.

| What | Location | Purpose |
|------|----------|---------|
| **Prompt Templates** | `apps/metrics/prompts/templates/` | Source of truth (Jinja2) |
| **Rendered Prompt** | `render_system_prompt()` | Compose from templates |
| **Version** | `PROMPT_VERSION` in `llm_prompts.py` | Track changes |
| **Schema Validation** | `apps/metrics/prompts/schemas.py` | JSON Schema for responses |
| **Promptfoo Config** | Auto-generated | `make export-prompts` |

### Template Structure

```
apps/metrics/prompts/templates/
├── system.jinja2              # Main template (composes sections)
└── sections/
    ├── intro.jinja2           # Tasks overview
    ├── ai_detection.jinja2    # AI detection rules
    ├── tech_detection.jinja2  # Technology detection
    ├── health_assessment.jinja2  # Health metrics guidelines
    ├── response_schema.jinja2 # JSON response format
    ├── definitions.jinja2     # Category & type definitions
    └── enums.jinja2           # Tool/language/framework lists
```

## Prompt Update Workflow

Modify prompts via templates, then regenerate config:

```bash
# 1. Edit the relevant template section
vim apps/metrics/prompts/templates/sections/ai_detection.jinja2

# 2. Verify template renders correctly
python manage.py shell -c "from apps.metrics.prompts.render import render_system_prompt; print(render_system_prompt())"

# 3. Run equivalence test (ensures templates match llm_prompts.py constant)
pytest apps/metrics/prompts/tests/test_render.py -k matches_original

# 4. If changing behavior, update PROMPT_VERSION in llm_prompts.py

# 5. Regenerate promptfoo config (auto-renders from templates)
make export-prompts

# 6. Run evaluation
cd dev/active/ai-detection-pr-descriptions/experiments
export GROQ_API_KEY="your-key"
npx promptfoo eval
npx promptfoo view
```

This eliminates manual sync between code and test files.

## LLM Response Schema (v6.0.0+)

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
  },
  "health": {
    "review_friction": "low",
    "scope": "medium",
    "risk_level": "low",
    "insights": ["Fast review turnaround indicates clear PR scope"]
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
- **Stored in**: `PullRequest.llm_summary`, `llm_summary_version`

## Testing Tools

### Promptfoo (Prompt Evaluation)

```bash
# Generate config from Python source (DO THIS FIRST!)
make export-prompts

# Navigate to experiments directory
cd dev/active/ai-detection-pr-descriptions/experiments

# Set API key (required for each terminal session)
export GROQ_API_KEY="your-key-here"

# Run evaluation
npx promptfoo eval

# View results in browser
npx promptfoo view
```

**Config file**: `promptfoo.yaml` (auto-generated, DO NOT EDIT)
**Prompt file**: `prompts/v{VERSION}-system.txt` (auto-generated)

### Export PRs for Testing

```bash
# Export random sample of 50 PRs to JSON
python manage.py export_prs_to_promptfoo --limit 50 --sample --format json

# Export from specific team
python manage.py export_prs_to_promptfoo --team "PostHog" --limit 100

# Export as YAML (for promptfoo)
python manage.py export_prs_to_promptfoo --format yaml
```

### Run LLM Analysis (Database Population)

```bash
# Analyze PRs and store results in database
export GROQ_API_KEY="your-key-here"
python manage.py run_llm_analysis --limit 50

# Analyze specific team
python manage.py run_llm_analysis --team "Gumroad" --limit 100

# Re-analyze with newer prompt version
python manage.py run_llm_analysis --reprocess
```

### Backfill AI Detection (Regex)

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
| `llm_summary` | JSONField | Full LLM analysis (ai, tech, summary, health) |
| `llm_summary_version` | CharField | Prompt version used |

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
3. **Export config** → `make export-prompts` (auto-generates promptfoo.yaml)
4. **Run evaluation** → `npx promptfoo eval`
5. **Analyze results** → `npx promptfoo view`
6. **Update patterns** → `ai_patterns.py` (for regex)
7. **Backfill** → `python manage.py backfill_ai_detection`

## Golden Test Cases

Test cases for LLM prompt evaluation are defined in Python and auto-generated for promptfoo.

### Adding a New Test Case

1. **Add to `apps/metrics/prompts/golden_tests.py`**:
   ```python
   GoldenTest(
       id="pos_new_tool",              # Unique ID with category prefix
       description="New AI tool detection",
       category=GoldenTestCategory.POSITIVE,
       pr_title="Add feature",
       pr_body="## AI Disclosure\nBuilt with NewTool.",
       expected_ai_assisted=True,
       expected_tools=["newtool"],
       min_confidence=0.8,
   ),
   ```

2. **Run tests**: `pytest apps/metrics/prompts/tests/test_golden_tests.py -v`

3. **Export**: `make export-prompts`

4. **Evaluate**: `cd dev/.../experiments && npx promptfoo eval`

### Test Categories

| Category | Prefix | Description |
|----------|--------|-------------|
| POSITIVE | `pos_` | Should detect AI (expected_ai_assisted=True) |
| NEGATIVE | `neg_` | Should NOT detect AI (expected_ai_assisted=False) |
| EDGE_CASE | `edge_` | Ambiguous cases (brainstorming, review) |
| TECH_DETECTION | `tech_` | Technology/framework detection |
| SUMMARY | `type_` | PR type classification |

## Files

```
apps/metrics/
├── services/
│   ├── llm_prompts.py          # PROMPT_VERSION + user prompt builder
│   ├── ai_detector.py          # detect_ai_in_text()
│   └── ai_patterns.py          # AI_PATTERNS dict (regex)
├── prompts/                    # Prompt template system
│   ├── __init__.py             # Package exports
│   ├── render.py               # render_system_prompt()
│   ├── schemas.py              # JSON Schema validation
│   ├── export.py               # Promptfoo config generation
│   ├── golden_tests.py         # GoldenTest dataclass, GOLDEN_TESTS
│   ├── templates/
│   │   ├── system.jinja2       # Main template (SOURCE OF TRUTH)
│   │   └── sections/           # Composable prompt sections
│   │       ├── intro.jinja2
│   │       ├── ai_detection.jinja2
│   │       ├── tech_detection.jinja2
│   │       ├── health_assessment.jinja2
│   │       ├── response_schema.jinja2
│   │       ├── definitions.jinja2
│   │       └── enums.jinja2
│   └── tests/
│       ├── test_export.py      # 16 tests
│       ├── test_render.py      # 16 tests
│       ├── test_schemas.py     # 32 tests
│       ├── test_golden_tests.py          # 27 tests
│       └── test_golden_regex_validation.py  # 14 tests
└── management/commands/
    ├── export_prompts.py       # Generate promptfoo config
    ├── export_prs_to_promptfoo.py
    ├── run_llm_analysis.py
    └── backfill_ai_detection.py

dev/active/ai-detection-pr-descriptions/
├── experiments/
│   ├── promptfoo.yaml          # Auto-generated config (DO NOT EDIT)
│   ├── prompts/
│   │   └── v{VERSION}-system.txt  # Auto-generated from templates
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
