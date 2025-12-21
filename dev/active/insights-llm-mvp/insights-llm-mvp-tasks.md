# Phase 2: LLM MVP - Tasks

**Last Updated:** 2025-12-21

## Task Checklist

### 1. Setup & Configuration [S]
- [ ] Add `google-genai` to `pyproject.toml`
- [ ] Run `uv sync`
- [ ] Add `GOOGLE_AI_API_KEY` to `.env.example`
- [ ] Add setting to `tformance/settings.py`
- [ ] Create `apps/insights/` Django app

**Acceptance:** Gemini client can be instantiated

---

### 2. Gemini Client Wrapper [S]
- [ ] Create `apps/insights/services/gemini_client.py`
- [ ] Implement `get_client()` function
- [ ] Implement `generate_content()` wrapper
- [ ] Add error handling (API errors, rate limits)
- [ ] Write tests with mocked API

**Acceptance:** Client wrapper handles errors gracefully

---

### 3. Insight Summarizer [M]
- [ ] Create `apps/insights/services/summarizer.py`
- [ ] Implement `summarize_daily_insights(team)` function
- [ ] Create summary prompt template
- [ ] Add caching (1 hour TTL)
- [ ] Write tests

**Acceptance:** Daily insights summarized in 2-3 sentences

---

### 4. Function Declarations [M]
- [ ] Create `apps/insights/services/function_defs.py`
- [ ] Define 6 core function declarations
- [ ] Create `apps/insights/services/function_executor.py`
- [ ] Implement execution routing
- [ ] Write tests for each function

**Acceptance:** All 6 functions callable via Gemini

---

### 5. Question Answering [M]
- [ ] Create `apps/insights/services/qa.py`
- [ ] Implement `answer_question(team, question)` function
- [ ] Handle multi-turn function calling
- [ ] Limit to 3 function calls per query
- [ ] Write tests

**Acceptance:** Can answer "How is Alice doing?" type questions

---

### 6. API Views [S]
- [ ] Create `apps/insights/views.py`
- [ ] Implement `get_summary` view (GET)
- [ ] Implement `ask_question` view (POST)
- [ ] Add rate limiting (10/min per user)
- [ ] Create `apps/insights/urls.py`
- [ ] Add to `team_urlpatterns`
- [ ] Write view tests

**Acceptance:** API endpoints work with HTMX

---

### 7. Dashboard Integration [M]
- [ ] Create `templates/insights/partials/summary_card.html`
- [ ] Create `templates/insights/partials/ask_form.html`
- [ ] Add to CTO dashboard
- [ ] Style with DaisyUI
- [ ] Add loading states
- [ ] Write E2E test

**Acceptance:** Summary shows on load, question form works

---

## Progress Summary

| Task | Status | Effort |
|------|--------|--------|
| 1. Setup & Configuration | ⬜ Not Started | S |
| 2. Gemini Client Wrapper | ⬜ Not Started | S |
| 3. Insight Summarizer | ⬜ Not Started | M |
| 4. Function Declarations | ⬜ Not Started | M |
| 5. Question Answering | ⬜ Not Started | M |
| 6. API Views | ⬜ Not Started | S |
| 7. Dashboard Integration | ⬜ Not Started | M |

**Total Effort:** ~2-3 days

## Dependencies

```
Phase 1 Complete (DailyInsight model exists)
    ↓
1. Setup & Configuration
    ↓
2. Gemini Client Wrapper
    ↓
3. Insight Summarizer ──┬── 4. Function Declarations
                        │
                        ↓
                  5. Question Answering
                        ↓
                  6. API Views
                        ↓
                  7. Dashboard Integration
```

## Test Queries for Validation

1. "Give me a summary of how the team is doing"
2. "How is Alice performing compared to the team?"
3. "What's our AI adoption trend?"
4. "Who reviews the most PRs?"
5. "Are there any concerning patterns I should know about?"
