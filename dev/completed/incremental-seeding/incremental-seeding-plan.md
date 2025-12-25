# Incremental Seeding Plan

**Last Updated:** 2025-12-24

## Executive Summary

Implement incremental seeding for the real project seeder that:
1. **Resumes from interruption** - Continue from where we stopped without `--clear`
2. **Caches parsed data** - Save fetched PR data locally to avoid re-fetching from GitHub API
3. **Skips existing records** - Don't re-process PRs already in the database

This will reduce GitHub API usage, enable faster iteration, and handle rate limits gracefully.

## Current State Analysis

### Existing Infrastructure
- `SeedingCheckpoint` class in `apps/metrics/seeding/checkpoint.py` - already tracks fetched PR numbers
- `GitHubGraphQLFetcher` - fetches data but doesn't cache
- `RealProjectSeeder` - orchestrates seeding but re-fetches everything each run
- Management command has `--checkpoint-file` arg (only used with REST API, not GraphQL)

### Current Behavior
1. **With `--clear`**: Deletes all team data, re-fetches everything from GitHub
2. **Without `--clear`**: Still re-fetches from GitHub, skips duplicate DB inserts
3. **No local caching**: Every run = full GitHub API round-trip

### Pain Points
- 500 PRs = ~500+ API calls (GraphQL pages + check runs)
- Rate limits or timeouts = lost progress
- Re-running without `--clear` still wastes API calls

## Proposed Future State

### Two-Level Caching Strategy

```
Level 1: GitHub API → Local JSON Cache (per repo)
Level 2: Local Cache → Database (skip existing PRs)
```

### Cache File Structure
```
.seeding_cache/
├── antiwork/
│   ├── gumroad.json          # PRs with all details
│   ├── flexile.json
│   └── helper.json
├── polar/
│   ├── polar.json
│   └── polar-adapters.json
└── posthog/
    ├── posthog.json
    └── posthog-js.json
```

### Cache File Format
```json
{
  "repo": "antiwork/gumroad",
  "fetched_at": "2025-12-24T10:00:00Z",
  "since_date": "2024-09-24",
  "total_prs": 150,
  "prs": [
    {
      "number": 1234,
      "title": "Add feature X",
      "created_at": "2024-10-01T...",
      "reviews": [...],
      "commits": [...],
      "files": [...],
      "check_runs": [...]
    }
  ]
}
```

### Behavior Changes

| Scenario | Current | Proposed |
|----------|---------|----------|
| First run | Fetch all | Fetch all, save to cache |
| Re-run (no --clear) | Re-fetch all | Load from cache, skip DB dupes |
| Re-run (--clear) | Delete + re-fetch | Delete + load from cache |
| Re-run (--refresh) | N/A | Delete cache, re-fetch |
| Cache exists but stale | N/A | Use cache, warn user |

## Implementation Phases

### Phase 1: Local PR Cache (Effort: M)
Add JSON caching for fetched PR data.

### Phase 2: Incremental DB Seeding (Effort: S)
Skip PRs that already exist in database.

### Phase 3: Cache Management (Effort: S)
Add cache refresh, expiry, and stats.

## Detailed Tasks

### Phase 1: Local PR Cache

#### 1.1 Create PRCache dataclass (S)
- File: `apps/metrics/seeding/pr_cache.py`
- Fields: repo, fetched_at, since_date, prs (list of FetchedPRFull as dicts)
- Methods: save(), load(), is_valid()
- Acceptance: Can serialize/deserialize FetchedPRFull

#### 1.2 Add cache save to GitHubGraphQLFetcher (S)
- File: `apps/metrics/seeding/github_graphql_fetcher.py`
- After fetching PRs, save to `.seeding_cache/{org}/{repo}.json`
- Acceptance: Cache file created after successful fetch

#### 1.3 Add cache load to GitHubGraphQLFetcher (S)
- Check for cache before fetching from API
- Use cache if exists and matches since_date
- Acceptance: Second run uses cache, no API calls

#### 1.4 Add --refresh flag to management command (S)
- File: `apps/metrics/management/commands/seed_real_projects.py`
- Deletes cache before fetching
- Acceptance: --refresh forces re-fetch

### Phase 2: Incremental DB Seeding

#### 2.1 Skip existing PRs in _create_prs (S)
- File: `apps/metrics/seeding/real_project_seeder.py`
- Query existing PR numbers before creating
- Skip PRs that exist in database
- Acceptance: Re-run without --clear doesn't duplicate PRs

#### 2.2 Add progress logging for skipped PRs (S)
- Show "Skipped X existing PRs, creating Y new"
- Acceptance: Clear feedback on incremental behavior

### Phase 3: Cache Management

#### 3.1 Add cache stats to management command (S)
- Show cache size, age, PR count before seeding
- Add `--cache-info` flag to just show cache status
- Acceptance: User can see cache state

#### 3.2 Add cache age warning (S)
- Warn if cache > 7 days old
- Suggest --refresh
- Acceptance: User informed of stale cache

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cache format changes | Medium | Medium | Version cache schema, auto-invalidate |
| Disk space | Low | Low | Cache is ~100KB per repo |
| Stale data confusion | Medium | Low | Show cache age, warn if old |

## Success Metrics

1. **API efficiency**: Second run uses 0 GitHub API calls (from cache)
2. **Resume capability**: Interrupted seeding can continue without re-fetching
3. **DB efficiency**: No duplicate PR records created

## Dependencies

- Existing `FetchedPRFull` dataclass with all fields
- Existing `SeedingCheckpoint` (can be reused or extended)
- `dataclasses.asdict()` for serialization
