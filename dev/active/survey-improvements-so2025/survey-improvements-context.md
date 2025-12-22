# Survey Improvements - Context Document

**Last Updated: 2025-12-22 (Session 4 - Phase 3 Complete)**

## Project Context

This feature enhances the PR survey system with **PR description-based voting** (not comments), **one-click voting**, **AI auto-detection**, and **Slack fallback**, informed by the Stack Overflow 2025 Developer Survey AI section. The goal is to capture more nuanced data about AI tool usage while maximizing response rates through frictionless voting directly from GitHub.

---

## Implementation Status

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

**How One-Click Voting Works:**
1. PR description contains links like `/survey/TOKEN/author/?vote=yes`
2. User clicks link → GitHub OAuth authenticates user
3. View checks `?vote=` parameter → Records vote with `response_source='github'`
4. Redirects to thank you page

**Visual Testing:**
- Tested complete page on mobile (375x667), tablet (768x1024), desktop (1920x1080)
- Design follows Easy Eyes Dashboard color scheme
- Responsive layout works across all device sizes

### ✅ COMPLETED: Phase 3 - Slack Fallback Integration

**Changes Made:**
- Created `schedule_slack_survey_fallback_task` Celery task with 1-hour countdown
- Updated `update_pr_description_survey_task` to schedule Slack fallback on success
- Updated `send_pr_surveys_task` to use existing surveys (get_or_create pattern)
- Updated Slack interaction handler to set `response_source='slack'`
- Skip logic verified: authors with auto-detected AI or GitHub responses are skipped
- Skip logic verified: reviewers who responded via GitHub are skipped
- Added 10 new tests for fallback task and skip logic

**How Slack Fallback Works:**
1. PR merges → `update_pr_description_survey_task` runs
2. PR description updated with survey links
3. `schedule_slack_survey_fallback_task` scheduled with 1-hour countdown
4. After 1 hour → `send_pr_surveys_task` runs
5. Task checks for existing responses (GitHub one-click or auto-detected)
6. Skips users who already responded, sends Slack DM to others

---

## Key Files Created/Modified This Session

### AI Detection Service
| File | Purpose |
|------|---------|
| `apps/integrations/services/ai_detection.py` | Centralized AI co-author detection patterns |
| `apps/integrations/tests/test_ai_detection.py` | 44 unit tests for detection |

### PR Description Service
| File | Purpose |
|------|---------|
| `apps/integrations/services/github_pr_description.py` | PR description update with survey links |
| `apps/integrations/tests/test_github_pr_description.py` | 21 unit tests for PR descriptions |

### Survey Service
| File | Change |
|------|--------|
| `apps/metrics/services/survey_service.py` | Added `_detect_ai_in_pr_commits()` integration |
| `apps/metrics/tests/test_survey_service.py` | Added 7 AI auto-detection tests |

### Celery Tasks
| File | Change |
|------|--------|
| `apps/integrations/tasks.py` | Added `update_pr_description_survey_task` |

### Models
| File | Change |
|------|--------|
| `apps/metrics/models/surveys.py` | Added "auto" to `RESPONSE_SOURCE_CHOICES` |
| `apps/metrics/migrations/0014_add_auto_response_source.py` | Migration for "auto" choice |

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
| **Total** | **245** | ✅ Passing |

### Verify All Tests Command

```bash
.venv/bin/pytest apps/integrations/tests/test_ai_detection.py apps/metrics/tests/models/test_survey.py apps/metrics/tests/test_survey_service.py apps/integrations/tests/test_github_pr_description.py apps/web/tests/test_survey_views.py apps/integrations/tests/test_slack_tasks.py apps/integrations/tests/test_slack_interactions.py -v
```

---

## Migrations

| Migration | App | Status |
|-----------|-----|--------|
| `0013_add_survey_response_source_fields.py` | metrics | Created |
| `0014_add_auto_response_source.py` | metrics | Created |

### Apply Migrations

```bash
make migrate
```

---

## PR Description Survey Format

### Normal PR (Author + Reviewers)

```markdown
<!-- tformance-survey-start -->

---

### tformance Survey

**@author** - Was this PR AI-assisted?
> [Yes](https://app.example.com/survey/TOKEN/author?vote=yes) | [No](https://app.example.com/survey/TOKEN/author?vote=no)

**Reviewers** - Rate this code:
> [Could be better](https://app.example.com/survey/TOKEN/review?vote=1) | [OK](https://app.example.com/survey/TOKEN/review?vote=2) | [Super](https://app.example.com/survey/TOKEN/review?vote=3)
<!-- tformance-survey-end -->
```

### AI-Detected PR (Reviewers Only)

```markdown
<!-- tformance-survey-start -->

---

### tformance Survey

**AI-assisted PR detected**

**Reviewers** - Rate this code:
> [Could be better](https://app.example.com/survey/TOKEN/review?vote=1) | [OK](https://app.example.com/survey/TOKEN/review?vote=2) | [Super](https://app.example.com/survey/TOKEN/review?vote=3)
<!-- tformance-survey-end -->
```

---

## Key Decisions Made

1. **PR Description Instead of Comment** - Always visible, doesn't add noise
2. **AI Co-Author Auto-Detection** - Reduces survey fatigue, more accurate data
3. **Centralized Pattern List** - Easy to add new AI tools in one place
4. **HTML Comment Markers** - Invisible to users, identifies section for updates
5. **"auto" Response Source** - Track auto-detection rate separately

---

## Next Steps (Handoff Notes)

### Immediate Next Task: Phase 4 - Dashboard Metrics

1. Add `get_response_channel_distribution()` to dashboard_service
2. Track percentage of PRs with AI auto-detected
3. Compare auto-detected vs self-reported AI usage
4. Calculate response time by channel (GitHub vs Slack)
5. Create dashboard visualizations for survey metrics

---

## Uncommitted Changes

### New Files
- `apps/integrations/services/ai_detection.py`
- `apps/integrations/tests/test_ai_detection.py`
- `apps/integrations/services/github_pr_description.py`
- `apps/integrations/tests/test_github_pr_description.py`
- `apps/metrics/migrations/0013_add_survey_response_source_fields.py`
- `apps/metrics/migrations/0014_add_auto_response_source.py`

### Modified Files
- `apps/metrics/models/surveys.py` (added "auto" choice, response source fields)
- `apps/metrics/tests/models/test_survey.py` (added response source tests)
- `apps/metrics/services/survey_service.py` (added AI detection, response_source params)
- `apps/metrics/tests/test_survey_service.py` (added 9 tests for response_source)
- `apps/integrations/tasks.py` (added `schedule_slack_survey_fallback_task`, integrated with PR description task)
- `apps/integrations/webhooks/slack_interactions.py` (added `response_source='slack'`)
- `apps/integrations/tests/test_slack_tasks.py` (added 10 tests for fallback + skip logic)
- `apps/integrations/tests/test_slack_interactions.py` (added 2 tests for response_source)
- `apps/web/views.py` (added one-click voting to survey_author and survey_reviewer)
- `apps/web/tests/test_survey_views.py` (added 18 one-click voting tests)
- `dev/active/survey-improvements-so2025/survey-improvements-context.md`
- `dev/active/survey-improvements-so2025/survey-improvements-tasks.md`

### Verify Before Commit

```bash
make test                    # All tests pass
make ruff                    # Code formatted
make migrations              # No missing migrations
```

---

## Related Documentation

- Plan: `survey-improvements-plan.md`
- Tasks: `survey-improvements-tasks.md`
- PRD: `prd/PRD-MVP.md` (Section 4, Features)
