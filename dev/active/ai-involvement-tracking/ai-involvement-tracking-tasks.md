# AI Involvement Tracking - Tasks

**Last Updated:** 2025-12-21 (Session 2)

## Progress Overview

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Database Schema | ✅ Complete | 3/3 |
| Phase 2: AI Detection Module | ✅ Complete | 2/2 |
| Phase 3: GitHub Fetcher Updates | ✅ Verified | 1/1 |
| Phase 4: Seeder Integration | ✅ Complete | 2/2 |
| Phase 5: Dashboard Integration | 🔲 Not Started | 0/2 |

---

## Phase 1: Database Schema Changes ✅ COMPLETE

### 1.1 Add AI fields to PullRequest model ✅
- [x] Add `body` TextField (store PR description)
- [x] Add `is_ai_assisted` BooleanField (default=False)
- [x] Add `ai_tools_detected` JSONField (default=list)
- [x] Update PullRequestFactory with new fields
- [x] Write test for new fields

### 1.2 Add AI fields to PRReview model ✅
- [x] Add `body` TextField (store review content)
- [x] Add `is_ai_review` BooleanField (default=False)
- [x] Add `ai_reviewer_type` CharField (max_length=50, blank=True)
- [x] Update PRReviewFactory with new fields
- [x] Write test for new fields

### 1.3 Add AI fields to Commit model ✅
- [x] Add `is_ai_assisted` BooleanField (default=False)
- [x] Add `ai_co_authors` JSONField (default=list)
- [x] Update CommitFactory with new fields
- [x] Write test for new fields
- [x] Create and run migration (`0012_add_ai_tracking_fields.py`)

---

## Phase 2: AI Detection Module ✅ COMPLETE

### 2.1 Create AI detector service (TDD) ✅
- [x] Create test file `apps/metrics/tests/test_ai_detector.py`
- [x] Write failing tests for `detect_ai_reviewer(username)` - 14 tests
- [x] Write failing tests for `detect_ai_in_text(text)` - 11 tests
- [x] Write failing tests for `parse_co_authors(message)` - 13 tests
- [x] Create `apps/metrics/services/ai_detector.py`
- [x] Implement `detect_ai_reviewer()` to pass tests
- [x] Implement `detect_ai_in_text()` to pass tests
- [x] Implement `parse_co_authors()` to pass tests

### 2.2 AI patterns registry ✅
- [x] Create `apps/metrics/services/ai_patterns.py`
- [x] Define AI_REVIEWER_BOTS dict (15+ bots)
- [x] Define AI_SIGNATURE_PATTERNS list (20+ patterns)
- [x] Define AI_CO_AUTHOR_PATTERNS list (12+ patterns)
- [x] Add docstrings explaining each pattern
- [x] Make patterns case-insensitive
- [x] Add PATTERNS_VERSION for historical reprocessing

---

## Phase 3: GitHub Fetcher Updates ✅ VERIFIED

### 3.1 Add PR comments fetching (DEFERRED)
- [ ] Add `FetchedComment` dataclass
- [ ] Add `_fetch_issue_comments()` method
- [ ] Add `comments` to `FetchedPRFull`
- [ ] Write tests for comment fetching
- **Note:** Deferred - CodeRabbit detection can use reviewer username

### 3.2 Verify existing data capture ✅
- [x] Confirm review body is captured (`FetchedReview.body`)
- [x] Confirm commit message is captured (`FetchedCommit.message`)
- [x] Confirm PR body is captured (`FetchedPRFull.body`)
- [x] **Result:** All data already captured, no changes needed

---

## Phase 4: Seeder Integration ✅ COMPLETE

### 4.1 Store body fields in seeder ✅
- [x] Store `pr_data.body` in PullRequest.body
- [x] Store `review_data.body` in PRReview.body
- [ ] Write integration test (deferred)

### 4.2 Run AI detection in seeder ✅
- [x] Import ai_detector service
- [x] Call `detect_ai_reviewer()` when creating reviews
- [x] Call `detect_ai_in_text()` on PR body/title
- [x] Call `parse_co_authors()` on commit messages
- [x] Store results in model fields
- [x] Track AI detection statistics (ai_assisted_prs, ai_reviews, ai_commits)
- [ ] Write integration test (deferred)

---

## Phase 5: Dashboard Integration 🔲 NOT STARTED

### 5.1 Add AI metrics to team dashboard
- [ ] Query AI-assisted PR count
- [ ] Query AI review count
- [ ] Display AI tool breakdown chart
- [ ] Add AI involvement trend line
- [ ] Write view tests

### 5.2 Add AI indicators to PR views
- [ ] Add AI badge component
- [ ] Show badge on AI-assisted PRs
- [ ] Show AI reviewer indicator on reviews
- [ ] Add filter for AI involvement
- [ ] Write template tests

---

## Verification Checklist

Before marking complete:
- [x] All tests pass: `make test ARGS='apps.metrics.tests.test_ai_detector apps.metrics.tests.test_ai_model_fields'`
- [x] Migrations applied: `make migrate`
- [ ] Ruff passes: `make ruff`
- [ ] Demo seeding works with AI detection
- [ ] Dashboard shows AI metrics

---

## Notes

- Follow TDD: Write tests FIRST, then implementation ✅
- Use `JSONField` for lists (ai_tools_detected, ai_co_authors) ✅
- Make AI patterns case-insensitive ✅
- Add pattern versioning for historical reprocessing ✅
- Log AI detection for debugging (TODO in seeder)
- Consider false positive mitigation (exact username matching prevents most)

---

## Session Log

### 2025-12-21 (Session 1 - Planning)
- Created implementation plan
- Identified gap: PR comments not captured (CodeRabbit)
- Ready for Phase 1 implementation

### 2025-12-21 (Session 2 - Implementation)
- ✅ Completed Phase 2: AI Detector with TDD (38 tests)
- ✅ Completed Phase 1: Model fields and migration (16 tests)
- ✅ Verified Phase 3: GitHub fetcher already captures needed data
- ✅ Completed Phase 4: Seeder integration

### Next Session Tasks
1. ✅ ~~Import `ai_detector` functions in `real_project_seeder.py`~~
2. ✅ ~~Update `_create_single_pr()` to detect AI in PR body/title~~
3. ✅ ~~Update review creation to detect AI reviewers~~
4. ✅ ~~Update commit creation to detect AI co-authors~~
5. ✅ ~~Track AI detection statistics~~
6. Run full seeding to verify AI detection works
7. Implement Phase 5: Dashboard integration
