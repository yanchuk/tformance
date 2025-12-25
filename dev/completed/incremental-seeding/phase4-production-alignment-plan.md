# Phase 4: Production Alignment Plan

## Current State Analysis

The production sync already has:
- ✅ GraphQL bulk fetching (1 call per 50 PRs vs 6-7 calls per PR with REST)
- ✅ Incremental sync (fetches only PRs updated since last_sync_at)
- ✅ Rate limit checking after each query
- ✅ Retry with exponential backoff (60s, 120s, 240s)

Missing:
- ❌ Rate limit WAIT logic (waits until reset instead of failing)
- ❌ Resume logic (tracks progress to resume from where it left off)

## 4.2 Rate Limit Wait Logic

### Problem
When rate limit is exceeded:
1. `GitHubGraphQLRateLimitError` is raised
2. Task retries with exponential backoff (60s, 120s, 240s)
3. If rate limit resets in 30+ minutes, all retries fail
4. User must manually re-trigger sync

### Solution
Wait until `resetAt` instead of failing:

```python
# In GitHubGraphQLClient._check_rate_limit()
if remaining < RATE_LIMIT_THRESHOLD:
    reset_at = datetime.fromisoformat(reset_at_str)
    wait_seconds = (reset_at - datetime.now(timezone.utc)).total_seconds()

    if wait_seconds > 0 and wait_seconds < MAX_RATE_LIMIT_WAIT:
        logger.info(f"Rate limit low ({remaining}), waiting {wait_seconds:.0f}s until reset")
        await asyncio.sleep(wait_seconds + 5)  # +5s buffer
        return  # Continue without error
    else:
        raise GitHubGraphQLRateLimitError(...)  # Too long to wait
```

### Configuration
- `MAX_RATE_LIMIT_WAIT = 3600` (1 hour) - configurable via settings
- Log warnings when waiting > 5 minutes

### Files to Modify
- `apps/integrations/services/github_graphql.py`
  - Add `wait_for_rate_limit` parameter to client
  - Update `_check_rate_limit()` to wait instead of error

### Tests (TDD)
1. Test wait when remaining < threshold and wait_seconds < MAX
2. Test error when wait_seconds > MAX
3. Test wait logs warning message
4. Test continues after wait (rate limit refreshes)

## 4.3 Resume Logic (OPTIONAL - Defer if needed)

### Problem
If sync fails mid-way (rate limit, timeout, etc.):
1. Progress is lost
2. On retry, sync starts from beginning
3. Wastes API calls re-fetching already-synced PRs

### Solution
Track `sync_cursor` on TrackedRepository:
- After each successful page, save cursor
- On retry, resume from cursor
- Clear cursor on successful completion

### Files to Modify
- `apps/integrations/models.py` - Add `sync_cursor` field
- `apps/integrations/services/github_graphql_sync.py` - Save/load cursor

### Priority
LOW - Rate limit wait logic (4.2) should handle most cases.
Only implement if users report partial sync issues.

## Implementation Order

1. **Phase 4.2**: Rate limit wait logic (HIGH PRIORITY)
   - TDD tests first
   - Implement in GitHubGraphQLClient
   - Verify with integration tests

2. **Phase 4.3**: Resume logic (DEFER)
   - Only if 4.2 doesn't solve sync failures
