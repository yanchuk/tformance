# Incremental Seeding Tasks

**Last Updated:** 2025-12-24 (Session End)

## Phase 1: Stability ✅ COMPLETE (Commit: a1bff2d)

- [x] **1.1** Create `PRCache` dataclass in `apps/metrics/seeding/pr_cache.py`
- [x] **1.2** Add cache directory to `.gitignore`
- [x] **1.3** Integrate cache save into `GitHubGraphQLFetcher`
- [x] **1.4** Integrate cache load into `GitHubGraphQLFetcher`
- [x] **1.5** Add `--refresh` flag to management command
- [x] **1.6** Add `--no-cache` flag to management command
- [x] **1.7** Remove team member limit for PR creation
- [x] **1.8** Commit changes

## Phase 2: Complete Data Collection ✅ COMPLETE (Commit: c93c575)

- [x] **2.1** Add new fields to GraphQL queries
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

- [x] **2.3** Update FetchedPRFull dataclass with new fields

- [x] **2.4** Update `_map_pr()` in github_graphql_fetcher.py

- [x] **2.5** Update `_create_single_pr()` in real_project_seeder.py

- [x] **2.6** Add TDD tests for Phase 2 (11 tests)

- [x] **2.7** Commit changes

## Phase 3: Speed (PLANNED)

- [ ] **3.1** Parallel repo fetching
- [ ] **3.2** Skip unchanged repos (compare updated_at)
- [ ] **3.3** Incremental PR fetching (only new PRs since last sync)

## Phase 4: Production Alignment (PLANNED)

- [ ] **4.1** Apply Phase 1-2 improvements to production Celery tasks
- [ ] **4.2** Rate limit wait logic for single-token users
- [ ] **4.3** Better error handling and resume in sync tasks

## Phase 5: Analytics (PLANNED)

- [ ] **5.1** Filter/group PRs by label in dashboard
- [ ] **5.2** Milestone progress tracking view
- [ ] **5.3** Assignee workload analysis

## Verification Checklist

### Phase 1 (Complete)
- [x] Run seeding, interrupt, resume - uses cache
- [x] Run without --clear - loads from cache
- [x] Run with --refresh - re-fetches from GitHub
- [x] Run with --no-cache - fetches without caching
- [x] All PR authors become team members

### Phase 2 (Complete)
- [x] Labels stored in PullRequest model
- [x] Milestones stored in PullRequest model
- [x] Assignees stored in PullRequest model
- [x] Linked issues stored in PullRequest model
- [x] 43 tests passing (32 Phase 1 + 11 Phase 2)

### Phase 3 (Pending)
- [ ] Parallel repo fetch reduces total time
- [ ] Unchanged repos skip API calls
- [ ] Incremental sync only fetches new PRs

## Test Commands

```bash
# Run Phase 1 + Phase 2 tests
.venv/bin/pytest apps/metrics/tests/test_pr_cache.py apps/metrics/tests/test_github_graphql_fetcher.py -v

# Check for missing migrations
python manage.py makemigrations --check

# Test seeding end-to-end
python manage.py seed_real_projects --project antiwork --max-prs 10 --refresh
```
