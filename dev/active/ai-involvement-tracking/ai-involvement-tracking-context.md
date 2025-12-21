# AI Involvement Tracking - Context

**Last Updated:** 2025-12-21 (Session 2)

## Status: PHASES 1-4 COMPLETE

Phase 1 (database schema), Phase 2 (AI detector), and Phase 4 (seeder integration) are complete.
Only Phase 5 (dashboard integration) remains.

---

## Implementation Progress

### Completed This Session
1. **AI Detector Service** - Created with TDD (38 tests passing)
   - `apps/metrics/services/ai_detector.py` - Detection functions
   - `apps/metrics/services/ai_patterns.py` - Configurable patterns registry
   - `apps/metrics/tests/test_ai_detector.py` - Comprehensive tests

2. **Model Fields Added** (migration applied)
   - `PullRequest`: `body`, `is_ai_assisted`, `ai_tools_detected`
   - `PRReview`: `body`, `is_ai_review`, `ai_reviewer_type`
   - `Commit`: `is_ai_assisted`, `ai_co_authors`
   - Migration: `apps/metrics/migrations/0012_add_ai_tracking_fields.py`

3. **Factories Updated**
   - `PullRequestFactory`: Added `body`, `is_ai_assisted`, `ai_tools_detected`
   - `PRReviewFactory`: Added `body`, `is_ai_review`, `ai_reviewer_type`
   - `CommitFactory`: Added `is_ai_assisted`, `ai_co_authors`

4. **Seeder Integration** - AI detection integrated into real project seeder
   - `apps/metrics/seeding/real_project_seeder.py` - Updated to detect AI
   - PRs: `detect_ai_in_text()` on body/title
   - Reviews: `detect_ai_reviewer()` on reviewer username
   - Commits: `parse_co_authors()` on commit message
   - Stats tracking: ai_assisted_prs, ai_reviews, ai_commits

### Remaining
- **Phase 5: Dashboard Integration** - Add AI metrics to CTO dashboard

---

## Key Files Created/Modified This Session

| File | Action | Purpose |
|------|--------|---------|
| `apps/metrics/services/__init__.py` | Created | Service package |
| `apps/metrics/services/ai_detector.py` | Created | AI detection functions |
| `apps/metrics/services/ai_patterns.py` | Created | Extensible patterns registry with versioning |
| `apps/metrics/tests/test_ai_detector.py` | Created | 38 TDD tests for detector |
| `apps/metrics/tests/test_ai_model_fields.py` | Created | 16 tests for model fields |
| `apps/metrics/models.py` | Modified | Added AI tracking fields |
| `apps/metrics/factories.py` | Modified | Added factory defaults |
| `apps/metrics/migrations/0012_add_ai_tracking_fields.py` | Created | Schema migration |

---

## Key Decisions Made This Session

### 1. Pattern Registry Architecture
**Decision:** Separate `ai_patterns.py` file with versioning
**Rationale:**
- Easy to extend without touching detection logic
- Version tracking enables selective historical reprocessing
- Clear documentation for each pattern

### 2. Pattern Versioning
**Decision:** Added `PATTERNS_VERSION = "1.0.0"` to track pattern changes
**Rationale:**
- User requested ability to reprocess historical data when patterns change
- Version stored with detections allows selective reprocessing

### 3. Extended Bot List
**Decision:** Expanded AI reviewer bots to include:
- CodeRabbit, Copilot, Dependabot, Renovate, Snyk, SonarCloud, Codecov, Linear, Vercel, GitHub Actions
**Rationale:** Cover all common automation bots in modern dev workflows

---

## AI Detection Patterns (Final Implementation)

### Reviewer Bots
Located in `apps/metrics/services/ai_patterns.py`:
- 15+ bot usernames mapped to AI tool types
- Case-insensitive matching

### Text Signatures
- Claude Code, Copilot, Cursor, Cody, Windsurf, Tabnine, CodeWhisperer, Amazon Q, Aider
- Generic: "AI-generated", "AI-assisted", "LLM-generated"

### Co-Author Patterns
- Claude (all variants), Copilot, Cursor, Cody, Windsurf, Aider
- Email domain matching (anthropic.com, github.com, cursor.sh, sourcegraph.com)

---

## Data Flow (Updated)

```
GitHub API
    │
    ▼
GitHubAuthenticatedFetcher
    │ (already captures body, author, message)
    ▼
RealProjectSeeder._create_single_pr()  ← NEXT TO UPDATE
    │
    ├─► ai_detector.detect_ai_reviewer(reviewer_login)
    ├─► ai_detector.detect_ai_in_text(pr_body + pr_title)
    └─► ai_detector.parse_co_authors(commit_message)
    │
    ▼
Database (PullRequest.is_ai_assisted, PRReview.is_ai_review, etc.)
    │
    ▼
Dashboard (Phase 5 - future)
```

---

## Test Commands

```bash
# Run all AI-related tests (54 tests)
.venv/bin/python manage.py test apps.metrics.tests.test_ai_detector apps.metrics.tests.test_ai_model_fields --keepdb

# Run just detector tests (38 tests)
.venv/bin/python manage.py test apps.metrics.tests.test_ai_detector --keepdb

# Run just model field tests (16 tests)
.venv/bin/python manage.py test apps.metrics.tests.test_ai_model_fields --keepdb

# Apply migrations (already done)
.venv/bin/python manage.py migrate metrics

# Check for new migrations needed
.venv/bin/python manage.py makemigrations --check
```

---

## Next Steps (Seeder Integration)

### 1. Update `_create_single_pr()` in `real_project_seeder.py`

```python
# Import at top of file
from apps.metrics.services.ai_detector import detect_ai_in_text, detect_ai_reviewer, parse_co_authors

# In _create_single_pr() - after creating PR factory:
# Detect AI in PR body/title
ai_text_result = detect_ai_in_text(f"{pr_data.title}\n{pr_data.body or ''}")
pr.body = pr_data.body or ""
pr.is_ai_assisted = ai_text_result["is_ai_assisted"]
pr.ai_tools_detected = ai_text_result["ai_tools"]
pr.save()
```

### 2. Update review creation
```python
# When creating reviews
ai_reviewer = detect_ai_reviewer(review_data.reviewer_login)
PRReviewFactory(
    ...
    body=review_data.body or "",
    is_ai_review=ai_reviewer["is_ai"],
    ai_reviewer_type=ai_reviewer["ai_type"],
)
```

### 3. Update commit creation
```python
# When creating commits
co_authors = parse_co_authors(commit_data.message)
CommitFactory(
    ...
    is_ai_assisted=co_authors["has_ai_co_authors"],
    ai_co_authors=co_authors["ai_co_authors"],
)
```

---

## Session Notes

### 2025-12-21 (Session 1 - Planning)
- Researched current data capture in GitHub fetcher
- Found that PR body and review body are captured but not stored
- Designed AI detection approach with patterns
- Created comprehensive implementation plan

### 2025-12-21 (Session 2 - Implementation)
- Implemented Phase 2 (AI Detector) with TDD - 38 tests
- Implemented Phase 1 (Model Fields) with TDD - 16 tests
- Created configurable patterns registry with versioning
- Applied migration 0012_add_ai_tracking_fields
- Started Phase 4 (Seeder Integration) - IN PROGRESS
- **Stopping point:** Reading `real_project_seeder.py:354` to update `_create_single_pr()`
