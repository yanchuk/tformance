# Incremental Seeding Tasks

**Last Updated:** 2025-12-24

## Phase 1: Stability ✅ COMPLETE

- [x] **1.1** Create `PRCache` dataclass in `apps/metrics/seeding/pr_cache.py`
  - [x] Define dataclass with repo, fetched_at, since_date, prs fields
  - [x] Implement `save()` method with datetime serialization
  - [x] Implement `load()` classmethod with datetime parsing
  - [x] Implement `is_valid(since_date)` to check cache freshness
  - [x] Add tests for save/load round-trip (18 tests passing)

- [x] **1.2** Add cache directory to `.gitignore`
  - [x] Add `.seeding_cache/` entry

- [x] **1.3** Integrate cache save into `GitHubGraphQLFetcher`
  - [x] Add `use_cache` parameter to dataclass
  - [x] After fetching, call `PRCache.save()`
  - [x] Print `💾 Saved X PRs to cache` message

- [x] **1.4** Integrate cache load into `GitHubGraphQLFetcher`
  - [x] Before fetching, check for valid cache
  - [x] If cache valid, load and return cached PRs
  - [x] Print `📦 Loaded X PRs from cache` message

- [x] **1.5** Add `--refresh` flag to management command
  - [x] Delete cache files before fetching
  - [x] Print "Refreshing cache..." message

- [x] **1.6** Add `--no-cache` flag to management command
  - [x] Disable cache read/write entirely

- [x] **1.7** Remove team member limit for PR creation
  - [x] Create team members on-the-fly from PR authors
  - [x] All PRs now imported regardless of `max_members`

## Phase 2: Speed (PLANNED)

- [ ] **2.1** Parallel repo fetching
  - [ ] Use ThreadPoolExecutor to fetch multiple repos concurrently
  - [ ] Limit to 2-3 parallel fetches to avoid rate limits
  - [ ] Show progress for each repo

- [ ] **2.2** Skip unchanged repos
  - [ ] Compare cache `fetched_at` with `--days-back` window
  - [ ] If cache covers requested date range, skip fetch
  - [ ] Print "Cache up-to-date for {repo}"

- [ ] **2.3** Incremental PR fetching
  - [ ] Track newest PR date in cache
  - [ ] Only fetch PRs newer than cached
  - [ ] Merge with existing cache

## Phase 3: Scale (PLANNED)

- [ ] **3.1** Multi-token rotation
  - [ ] Track rate limit per token
  - [ ] Switch to next token when limit approached
  - [ ] Health check tokens before use

- [ ] **3.2** Smart rate limit handling
  - [ ] When rate limited, calculate wait time
  - [ ] Option to wait instead of fail
  - [ ] Progress bar during wait

- [ ] **3.3** Resume from specific repo
  - [ ] Track last successfully fetched repo
  - [ ] `--resume` flag to continue from there
  - [ ] Skip already-cached repos

## Phase 4: Production Alignment (CRITICAL)

**Key Insight**: Improvements must work for real users with single OAuth token, not just seeding with multiple PATs.

- [ ] **4.1** Align with production sync
  - [ ] Ensure `apps/integrations/services/github_graphql.py` improvements benefit Celery tasks
  - [ ] Add rate limit wait logic that works for single-token users
  - [ ] Share retry patterns between seeding and production

- [ ] **4.2** Production sync improvements
  - [ ] Incremental sync using `updated_since` (already in GraphQL query)
  - [ ] Better Celery task error handling
  - [ ] Resume from specific repo on failure

## Phase 5: Data Richness (PLANNED)

- [ ] **5.1** Additional PR metadata
  - [ ] Fetch labels
  - [ ] Fetch milestones
  - [ ] Fetch deployments

- [ ] **5.2** Issue references
  - [ ] Parse issue numbers from PR bodies
  - [ ] Link PRs to issues

## Verification

- [x] Run seeding, interrupt, resume - should use cache
- [x] Run without --clear - should load from cache
- [x] Run with --refresh - should re-fetch from GitHub
- [x] Run with --no-cache - should fetch without caching
- [x] Check cache files are created in `.seeding_cache/`
- [x] All PR authors become team members (no skipping)
