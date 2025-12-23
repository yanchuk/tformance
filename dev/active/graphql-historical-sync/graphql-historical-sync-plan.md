# GitHub GraphQL Migration: Full Parser Overhaul

**Last Updated:** 2025-12-23

## Executive Summary

Current historical data sync for Gumroad took ~1 hour due to serial REST API calls. This plan covers **migrating the entire GitHub parser to GraphQL**, achieving **10-50x speedup** while keeping REST only where absolutely necessary (Copilot metrics, webhooks).

---

## Scope: What Moves to GraphQL vs Stays REST

### ✅ Migrate to GraphQL (90% of GitHub calls)

| Function | Current File | REST Calls | GraphQL Benefit |
|----------|--------------|------------|-----------------|
| `sync_repository_history` | github_sync.py | ~7 per PR | 1 per 50 PRs |
| `sync_repository_incremental` | github_sync.py | ~7 per PR | 1 per 50 PRs |
| `fetch_pr_complete_data_task` | tasks.py | 6 per PR | 1 per PR |
| `sync_github_members` | member_sync.py | 1+ per page | 1 per 100 members |
| `get_repository_pull_requests` | github_sync.py | 1 per page | 1 per 100 PRs |
| `get_pull_request_reviews` | github_sync.py | 1 per PR | Nested in PR query |
| `sync_pr_commits` | github_sync.py | 1 per PR | Nested in PR query |
| `sync_pr_files` | github_sync.py | 1 per PR | Nested in PR query |
| `sync_pr_check_runs` | github_sync.py | 1 per PR | Nested in PR query |
| `sync_pr_comments` | github_sync.py | 2 per PR | Nested in PR query |

### ❌ Keep REST (No GraphQL Alternative)

| Function | Reason |
|----------|--------|
| **Copilot Metrics** | `/orgs/{org}/copilot/usage` - GraphQL doesn't support |
| **Copilot Billing** | `/orgs/{org}/copilot/billing/seats` - GraphQL doesn't support |
| **Webhook Handlers** | GitHub sends REST payloads, we receive them |
| **OAuth Flow** | REST endpoints for token exchange |

### ⚠️ Hybrid (GraphQL preferred, REST fallback)

| Function | Notes |
|----------|-------|
| `sync_repository_deployments` | GraphQL partial support, may need REST fallback |
| Rate limit exceeded | Fall back to REST if GraphQL quota exhausted |

---

## Migration Strategy: Keep REST, Add GraphQL

### Why Keep REST API Code?

| Reason | Explanation |
|--------|-------------|
| **Fallback safety** | If GraphQL fails, automatically fall back to REST |
| **Rate limit overflow** | GraphQL quota exhausted → switch to REST quota |
| **Feature gaps** | Some data only in REST (Copilot, deployments) |
| **Gradual rollout** | Feature flag controls which API is used |
| **Debugging** | Compare REST vs GraphQL results during testing |
| **Rollback** | Instant rollback by flipping feature flag |

### Architecture: Dual API Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GitHub Sync Service                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    API Router Layer                          │   │
│   │                                                              │   │
│   │   if USE_GRAPHQL and operation in GRAPHQL_SUPPORTED:        │   │
│   │       try:                                                   │   │
│   │           return graphql_client.execute(operation)          │   │
│   │       except (RateLimitError, GraphQLError):                │   │
│   │           logger.warning("GraphQL failed, using REST")      │   │
│   │           return rest_client.execute(operation)             │   │
│   │   else:                                                      │   │
│   │       return rest_client.execute(operation)                 │   │
│   │                                                              │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│              ┌───────────────┴───────────────┐                      │
│              │                               │                      │
│              ▼                               ▼                      │
│   ┌─────────────────────┐         ┌─────────────────────┐          │
│   │  GraphQL Client     │         │  REST Client        │          │
│   │  (gql library)      │         │  (PyGithub)         │          │
│   │                     │         │                     │          │
│   │  - Bulk PR fetch    │         │  - Copilot metrics  │          │
│   │  - Nested data      │         │  - Deployments      │          │
│   │  - Member sync      │         │  - Fallback ops     │          │
│   │                     │         │                     │          │
│   └─────────────────────┘         └─────────────────────┘          │
│              │                               │                      │
│              └───────────────┬───────────────┘                      │
│                              │                                       │
│                              ▼                                       │
│                    ┌─────────────────────┐                          │
│                    │  Unified Data Model │                          │
│                    │  (Same output format│                          │
│                    │   regardless of API)│                          │
│                    └─────────────────────┘                          │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Feature Flag Strategy

```python
# settings.py
GITHUB_API_CONFIG = {
    # Master switch
    "USE_GRAPHQL": env.bool("GITHUB_USE_GRAPHQL", default=False),

    # Per-operation control (for gradual rollout)
    "GRAPHQL_OPERATIONS": {
        "initial_sync": env.bool("GITHUB_GRAPHQL_INITIAL_SYNC", default=True),
        "incremental_sync": env.bool("GITHUB_GRAPHQL_INCREMENTAL_SYNC", default=False),
        "pr_complete_data": env.bool("GITHUB_GRAPHQL_PR_COMPLETE", default=True),
        "member_sync": env.bool("GITHUB_GRAPHQL_MEMBERS", default=False),
    },

    # Fallback behavior
    "FALLBACK_TO_REST": env.bool("GITHUB_FALLBACK_REST", default=True),
}
```

### Rollout Plan

```
Phase 1: GraphQL for initial_sync only (biggest win)
         REST for everything else
         ↓
Phase 2: Add incremental_sync to GraphQL
         ↓
Phase 3: Add pr_complete_data to GraphQL
         ↓
Phase 4: Add member_sync to GraphQL
         ↓
Phase 5: GraphQL as default, REST as fallback
         ↓
(Optional) Phase 6: Remove REST code after 6 months stable
```

### When to Delete REST Code?

**Don't delete REST until:**
- [ ] GraphQL has been stable in production for 6+ months
- [ ] All edge cases handled
- [ ] No fallback incidents in 3+ months
- [ ] Team confident in GraphQL-only approach

**Keep REST permanently for:**
- Copilot metrics (no GraphQL alternative)
- Webhook payload processing
- OAuth token exchange

---

## Problem Statement

### Current Performance

| Metric | Gumroad Example |
|--------|-----------------|
| Total PRs | ~400 |
| Time to sync | ~1 hour |
| API calls per PR | 6-7 |
| Total API calls | ~2,400+ |
| Processing mode | Serial |

### Root Cause Analysis

From `apps/integrations/services/github_sync.py`:

```python
# For EACH PR, we make 6-7 separate API calls:
def _process_prs(prs_data, tracked_repo, access_token):
    for pr_data in prs_data:
        # 1. Create PR record
        prs_synced += 1

        # 2. Fetch reviews (separate API call)
        reviews_synced += _sync_pr_reviews(...)

        # 3. Fetch commits (separate API call)
        commits_synced += sync_pr_commits(...)

        # 4. Fetch check runs (separate API call)
        check_runs_synced += sync_pr_check_runs(...)

        # 5. Fetch files (separate API call)
        files_synced += sync_pr_files(...)

        # 6. Fetch issue comments (separate API call)
        comments_synced += sync_pr_issue_comments(...)

        # 7. Fetch review comments (separate API call)
        comments_synced += sync_pr_review_comments(...)
```

**Additional inefficiencies:**
- Creates new `Github(access_token)` client for each operation
- No connection reuse
- No batching
- No parallelization (GitHub ToS requires serial requests anyway)

---

## Solution: GitHub GraphQL API

### Why GraphQL?

| Aspect | REST (Current) | GraphQL (Proposed) |
|--------|----------------|-------------------|
| **API calls per 100 PRs** | 600-700 | 1-2 |
| **Data returned** | Fixed, over-fetched | Only what we need |
| **Nested data** | Separate calls | Single query |
| **Rate limit** | 5,000 requests/hour | 5,000 points/hour |
| **Efficiency** | 1 request = 1 resource | 1 request = N resources |

### Single GraphQL Query for Complete PR Data

```graphql
query GetPRsWithAllData($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 50, after: $cursor, states: [MERGED, OPEN, CLOSED]) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        databaseId
        number
        title
        state
        merged
        mergedAt
        createdAt
        updatedAt
        additions
        deletions
        changedFiles

        author {
          login
          ... on User { databaseId }
        }

        baseRefName
        headRefName
        headRefOid
        url

        # Nested: Reviews (would be separate API call in REST)
        reviews(first: 100) {
          nodes {
            databaseId
            state
            submittedAt
            author {
              login
              ... on User { databaseId }
            }
            body
          }
        }

        # Nested: Commits (would be separate API call in REST)
        commits(first: 100) {
          nodes {
            commit {
              oid
              message
              committedDate
              additions
              deletions
              author {
                user { login }
              }
            }
          }
        }

        # Nested: Files (would be separate API call in REST)
        files(first: 100) {
          nodes {
            path
            additions
            deletions
            changeType
          }
        }

        # Nested: Comments (would be 2 separate API calls in REST)
        comments(first: 100) {
          nodes {
            databaseId
            body
            createdAt
            updatedAt
            author { login }
          }
        }

        reviewThreads(first: 100) {
          nodes {
            comments(first: 20) {
              nodes {
                databaseId
                body
                path
                line
                createdAt
                author { login }
              }
            }
          }
        }
      }
    }
  }
  rateLimit {
    remaining
    resetAt
    cost
  }
}
```

### Performance Comparison

| Scenario | REST API Calls | GraphQL Calls | Improvement |
|----------|---------------|---------------|-------------|
| 100 PRs | ~700 | 2 | **350x** |
| 400 PRs (Gumroad) | ~2,800 | 8 | **350x** |
| 1,000 PRs | ~7,000 | 20 | **350x** |

### Rate Limit Analysis

**REST (Current):**
- 5,000 requests/hour
- Gumroad sync: ~2,800 calls = 56% of hourly limit
- Time: ~1 hour (due to rate limiting pauses)

**GraphQL (Proposed):**
- 5,000 points/hour
- Complex query cost: ~50-200 points
- Gumroad sync: ~8 queries × 200 points = 1,600 points (32% of hourly limit)
- Time: **~2-5 minutes** (just network latency)

---

## Architecture Options

### Option 1: Hybrid Approach (Recommended)

**Keep REST for:**
- Webhooks (already work well)
- Incremental sync (REST `since` parameter is efficient)
- Copilot metrics (no GraphQL equivalent)
- Simple operations (member sync, repo listing)

**Use GraphQL for:**
- Initial historical sync (bulk PR fetch)
- `fetch_pr_complete_data_task` (merged PR details)

**Pros:**
- Minimal migration risk
- Best tool for each job
- Can implement incrementally

**Cons:**
- Two API patterns to maintain

### Option 2: Full GraphQL Migration

Replace all GitHub REST calls with GraphQL.

**Pros:**
- Single consistent API pattern
- Maximum efficiency everywhere

**Cons:**
- Large migration effort
- PyGithub library not used (lose pagination helpers)
- Webhooks still REST (GitHub sends REST payloads)

### Option 3: Separate Sync Service (Microservice)

Build a dedicated Python service for historical sync using GraphQL.

**Pros:**
- Can scale independently
- Could be async/parallel
- Clean separation of concerns

**Cons:**
- Operational overhead
- Infrastructure complexity
- Overkill for current scale

---

## Recommendation: Option 1 (Hybrid)

Implement GraphQL for initial sync while keeping REST for everything else.

### Implementation Plan

#### Phase 1: GraphQL Client & Infrastructure (2-3 days)

1. Add `gql[aiohttp]` dependency
2. Create `apps/integrations/services/github_graphql.py` with:
   - `GitHubGraphQLClient` class
   - Rate limit monitoring
   - Error handling & retry logic
   - Async execution support
3. Create query templates module `apps/integrations/services/github_queries.py`
4. Add unit tests for GraphQL client

```python
# apps/integrations/services/github_graphql.py
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport

class GitHubGraphQLClient:
    """GraphQL client for GitHub API with rate limit handling."""

    def __init__(self, access_token: str):
        transport = AIOHTTPTransport(
            url="https://api.github.com/graphql",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        self.client = Client(transport=transport)

    async def fetch_prs_bulk(
        self,
        owner: str,
        repo: str,
        cursor: str = None
    ) -> dict:
        """Fetch PRs with all nested data in one request."""
        query = gql(PR_COMPLETE_QUERY)
        result = await self.client.execute_async(
            query,
            variable_values={"owner": owner, "repo": repo, "cursor": cursor}
        )
        return result
```

#### Phase 2: Bulk Sync Implementation (2-3 days)

1. Create `sync_repository_history_graphql()` function
2. Implement pagination with cursor
3. Map GraphQL response to existing model format
4. Add progress tracking

```python
async def sync_repository_history_graphql(
    tracked_repo: TrackedRepository,
) -> dict:
    """Sync historical PR data using GraphQL (10-50x faster)."""

    client = GitHubGraphQLClient(tracked_repo.integration.credential.access_token)
    owner, repo = tracked_repo.full_name.split("/")

    cursor = None
    total_synced = {"prs": 0, "reviews": 0, "commits": 0, "files": 0}

    while True:
        # Fetch batch of 50 PRs with all nested data
        result = await client.fetch_prs_bulk(owner, repo, cursor)

        prs = result["repository"]["pullRequests"]["nodes"]
        for pr_data in prs:
            # Process PR and all nested data in one go
            _process_graphql_pr(tracked_repo.team, pr_data, total_synced)

        # Check pagination
        page_info = result["repository"]["pullRequests"]["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        cursor = page_info["endCursor"]

        # Log rate limit
        rate_limit = result["rateLimit"]
        logger.info(f"GraphQL rate limit: {rate_limit['remaining']} remaining")

    return total_synced
```

#### Phase 3: Integration & Testing (1-2 days)

1. Add feature flag for GraphQL sync
2. Update `sync_repository_initial_task` to use GraphQL
3. Add fallback to REST on errors
4. Performance benchmarking

```python
# In tasks.py
@shared_task
def sync_repository_initial_task(tracked_repo_id: int):
    tracked_repo = TrackedRepository.objects.get(id=tracked_repo_id)

    # Use GraphQL for initial bulk sync (faster)
    if settings.USE_GRAPHQL_SYNC:
        try:
            result = async_to_sync(sync_repository_history_graphql)(tracked_repo)
            return result
        except Exception as e:
            logger.warning(f"GraphQL sync failed, falling back to REST: {e}")

    # Fallback to REST
    return sync_repository_history(tracked_repo)
```

#### Phase 4: Production Rollout (1 day)

1. Deploy with feature flag OFF
2. Test with small repositories
3. Gradual rollout
4. Monitor rate limits and performance

---

## Data We Can/Cannot Get via GraphQL

### ✅ Available via GraphQL

| Data | GraphQL Field | Notes |
|------|--------------|-------|
| Pull Requests | `repository.pullRequests` | Full support |
| PR Reviews | `pullRequest.reviews` | Full support |
| PR Commits | `pullRequest.commits` | Full support |
| PR Files | `pullRequest.files` | Full support |
| PR Comments | `pullRequest.comments` | Issue comments |
| Review Comments | `pullRequest.reviewThreads` | Inline comments |
| Check Runs | `commit.checkSuites.checkRuns` | CI/CD status |
| Org Members | `organization.membersWithRole` | Full support |
| Repository | `repository` | Metadata |

### ❌ NOT Available via GraphQL

| Data | Alternative | Notes |
|------|-------------|-------|
| **Copilot Metrics** | REST API only | `/orgs/{org}/copilot/usage` |
| **Copilot Billing** | REST API only | `/orgs/{org}/copilot/billing` |
| **Deployments** | REST API (or partial GraphQL) | Use REST for now |
| **Webhooks** | N/A | Webhooks push REST payloads |

---

## Python GraphQL Libraries Comparison

### Available Options

| Library | Type | GitHub Stars | Best For |
|---------|------|--------------|----------|
| **[gql](https://github.com/graphql-python/gql)** | Generic GraphQL client | 1.7k+ | Write queries as strings, async support |
| **[sgqlc](https://github.com/profusion/sgqlc)** | Schema-first client | 500+ | Type-safe Python code from schema |
| **requests** | Direct HTTP | N/A | Simple, no dependencies |

### Detailed Comparison

#### Option A: gql (Recommended)

```python
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

async def fetch_prs():
    transport = AIOHTTPTransport(
        url="https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {token}"}
    )
    client = Client(transport=transport)

    query = gql("""
        query($owner: String!, $repo: String!) {
            repository(owner: $owner, name: $repo) {
                pullRequests(first: 50) {
                    nodes { number title }
                }
            }
        }
    """)

    async with client as session:
        result = await session.execute(query, variable_values={...})
```

**Pros:**
- Well-documented, mature library
- Native async support (aiohttp, httpx)
- Supports subscriptions, file uploads
- Schema validation available
- MIT license

**Cons:**
- Queries written as strings (no code completion)
- No GitHub-specific helpers

#### Option B: sgqlc (Schema-First)

```python
from sgqlc.endpoint.http import HTTPEndpoint
from sgqlc.operation import Operation
from github_schema import Query  # Auto-generated from GitHub schema

# Generate schema once:
# python3 -m sgqlc.introspection -H "Authorization: bearer TOKEN" \
#   https://api.github.com/graphql github_schema.json
# sgqlc-codegen schema github_schema.json github_schema.py

endpoint = HTTPEndpoint(
    'https://api.github.com/graphql',
    {'Authorization': f'bearer {token}'}
)

op = Operation(Query)
repo = op.repository(owner='gumroad', name='repo')
prs = repo.pull_requests(first=50)
prs.nodes.number()
prs.nodes.title()
prs.nodes.merged_at()  # Pythonic snake_case!

data = endpoint(op)
```

**Pros:**
- Type-safe, IDE autocomplete works
- Pythonic snake_case (not camelCase)
- Code generation from GitHub schema
- No string queries

**Cons:**
- Steeper learning curve
- Schema generation step required
- Less mature than gql

#### Option C: Direct requests (Simplest)

```python
import requests

def fetch_prs(token, owner, repo):
    query = """
        query($owner: String!, $repo: String!) {
            repository(owner: $owner, name: $repo) {
                pullRequests(first: 50) {
                    nodes { number title }
                }
            }
        }
    """
    response = requests.post(
        'https://api.github.com/graphql',
        json={'query': query, 'variables': {'owner': owner, 'repo': repo}},
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()
```

**Pros:**
- No new dependencies (requests already used)
- Simple, easy to understand
- Full control

**Cons:**
- No pagination helpers
- No retry logic
- No schema validation
- Manual error handling

### Recommendation

**Start with `gql`** for these reasons:
1. Best balance of features and simplicity
2. Native async support (good for batch fetching)
3. Well-documented with active maintenance
4. Can add schema validation later if needed

**Consider `sgqlc` later** if:
- Type safety becomes important
- You want IDE autocomplete for GitHub API
- You're building many different queries

---

## GitHub REST → GraphQL Migration Guide

From [GitHub's official migration guide](https://docs.github.com/en/graphql/guides/migrating-from-rest-to-graphql):

### Key Concepts

1. **Precise Data Retrieval** - Only get fields you request
2. **Nested Field Querying** - 4 REST calls → 1 GraphQL query
3. **Strong Type Safety** - Schema validation catches errors early

### Example: Fetching PR with Related Data

**REST (4+ API calls):**
```python
# Call 1: Get PR
pr = repo.get_pull(42)

# Call 2: Get reviews
reviews = pr.get_reviews()

# Call 3: Get commits
commits = pr.get_commits()

# Call 4: Get files
files = pr.get_files()
```

**GraphQL (1 API call):**
```graphql
query {
  repository(owner: "owner", name: "repo") {
    pullRequest(number: 42) {
      title
      reviews(first: 100) { nodes { state } }
      commits(first: 100) { nodes { commit { message } } }
      files(first: 100) { nodes { path additions } }
    }
  }
}
```

### Migration Tips from GitHub

1. **Don't assume 1:1 mapping** - GraphQL structure differs from REST
2. **Use Global Node IDs** - For cross-API object references
3. **Leverage nested capabilities** - Reduce round trips
4. **Validate locally** - Schema catches type errors before API call

---

## Dependencies to Add

```toml
# pyproject.toml - Option A (gql)
[project.dependencies]
gql = { version = "^3.5.0", extras = ["aiohttp"] }

# OR Option B (sgqlc) - if type safety preferred
# sgqlc = "^16.0"
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GraphQL rate limit exceeded | Low | Medium | Monitor cost per query, batch smaller |
| Query complexity limit | Low | Low | Split into smaller queries if needed |
| Learning curve | Low | Low | Well-documented, examples exist |
| Breaking changes | Very Low | Medium | Version lock API, feature flag |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Initial sync time (400 PRs) | ~60 min | <5 min |
| API calls (400 PRs) | ~2,800 | ~8-10 |
| Rate limit usage | 56% | <35% |
| User wait time | Too long | Acceptable |

---

## Decision Points

1. **Async vs Sync?**
   - Recommend: Start with `async_to_sync()` wrapper
   - Future: Full async if performance needs grow

2. **Batch size?**
   - Start with 50 PRs per query (safe)
   - Increase to 100 if rate limits allow

3. **Feature flag strategy?**
   - Environment variable: `USE_GRAPHQL_SYNC=true`
   - Default OFF in production initially

4. **Error handling?**
   - Always fall back to REST on GraphQL failure
   - Log errors for debugging

---

## Conclusion

**Recommendation:** Implement Option 1 (Hybrid) starting with Phase 1.

**Expected outcome:** Initial sync reduced from ~1 hour to ~2-5 minutes for Gumroad-sized repositories.

**Next steps:**
1. Approve this plan
2. Add `gql` dependency
3. Implement Phase 1 (GraphQL client)
4. Test with a small repository
5. Roll out gradually
