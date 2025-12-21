# Real Project Seeding - Context

**Last Updated:** 2025-12-21 (Session 2)

## Status: COMPLETE - All bugs fixed, tests passing, seeding works

Feature is fully implemented and tested. End-to-end seeding works successfully with real GitHub data.

## Key Files

### Files Created
| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/seeding/github_authenticated_fetcher.py` | Authenticated GitHub API fetcher with parallel fetching | ✅ |
| `apps/metrics/seeding/real_projects.py` | Project configurations (PostHog, Polar, FastAPI) | ✅ |
| `apps/metrics/seeding/jira_simulator.py` | Simulates Jira issues from PR data | ✅ |
| `apps/metrics/seeding/survey_ai_simulator.py` | Simulates surveys and AI usage | ✅ |
| `apps/metrics/seeding/real_project_seeder.py` | Main orchestrator class | ✅ |
| `apps/metrics/management/commands/seed_real_projects.py` | Management command | ✅ |
| `apps/metrics/tests/test_real_project_seeding.py` | TDD tests for seeding (6 tests) | ✅ NEW |
| `scripts/seed_with_progress.py` | Progress tracking script with resume | ✅ NEW |

### Files Modified
| File | Changes |
|------|---------|
| `.env.example` | Added `GITHUB_SEEDING_TOKEN` |
| `.env` | User added their GitHub PAT |
| `dev/DEV-ENVIRONMENT.md` | Added real project seeding documentation |
| `apps/metrics/seeding/__init__.py` | Added exports for new modules |
| `apps/metrics/seeding/deterministic.py` | Added `random()` method |

## Session 2 Bug Fixes (TDD Approach)

This session focused on testing the seeding and fixing all bugs using TDD.

### Bugs Fixed
| Bug | Fix | File |
|-----|-----|------|
| `FetchedFile.changes` AttributeError | Compute from `additions + deletions` | `real_project_seeder.py:411-412` |
| `FetchedCheckRun.github_id` missing | Added `github_id` field to dataclass | `github_authenticated_fetcher.py:77` |
| `FetchedCheckRun.duration_seconds` missing | Compute from timestamps | `real_project_seeder.py:436-438` |
| `timezone.utc` not in Django | Changed to `datetime.UTC` | `jira_simulator.py:18, 175` |
| JiraIssue field mismatches | Fixed: `issue_key`→`jira_key`, `resolution_date`→`resolved_at`, removed non-existent fields | `jira_simulator.py:280-293` |
| `DeterministicRandom.random()` missing | Added `random()` method | `deterministic.py:75-81` |
| `TeamMember.pr_reviews` wrong | Changed to `reviews_given` | `real_project_seeder.py:525` |
| `WeeklyMetrics.lines_deleted` wrong | Changed to `lines_removed` | `real_project_seeder.py:645, 658` |

### TDD Tests Created
- `test_fetched_file_has_correct_fields` - Verifies FetchedFile dataclass fields
- `test_fetched_file_changes_computed_from_additions_deletions` - Validates computed changes
- `test_fetched_check_run_has_correct_fields` - Verifies FetchedCheckRun dataclass fields
- `test_fetched_check_run_duration_computed` - Validates duration computation
- `test_create_pr_files_uses_computed_changes` - Integration test for PRFile creation
- `test_create_pr_check_runs_uses_computed_duration` - Integration test for PRCheckRun creation

## Implementation Details

### GitHubAuthenticatedFetcher (`github_authenticated_fetcher.py`)
- Uses PyGithub with PAT for 5000 req/hour
- Parallel fetching with `ThreadPoolExecutor(max_workers=10)`
- Fetches PRs with: commits, reviews, files, check_runs
- Dataclasses: `FetchedPRFull`, `FetchedCommit`, `FetchedReview`, `FetchedFile`, `FetchedCheckRun`, `ContributorInfo`
- Jira key extraction from PR titles and branch names
- Uses `datetime.UTC` for timezone-aware timestamps

### JiraIssueSimulator (`jira_simulator.py`)
- Extracts Jira keys from PR title/branch (regex: `[A-Z][A-Z0-9]+-\d+`)
- Generates synthetic keys if none found (e.g., `POST-1001`)
- Story points based on PR size: <50 lines = 1pt, <150 = 2pt, <400 = 3pt, <800 = 5pt, else 8pt
- Sprint assignment based on PR dates (2-week sprints)
- Uses correct JiraIssue model fields: `jira_key`, `jira_id`, `resolved_at`

### SurveyAISimulator (`survey_ai_simulator.py`)
- AI probability calculation: base rate + size modifier + file type modifier
- Quality ratings: 50% "Super", 35% "OK", 15% "Could be better"
- Reviewer accuracy: 60-75% correct AI guesses
- AI sources: 70% Copilot, 30% Cursor

### RealProjectSeeder (`real_project_seeder.py`)
- Orchestrates all components
- Creates team, members, PRs, reviews, commits, files, check runs
- Simulates Jira issues, surveys, AI usage
- Calculates WeeklyMetrics aggregates
- Transaction-wrapped for atomicity
- Computes derived fields: `changes = additions + deletions`, `duration_seconds` from timestamps

## Command Usage

```bash
# List available projects
python manage.py seed_real_projects --list-projects

# Seed specific project
python manage.py seed_real_projects --project posthog

# Seed with custom options
python manage.py seed_real_projects --project posthog --max-prs 50 --max-members 5 --days-back 30

# Clear and reseed
python manage.py seed_real_projects --project polar --clear

# Use progress tracking script
python scripts/seed_with_progress.py --project posthog --max-prs 50 --clear

# Resume from checkpoint if interrupted
python scripts/seed_with_progress.py --resume
```

## Verified Working

Seeding tested successfully:
```
PostHog Analytics seeded successfully!
  Team members: 2
  Pull requests: 1-3
  Reviews: 0-1
  Commits: 1-7
  Files: 3-5
  Check runs: 132-455
  Jira issues: 1-3
  Surveys: 1-2
  Survey reviews: 0-1
  AI usage records: 9-18
  Weekly metrics: 1-2
```

## Django-Specific Notes

- **No migrations needed**: All models already exist
- **No new views/URLs**: This is a management command only
- **Factories used**: Uses existing factories from `apps/metrics/factories.py`
- **Test database**: Tests use `--keepdb` flag

## Uncommitted Changes

All changes are uncommitted. To commit:

```bash
git add apps/metrics/seeding/
git add apps/metrics/management/commands/seed_real_projects.py
git add apps/metrics/tests/test_real_project_seeding.py
git add scripts/seed_with_progress.py
git add .env.example
git add dev/

git commit -m "Add real project seeding from GitHub (PostHog, Polar, FastAPI)

- Fetch real PRs, commits, reviews, files, check runs from GitHub API
- Simulate Jira issues, surveys, AI usage from PR data
- TDD tests for dataclass mappings (6 tests)
- Progress tracking script with resume capability
- Supports PostHog, Polar.sh, and FastAPI projects"
```

## Verification Commands

```bash
# Verify tests pass
.venv/bin/python manage.py test apps.metrics.tests.test_real_project_seeding --keepdb

# Test command
python manage.py seed_real_projects --list-projects

# Run actual seeding
python manage.py seed_real_projects --project posthog --max-prs 10

# Check for lint issues
make ruff
```

## Session Notes

### 2025-12-21 (Session 2)
- Fixed 8 bugs discovered during end-to-end testing
- Created 6 TDD tests covering dataclass field mappings
- All tests passing
- End-to-end seeding works successfully
- Created progress tracking script with resume capability
- Linter auto-fixed: `datetime.timezone.utc` → `datetime.UTC`
