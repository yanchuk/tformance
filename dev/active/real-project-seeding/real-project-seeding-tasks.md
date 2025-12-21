# Real Project Seeding - Tasks

**Last Updated:** 2025-12-21 (Session 2)

## Phase 1: Authenticated GitHub Fetcher ✅ COMPLETED

- [x] Create `github_authenticated_fetcher.py`
- [x] Define `FetchedPRFull` dataclass with all PR details
- [x] Define `FetchedCommit`, `FetchedReview`, `FetchedFile`, `FetchedCheckRun` dataclasses
- [x] Define `ContributorInfo` dataclass for team member creation
- [x] Implement `GitHubAuthenticatedFetcher` class
- [x] Implement `__init__` with token from env var
- [x] Implement rate limit tracking and logging
- [x] Implement `fetch_prs_with_details(repo, since, max_prs)` method
- [x] Implement `get_top_contributors(repo, max_count, since)` method
- [x] Add error handling for rate limits and API errors
- [x] Add parallel fetching with ThreadPoolExecutor
- [x] Add `GITHUB_SEEDING_TOKEN` to `.env.example`

---

## Phase 2: Project Configuration ✅ COMPLETED

- [x] Create `real_projects.py`
- [x] Define `RealProjectConfig` dataclass
- [x] Configure PostHog project (posthog/posthog)
- [x] Configure Polar project (polarsource/polar)
- [x] Configure FastAPI project (tiangolo/fastapi)
- [x] Create `REAL_PROJECTS` registry dict
- [x] Add `get_project(name)` helper function
- [x] Add `list_projects()` helper function

---

## Phase 3: Jira Simulator ✅ COMPLETED

- [x] Create `jira_simulator.py`
- [x] Implement `JiraIssueSimulator` class
- [x] Implement Jira key extraction from PR title regex
- [x] Implement Jira key extraction from branch name
- [x] Implement synthetic key generation with counter
- [x] Implement story point estimation from PR size
- [x] Implement sprint assignment based on PR dates
- [x] Implement `create_jira_issue(team, jira_key, pr, assignee)` method

---

## Phase 4: Survey/AI Simulator ✅ COMPLETED

- [x] Create `survey_ai_simulator.py`
- [x] Implement `SurveyAISimulator` class
- [x] Implement AI-assisted probability calculation
- [x] Implement `determine_ai_assisted(pr)` method
- [x] Implement `create_survey_with_responses(team, pr, is_ai_assisted, reviewers)` method
- [x] Implement reviewer guess accuracy (60-75%)
- [x] Implement quality rating distribution (skewed positive)
- [x] Implement `generate_ai_usage_records(team, member, date_range)` method

---

## Phase 5: Seeder Orchestrator ✅ COMPLETED

- [x] Create `real_project_seeder.py`
- [x] Define `RealProjectStats` dataclass for statistics
- [x] Implement `RealProjectSeeder` class
- [x] Implement `_get_or_create_team()` method
- [x] Implement `_create_team_members(team, contributors)` method
- [x] Implement PR creation with reviews, commits, files, check runs
- [x] Implement `_simulate_jira_issues(team)` method
- [x] Implement `_simulate_surveys(team)` method
- [x] Implement `_generate_ai_usage(team)` method
- [x] Implement `_calculate_weekly_metrics(team)` method
- [x] Implement main `seed()` method with progress logging
- [x] Implement `clear_project_data()` helper function

---

## Phase 6: Management Command ✅ COMPLETED

- [x] Create `seed_real_projects.py` management command
- [x] Add `--project` argument (choices + 'all')
- [x] Add `--list-projects` argument
- [x] Add `--clear` argument
- [x] Add `--max-prs` argument
- [x] Add `--days-back` argument
- [x] Add `--seed` argument for reproducibility
- [x] Implement progress output
- [x] Implement error handling and helpful messages
- [x] Test command with --list-projects ✅

---

## Phase 7: Testing & Bug Fixes ✅ COMPLETED (Session 2)

- [x] Create TDD tests for dataclass field mappings
- [x] Fix `FetchedFile.changes` - compute from additions+deletions
- [x] Fix `FetchedCheckRun.github_id` - add to dataclass
- [x] Fix `FetchedCheckRun.duration_seconds` - compute from timestamps
- [x] Fix `timezone.utc` issues in jira_simulator.py
- [x] Fix JiraIssue field mismatches (issue_key→jira_key, etc.)
- [x] Fix `DeterministicRandom.random()` - add method
- [x] Fix `TeamMember.pr_reviews` → `reviews_given`
- [x] Fix `WeeklyMetrics.lines_deleted` → `lines_removed`
- [x] Update `dev/DEV-ENVIRONMENT.md` with usage docs
- [x] Document environment variable requirement
- [x] Document available projects and options
- [x] Run full test suite - ALL PASSING

---

## Phase 8: Progress Script ✅ COMPLETED (Session 2)

- [x] Create `scripts/seed_with_progress.py`
- [x] Add progress display with timing
- [x] Add checkpoint/resume capability
- [x] Add batch statistics output
- [x] Test script with real seeding

---

## Final Validation ✅ COMPLETED

- [x] Run `python manage.py seed_real_projects --project posthog`
- [x] Verify seeding completes without errors
- [x] Verify data created in database
- [ ] Check data in Django admin (user task)
- [ ] Verify dashboard displays data correctly (user task)
- [ ] Commit all changes (ready)

---

## Notes

- GitHub PAT is configured in `.env`
- All tests passing (6 tests)
- No migrations needed - uses existing models
- Parallel fetching uses 10 workers for performance
- Linter auto-applied `datetime.UTC` instead of `datetime.timezone.utc`
