# Phase 2: LLM MVP - Context

**Last Updated:** 2025-12-21
**Status:** ✅ COMPLETE

## Implementation Summary

Phase 2 adds LLM-powered insights to the tformance platform using Google Gemini with function calling. The system can summarize daily insights and answer natural language questions about team metrics.

### Commits

| Commit | Description |
|--------|-------------|
| 867d0ab | Phase 2 foundation - PostHog, Gemini SDK, client wrapper |
| 5c12229 | Insight summarizer with 1-hour cache |
| 1c39ae7 | Function declarations and executor |
| 0e19ec9 | Question answering with function calling |
| e491a5e | API views with rate limiting and team isolation |
| b23c767 | Dashboard UI with HTMX integration |

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  CTO Dashboard  │────▶│  HTMX Partials  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
┌─────────────────────────────────────────┐
│           Django Views                   │
│  (get_summary, ask_question, suggested)  │
└────────┬────────────────────┬───────────┘
         │                    │
         ▼                    ▼
┌─────────────────┐  ┌─────────────────────┐
│   Summarizer    │  │   Question Answering │
│  (with cache)   │  │  (function calling)  │
└────────┬────────┘  └──────────┬──────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌─────────────────┐
         │  Gemini Client  │
         │  (with PostHog) │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │  Dashboard      │
         │  Service        │
         │  (data layer)   │
         └─────────────────┘
```

## Key Components

### 1. Gemini Client (`apps/insights/services/gemini_client.py`)
- Lazy loading of API client
- PostHog LLM analytics ($ai_generation events)
- Cost calculation for different models
- Standardized `LLMResponse` dataclass

### 2. Summarizer (`apps/insights/services/summarizer.py`)
- Summarizes DailyInsight records
- 1-hour cache TTL
- Graceful fallback when API unavailable

### 3. Function Declarations (`apps/insights/services/function_defs.py`)
- 6 functions exposed to Gemini:
  - `get_team_metrics` - Overview stats
  - `get_ai_adoption_trend` - AI adoption over time
  - `get_developer_stats` - Per-person metrics
  - `get_ai_quality_comparison` - AI vs non-AI quality
  - `get_reviewer_workload` - Reviewer stats
  - `get_recent_prs` - Latest pull requests

### 4. Q&A Service (`apps/insights/services/qa.py`)
- Multi-turn conversation with Gemini
- Function calling with 3-call limit per query
- Suggested questions for UI

### 5. API Views (`apps/insights/views.py`)
- Dual response format: JSON (API) and HTML (HTMX)
- Rate limiting: 10 requests/minute per user
- Team data isolation

### 6. Dashboard UI (`templates/insights/partials/`)
- AI summary card with refresh button
- Q&A form with suggested questions
- Loading states and error handling

## Security Model

1. **Authentication**: `@login_and_team_required` decorator
2. **Team Isolation**: Data scoped to `request.team`
3. **Rate Limiting**: `@ratelimit(key="user", rate="10/m")`
4. **Session Tampering**: Falls back to user's own team

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/app/insights/summary/` | GET | AI summary of daily insights |
| `/app/insights/summary/?refresh=true` | GET | Force refresh (skip cache) |
| `/app/insights/ask/` | POST | Ask a question (form or JSON) |
| `/app/insights/suggested/` | GET | Get suggested questions |

## Test Coverage

76 tests across 6 test files:
- `test_gemini_client.py` - 10 tests
- `test_summarizer.py` - 13 tests
- `test_function_defs.py` - 8 tests
- `test_function_executor.py` - 14 tests
- `test_qa.py` - 9 tests
- `test_views.py` - 22 tests

## Environment Variables

```bash
# Required for LLM features
GOOGLE_AI_API_KEY=""

# Optional but recommended for observability
POSTHOG_API_KEY=""
POSTHOG_HOST="https://us.i.posthog.com"
```

## Usage

```python
# Generate AI summary
from apps.insights.services.summarizer import summarize_daily_insights
summary = summarize_daily_insights(team=team)

# Answer questions
from apps.insights.services.qa import answer_question
answer = answer_question(team=team, question="How is the team?")
```

## Test Commands

```bash
# Generate sample insights
python manage.py generate_insights --sample --clear

# Run all insight tests
make test ARGS='apps.insights.tests --keepdb'
```
