# AI Involvement Tracking - Context

**Last Updated:** 2025-12-21 (Session 3 - End)

## Status: PHASES 1-5.1 COMPLETE

Phase 1 (database schema), Phase 2 (AI detector), Phase 4 (seeder integration), and Phase 5.1 (dashboard integration) are complete.
Only Phase 5.2 (AI indicators on PR views) remains.

---

## Current State Summary

### What's Complete
1. **Database Schema** - Migration `0012_add_ai_tracking_fields.py` applied
   - PullRequest: `body`, `is_ai_assisted`, `ai_tools_detected`
   - PRReview: `body`, `is_ai_review`, `ai_reviewer_type`
   - Commit: `is_ai_assisted`, `ai_co_authors`

2. **AI Detector Service** - 38 tests passing
   - `detect_ai_reviewer(username)` - Bot detection
   - `detect_ai_in_text(text)` - Text signature detection
   - `parse_co_authors(message)` - Co-author parsing

3. **Patterns Registry** - `ai_patterns.py` with versioning
   - `PATTERNS_VERSION = "1.0.0"` for historical reprocessing
   - 15+ bot usernames, 20+ text patterns, 12+ co-author patterns

4. **Seeder Integration** - AI detection in `real_project_seeder.py`
   - Detects AI in PR body/title, reviews, commits
   - Tracks stats: `ai_assisted_prs`, `ai_reviews`, `ai_commits`

5. **Dashboard Integration (Phase 5.1)** - 16 tests passing
   - 3 service functions in `dashboard_service.py`
   - 3 chart views with URL patterns
   - 3 template partials
   - CTO overview updated with AI Detection section

### What's Remaining
- **Phase 5.2: AI Indicators on PR Views** - Add AI badges to PR tables

---

## Files Created/Modified This Session

| File | Action | Purpose |
|------|--------|---------|
| `apps/metrics/services/dashboard_service.py` | Modified | Added 3 AI detection functions (lines 1054-1175) |
| `apps/metrics/tests/test_dashboard_ai_detection.py` | Created | 16 TDD tests for dashboard functions |
| `apps/metrics/views/chart_views.py` | Modified | Added 3 chart view functions |
| `apps/metrics/views/__init__.py` | Modified | Exported new views |
| `apps/metrics/urls.py` | Modified | Added 3 URL patterns |
| `templates/metrics/partials/ai_detected_metrics_card.html` | Created | AI detection summary card |
| `templates/metrics/partials/ai_tool_breakdown_chart.html` | Created | Tool breakdown visualization |
| `templates/metrics/partials/ai_bot_reviews_card.html` | Created | Bot reviewer stats |
| `templates/metrics/cto_overview.html` | Modified | Added AI Detection section (lines 127-188) |

---

## Key Code Locations

### Dashboard Service Functions
```python
# apps/metrics/services/dashboard_service.py

def get_ai_detected_metrics(team, start_date, end_date) -> dict:
    """Line 1061 - Returns {total_prs, ai_assisted_prs, ai_assisted_pct}"""

def get_ai_tool_breakdown(team, start_date, end_date) -> list[dict]:
    """Line 1099 - Returns [{tool, count}, ...] sorted by count desc"""

def get_ai_bot_review_stats(team, start_date, end_date) -> dict:
    """Line 1131 - Returns {total_reviews, ai_reviews, ai_review_pct, by_bot}"""
```

### Chart Views
```python
# apps/metrics/views/chart_views.py (lines 340-390)
def ai_detected_metrics_card(request)   # cards_ai_detected
def ai_tool_breakdown_chart(request)    # chart_ai_tools
def ai_bot_reviews_card(request)        # cards_ai_bot_reviews
```

### URL Patterns
```python
# apps/metrics/urls.py (lines 42-45)
path("cards/ai-detected/", views.ai_detected_metrics_card, name="cards_ai_detected"),
path("charts/ai-tools/", views.ai_tool_breakdown_chart, name="chart_ai_tools"),
path("cards/ai-bot-reviews/", views.ai_bot_reviews_card, name="cards_ai_bot_reviews"),
```

---

## Test Commands

```bash
# Run all AI-related tests (70 tests)
.venv/bin/python manage.py test apps.metrics.tests.test_ai_detector apps.metrics.tests.test_ai_model_fields apps.metrics.tests.test_dashboard_ai_detection --keepdb

# Run just dashboard tests (16 tests)
.venv/bin/python manage.py test apps.metrics.tests.test_dashboard_ai_detection --keepdb

# Verify all tests pass
make test

# Check code style
make ruff
```

---

## Uncommitted Changes

Check with `git status`:
- Dashboard service functions
- Test file for AI dashboard
- Chart views
- Template partials
- CTO overview template

**Commit message suggestion:**
```
Add AI detection dashboard integration (Phase 5.1)

- Add dashboard service functions for AI metrics
- Create chart views and URL patterns
- Add template partials for AI detection section
- Update CTO overview with AI Detection section
- 16 new tests for dashboard functions

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
```

---

## Next Session: Phase 5.2 Tasks

### 5.2 Add AI Indicators to PR Views
1. **Update `recent_prs_table.html`** - Add AI badge column
   - Show badge when `is_ai_assisted=True`
   - Display tool icon (Claude, Copilot, etc.)

2. **Update `get_recent_prs()` service** - Include AI detection data
   - Currently uses survey-based `ai_assisted`
   - Add `is_ai_assisted` and `ai_tools_detected` from model

3. **Create AI badge component** - Reusable badge template
   - `templates/metrics/components/ai_badge.html`
   - Show tool name on hover

4. **Add AI filter** - Filter PRs by AI involvement
   - Add query parameter support
   - Update template with filter dropdown

---

## Architectural Decisions Made

1. **Separate from Survey-Based AI Tracking**
   - Existing dashboard uses `survey__author_ai_assisted` (user self-report)
   - New detection uses `is_ai_assisted` (auto-detected from content)
   - Both shown separately - survey in "AI Adoption", detection in new section

2. **Bot Reviewer Detection via Username**
   - Exact username matching prevents false positives
   - No fuzzy matching or partial matches
   - Easy to extend in `ai_patterns.py`

3. **Pattern Versioning for Reprocessing**
   - `PATTERNS_VERSION` tracks pattern changes
   - Enables selective historical reprocessing when patterns updated

---

## Django-Specific Notes

- **No new migrations needed** - Schema complete from Session 2
- **Apps modified:** `apps.metrics` (service, views, tests)
- **Templates modified:** `templates/metrics/` (partials, cto_overview)
- **Celery tasks:** None added this session
- **Test coverage:** 70 AI-related tests passing
