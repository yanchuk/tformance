# Local Public Repo Incremental Reuse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the local public repo-page dataset by reusing the existing local DB and `.seeding_cache`, importing only missing or stale data, and generating only the minimum LLM output needed for public pages.

**Architecture:** Local DB is the primary source of truth, `.seeding_cache` is the secondary source for missing or stale repo data, and live GitHub fetches are disabled for this phase. Reuse the existing real-project persistence flow for PRs and related records, then rebuild only the repo/org public snapshots that changed.

**Tech Stack:** Django 5.2.9, Python 3.12, PostgreSQL, existing `PullRequest` and GitHub child models, `.seeding_cache` JSON manifests, public snapshot services, optional Groq Batch only for page-visible enrichment.

---

## 1. Intent

### What this plan is for
- Give a separate execution team a decision-complete implementation plan for local public repo-page data reuse.
- Avoid reparsing repositories that already have usable local DB coverage.
- Import only missing PRs, stale PRs, and missing related records from `.seeding_cache`.
- Keep Groq usage narrowly scoped to public-page-visible functionality.
- Produce a local dataset that can be visually verified on `http://localhost:8000`.

### What this plan is not for
- Not for moving the local DB to Unraid. That is a later, separate step.
- Not for production scheduling or live GitHub PAT sync.
- Not for broad historical LLM backfills.
- Not for prompt redesign or prompt-template edits under `apps/metrics/prompts/templates/*`.

### Product constraints
- Scope is local DB only.
- Existing local data must be reused first.
- `.seeding_cache` is the approved source of delta and repair data.
- Backup restore is fallback-only and must never overwrite the active local DB automatically.
- Public pages must still render meaningfully if Groq is disabled.

---

## 2. Verified Starting Point

These facts were verified in the current repo and local environment and should be treated as the implementation starting point.

### Schema and app state
- `public` migration `0003_public_repo_pages` exists but is not applied locally.
- The current repo-page routes fail locally until that migration is applied.

### Existing public org data in the local DB
- `polar` exists as a public org and has existing public-org stats.
- `posthog` exists as a public org and has existing public-org stats.
- Local DB already contains substantial PR data for both orgs.

### Existing cache coverage in `.seeding_cache`
- `polarsource/polar`
- `polarsource/polar-adapters`
- `polarsource/polar-js`
- `polarsource/polar-python`
- `PostHog/posthog`
- `PostHog/posthog.com`
- `PostHog/posthog-js`
- `PostHog/posthog-python`

Each cache file has the structure:
- top-level keys: `repo`, `fetched_at`, `repo_pushed_at`, `since_date`, `prs`
- `prs[]` entries already include rich data: core PR fields, `reviews`, `commits`, `files`, `check_runs`, and per-PR `updated_at`

### Existing implementation that must be reused
- `apps.metrics.seeding.pr_cache.PRCache` already defines cache shape and paths.
- `apps.metrics.seeding.github_graphql_fetcher.GitHubGraphQLFetcher` already supports cache validation and incremental merge logic.
- `apps.metrics.seeding.real_project_seeder.RealProjectSeeder` already has richer PR persistence logic for:
  - `PullRequest`
  - `PRReview`
  - `Commit`
  - `PRFile`
  - `PRCheckRun`
  - `TeamMember` reuse
- `apps.public.public_sync` is currently too lossy because it only persists bare `PullRequest` rows.
- `apps.integrations.services.groq_batch.GroqBatchProcessor` already exists and is the only approved Groq interface for this work.

---

## 3. Fixture Set For Local Verification

Use these orgs and repo mappings for this phase. Do not let the execution team improvise different repo slugs or flagship assignments.

### Polar
- Org slug: `polar`
- Flagship repo:
  - `polarsource/polar` -> `repo_slug="polar"`
- Secondary repos:
  - `polarsource/polar-adapters` -> `repo_slug="polar-adapters"`
  - `polarsource/polar-js` -> `repo_slug="polar-js"`
  - `polarsource/polar-python` -> `repo_slug="polar-python"`

### PostHog
- Org slug: `posthog`
- Flagship repo:
  - `PostHog/posthog` -> `repo_slug="posthog"`
- Secondary repos:
  - `PostHog/posthog.com` -> `repo_slug="posthog-com"`
  - `PostHog/posthog-js` -> `repo_slug="posthog-js"`
  - `PostHog/posthog-python` -> `repo_slug="posthog-python"`

### Visibility defaults
- Flagship repos are featured on the org hub.
- Secondary repos are public and routable but not featured above the fold.
- No additional orgs or repos are in scope for v1 of this local reuse flow.

---

## 4. Success Criteria

The work is complete only when all of the following are true:

1. The local DB can be reconciled from existing DB rows plus `.seeding_cache` without live GitHub calls.
2. Running the reconciliation flow twice with unchanged inputs does not duplicate PRs or related records.
3. Missing PRs and partial PR child data are imported or repaired from cache.
4. `PublicRepoProfile`, `PublicRepoStats`, and `PublicRepoInsight` exist for the configured fixture repos.
5. Org and repo pages render on the local dev server without `500` errors.
6. Groq is not used by default, and when explicitly enabled it is capped and limited to public-page-visible needs.
7. The plan leaves Unraid export/import entirely out of scope.

---

## 5. Implementation Tasks

### Task 1: Add the orchestration command and fixture manifest

**Files**
- Create: `apps/public/management/commands/reconcile_public_repo_local_data.py`
- Create: `apps/public/services/local_reconciliation.py`
- Create: `apps/public/services/local_fixture_manifest.py`
- Test: `apps/public/tests/test_local_reconciliation_command.py`

**Requirements**
- Add one orchestration command:
  - `.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog`
- Supported options:
  - `--dry-run`
  - `--org <slug>` repeated
  - `--repo <owner/repo>` repeated
  - `--rebuild-snapshots`
  - `--with-llm`
  - `--max-llm-prs-per-repo` default `50`
  - `--allow-backup-fallback`
- Add a locked manifest of org -> repo mappings using the fixture set from Section 3.
- Fail fast with a clear error if migration `public 0003` is not applied.
- In dry-run mode, print a deterministic reconciliation summary without mutating the DB.

**Acceptance criteria**
- Dry-run returns exit code `0` when prerequisites are satisfied.
- Dry-run returns a non-zero exit code and a specific message if repo-page tables are missing.
- The command resolves fixture repos from the manifest when `--org` is used.
- The command can narrow to a subset when `--repo` is provided.

**TDD**
1. Write failing tests for:
   - missing migration handling
   - manifest resolution for `polar` and `posthog`
   - `--dry-run` path with no writes
2. Run:
   - `.venv/bin/pytest apps/public/tests/test_local_reconciliation_command.py -n 0`
3. Implement command parsing and fixture-manifest loading.
4. Re-run the same tests.

**Commit checkpoint**
- `git commit -m "feat: add local public repo reconciliation command shell"`

---

### Task 2: Implement read-only DB-vs-cache reconciliation analysis

**Files**
- Modify: `apps/public/services/local_reconciliation.py`
- Test: `apps/public/tests/test_local_reconciliation_analysis.py`

**Requirements**
- Build a pure analysis layer before any write logic.
- For each repo, load:
  - local DB PRs filtered by `(team, github_repo)`
  - cache file `.seeding_cache/<org>/<repo>.json`
- Produce a reconciliation report with:
  - `db_pr_count`
  - `cache_pr_count`
  - `ready_pr_count`
  - `missing_pr_count`
  - `stale_pr_count`
  - `partial_pr_count`
  - `unusable_repo` flag
  - `llm_candidate_count`

**Classification rules**
- `ready_repo`
  - DB merged PR count >= 70% of cache PR count
  - latest DB `merged_at` within 45 days of latest cached `merged_at`
  - no material child-record gaps in recent PRs
- `missing_pr`
  - no `PullRequest` exists for `(team, github_repo, github_pr_id)`
- `stale_pr`
  - cache `updated_at` > local `synced_at`
  - or one of these fields differs materially:
    - `title`, `body`, `state`, `pr_created_at`, `merged_at`
    - `additions`, `deletions`, `changed_files`
    - `is_draft`, `labels`, `milestone_title`, `assignees`, `linked_issues`
- `partial_pr`
  - PR exists, but cached child records are missing locally
- `unusable_repo`
  - cache missing and DB coverage is not good enough

**Child-record keys**
- PR: `(team_id, github_repo, github_pr_id)`
- review: `github_review_id`; if null, fallback to `(pull_request_id, reviewer_id, submitted_at, state)`
- commit: `(team_id, github_sha)`
- file: `(team_id, pull_request_id, filename)`
- check run: `(team_id, github_check_run_id)`

**Acceptance criteria**
- The analysis output correctly classifies each repo and PR.
- No database writes occur during analysis.
- No live GitHub or backup access occurs during analysis.

**TDD**
1. Write failing unit tests for:
   - repo readiness classification
   - missing/stale/partial PR classification
   - child-gap detection
2. Run:
   - `.venv/bin/pytest apps/public/tests/test_local_reconciliation_analysis.py -n 0`
3. Implement pure analysis helpers.
4. Re-run the same tests.

**Commit checkpoint**
- `git commit -m "feat: add db vs cache reconciliation analysis for public repos"`

---

### Task 3: Extract a reusable rich persistence service from the real-project seeder

**Files**
- Create: `apps/metrics/seeding/persistence.py`
- Modify: `apps/metrics/seeding/real_project_seeder.py`
- Modify: `apps/public/services/local_reconciliation.py`
- Test: `apps/public/tests/test_local_reconciliation_persistence.py`

**Requirements**
- Do not extend `apps/public/public_sync.py` into a second seeding system.
- Extract PR + child persistence from `RealProjectSeeder` into a reusable service.
- Reuse that service from the local reconciliation flow.

**Behavior**
- Reuse `TeamMember` rows by GitHub ID or username before creating new ones.
- Create missing PRs with all related rows.
- Update only stale PR core fields.
- Repair only missing child records for partial PRs.
- Never delete and recreate a PR just to fix missing children.
- Never overwrite unrelated local data when the existing row is already richer.
- Preserve unique-constraint-driven dedupe.

**Derived timing behavior**
- Use the same fetched PR dataclass flow so:
  - `first_review_at`
  - `cycle_time_hours`
  - `review_time_hours`
  can be reconstructed from cache payloads.
- If touched PRs still lack derived timing fields, run the existing timing backfill only for touched PR IDs, not the whole team.

**Acceptance criteria**
- Missing PRs are imported with reviews, commits, files, and check runs.
- Existing PRs are updated only when stale.
- Partial child data is repaired without destructive replacement.
- A second run writes zero duplicates.

**TDD**
1. Write failing integration tests for:
   - missing PR import
   - stale PR update
   - missing reviews/files/commits/check runs repair
   - rerun idempotency
2. Run:
   - `.venv/bin/pytest apps/public/tests/test_local_reconciliation_persistence.py -n 0`
3. Extract shared persistence functions.
4. Switch the local reconciliation service to use them.
5. Re-run the same tests.

**Commit checkpoint**
- `git commit -m "refactor: extract reusable PR persistence for cache reconciliation"`

---

### Task 4: Apply reconciliation and bootstrap public repo entities

**Files**
- Modify: `apps/public/services/local_reconciliation.py`
- Test: `apps/public/tests/test_local_reconciliation_bootstrap.py`

**Requirements**
- In apply mode, do the following in order:
  1. ensure `PublicRepoProfile` rows exist for the locked fixture mapping
  2. reconcile missing/stale/partial PR data from cache into the local DB
  3. rebuild only changed or missing `PublicRepoStats`
  4. rebuild only changed or missing parent `PublicOrgStats`
  5. generate deterministic local `PublicRepoInsight` rows from stored stats

**Bootstrap rules**
- Flagship repos:
  - `polarsource/polar`
  - `PostHog/posthog`
- Secondary repos are public but not featured.
- Rebuild repo snapshots only for changed repos or repos missing `PublicRepoStats`.
- Rebuild org stats only for orgs with changed repos or missing org stats.
- Deterministic local repo insights must not call Groq.

**Acceptance criteria**
- `PublicRepoProfile`, `PublicRepoStats`, and `PublicRepoInsight` exist for all configured fixture repos after apply mode.
- Org hubs and repo pages render from stored data.
- Unchanged repos do not trigger unnecessary snapshot writes.

**TDD**
1. Write failing tests for:
   - repo profile bootstrap
   - selective snapshot rebuild
   - deterministic local repo insights
2. Run:
   - `.venv/bin/pytest apps/public/tests/test_local_reconciliation_bootstrap.py -n 0`
3. Implement apply mode and selective rebuild behavior.
4. Re-run the same tests.

**Commit checkpoint**
- `git commit -m "feat: bootstrap public repo entities from local db and cache"`

---

### Task 5: Add Groq scoping logic but keep it disabled by default

**Files**
- Modify: `apps/public/services/local_reconciliation.py`
- Test: `apps/public/tests/test_local_reconciliation_llm_scope.py`

**Requirements**
- Default rule:
  - The reconciliation command does not use Groq unless `--with-llm` is explicitly passed.
- Use `GroqBatchProcessor` only.
- Never call:
  - `run_llm_analysis_batch`
  - `run_all_teams_llm_analysis`
  - `backfill_ai_detection_batch`
- Groq is allowed only for public-page-visible functionality.

**Allowed Groq targets**
- Snapshot-level repo insight generation for flagship repos only.
- PR-level enrichment only when the public page would be meaningfully degraded without `llm_summary`.

**PR-level scope**
- Flagship repos only by default.
- Only merged PRs from the last 90 days.
- Only PRs that:
  - appear in the repo recent-proof block,
  - appear on the first page of the repo PR explorer,
  - or are missing current `llm_summary` for visible explorer filters/labels
- Hard cap:
  - `50` PRs per repo per run
- Dry-run must report how many PRs would be sent to Groq and why.

**Fallback rule**
- If `llm_summary` is absent, public pages must still render using:
  - `is_ai_assisted`
  - `ai_tools_detected`
  - file-based categories
  - deterministic snapshot calculations

**Acceptance criteria**
- No Groq usage happens by default.
- With `--with-llm`, only scoped PRs are submitted.
- No batch is submitted for all PRs in a team or for all historical PRs in a repo.
- Pages still render with Groq disabled.

**TDD**
1. Write failing tests for:
   - LLM candidate selection
   - cap enforcement
   - zero-Groq default behavior
   - fallback page rendering with no `llm_summary`
2. Run:
   - `.venv/bin/pytest apps/public/tests/test_local_reconciliation_llm_scope.py -n 0`
3. Implement the scoping logic.
4. Re-run the same tests.

**Commit checkpoint**
- `git commit -m "feat: add scoped Groq policy for local public repo reconciliation"`

---

### Task 6: Add the local visual verification runbook

**Files**
- Modify: `docs/plans/2026-03-14-local-public-repo-incremental-reuse-plan.md`
- Optionally add Playwright QA notes to an adjacent doc if the team prefers separate QA documentation

**Required local sequence**
1. `.venv/bin/python manage.py showmigrations public`
2. `.venv/bin/python manage.py migrate public 0003`
3. `.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog --dry-run`
4. `.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog --rebuild-snapshots`
5. Optional scoped LLM pass:
   - `.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog --with-llm`
6. `make dev`

**Routes to verify**
- `/open-source/`
- `/open-source/polar/`
- `/open-source/polar/repos/polar/`
- `/open-source/polar/repos/polar-adapters/`
- `/open-source/polar/repos/polar/pull-requests/`
- `/open-source/posthog/`
- `/open-source/posthog/repos/posthog/`
- `/open-source/posthog/repos/posthog-js/`
- `/open-source/posthog/repos/posthog/pull-requests/`

**Playwright requirements**
- Use `http://localhost:8000`
- Save screenshots to `output/playwright/public-repo-local/`
- Desktop viewport: `1440x900`
- Mobile viewport: `390x844`

**Visual acceptance criteria**
- No `500` or missing-table errors.
- Org hubs render flagship repo cards.
- Repo pages render populated hero, citable summary, proof block, and charts.
- PR explorer pages show repo-scoped rows, not org-scoped rows.
- Pages do not collapse into all-zero metrics unless the underlying repo genuinely has no usable data.

**Commit checkpoint**
- `git commit -m "docs: add local public repo reconciliation runbook"`

---

## 6. Cross-Cutting Acceptance Criteria

The execution team must not mark this work complete unless all of the following are true:

- Existing local DB data is reused as the first source.
- `.seeding_cache` is only used for delta import and repair, not wholesale reparse.
- No live GitHub fetch is used anywhere in this local flow.
- No automatic backup restore occurs unless explicitly enabled.
- No duplicate PRs or child records are created on rerun.
- Public repo profiles, stats, and insights exist for the configured fixture repos.
- The local dev server renders the selected org and repo pages successfully.
- Groq remains opt-in and narrowly scoped.

---

## 7. Test Plan

### New test modules
- `apps/public/tests/test_local_reconciliation_command.py`
- `apps/public/tests/test_local_reconciliation_analysis.py`
- `apps/public/tests/test_local_reconciliation_persistence.py`
- `apps/public/tests/test_local_reconciliation_bootstrap.py`
- `apps/public/tests/test_local_reconciliation_llm_scope.py`

### Minimum scenarios
- missing migration causes command failure
- dry-run with ready repo
- dry-run with missing PRs
- import from cache creates only missing PRs
- stale PR core fields update in place
- partial PR child rows are repaired
- rerun is idempotent
- selective snapshot rebuild
- deterministic repo insight generation without Groq
- scoped Groq batch selection with cap
- pages render with Groq disabled
- pages render after reconciliation with repo routes returning `200`

### Required verification commands
- `.venv/bin/python manage.py check`
- `.venv/bin/pytest apps/public/tests -n 0`
- targeted reconciliation test modules during development
- visual Playwright pass on desktop and mobile after local bootstrap

---

## 8. Explicit Non-Goals

Do not include any of the following in this execution:
- exporting the local DB to Unraid
- importing into Unraid
- restoring the full backup into the active local DB automatically
- production scheduling or Celery orchestration for this local flow
- live GitHub API sync
- team-wide or full-history Groq backfills
- prompt-template edits under `apps/metrics/prompts/templates/*`

---

## 9. Local Visual Verification Runbook

### Setup sequence

```bash
# 1. Ensure migration is applied
.venv/bin/python manage.py showmigrations public
.venv/bin/python manage.py migrate public

# 2. Dry-run analysis (no writes)
.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog --dry-run

# 3. Full reconciliation with snapshot rebuild
.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog --rebuild-snapshots

# 4. (Optional) Scoped LLM enrichment for flagship repos
.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog --with-llm

# 5. Verify idempotency (second run should report zero changes)
.venv/bin/python manage.py reconcile_public_repo_local_data --org polar --org posthog --rebuild-snapshots

# 6. Start dev server
make dev
```

### Routes to verify

| Route | Expected |
|-------|----------|
| `/open-source/` | Directory with polar + posthog orgs |
| `/open-source/polar/` | Org hub with flagship repo card |
| `/open-source/polar/repos/polar/` | Repo detail with hero, stats, charts |
| `/open-source/polar/repos/polar-adapters/` | Secondary repo page |
| `/open-source/polar/repos/polar/pull-requests/` | PR explorer (repo-scoped) |
| `/open-source/posthog/` | Org hub with flagship repo card |
| `/open-source/posthog/repos/posthog/` | Repo detail page |
| `/open-source/posthog/repos/posthog-js/` | Secondary repo page |
| `/open-source/posthog/repos/posthog/pull-requests/` | PR explorer (repo-scoped) |

### Visual acceptance criteria

- No 500 or missing-table errors on any route
- Org hubs render flagship repo cards
- Repo pages render populated hero, citable summary, proof block, and charts
- PR explorer pages show repo-scoped rows, not org-scoped rows
- Pages do not collapse into all-zero metrics unless the underlying repo genuinely has no usable data
- Pages render meaningfully without `llm_summary` (fallback to `is_ai_assisted`, `ai_tools_detected`, file categories)

### Playwright screenshot capture

```bash
# Desktop viewport (1440x900)
# Mobile viewport (390x844)
# Save to output/playwright/public-repo-local/
```

---

## 10. Final Handoff Notes

- This plan is for a separate execution team.
- The expected implementation style is TDD-first, idempotent, and reuse-first.
- The execution team should treat `.seeding_cache` as the controlled source of delta data, not as a reason to rebuild everything.
- If the team discovers that a repo cannot be repaired from DB + cache alone, they must stop and document the gap before attempting backup-based recovery or any live GitHub fetch.
