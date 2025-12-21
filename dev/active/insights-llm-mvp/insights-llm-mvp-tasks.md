# Phase 2: LLM MVP - Tasks

**Last Updated:** 2025-12-21
**Status:** ✅ COMPLETE

## Task Checklist

### 1. Setup & Configuration [S] ✅ COMPLETE
- [x] Add `google-genai` to `pyproject.toml`
- [x] Add `posthog` for LLM analytics
- [x] Run `uv sync`
- [x] Add `GOOGLE_AI_API_KEY` to `.env.example`
- [x] Add `POSTHOG_API_KEY` to `.env.example`
- [x] Add settings to `tformance/settings.py`
- [x] Create `apps/insights/` app structure

**Acceptance:** ✅ Gemini client can be instantiated, PostHog configured

---

### 2. Gemini Client Wrapper [S] ✅ COMPLETE
- [x] Create `apps/insights/services/gemini_client.py`
- [x] Implement `GeminiClient` class with lazy loading
- [x] Implement `generate()` method with PostHog tracking
- [x] Add `LLMResponse` dataclass for standardized responses
- [x] Add cost calculation for different models
- [x] Add error handling (API errors, rate limits)
- [x] Write tests with mocked API (10 tests)

**Acceptance:** ✅ Client wrapper handles errors gracefully, tracks to PostHog

---

### 3. Testing Support [S] ✅ COMPLETE
- [x] Create `generate_insights` management command
- [x] Support `--sample` flag for UI testing
- [x] Support `--clear` flag to reset insights
- [x] Support `--team-slug` for specific teams

**Acceptance:** ✅ Can generate test data without API calls

---

### 4. Insight Summarizer [M] ✅ COMPLETE (5c12229)
- [x] Create `apps/insights/services/summarizer.py`
- [x] Implement `summarize_daily_insights(team)` function
- [x] Create summary prompt template
- [x] Add caching (1 hour TTL)
- [x] Write tests (13 tests)

**Acceptance:** ✅ Daily insights summarized in 2-3 sentences

---

### 5. Function Declarations [M] ✅ COMPLETE (1c39ae7)
- [x] Create `apps/insights/services/function_defs.py`
- [x] Define 6 core function declarations
- [x] Create `apps/insights/services/function_executor.py`
- [x] Implement execution routing
- [x] Write tests for each function (22 tests)

**Acceptance:** ✅ All 6 functions callable via Gemini

---

### 6. Question Answering [M] ✅ COMPLETE (0e19ec9)
- [x] Create `apps/insights/services/qa.py`
- [x] Implement `answer_question(team, question)` function
- [x] Handle multi-turn function calling
- [x] Limit to 3 function calls per query
- [x] Write tests (9 tests)

**Acceptance:** ✅ Can answer "How is Alice doing?" type questions

---

### 7. API Views [S] ✅ COMPLETE (e491a5e)
- [x] Create `apps/insights/views.py`
- [x] Implement `get_summary` view (GET)
- [x] Implement `ask_question` view (POST)
- [x] Implement `suggested_questions` view (GET)
- [x] Add rate limiting (10/min per user)
- [x] Create `apps/insights/urls.py`
- [x] Add to `team_urlpatterns`
- [x] Write view tests (16 tests)

**Acceptance:** ✅ API endpoints work with HTMX

---

### 8. Dashboard Integration [M] ✅ COMPLETE (b23c767)
- [x] Create `templates/insights/partials/ai_summary.html`
- [x] Create `templates/insights/partials/ask_form.html`
- [x] Create HTMX response partials
- [x] Update views for HTMX support
- [x] Add to CTO dashboard
- [x] Style with DaisyUI
- [x] Add loading states
- [x] Write HTMX tests (6 tests)

**Acceptance:** ✅ Summary shows on load, question form works

---

## Progress Summary

| Task | Status | Effort | Commit |
|------|--------|--------|--------|
| 1. Setup & Configuration | ✅ Complete | S | 867d0ab |
| 2. Gemini Client Wrapper | ✅ Complete | S | 867d0ab |
| 3. Testing Support | ✅ Complete | S | 867d0ab |
| 4. Insight Summarizer | ✅ Complete | M | 5c12229 |
| 5. Function Declarations | ✅ Complete | M | 1c39ae7 |
| 6. Question Answering | ✅ Complete | M | 0e19ec9 |
| 7. API Views | ✅ Complete | S | e491a5e |
| 8. Dashboard Integration | ✅ Complete | M | b23c767 |

**Completed:** 8/8 tasks (100%)

## Files Created

```
apps/insights/
├── __init__.py
├── urls.py                            # API URL patterns
├── views.py                           # API endpoints with HTMX support
├── services/
│   ├── __init__.py
│   ├── gemini_client.py               # Gemini wrapper with PostHog
│   ├── summarizer.py                  # Daily insight summarization
│   ├── function_defs.py               # Function declarations for Gemini
│   ├── function_executor.py           # Executes function calls
│   └── qa.py                          # Question answering with function calling
└── tests/
    ├── __init__.py
    ├── test_gemini_client.py          # 10 tests
    ├── test_summarizer.py             # 13 tests
    ├── test_function_defs.py          # 8 tests
    ├── test_function_executor.py      # 14 tests
    ├── test_qa.py                     # 9 tests
    └── test_views.py                  # 22 tests

templates/insights/partials/
├── ai_summary.html                    # AI summary card
├── ask_form.html                      # Q&A form
├── answer_response.html               # Answer partial
├── suggested_response.html            # Suggested questions
└── summary_response.html              # Summary partial

apps/metrics/management/commands/
└── generate_insights.py               # Test insight generator
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/app/insights/summary/` | GET | Get AI summary of today's insights |
| `/app/insights/ask/` | POST | Ask a question about team metrics |
| `/app/insights/suggested/` | GET | Get suggested questions |

## Test Coverage

```
apps.insights.tests
├── test_gemini_client.py     - 10 tests ✅
├── test_summarizer.py        - 13 tests ✅
├── test_function_defs.py     -  8 tests ✅
├── test_function_executor.py - 14 tests ✅
├── test_qa.py                -  9 tests ✅
└── test_views.py             - 22 tests ✅
                              ─────────────
                               76 tests total
```

## Environment Variables

```bash
# PostHog Analytics (for LLM observability)
POSTHOG_API_KEY=""
POSTHOG_HOST="https://us.i.posthog.com"

# Google Gemini AI
GOOGLE_AI_API_KEY=""
```
