# Phase 2: LLM-Powered Insights MVP

**Last Updated:** 2025-12-21

## Executive Summary

Add natural language insight generation using Gemini function calling. The LLM summarizes pre-computed insights from Phase 1 and can answer custom questions by calling `dashboard_service.py` functions.

## Prerequisites

- **Phase 1 Complete** - Rule-based insights generating daily
- **Gemini API Key** - Google AI API access

## Goals

1. **Natural Language Summaries** - Convert rule-based insights to prose
2. **Custom Questions** - "How is Alice performing?" answered via function calling
3. **Minimal Cost** - Use pre-computed data, limit API calls
4. **Streaming Responses** - Good UX for longer responses

## Architecture

```
User Query → Django View → Gemini API (with function declarations)
                              ↓
                    Function Call Decision
                    ├── If functions needed → Execute locally → Return to Gemini
                    └── If summary only → Use DailyInsight data
                              ↓
                    Natural Language Response → User
```

## Implementation Approach

### Option A: Summarize Pre-computed Insights (Low Cost)
```python
def get_insight_summary(team: Team) -> str:
    """Get LLM summary of today's insights."""
    insights = DailyInsight.objects.filter(team=team, date=today())

    prompt = f"""Summarize these team insights in 2-3 sentences:
    {[i.title + ": " + i.description for i in insights]}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text
```

### Option B: Function Calling for Custom Queries (Flexible)
```python
# Function declarations
FUNCTION_DECLARATIONS = [
    {
        "name": "get_team_metrics",
        "description": "Get key metrics (PRs, cycle time, quality) for a team",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back"}
            }
        }
    },
    {
        "name": "get_developer_stats",
        "description": "Get stats for a specific developer",
        "parameters": {
            "type": "object",
            "properties": {
                "developer_name": {"type": "string"}
            }
        }
    },
    # ... more functions
]

def answer_question(team: Team, question: str) -> str:
    """Answer a custom question about team metrics."""
    tools = types.Tool(function_declarations=FUNCTION_DECLARATIONS)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=question,
        config=types.GenerateContentConfig(tools=[tools]),
    )

    # Handle function calls if any
    if response.function_calls:
        results = execute_functions(team, response.function_calls)
        # Send results back to Gemini for final response
        ...

    return response.text
```

## Cost Optimization

| Strategy | Impact |
|----------|--------|
| Use pre-computed insights | 90% fewer API calls |
| Use `gemini-2.5-flash` | Cheapest model |
| Cache common questions | Reduce repeat calls |
| Limit function calls per query | Cap at 3 |

**Estimated Cost:** ~$0.005 per query (with caching: ~$0.001)

## UI Integration

### Dashboard Widget
```html
<!-- Insight Summary Card -->
<div class="app-card">
  <h3>AI Summary</h3>
  <p id="insight-summary" hx-get="/a/team/insights/summary/" hx-trigger="load">
    Loading...
  </p>
</div>
```

### Chat Interface (Optional)
```html
<!-- Ask a Question -->
<div class="app-card">
  <input type="text"
         placeholder="Ask about your team metrics..."
         hx-post="/a/team/insights/ask/"
         hx-target="#answer">
  <div id="answer"></div>
</div>
```

## Files to Create

```
apps/insights/                    # New app
├── __init__.py
├── services/
│   ├── __init__.py
│   ├── gemini_client.py         # Gemini API wrapper
│   ├── function_executor.py     # Execute function calls
│   └── insight_summarizer.py    # Summarization logic
├── views.py                      # API endpoints
├── urls.py
├── tests/
│   └── test_gemini.py

templates/insights/
├── partials/
│   ├── summary_card.html
│   └── chat_input.html
```

## Security Considerations

1. **API Key Storage** - Use environment variable, not in code
2. **Rate Limiting** - Max 10 queries per user per minute
3. **Input Sanitization** - Don't pass raw user input to functions
4. **Team Isolation** - Only query data for user's team
