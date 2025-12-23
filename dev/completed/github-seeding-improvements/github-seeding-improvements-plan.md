# GitHub Seeding Improvements Plan

**Last Updated:** 2025-12-22

## Executive Summary

The GitHub demo data seeding process is hitting rate limits despite having 2 tokens (10,000 requests/hour combined). The issue is GitHub's **secondary rate limit** (abuse detection) which triggers 403 errors when making too many requests in a short time window.

This plan addresses three improvements:
1. **Checkpointing** - Save progress and resume after rate limiting
2. **Secondary Rate Limit Detection** - Distinguish between primary (quota) and secondary (abuse) limits
3. **Configurable Delays** - Allow tuning of batch delays to avoid abuse detection

## Problem Analysis

### Current State

- **Token Pool**: Already supports multiple tokens (`GitHubTokenPool`)
- **Batch Processing**: Fetches PRs in batches of 10 with 1-second delay
- **Retry Logic**: Exponential backoff on 403 errors (5s → 10s → 20s)
- **Checkpoint File**: Exists (`.seeding_checkpoint.json`) but only tracks step, not PR progress

### Root Cause

With 919 PRs, each requiring ~4-5 API calls (PR details + commits + reviews + files + check runs):
- Total API calls: ~4,500
- Even with 2 tokens (10,000/hour limit), making these calls too quickly triggers GitHub's secondary rate limit
- Secondary limits return 403 with `X-RateLimit-Remaining` > 0 but include `Retry-After` header

### Current Checkpoint Content

```json
{
  "project": "gumroad",
  "step": 1,
  "started_at": "2025-12-21T22:20:40.088451",
  "options": {...}
}
```

Missing: Which PRs have been successfully fetched (needed for resume)

## Proposed Solution

### Feature 1: PR-Level Checkpointing

Save which PR numbers have been successfully fetched, allowing resume after interruption.

**Checkpoint Schema:**
```json
{
  "repo": "antiwork/gumroad",
  "fetched_pr_numbers": [1, 2, 3, ...],
  "last_updated": "2025-12-22T10:30:00Z",
  "total_prs_found": 919,
  "completed": false
}
```

### Feature 2: Secondary Rate Limit Detection

Distinguish between:
- **Primary limit**: `X-RateLimit-Remaining` = 0 → switch token
- **Secondary limit**: 403 with `Retry-After` header → pause all tokens

### Feature 3: Configurable Delays

Allow tuning via environment variables:
- `GITHUB_BATCH_SIZE`: PRs per batch (default: 10)
- `GITHUB_BATCH_DELAY`: Seconds between batches (default: 1.0)
- `GITHUB_MAX_WORKERS`: Parallel threads (default: 3)

## Implementation Phases

### Phase 1: Checkpointing (Priority: HIGH)

**Scope:** Add checkpoint save/load to `GitHubAuthenticatedFetcher`

**Changes:**
1. Add `checkpoint_file` parameter to fetcher
2. Load checkpoint on init (if exists and matches repo)
3. Skip PRs already in checkpoint
4. Save checkpoint after each batch
5. Clear checkpoint on successful completion

### Phase 2: Secondary Rate Limit Detection (Priority: MEDIUM)

**Scope:** Improve 403 handling to detect abuse limits

**Changes:**
1. Check for `Retry-After` header on 403 responses
2. Pause ALL tokens when secondary limit hit (not just current token)
3. Add logging to distinguish limit types

### Phase 3: Configurable Delays (Priority: LOW)

**Scope:** Make rate limiting parameters configurable

**Changes:**
1. Read delays from environment variables
2. Add `SeedingConfig` dataclass for configuration
3. Document configuration options

## Technical Design

### Checkpointing Implementation

```python
@dataclass
class SeedingCheckpoint:
    repo: str
    fetched_pr_numbers: list[int]
    last_updated: str
    total_prs_found: int = 0
    completed: bool = False

    def save(self, path: str) -> None:
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str, repo: str) -> 'SeedingCheckpoint':
        try:
            with open(path) as f:
                data = json.load(f)
            if data.get('repo') != repo:
                return cls(repo=repo, fetched_pr_numbers=[])
            return cls(**data)
        except (FileNotFoundError, json.JSONDecodeError):
            return cls(repo=repo, fetched_pr_numbers=[])
```

### Secondary Rate Limit Detection

```python
def is_secondary_rate_limit(exception: GithubException) -> bool:
    """Check if 403 is secondary (abuse) limit vs primary (quota) limit."""
    if exception.status != 403:
        return False
    headers = getattr(exception, 'headers', {})
    # Secondary limit has Retry-After but X-RateLimit-Remaining > 0
    return 'Retry-After' in headers
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Checkpoint file corruption | Low | Medium | JSON validation, backup before overwrite |
| Disk full during checkpoint save | Low | Low | Catch IOError, continue without checkpoint |
| Secondary limit detection wrong | Medium | Low | Log both limit types, allow manual override |
| Tests flaky with file I/O | Medium | Low | Use temp directories in tests |

## Success Metrics

1. **Checkpointing**: Seeding can resume after 403 errors without re-fetching PRs
2. **Rate Limit Detection**: Logs clearly show which type of limit was hit
3. **Configurable Delays**: `GITHUB_BATCH_DELAY=2` reduces 403 errors by 50%+

## TDD Implementation Order

Following strict Red-Green-Refactor:

1. **Checkpointing Tests** (RED)
   - `test_fetcher_accepts_checkpoint_file_parameter`
   - `test_checkpoint_saves_after_each_batch`
   - `test_checkpoint_contains_required_fields`
   - `test_fetcher_resumes_from_checkpoint`
   - `test_checkpoint_cleared_on_successful_completion`
   - `test_checkpoint_handles_missing_file`
   - `test_checkpoint_handles_corrupt_file`
   - `test_checkpoint_handles_different_repo`

2. **Checkpointing Implementation** (GREEN)
   - Add `SeedingCheckpoint` dataclass
   - Add `checkpoint_file` to `GitHubAuthenticatedFetcher.__init__`
   - Modify `fetch_prs_with_details` to use checkpoint

3. **Secondary Rate Limit Tests** (RED)
   - `test_detects_secondary_rate_limit_by_retry_after_header`
   - `test_pauses_all_tokens_on_secondary_limit`
   - `test_logs_secondary_vs_primary_limit_type`

4. **Secondary Rate Limit Implementation** (GREEN)
   - Add `is_secondary_rate_limit()` helper
   - Modify 403 handling in `_fetch_batch_with_retry`

5. **Configurable Delays Tests** (RED)
   - `test_reads_batch_delay_from_environment`
   - `test_reads_batch_size_from_environment`
   - `test_uses_default_values_when_not_configured`

6. **Configurable Delays Implementation** (GREEN)
   - Add environment variable reading
   - Replace constants with configurable values

## Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `apps/metrics/seeding/github_authenticated_fetcher.py` | Modify | Add checkpointing, improve rate limit handling |
| `apps/metrics/seeding/checkpoint.py` | Create | New `SeedingCheckpoint` dataclass |
| `apps/metrics/tests/test_github_authenticated_fetcher.py` | Modify | Add new test classes |
| `apps/metrics/seeding/real_project_seeder.py` | Modify | Pass checkpoint_file to fetcher |

## Dependencies

- No new external packages required
- Uses existing `json` standard library
- Uses existing test infrastructure
