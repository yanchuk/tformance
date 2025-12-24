# Incremental Seeding Tasks

**Last Updated:** 2025-12-24

## Phase 1: Stability ✅ COMPLETE

- [x] **1.1** Create `PRCache` dataclass in `apps/metrics/seeding/pr_cache.py`
- [x] **1.2** Add cache directory to `.gitignore`
- [x] **1.3** Integrate cache save into `GitHubGraphQLFetcher`
- [x] **1.4** Integrate cache load into `GitHubGraphQLFetcher`
- [x] **1.5** Add `--refresh` flag to management command
- [x] **1.6** Add `--no-cache` flag to management command
- [x] **1.7** Remove team member limit for PR creation
- [x] **1.8** Commit changes: `a1bff2d`

## Phase 2: Complete Data Collection ✅ COMPLETE

- [x] **2.1** Add new fields to GraphQL queries (FETCH_PRS_BULK_QUERY, FETCH_PRS_UPDATED_QUERY, FETCH_SINGLE_PR_QUERY)
  - `isDraft` field
  - `labels(first: 10) { nodes { name color } }`
  - `milestone { title number dueOn }`
  - `assignees(first: 10) { nodes { login } }`
  - `closingIssuesReferences(first: 5) { nodes { number title } }`

- [x] **2.2** Add fields to PullRequest model (migration 0017)
  - `is_draft` BooleanField
  - `labels` JSONField (list of label names)
  - `milestone_title` CharField
  - `assignees` JSONField (list of usernames)
  - `linked_issues` JSONField (list of issue numbers)

- [x] **2.3** Update FetchedPRFull dataclass
  - Added `milestone_title: str | None = None`
  - Added `assignees: list[str] = field(default_factory=list)`
  - Added `linked_issues: list[int] = field(default_factory=list)`

- [x] **2.4** Update `_map_pr()` in github_graphql_fetcher.py
  - Map labels from `labels.nodes[].name`
  - Map milestone_title from `milestone.title`
  - Map assignees from `assignees.nodes[].login`
  - Map linked_issues from `closingIssuesReferences.nodes[].number`

- [x] **2.5** Update `_create_single_pr()` in real_project_seeder.py
  - Pass new fields to PullRequestFactory

- [x] **2.6** Add TDD tests for Phase 2 (11 tests)
  - `TestGitHubGraphQLFetcherMapPR` class
  - Tests for labels, milestone, assignees, linked_issues, is_draft

## Phase 3: Speed (PLANNED)

- [ ] **3.1** Parallel repo fetching
- [ ] **3.2** Skip unchanged repos
- [ ] **3.3** Incremental PR fetching

## Phase 4: Production Alignment (PLANNED)

- [ ] **4.1** Align improvements with production Celery tasks
- [ ] **4.2** Rate limit wait logic for single-token users
- [ ] **4.3** Better error handling and resume

## Phase 5: Analytics (PLANNED)

- [ ] **5.1** Filter/group PRs by label
- [ ] **5.2** Milestone progress tracking
- [ ] **5.3** Assignee workload analysis

## Verification

- [x] Run seeding, interrupt, resume - uses cache
- [x] Run without --clear - loads from cache
- [x] Run with --refresh - re-fetches from GitHub
- [x] Run with --no-cache - fetches without caching
- [x] All PR authors become team members
- [x] Labels stored in PullRequest model (Phase 2)
- [x] Milestones stored in PullRequest model (Phase 2)
- [x] Assignees stored in PullRequest model (Phase 2)
- [x] Linked issues stored in PullRequest model (Phase 2)
- [x] 43 tests passing (32 existing + 11 new Phase 2)
