# GraphQL Seeding Migration Plan

**Last Updated:** 2025-12-24

## Executive Summary

Migrate the real project seeding infrastructure from REST API to GraphQL API for ~10x faster data fetching. The existing `GitHubGraphQLClient` already has the queries needed - we just need to connect it to the seeder.

## Current State Analysis

### Current Architecture (REST-based)
- `GitHubAuthenticatedFetcher` uses PyGitHub (REST API)
- Fetches PRs sequentially with separate calls per PR for:
  - PR metadata (~1 call)
  - Reviews (~1 call)
  - Commits (~1 call)
  - Files (~1 call)
  - Check runs (~1 call)
- **Total: ~5 API calls per PR** = 500 calls for 100 PRs
- REST rate limit: 5000 requests/hour

### Proposed Architecture (GraphQL-based)
- `GitHubGraphQLClient` already exists in `apps/integrations/services/github_graphql.py`
- Single query fetches PR + reviews + commits + files in one request
- **Total: ~2 calls per 50 PRs** (paginated) = ~4 calls for 100 PRs
- GraphQL rate limit: 5000 points/hour (~1 point per query)

### Performance Comparison
| Metric | REST (current) | GraphQL (proposed) |
|--------|----------------|-------------------|
| API calls for 100 PRs | ~500 | ~4 |
| Time for 100 PRs | ~5-10 min | ~30 sec |
| Rate limit impact | High | Minimal |

## Key Files

### Current (to be replaced)
- `apps/metrics/seeding/github_authenticated_fetcher.py` - REST-based fetcher

### Existing (to be used)
- `apps/integrations/services/github_graphql.py` - GraphQL client with queries
- `apps/metrics/seeding/real_project_seeder.py` - Orchestrator (needs updates)
- `apps/metrics/seeding/real_projects.py` - Config (no changes needed)

## Implementation Phases

### Phase 1: Create GraphQL Seeding Adapter (Effort: M)
Create adapter that translates GraphQL responses to existing dataclasses.

### Phase 2: Update Seeder to Use GraphQL (Effort: S)
Replace `GitHubAuthenticatedFetcher` calls with GraphQL adapter.

### Phase 3: Add Contributors Query (Effort: S)
Add GraphQL query for fetching repository contributors.

### Phase 4: Test & Validate (Effort: S)
Ensure seeding produces identical results to REST version.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data format differences | Medium | Low | Adapter layer handles mapping |
| Missing check runs in GraphQL | High | Low | Can fetch separately or skip |
| Async complexity | Low | Medium | Use asyncio.run() wrapper |

## Success Metrics

- [ ] Seeding 100 PRs completes in < 1 minute
- [ ] API calls reduced by 90%+
- [ ] All PR data (reviews, commits, files) properly imported
- [ ] No regressions in seeded data quality
