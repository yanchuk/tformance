# Survey Improvements - Context Document

**Last Updated: 2025-12-23 (Session 5 - ALL PHASES COMPLETE)**

## Project Context

This feature enhances the PR survey system with **PR description-based voting** (not comments), **one-click voting**, **AI auto-detection**, **Slack fallback**, and **dashboard analytics**, informed by the Stack Overflow 2025 Developer Survey AI section. The goal is to capture more nuanced data about AI tool usage while maximizing response rates through frictionless voting directly from GitHub.

---

## Implementation Status: ✅ ALL PHASES COMPLETE

### ✅ COMPLETED: Model Changes

**Changes Made:**
- Added `RESPONSE_SOURCE_CHOICES` constant (github/slack/web/auto)
- Added `MODIFICATION_EFFORT_CHOICES` constant (none/minor/moderate/major/na)
- Added `author_response_source` field to PRSurvey
- Added `ai_modification_effort` field to PRSurvey
- Added `response_source` field to PRSurveyReview
- Created migration `0013_add_survey_response_source_fields.py`
- Updated factories with new fields

### ✅ COMPLETED: Phase 0 - AI Auto-Detection

**Changes Made:**
- Created `apps/integrations/services/ai_detection.py` with centralized patterns
- Implemented `detect_ai_coauthor()`, `get_detected_ai_tool()`, `get_all_detected_ai_tools()`
- Added 12 AI coding tools with detection patterns (extensible list)
- Added "auto" to `RESPONSE_SOURCE_CHOICES`
- Created migration `0014_add_auto_response_source.py`
- Integrated AI detection into `create_pr_survey()` function

**Supported AI Tools:**
- GitHub Copilot, Claude Code, Cursor, Devin
- Amazon CodeWhisperer, Codeium/Windsurf, Tabnine
- Sourcegraph Cody, Aider, Gemini Code Assist
- Replit AI, JetBrains AI

### ✅ COMPLETED: Phase 1 - PR Description Survey Delivery

**Changes Made:**
- Created `apps/integrations/services/github_pr_description.py`
- Implemented survey section builder with HTML comment markers
- Created `update_pr_description_survey_task` Celery task
- Task auto-detects AI and uses appropriate template
- Templates for both normal PRs and AI-detected PRs

### ✅ COMPLETED: Phase 2 - One-Click Voting System

**Changes Made:**
- Updated `record_author_response()` to accept `response_source` parameter (defaults to "web")
- Updated `record_reviewer_response()` to accept `response_source` parameter (defaults to "web")
- Added new `record_reviewer_quality_vote()` function for one-click quality-only votes
- Modified `survey_author` view to handle `?vote=yes/no` query parameter
- Modified `survey_reviewer` view to handle `?vote=1/2/3` query parameter
- One-click votes set `response_source='github'`
- One-click votes redirect to existing `complete.html` thank you page
- Added 18 unit tests for one-click voting views

### ✅ COMPLETED: Phase 3 - Slack Fallback Integration

**Changes Made:**
- Created `schedule_slack_survey_fallback_task` Celery task with 1-hour countdown
- Updated `update_pr_description_survey_task` to schedule Slack fallback on success
- Updated `send_pr_surveys_task` to use existing surveys (get_or_create pattern)
- Updated Slack interaction handler to set `response_source='slack'`
- Skip logic: authors with auto-detected AI or GitHub responses are skipped
- Skip logic: reviewers who responded via GitHub are skipped
- Added 10 new tests for fallback task and skip logic

### ✅ COMPLETED: Phase 4 - Dashboard Metrics

**Changes Made (this session):**
- Added `get_response_channel_distribution()` - survey responses by channel with counts/percentages
- Added `get_ai_detection_metrics()` - auto-detected vs self-reported AI usage stats
- Added `get_response_time_metrics()` - average response times by channel (hours from PR merge)
- Extracted `_filter_by_date_range()` helper function (reusable across all metrics)
- Extracted `_calculate_average_response_times()` helper function
- Added 3 new HTMX card views: `survey_channel_distribution_card`, `survey_ai_detection_card`, `survey_response_time_card`
- Added 3 new URL routes for HTMX endpoints
- Created 3 new template partials in `templates/metrics/partials/`
- Added "Survey Analytics" section to CTO Overview dashboard
- **53 new tests** for dashboard channel metrics (TDD)

---

## Key Files Created/Modified This Session (Phase 4)

### Dashboard Service
| File | Change |
|------|--------|
| `apps/metrics/services/dashboard_service.py` | Added 3 new functions + 2 helper functions |

### Views
| File | Change |
|------|--------|
| `apps/metrics/views/chart_views.py` | Added 3 new card views |
| `apps/metrics/views/__init__.py` | Exported new views |

### URLs
| File | Change |
|------|--------|
| `apps/metrics/urls.py` | Added 3 new URL routes |

### Templates
| File | Purpose |
|------|---------|
| `templates/metrics/partials/survey_channel_distribution_card.html` | Response channel breakdown |
| `templates/metrics/partials/survey_ai_detection_card.html` | AI detection vs self-reported stats |
| `templates/metrics/partials/survey_response_time_card.html` | Response times by channel |
| `templates/metrics/cto_overview.html` | Added "Survey Analytics" section |

### Tests
| File | Tests | Purpose |
|------|-------|---------|
| `apps/metrics/tests/dashboard/test_channel_metrics.py` | 53 | Response channel, AI detection, response time metrics |

---

## Testing Status

| Test File | Tests | Status |
|-----------|-------|--------|
| `apps/metrics/tests/models/test_survey.py` | 52 | ✅ Passing |
| `apps/integrations/tests/test_ai_detection.py` | 44 | ✅ Passing |
| `apps/metrics/tests/test_survey_service.py` | 30 | ✅ Passing |
| `apps/integrations/tests/test_github_pr_description.py` | 21 | ✅ Passing |
| `apps/web/tests/test_survey_views.py` | 61 | ✅ Passing |
| `apps/integrations/tests/test_slack_tasks.py` | 22 | ✅ Passing |
| `apps/integrations/tests/test_slack_interactions.py` | 20 | ✅ Passing |
| `apps/metrics/tests/dashboard/test_channel_metrics.py` | 53 | ✅ Passing |
| **Total Survey-Related** | **~300** | ✅ Passing |

### Verify All Tests Command

```bash
.venv/bin/pytest apps/metrics/tests/dashboard/test_channel_metrics.py apps/integrations/tests/test_ai_detection.py apps/metrics/tests/models/test_survey.py apps/metrics/tests/test_survey_service.py apps/integrations/tests/test_github_pr_description.py apps/web/tests/test_survey_views.py apps/integrations/tests/test_slack_tasks.py apps/integrations/tests/test_slack_interactions.py -v
```

---

## Migrations

| Migration | App | Status |
|-----------|-----|--------|
| `0013_add_survey_response_source_fields.py` | metrics | ✅ Created (needs apply) |
| `0014_add_auto_response_source.py` | metrics | ✅ Created (needs apply) |

### Apply Migrations

```bash
make migrate
```

---

## Dashboard Metrics API

### get_response_channel_distribution(team, start_date, end_date)

Returns survey response counts by channel:
```python
{
    "author_responses": {"github": 10, "slack": 5, "web": 2, "auto": 8},
    "reviewer_responses": {"github": 15, "slack": 8, "web": 3},
    "author_percentages": {"github": Decimal("40.00"), ...},
    "reviewer_percentages": {"github": Decimal("57.69"), ...}
}
```

### get_ai_detection_metrics(team, start_date, end_date)

Returns AI detection stats:
```python
{
    "auto_detected_count": 8,
    "self_reported_count": 12,
    "not_ai_count": 15,
    "no_response_count": 5,
    "total_surveys": 40,
    "auto_detection_rate": Decimal("40.00"),  # % of AI PRs auto-detected
    "ai_usage_rate": Decimal("50.00")  # % of all PRs that used AI
}
```

### get_response_time_metrics(team, start_date, end_date)

Returns response times in hours:
```python
{
    "author_avg_response_time": Decimal("4.50"),
    "reviewer_avg_response_time": Decimal("3.25"),
    "by_channel": {
        "author": {"github": Decimal("2.00"), "slack": Decimal("6.00"), "web": Decimal("8.00")},
        "reviewer": {"github": Decimal("1.50"), "slack": Decimal("5.00"), "web": Decimal("7.50")}
    },
    "total_author_responses": 25,
    "total_reviewer_responses": 38
}
```

---

## Key Decisions Made

1. **PR Description Instead of Comment** - Always visible, doesn't add noise
2. **AI Co-Author Auto-Detection** - Reduces survey fatigue, more accurate data
3. **Centralized Pattern List** - Easy to add new AI tools in one place
4. **HTML Comment Markers** - Invisible to users, identifies section for updates
5. **"auto" Response Source** - Track auto-detection rate separately
6. **1-Hour Slack Delay** - Gives users time to respond via GitHub first
7. **TDD for Phase 4** - 53 tests written before implementation
8. **Decimal for Percentages** - Consistent with existing dashboard code

---

## Commits Made This Session

1. `59fc6a9` - Add Phase 4 dashboard metrics for survey improvements
   - 53 new tests (TDD)
   - 3 new service functions
   - 3 new views + URLs
   - 3 new templates
   - CTO Overview dashboard updated

---

## Remaining Work

### Manual Testing Checklist (from tasks.md)
- [ ] PR merge triggers description update
- [ ] AI co-authored commit auto-detected
- [ ] Click vote link → OAuth → Thank you page
- [ ] Verify Slack not sent if already responded
- [ ] Test vote change functionality
- [ ] Test mobile responsiveness

### Definition of Done
- [x] All tests passing
- [ ] Code reviewed
- [ ] Migration tested on staging
- [ ] Documentation updated
- [ ] Survey response rate measured (baseline + after)
- [ ] PR description update works in real repo

---

## Verify Before Next Session

```bash
make test                    # All tests pass (~2000 tests)
make ruff                    # Code formatted
make migrations              # No missing migrations
```

---

## Related Documentation

- Plan: `survey-improvements-plan.md`
- Tasks: `survey-improvements-tasks.md`
- PRD: `prd/PRD-MVP.md` (Section 4, Features)
