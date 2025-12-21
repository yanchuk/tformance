# Real Project Seeding - Context

**Last Updated:** 2025-12-21 (Session 3)

## Status: COMPLETE - Ready for seeding with rate limit handling

Feature is fully implemented, tested, and has rate limit protection. User can now run seeding in a separate terminal.

## Key Files

### Files Created
| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/seeding/github_authenticated_fetcher.py` | Authenticated GitHub API fetcher with rate limit handling | ✅ |
| `apps/metrics/seeding/real_projects.py` | Project configs (Gumroad, Polar, PostHog, FastAPI) | ✅ |
| `apps/metrics/seeding/jira_simulator.py` | Simulates Jira issues from PR data | ✅ |
| `apps/metrics/seeding/survey_ai_simulator.py` | Simulates surveys and AI usage | ✅ |
| `apps/metrics/seeding/real_project_seeder.py` | Main orchestrator class | ✅ |
| `apps/metrics/management/commands/seed_real_projects.py` | Management command | ✅ |
| `apps/metrics/tests/test_real_project_seeding.py` | TDD tests for seeding (6 tests) | ✅ |
| `scripts/seed_with_progress.py` | Progress tracking script with resume | ✅ |

### Files Modified
| File | Changes |
|------|---------|
| `.env.example` | Added `GITHUB_SEEDING_TOKEN` |
| `.env` | User added their GitHub PAT |
| `dev/DEV-ENVIRONMENT.md` | Added real project seeding documentation |
| `apps/metrics/seeding/__init__.py` | Added exports for new modules |
| `apps/metrics/seeding/deterministic.py` | Added `random()` method |

## Session 3 Updates

### Added Gumroad Project
- Added `antiwork/gumroad` as new seeding target
- Full parsing mode (1000 PRs, 50 members) for Gumroad and Polar
- Sampled mode (200 PRs, 25 members) for PostHog (very active repo)

### Fixed GitHub Rate Limit (403 Errors)
User encountered 403 Forbidden errors with GitHub's secondary rate limits (abuse detection).

**Solution implemented:**
- **Batch processing**: Process PRs in batches of 10 instead of all at once
- **Batch delays**: 1 second delay between batches
- **Reduced parallelism**: MAX_WORKERS reduced from 10 to 3
- **Retry logic**: Exponential backoff (5s → 10s → 20s) for 403 errors
- **Max retries**: 3 retries before failing a batch

**Constants in `github_authenticated_fetcher.py`:**
```python
MAX_WORKERS = 3      # Parallel threads per batch
BATCH_SIZE = 10      # PRs per batch
BATCH_DELAY = 1.0    # Seconds between batches
MAX_RETRIES = 3      # Retry attempts for 403 errors
INITIAL_BACKOFF = 5.0  # Initial retry delay (doubles each retry)
```

## Project Configurations

| Project | Repo | Mode | Max PRs | Max Members | Notes |
|---------|------|------|---------|-------------|-------|
| **gumroad** | antiwork/gumroad | Full | 1000 | 50 | Complete team picture |
| **polar** | polarsource/polar | Full | 1000 | 50 | Complete team picture |
| **posthog** | posthog/posthog | Sampled | 200 | 25 | Very active repo |
| **fastapi** | tiangolo/fastapi | Sampled | 300 | 15 | Framework repo |

## Command Usage

```bash
# Run seeding with progress (in separate terminal)
GITHUB_SEEDING_TOKEN="ghp_xxx" python scripts/seed_with_progress.py --clear

# Seed specific project
GITHUB_SEEDING_TOKEN="ghp_xxx" python scripts/seed_with_progress.py --project gumroad --clear

# Resume from checkpoint if interrupted
python scripts/seed_with_progress.py --resume

# List available projects
python manage.py seed_real_projects --list-projects
```

## GitHubAuthenticatedFetcher Details

### Rate Limit Handling Flow
```
1. Fetch PRs (basic info)
2. Process PR details in batches of 10:
   a. Fetch batch with 3 parallel workers
   b. If 403 error → retry with exponential backoff
   c. Delay 1s before next batch
3. Sort results by created_at
```

### Data Fetched Per PR
- Commits (author, sha, message, additions, deletions)
- Reviews (reviewer, state, submitted_at, body)
- Files (filename, status, additions, deletions)
- Check runs (name, status, conclusion, started_at, completed_at)

## Django-Specific Notes

- **No migrations needed**: All models already exist
- **No new views/URLs**: This is a management command only
- **Factories used**: Uses existing factories from `apps/metrics/factories.py`
- **Test database**: Tests use `--keepdb` flag

## Uncommitted Changes

Files with uncommitted changes:
- `apps/metrics/seeding/real_projects.py` (added Gumroad)
- `apps/metrics/seeding/github_authenticated_fetcher.py` (rate limit handling)
- Previous session files (tests, progress script, etc.)

## Verification Commands

```bash
# Verify tests pass
.venv/bin/python manage.py test apps.metrics.tests.test_real_project_seeding --keepdb

# Test command
python manage.py seed_real_projects --list-projects

# Run actual seeding (separate terminal)
GITHUB_SEEDING_TOKEN="ghp_xxx" python scripts/seed_with_progress.py --project gumroad --max-prs 50 --clear

# Check for lint issues
make ruff
```

## Session Notes

### 2025-12-21 (Session 3)
- Added Gumroad project (antiwork/gumroad) with full parsing
- Fixed GitHub 403 rate limit errors with batch processing + retry logic
- Reduced parallel workers from 10 to 3
- Added 1s delay between batches
- Added exponential backoff retry for 403 errors

### 2025-12-21 (Session 2)
- Fixed 8 bugs discovered during end-to-end testing
- Created 6 TDD tests covering dataclass field mappings
- All tests passing
- End-to-end seeding works successfully
- Created progress tracking script with resume capability
