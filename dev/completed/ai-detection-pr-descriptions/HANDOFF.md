# AI Detection System - Handoff Summary

## What We're Building

An LLM-based system to detect AI tool usage in pull requests by analyzing PR descriptions, commit messages, and metadata. This supplements regex-based detection with nuanced understanding of context.

## Current State

### Architecture

```
PR Data → get_user_prompt() → LLM (Groq) → JSON Response → Store in DB
              ↓
         Full context:
         - Title, author, state
         - Files, timing metrics
         - Commits, reviews
         - Labels, Jira, milestone
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| **Prompt Templates** | `apps/metrics/prompts/templates/` | Jinja2 templates for system prompt |
| **User Prompt Builder** | `apps/metrics/services/llm_prompts.py` | `get_user_prompt()` with 20+ fields |
| **Golden Tests** | `apps/metrics/prompts/golden_tests.py` | 29 test cases for evaluation |
| **Promptfoo Export** | `apps/metrics/prompts/export.py` | Generate promptfoo.yaml with both models |
| **Batch Processor** | `apps/integrations/services/groq_batch.py` | Process PRs via Groq API |

### LLM Response Schema (v6.2.0)

```json
{
  "ai": {
    "is_assisted": true/false,
    "tools": ["cursor", "claude", "copilot"],
    "usage_type": "authored" | "assisted" | "reviewed" | "brainstorm",
    "confidence": 0.0-1.0
  },
  "tech": {
    "languages": ["python", "typescript"],
    "frameworks": ["django", "react"],
    "categories": ["backend", "frontend", "devops"]
  },
  "summary": {
    "title": "Brief description",
    "description": "1-2 sentence CTO summary",
    "type": "feature" | "bugfix" | "refactor" | "docs" | "test" | "chore" | "ci"
  },
  "health": {
    "review_friction": "low" | "medium" | "high",
    "scope": "small" | "medium" | "large" | "xlarge",
    "risk_level": "low" | "medium" | "high",
    "insights": ["observations about PR process"]
  }
}
```

## Models

| Model | ID | Use Case | Cost |
|-------|-----|----------|------|
| **Llama 3.3 70B** | `groq:llama-3.3-70b-versatile` | Primary, best quality | ~$1.16/1000 PRs |
| **GPT-OSS-20B** | `groq:openai/gpt-oss-20b` | Faster iteration | ~$0.32/1000 PRs |

### ⚠️ Critical: GPT-OSS-20B Configuration

GPT-OSS-20B outputs "Thinking: ..." before JSON by default. **Always set:**

```yaml
config:
  include_reasoning: false  # REQUIRED
  response_format:
    type: json_object
```

## How to Test

### 1. Golden Tests (29 synthetic cases)

```bash
cd dev/active/ai-detection-pr-descriptions/experiments
export GROQ_API_KEY='your-key'

# Run all golden tests
npx promptfoo eval

# Run subset
npx promptfoo eval --filter-pattern "health_"

# View results
npx promptfoo view  # Opens http://localhost:15500
```

### 2. Real PR Validation (50 PRs)

```bash
npx promptfoo eval -c model-comparison-final.yaml
```

### 3. Regenerate After Changes

```bash
python manage.py export_prompts
```

## Test Results (Latest)

| Test Suite | Pass Rate | Notes |
|------------|-----------|-------|
| Golden tests (29) | 79% (23/29) | Some edge cases fail |
| Real PRs (50×2 models) | 98% (98/100) | 2 mislabeled test cases |
| Model agreement | 100% | Both models agree on all PRs |

## Key Files

```
apps/metrics/prompts/
├── templates/
│   ├── system.jinja2           # Main system prompt
│   ├── user.jinja2             # User prompt template
│   └── sections/               # Prompt sections
├── golden_tests.py             # 29 test cases
├── export.py                   # Promptfoo config generator
├── render.py                   # Template rendering
└── schemas.py                  # JSON Schema validation

apps/metrics/services/
├── llm_prompts.py              # PROMPT_VERSION, get_user_prompt()
├── ai_patterns.py              # Regex patterns (fallback)
└── ai_detector.py              # Detection functions

dev/active/ai-detection-pr-descriptions/experiments/
├── promptfoo.yaml              # Auto-generated config
├── model-comparison-final.yaml # 50 PR comparison config
├── prompts/v6.2.0-system.txt   # Rendered system prompt
├── test-cases-50-array.json    # Real PR test data
└── results/                    # Evaluation outputs
```

## Workflow

### Adding a New AI Tool Pattern

1. Update `AI_SIGNATURE_PATTERNS` in `ai_patterns.py`
2. Add test case to `golden_tests.py`
3. Increment `PATTERNS_VERSION`
4. Run: `python manage.py export_prompts`
5. Test: `npx promptfoo eval`

### Modifying Prompts

1. Edit template in `apps/metrics/prompts/templates/sections/`
2. Run: `python manage.py export_prompts`
3. Test: `npx promptfoo eval`
4. Verify: `pytest apps/metrics/prompts/tests/`

### Production Deployment

1. Update `PROMPT_VERSION` in `llm_prompts.py`
2. Run full validation: `npx promptfoo eval -c model-comparison-final.yaml`
3. Deploy code
4. Optionally backfill historical PRs

## Context Passed to LLM

The `get_user_prompt()` function builds complete PR context:

- **Basic**: title, author, state, labels
- **Flags**: is_draft, is_hotfix, is_revert
- **Metadata**: milestone, jira_key, assignees, linked_issues
- **Code**: file_count, additions, deletions, file_paths
- **Timing**: cycle_time_hours, review_time_hours, review_rounds
- **Collaboration**: commit_messages, reviewers, review_comments
- **Repository**: repo_languages

All fields are visible in promptfoo UI for debugging.

## Next Steps

1. **Fix mislabeled test cases** in `test-cases-50-array.json`
2. **Add more edge cases** to golden tests as discovered in production
3. **Consider caching** LLM responses for unchanged PRs
4. **Monitor costs** - track token usage in production
