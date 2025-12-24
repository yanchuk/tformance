# GraphQL Seeding Tasks

**Last Updated:** 2025-12-24

## Phase 1: Create GraphQL Seeding Adapter ✅

- [x] **1.1** Create `apps/metrics/seeding/github_graphql_fetcher.py`
  - `GitHubGraphQLFetcher` class
  - Same interface as `GitHubAuthenticatedFetcher`

- [x] **1.2** Implement PR response mapping
  - `_map_pr()` - GraphQL node → `FetchedPRFull`
  - Maps reviews, commits, files

- [x] **1.3** Add contributors query
  - Uses `mentionableUsers` from repository
  - Maps to `ContributorInfo`

## Phase 2: Update Seeder ✅

- [x] **2.1** Update `RealProjectSeeder.__post_init__`
  - Added `use_graphql: bool = True` parameter
  - Selects fetcher based on flag

- [x] **2.2** Add `--no-graphql` CLI flag
  - Fallback to REST API

## Phase 3: REST Fallback for Check Runs ✅

- [x] **3.1** Add `_fetch_check_runs_rest()` method
  - Uses PyGithub to fetch check runs per PR
  - Lazy-loads REST client

- [x] **3.2** Add `_add_check_runs_to_prs()` method
  - Iterates PRs and fetches check runs
  - Logs progress

- [x] **3.3** Make check runs configurable
  - Added `fetch_check_runs: bool = True` parameter
  - Default enabled for complete data

## Phase 4: Test & Validate ✅

- [x] **4.1** Test with Antiwork (3 repos, 10 PRs)
  ```
  PRs: 10, Check runs: 156, API calls: 78
  ```

- [x] **4.2** Test with Polar (4 repos, 18 PRs)
  ```
  PRs: 18, Check runs: 0 (pre-check runs test)
  ```

- [x] **4.3** Verify data quality
  - PRs have reviews, commits, files ✅
  - Check runs included (success/failure) ✅
  - Team members created ✅
  - No duplicate entries ✅

## Verification Checklist ✅

- [x] Seeding completes without errors
- [x] PRs have all expected fields populated
- [x] Reviews linked to PRs correctly
- [x] Commits linked to PRs correctly
- [x] Files have correct categories assigned
- [x] Team members created from contributors
- [x] Check runs fetched via REST fallback
- [x] CI/CD metrics available in dashboard

## Phase 5: Full Seeding ⏳

- [ ] **5.1** Run full seeding for Antiwork (90 days, 100 PRs)
  ```bash
  python manage.py seed_real_projects --project antiwork --clear --max-prs 100 --days-back 90
  ```

- [ ] **5.2** Run full seeding for Polar (90 days, 100 PRs)
  ```bash
  python manage.py seed_real_projects --project polar --clear --max-prs 100 --days-back 90
  ```

- [ ] **5.3** Verify dashboard displays multi-repo data
  - Check PR list shows repos from multiple sources
  - Check Technology column shows variety
  - Check CI/CD pass rate metric works

## Notes

- GraphQL is default (use `--no-graphql` for REST)
- Check runs fetched via REST (~3 API calls per PR)
- Token from `GITHUB_SEEDING_TOKENS` env var
- Full seeding will take ~2-5 minutes per team
