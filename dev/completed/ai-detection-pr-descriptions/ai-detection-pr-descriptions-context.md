# AI Detection via PR Description Analysis - Context

**Last Updated: 2025-12-25**

## Status: ✅ COMPLETE

This feature is complete and ready for production use.

---

## Final State

### Prompt Version: v6.3.2

| Version | Feature |
|---------|---------|
| v6.0.0 | Health assessment section |
| v6.1.0 | Additional PR metadata |
| v6.2.0 | Unified build_llm_pr_context() |
| v6.3.0 | Unified timeline (replaced timestamps) |
| v6.3.1 | AI product feature detection |
| v6.3.2 | is_assisted clarification for brainstorm/review |

### Test Results

- **Golden Tests**: 28/29 passing (96.55%)
- **Unit Tests**: 100+ passing
- **A/B Timeline Test**: +5.8% accuracy improvement

---

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | PROMPT_VERSION, get_user_prompt(), build_llm_pr_context(), build_timeline() |
| `apps/metrics/prompts/` | Jinja2 template system |
| `apps/metrics/prompts/golden_tests.py` | 29 test cases for LLM evaluation |
| `apps/metrics/prompts/export.py` | Promptfoo config generation |
| `apps/metrics/services/ai_patterns.py` | Regex patterns v1.7.0 |
| `apps/metrics/services/ai_detector.py` | Detection functions |
| `apps/integrations/services/groq_batch.py` | LLM batch processing |

---

## Response Schema (v6.3.2)

```json
{
  "ai": {
    "is_assisted": true,
    "tools": ["claude"],
    "usage_type": "authored",
    "confidence": 0.95
  },
  "tech": {
    "languages": ["python", "typescript"],
    "frameworks": ["django", "react"],
    "categories": ["backend", "frontend"]
  },
  "summary": {
    "title": "Brief title",
    "description": "CTO-friendly description",
    "type": "feature"
  },
  "health": {
    "review_friction": "low",
    "scope": "medium",
    "risk_level": "low",
    "insights": ["Observations about PR process"]
  }
}
```

---

## Database

- `llm_summary`: JSONB field with full analysis
- `llm_summary_version`: Prompt version string
- Migration 0020: GIN indexes for JSONB queries

---

## Commands

```bash
# Run LLM analysis
.venv/bin/python manage.py run_llm_analysis --limit 50

# Export promptfoo config
.venv/bin/python manage.py export_prompts

# Run promptfoo eval
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=... npx promptfoo eval -c promptfoo.yaml
```
