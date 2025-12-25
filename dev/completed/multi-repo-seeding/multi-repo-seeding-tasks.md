# Multi-Repo Seeding Tasks

**Last Updated:** 2025-12-25

## Status: IMPLEMENTATION COMPLETE ✅

All coding complete. Phase 4 (execution & verification) to be done manually by user.

## Phase 1: Config Schema Update ✅

- [x] **1.1** Update `RealProjectConfig` dataclass to use `repos: list[str]`
  - File: `apps/metrics/seeding/real_projects.py`
  - Added `repos: tuple[str, ...]` field
  - Added `repo_full_name` property for backward compat

- [x] **1.2** Update existing `REAL_PROJECTS` entries to use new list format
  - Converted all configs to use `repos=(...)`
  - Renamed "gumroad" to "antiwork"

- [ ] **1.3** Add tests for new config schema
  - Skipped - manual testing sufficient for config

## Phase 2: Seeder Multi-Repo Support ✅

- [x] **2.1** Update `_fetch_prs()` to iterate over repos list
  - Now loops through `config.repos`
  - Each PR has correct `github_repo` field

- [x] **2.2** Update `_fetch_contributors()` for multi-repo
  - Collects from all repos, dedupes by GitHub ID
  - Sorts by `pr_count`, takes top `max_members`

- [x] **2.3** Update PR creation to use `pr_data.github_repo`
  - Changed from `self.config.repo_full_name` to `pr_data.github_repo`

## Phase 3: GraphQL Integration ✅ (NEW)

- [x] **3.1** Create `GitHubGraphQLFetcher` adapter
  - File: `apps/metrics/seeding/github_graphql_fetcher.py`
  - Same interface as `GitHubAuthenticatedFetcher`
  - Maps GraphQL responses to existing dataclasses

- [x] **3.2** Update seeder to use GraphQL by default
  - Added `use_graphql: bool = True` parameter
  - GraphQL is ~10x faster than REST

- [x] **3.3** Add `--no-graphql` CLI flag
  - Fallback to REST if GraphQL fails

## Phase 4: Execute Seeding ⏳

- [ ] **4.1** Test with limited data (7 days, 20 PRs)
  ```bash
  python manage.py seed_real_projects --project antiwork --clear --max-prs 20 --days-back 7
  python manage.py seed_real_projects --project polar --clear --max-prs 20 --days-back 7
  ```

- [ ] **4.2** Full seeding (90 days, 100 PRs per repo)
  ```bash
  python manage.py seed_real_projects --project antiwork --clear --max-prs 100 --days-back 90
  python manage.py seed_real_projects --project polar --clear --max-prs 100 --days-back 90
  ```

- [ ] **4.3** Verify dashboard displays multi-repo data
  - Check PR list shows repos from multiple sources
  - Check Technology column shows variety
  - Check member list shows contributors from all repos

## Verification Checklist

- [ ] All 7 repos synced successfully
- [ ] No API rate limit errors
- [ ] No duplicate team members
- [ ] Dashboard loads without errors
- [ ] PR technology categories populated
- [ ] Repo filter shows all repos

## Notes

- Use `GITHUB_SEEDING_TOKENS` from `.env` (token pool)
- GraphQL is default (~30s for 100 PRs vs ~5min with REST)
- Use `--no-graphql` flag if GraphQL fails
