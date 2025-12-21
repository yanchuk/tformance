# Phase 2: LLM MVP - Context

**Last Updated:** 2025-12-21

## Key Files

### From Phase 1
- `apps/metrics/models.py` - DailyInsight model
- `apps/metrics/services/dashboard_service.py` - Data functions to expose

### Gemini API Reference
- Docs: https://ai.google.dev/gemini-api/docs/function-calling
- Python SDK: `google-genai`

## Dependencies

```toml
# pyproject.toml
[project.dependencies]
google-genai = "^1.0.0"
```

## Environment Variables

```bash
# .env
GOOGLE_AI_API_KEY=your-api-key-here
```

## Function Declarations to Create

| Function | Maps To | Purpose |
|----------|---------|---------|
| `get_team_metrics` | `get_key_metrics()` | Overview stats |
| `get_ai_trends` | `get_ai_adoption_trend()` | AI adoption over time |
| `get_developer_stats` | `get_team_breakdown()` | Per-person metrics |
| `get_quality_comparison` | `get_ai_quality_comparison()` | AI vs non-AI |
| `get_reviewer_info` | `get_reviewer_workload()` | Reviewer stats |
| `get_recent_prs` | `get_recent_prs()` | Latest PRs |

## Gemini Client Pattern

```python
from google import genai
from google.genai import types
from django.conf import settings

def get_gemini_client():
    return genai.Client(api_key=settings.GOOGLE_AI_API_KEY)

def generate_with_functions(prompt: str, functions: list) -> str:
    client = get_gemini_client()
    tools = types.Tool(function_declarations=functions)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(tools=[tools]),
    )
    return response
```

## Decisions Made

1. **Gemini over Claude** - 6x cheaper, good enough quality for MVP
2. **Flash model** - Fastest, cheapest, sufficient for this use case
3. **Function calling** - More flexible than prompt-only
4. **Pre-computed first** - Summarize DailyInsight before custom queries
5. **HTMX integration** - No frontend JS framework needed

## Team Isolation

All functions must be scoped to the user's team:

```python
def execute_function(team: Team, name: str, args: dict) -> dict:
    """Execute a function with team context."""
    if name == "get_team_metrics":
        return get_key_metrics(team, **args)
    # ... etc
```
