# GitHub Seeding Improvements - Context

**Last Updated:** 2025-12-22 (Session Complete)
**Status:** IMPLEMENTATION COMPLETE

## Summary

All planned improvements to the GitHub seeding system have been implemented following TDD Red-Green-Refactor methodology. The system now supports:
1. **Checkpointing** - Resume from where we left off after rate limit interruptions
2. **Secondary Rate Limit Detection** - Properly handle GitHub's abuse detection (403 with Retry-After)
3. **Management Command Integration** - `--checkpoint-file` option for the seed command

## Files Modified This Session

| File | Changes |
|------|---------|
| `apps/metrics/seeding/checkpoint.py` | **NEW** - SeedingCheckpoint dataclass with save/load/resume |
| `apps/metrics/seeding/github_authenticated_fetcher.py` | Added `checkpoint_file` param, `is_secondary_rate_limit()`, checkpoint integration |
| `apps/metrics/seeding/real_project_seeder.py` | Added `checkpoint_file` field, passes to fetcher |
| `apps/metrics/management/commands/seed_real_projects.py` | Added `--checkpoint-file` argument |
| `apps/metrics/tests/test_github_authenticated_fetcher.py` | Added 13 new tests (27 total, all pass) |

## Key Implementations

### 1. SeedingCheckpoint Class (`checkpoint.py`)

```python
@dataclass
class SeedingCheckpoint:
    repo: str
    fetched_pr_numbers: list[int]
    last_updated: str
    total_prs_found: int = 0
    completed: bool = False

    def save(self, path) -> None
    def add_fetched_pr(self, pr_number) -> None
    def is_fetched(self, pr_number) -> bool
    def mark_completed(self, path=None) -> None
    @classmethod
    def load(cls, path, repo) -> SeedingCheckpoint
```

### 2. Secondary Rate Limit Detection

```python
def is_secondary_rate_limit(exception: GithubException) -> bool:
    """Detect GitHub abuse detection (403 with Retry-After header)."""
    if exception.status != 403:
        return False
    headers = getattr(exception, "headers", {}) or {}
    return "Retry-After" in headers
```

### 3. Usage Example

```bash
# Seed with checkpointing (default file)
python manage.py seed_real_projects --project posthog

# Custom checkpoint file
python manage.py seed_real_projects --project posthog --checkpoint-file my_checkpoint.json

# If rate limited, re-run same command - resumes automatically
```

## Test Results

All **27 tests** pass in `test_github_authenticated_fetcher.py`:
- 8 checkpointing tests (`TestGitHubFetcherCheckpointing`)
- 5 secondary rate limit tests (`TestSecondaryRateLimitDetection`)
- 14 existing tests (token pool, rotation, fetching)

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Checkpoint format | JSON dataclass | Human-readable, easy to debug |
| Resume behavior | Skip PRs in checkpoint | Avoid re-fetching completed work |
| Checkpoint location | Configurable parameter | Flexibility for different projects |
| Secondary limit handling | Wait for Retry-After | Don't waste tokens on abuse detection |
| Default checkpoint file | `.seeding_checkpoint.json` | Project root, gitignored |

## Test Patterns Used

```python
# Mock GitHub client and token pool together
@patch("apps.metrics.seeding.github_authenticated_fetcher.GitHubTokenPool")
@patch("apps.metrics.seeding.github_authenticated_fetcher.Github")
def test_feature(self, mock_github, mock_pool):
    ...

# Mock time module for sleep tests
@patch("apps.metrics.seeding.github_authenticated_fetcher.time")
def test_waits_for_retry_after(self, mock_time):
    ...

# Use temp directories for checkpoint file tests
import tempfile
with tempfile.TemporaryDirectory() as tmpdir:
    checkpoint_path = os.path.join(tmpdir, "test.json")
    ...
```

## Architecture

```
Management Command (seed_real_projects.py)
    └── RealProjectSeeder
            ├── checkpoint_file parameter
            └── GitHubAuthenticatedFetcher
                    ├── checkpoint_file parameter
                    ├── SeedingCheckpoint (load/save)
                    ├── is_secondary_rate_limit() check
                    ├── GitHubTokenPool (multi-token)
                    └── ThreadPoolExecutor (parallel)
```

## No Migrations Required

This implementation only modifies seeding/utility code, no model changes.

## Verification Commands

```bash
# Run all fetcher tests
make test ARGS='apps.metrics.tests.test_github_authenticated_fetcher --keepdb'

# Verify management command
python manage.py seed_real_projects --help | grep checkpoint

# Full test suite
make test
```

## Phase 3 (Configurable Delays) - SKIPPED

The configurable delays feature (environment variables for batch size, delay, workers) was marked as LOW priority and skipped. The current hardcoded values work well for avoiding abuse detection.

## Uncommitted Changes

The following files have modifications that should be committed:
- `apps/metrics/seeding/checkpoint.py` (NEW)
- `apps/metrics/seeding/github_authenticated_fetcher.py` (modified)
- `apps/metrics/seeding/real_project_seeder.py` (modified)
- `apps/metrics/management/commands/seed_real_projects.py` (modified)
- `apps/metrics/tests/test_github_authenticated_fetcher.py` (modified)

## Next Steps (if continuing work)

1. **Optional**: Implement Phase 3 configurable delays if needed
2. **Test in production**: Run full seeding with 2 tokens to verify improvements
3. **Clean up**: Delete `.seeding_checkpoint.json` after successful seeding

## Related Documentation

- Original problem: 403 errors with ~25 minute backoffs despite having 2 tokens
- Root cause: GitHub secondary rate limit (abuse detection) triggers regardless of quota
- Solution: Checkpointing + proper secondary limit handling
