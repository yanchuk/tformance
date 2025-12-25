# Multi-Repo Seeding Context

**Last Updated:** 2025-12-24

## Current Implementation State

### ✅ COMPLETED
- `RealProjectConfig` now uses `repos: tuple[str, ...]` instead of single `repo_full_name`
- Added `repo_full_name` property for backward compatibility
- Updated `REAL_PROJECTS` registry with multi-repo configs:
  - **Antiwork**: gumroad, flexile, helper (3 repos)
  - **Polar**: polar, polar-adapters, polar-python, polar-js (4 repos)
- Updated `RealProjectSeeder._fetch_contributors()` to collect from all repos and dedupe
- Updated `RealProjectSeeder._fetch_prs()` to iterate over all repos
- Updated management command to show all repos in `--list` output
- Renamed "Gumroad" team to "Antiwork" (org name)

### ⚡ GraphQL Integration (COMPLETED)
- Created `apps/metrics/seeding/github_graphql_fetcher.py` - GraphQL adapter
- Seeder now uses GraphQL by default (10x faster than REST)
- Added `--no-graphql` flag for fallback to REST API
- Added `use_graphql: bool = True` parameter to `RealProjectSeeder`
- **Added REST fallback for check runs** - CI/CD data now included

## Key Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/seeding/real_projects.py` | `repos: tuple[str, ...]` field, registry updates |
| `apps/metrics/seeding/real_project_seeder.py` | Multi-repo iteration, GraphQL support |
| `apps/metrics/seeding/github_graphql_fetcher.py` | **NEW** - GraphQL adapter with REST fallback |
| `apps/metrics/management/commands/seed_real_projects.py` | Multi-repo display, `--no-graphql` flag |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repos per team | 3-4 | Balance between data richness and seeding time |
| Antiwork repos | gumroad, flexile, helper | Main product + most active projects |
| Polar repos | polar, polar-adapters, polar-python, polar-js | Main product + SDKs |
| Config structure | `repos: tuple[str, ...]` | Immutable, extensible |
| Default API | GraphQL | 10x faster than REST |
| Check runs | REST fallback | GraphQL doesn't support check runs well |
| Team name | "Antiwork" not "Gumroad" | Gumroad is just one repo in org |

## Data Flow

```
RealProjectConfig.repos = ("org/repo1", "org/repo2", ...)
    ↓
_fetch_contributors() → iterates repos, dedupes by github_id
    ↓
_fetch_prs() → iterates repos, uses pr_data.github_repo for each PR
    ↓                          ↓
GraphQL: fetch PRs, reviews, commits, files
                               ↓
REST fallback: fetch check runs per PR
    ↓
_create_prs() → creates PRs with correct github_repo field
```

## Test Results

### Antiwork (3 repos, 10 PRs, 7 days)
```
Team members: 50
Pull requests: 10
Reviews: 3
Commits: 25
Files: 52
Check runs: 156 (140 success, 7 failed)
GitHub API calls: 78
```

### Polar (4 repos, 18 PRs, 7 days)
```
Team members: 50
Pull requests: 18
Reviews: 3
Commits: 46
Files: 86
Check runs: 0 (pre-REST fallback test)
GitHub API calls: 7
```

## Dependencies

- `gql[aiohttp]` - GraphQL client (already installed)
- `PyGithub` - REST fallback for check runs (already installed)
- `GITHUB_SEEDING_TOKENS` env var - comma-separated tokens

## Test Commands

```bash
# Quick test (7 days, 10-20 PRs)
python manage.py seed_real_projects --project antiwork --clear --max-prs 10 --days-back 7
python manage.py seed_real_projects --project polar --clear --max-prs 20 --days-back 7

# Full seeding (90 days, 100 PRs)
python manage.py seed_real_projects --project antiwork --clear --max-prs 100 --days-back 90
python manage.py seed_real_projects --project polar --clear --max-prs 100 --days-back 90

# Fallback to REST (slower but more reliable)
python manage.py seed_real_projects --project antiwork --clear --no-graphql
```

## Next Steps

1. **Run full seeding** for both teams (90 days, 100 PRs)
2. **Verify dashboard** - PR list shows multiple repos per team
3. **Check CI/CD metrics** - pass rate should work with check runs data

## Blockers/Issues

- None - all phases completed successfully
