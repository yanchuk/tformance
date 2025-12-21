# Multi-Token GitHub Fetcher - Implementation Plan

**Last Updated:** 2025-12-21

## Executive Summary

Implement multi-token support for the GitHub authenticated fetcher to increase parsing throughput. By using multiple GitHub Personal Access Tokens (PATs), we can effectively multiply our rate limit capacity (5,000 requests/hour per token), enabling faster seeding of large real project datasets.

### Goals
1. Support multiple GitHub tokens for parallel rate limit capacity
2. Intelligent token rotation based on remaining quota
3. Automatic failover when a token is rate-limited
4. Backward compatible with single-token usage

---

## Current State Analysis

### Current Implementation

| Component | Location | Behavior |
|-----------|----------|----------|
| GitHubAuthenticatedFetcher | `apps/metrics/seeding/github_authenticated_fetcher.py` | Single token via `GITHUB_SEEDING_TOKEN` env var |
| Rate Limit | 5,000 requests/hour | Per token |
| Parallel Fetching | ThreadPoolExecutor (3 workers) | Within single token |
| Retry Logic | Exponential backoff for 403s | Max 3 retries |

### Rate Limit Bottleneck

For large projects like PostHog or Gumroad:
- ~1000 PRs with commits, reviews, files, check runs
- ~5-10 API calls per PR for detailed data
- **5,000-10,000 requests needed** vs 5,000/hour limit

With 2 tokens: 10,000 requests/hour = **2x throughput**

---

## Proposed Future State

### Multi-Token Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   GitHubTokenPool                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ Token 1  │  │ Token 2  │  │ Token N  │              │
│  │ 5000/hr  │  │ 5000/hr  │  │ 5000/hr  │              │
│  │ rem: 4200│  │ rem: 2100│  │ rem: 4800│              │
│  └──────────┘  └──────────┘  └──────────┘              │
│         │            │            │                     │
│         └────────────┼────────────┘                     │
│                      ▼                                  │
│              Token Selection                            │
│     (highest remaining quota + not exhausted)           │
└─────────────────────────────────────────────────────────┘
                       │
                       ▼
            GitHubAuthenticatedFetcher
                       │
                       ▼
                 GitHub API
```

### Environment Configuration

```bash
# Option 1: Comma-separated tokens (new)
GITHUB_SEEDING_TOKENS=ghp_token1,ghp_token2

# Option 2: Single token (backward compatible)
GITHUB_SEEDING_TOKEN=ghp_single_token
```

---

## Implementation Phases

### Phase 1: Token Pool Manager
**Effort:** Medium | **Priority:** High | **Dependencies:** None

Create a new `GitHubTokenPool` class to manage multiple tokens.

### Phase 2: Fetcher Integration
**Effort:** Small | **Priority:** High | **Dependencies:** Phase 1

Modify `GitHubAuthenticatedFetcher` to use the token pool.

### Phase 3: Testing & Documentation
**Effort:** Small | **Priority:** Medium | **Dependencies:** Phase 2

Add tests and update documentation.

---

## Detailed Tasks

### Phase 1: Token Pool Manager

#### 1.1 Create GitHubTokenPool class
**Effort:** M | **File:** `apps/metrics/seeding/github_token_pool.py`

**Acceptance Criteria:**
- [ ] Create `TokenInfo` dataclass with: token, client, remaining, reset_time, is_exhausted
- [ ] Create `GitHubTokenPool` class with multi-token support
- [ ] Implement `get_best_client()` - returns client with highest remaining quota
- [ ] Implement `mark_rate_limited(client, reset_time)` - marks token as exhausted
- [ ] Implement `refresh_rate_limits()` - refreshes all token limits from API
- [ ] Implement `all_exhausted` property - returns True if all tokens are rate-limited
- [ ] Implement `wait_for_reset()` - sleeps until next token resets
- [ ] Thread-safe access to token state

#### 1.2 Token loading from environment
**Effort:** S | **File:** `apps/metrics/seeding/github_token_pool.py`

**Acceptance Criteria:**
- [ ] Parse `GITHUB_SEEDING_TOKENS` (comma-separated)
- [ ] Fall back to `GITHUB_SEEDING_TOKEN` (single)
- [ ] Validate tokens (non-empty, stripped)
- [ ] Log number of tokens loaded
- [ ] Raise clear error if no tokens available

### Phase 2: Fetcher Integration

#### 2.1 Update GitHubAuthenticatedFetcher constructor
**Effort:** S | **File:** `apps/metrics/seeding/github_authenticated_fetcher.py`

**Acceptance Criteria:**
- [ ] Accept optional `tokens: list[str]` parameter (plural)
- [ ] If tokens provided, create GitHubTokenPool
- [ ] If single token provided (existing behavior), create pool with 1 token
- [ ] Update `self._client` usage to use `self._token_pool.get_best_client()`
- [ ] Backward compatible with existing `token` parameter

#### 2.2 Handle rate limit switching
**Effort:** M | **File:** `apps/metrics/seeding/github_authenticated_fetcher.py`

**Acceptance Criteria:**
- [ ] Catch `RateLimitExceededException` in fetch methods
- [ ] Call `token_pool.mark_rate_limited()` for exhausted token
- [ ] Switch to next available token via `get_best_client()`
- [ ] If all tokens exhausted, optionally wait for reset or return partial results
- [ ] Log token switches for debugging

#### 2.3 Update rate limit logging
**Effort:** S | **File:** `apps/metrics/seeding/github_authenticated_fetcher.py`

**Acceptance Criteria:**
- [ ] Log rate limits for all tokens on initialization
- [ ] Update `_log_rate_limit()` to show pool status
- [ ] Log which token is being used for requests

### Phase 3: Testing & Documentation

#### 3.1 Write unit tests for TokenPool
**Effort:** M | **File:** `apps/metrics/tests/test_github_token_pool.py`

**Acceptance Criteria:**
- [ ] Test single token initialization
- [ ] Test multiple token initialization
- [ ] Test `get_best_client()` returns highest quota token
- [ ] Test `mark_rate_limited()` excludes token from selection
- [ ] Test `all_exhausted` behavior
- [ ] Test thread safety (concurrent access)
- [ ] Test env var parsing

#### 3.2 Update documentation
**Effort:** S | **Files:** `dev/DEV-ENVIRONMENT.md`, docstrings

**Acceptance Criteria:**
- [ ] Document `GITHUB_SEEDING_TOKENS` env var format
- [ ] Add usage examples for multi-token setup
- [ ] Update fetcher docstring with multi-token info

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Token state race conditions | Medium | Low | Use threading.Lock for token state |
| All tokens exhausted | Low | Medium | Implement wait_for_reset() with timeout |
| Different token scopes | Low | Low | Document required scopes in env var comments |
| API changes token format | Low | Low | Validate token format on load |

---

## Success Metrics

1. **Throughput:** 2x parsing speed with 2 tokens
2. **Reliability:** Graceful degradation when tokens exhausted
3. **Backward Compatibility:** Existing single-token usage unchanged
4. **Observability:** Clear logging of token usage and switches

---

## Required Resources

### Dependencies
- No new packages required
- Uses existing `PyGithub` library

### Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `apps/metrics/seeding/github_token_pool.py` | Create | Token pool manager |
| `apps/metrics/seeding/github_authenticated_fetcher.py` | Modify | Use token pool |
| `apps/metrics/tests/test_github_token_pool.py` | Create | Unit tests |
| `dev/DEV-ENVIRONMENT.md` | Modify | Document multi-token setup |

---

## Coordination with AI Involvement Tracking

This feature is **independent** and can be developed in parallel with the AI involvement tracking feature. Both enhance the seeding pipeline but touch different areas:

| Feature | Files Modified | Purpose |
|---------|---------------|---------|
| Multi-Token | github_authenticated_fetcher.py, NEW github_token_pool.py | Throughput |
| AI Tracking | models.py, NEW ai_detector.py, real_project_seeder.py | Detection |

No conflicts expected.
