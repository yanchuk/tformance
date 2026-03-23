# Public Repo Catalog, Benchmarks, SEO/GEO, and Unraid Transition Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make public repo parsing, public page UX, SEO/GEO metadata, and Unraid operations fully DB-driven, predictable, and editable from Django Admin without code edits.

**Architecture:** Use `PublicRepoProfile` as the single source of truth for public repos, add explicit sync state in the DB, run daily delta sync for all public repos, and keep flagship-only weekly Groq insights. Canonical pages remain server-rendered and citation-friendly; `/analytics/` becomes a support page, not a competing search surface.

**Tech Stack:** Django public app, Django Admin, Celery, PostgreSQL, Redis, HTMX, Chart.js, Pillow for OG generation, Cloudflare Tunnel, Docker Compose on Unraid.

---

## Verified Current State
- Public sync currently fetches `last 90 days` with `max_prs=500` per repo via `apps/public/public_sync.py`.
- Public summary/trend windows are currently `30 days` and `90 days` via `apps/public/views/helpers.py`.
- Daily sync and weekly insight jobs currently target only `is_flagship=True` repos via `apps/public/tasks.py`.
- Repo selection is currently duplicated across DB rows, `real_projects.py`, and `local_fixture_manifest.py`.
- `/open-source/<org>/analytics/` currently uses “Read-only analytics” in visible copy and metadata.
- `docker-compose.unraid.yml` currently lacks `GITHUB_SEEDING_TOKENS`, a site-domain bootstrap step, and a persistent media volume for generated OG images.

## Locked Decisions
- `PublicRepoProfile` becomes the only source of truth for the public repo catalog.
- Django Admin is the primary editing surface for public repo configuration.
- New public repos added in Admin are picked up automatically on the next scheduled sync.
- New repos receive a retrospective backfill of `180 days` by default.
- Daily sync runs for all repos where `is_public=True` and `sync_enabled=True`.
- `is_flagship` controls prominence and weekly insight generation only.
- Main org/repo pages keep `90-day` trend charts; deeper history may exist in storage but is not the default chart window.
- Weekly Groq insights remain `flagship only`.
- No public PR-wide Groq reanalysis or historical PR review is allowed in this phase.
- `/open-source/` becomes `benchmark-first + sortable table`.
- `/open-source/<org>/analytics/` remains available but is `support-only`, `noindex,follow`, and canonical to the primary org or repo page.
- Dynamic OG images are implemented with `Pillow`, cached under `MEDIA_ROOT`, and invalidated after stats refresh.
- Unraid runs split Celery workers by queue to control GitHub API pressure.

## Required TDD Workflow For Every Task
1. Write the failing targeted test first.
2. Run the narrowest test with `.venv/bin/pytest -n 0`.
3. Implement the minimum change.
4. Re-run the targeted test.
5. Run the task verification set.
6. Commit before starting the next task.

---

### Task 1: Make the Public Repo Catalog DB-Driven

**User story:** As an operator, I can add, edit, pause, and prioritize public repos in Django Admin, and those changes become effective on the next scheduled sync without code edits.

**Files**
- Modify: `apps/public/models.py`
- Modify: `apps/public/admin.py`
- Create: `apps/public/migrations/00xx_public_repo_catalog_state.py`
- Create: `apps/public/tests/test_public_repo_catalog_admin.py`

**Implementation requirements**
- Keep `PublicRepoProfile` as the canonical catalog row.
- Add fields to `PublicRepoProfile`:
  - `sync_enabled` default `True`
  - `insights_enabled` default `False`, seeded from `is_flagship`
  - `initial_backfill_days` default `180`
  - `display_order` default `0`
- Add `PublicRepoSyncState` one-to-one model with:
  - `status` = `pending_backfill|ready|syncing|failed`
  - `last_successful_sync_at`
  - `last_attempted_sync_at`
  - `last_synced_updated_at`
  - `checkpoint_payload` JSON
  - `last_error`
  - `last_backfill_completed_at`
- In Admin:
  - `org_profile` is editable
  - `team` is derived from `org_profile.team` and not user-editable
  - `repo_slug` and `github_repo` are editable only before first successful sync
  - `display_name`, `description`, `is_public`, `is_flagship`, `sync_enabled`, `insights_enabled`, `initial_backfill_days`, `display_order` stay editable
- Visibility rule:
  - `is_public` controls whether a repo is routable
  - `sync_enabled` controls whether future syncs run
  - if `is_public=True` and a valid snapshot exists, the page stays visible even if `sync_enabled=False`
  - if no valid snapshot exists yet, the page must not render publicly

**Acceptance criteria**
- A repo created in Admin produces a `PublicRepoProfile` row and a `PublicRepoSyncState` row.
- A change to `is_flagship` changes org-hub prominence and weekly insight eligibility on the next run.
- A change to `sync_enabled` changes sync eligibility on the next run.
- A change to `display_name` or `description` appears on the next page render.
- The team cannot drift from the selected org profile.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_repo_catalog_admin.py -n 0`
- Manual admin scenario:
  - create a new repo row
  - reload admin list
  - confirm sync state row exists
  - edit `is_flagship`, `sync_enabled`, `display_name`
  - confirm saved values persist

---

### Task 2: Change Public Sync to Daily-All-Public With Automatic Backfill

**User story:** As an operator, when I add a new public repo, the next sync automatically backfills enough history for public pages; when I update an existing repo config, the next sync respects it.

**Files**
- Modify: `apps/public/tasks.py`
- Modify: `apps/public/public_sync.py`
- Modify: `apps/public/repo_snapshot_service.py`
- Create: `apps/public/tests/test_public_repo_sync_orchestration.py`

**Implementation requirements**
- Daily public sync selection must query `PublicRepoProfile` fresh every run and include all rows where:
  - `is_public=True`
  - `sync_enabled=True`
- Stop filtering daily sync by `is_flagship`.
- Keep weekly insight generation filtered to `insights_enabled=True`.
- Initial sync behavior for `pending_backfill` repos:
  - fetch up to `180 days` of history
  - use a hard cap of `2000` PRs per backfill pass
  - if the cap is hit, persist resume state in `checkpoint_payload` and continue in later runs
- Incremental sync behavior for `ready` repos:
  - fetch from `last_synced_updated_at - 7 days`
  - max `500` PRs per pass
  - if missed window > `30 days`, switch to bounded recovery backfill
- Use `PRPersistenceService` for create/update/repair; do not implement a second write path.
- Keep `fetch_check_runs=False` for the public pipeline in this phase.
- After sync:
  - rebuild repo snapshots for all changed public repos
  - rebuild affected org stats
  - invalidate public cache
  - invalidate impacted OG images
- `compute_public_stats_task` must build snapshots for all public repos with valid snapshots, not just flagship repos.

**Acceptance criteria**
- A new Admin-created public repo is picked up automatically on the next scheduled sync.
- New repos backfill `180 days` by default.
- Existing repos use delta sync with overlap, not a full refetch.
- Secondary public repos stay fresh daily.
- Weekly insights remain flagship-only unless `insights_enabled=True` is explicitly set.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_repo_sync_orchestration.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_public_sync_tasks.py -n 0`
- Dry verification in shell:
  - create a public repo with `pending_backfill`
  - run sync task in test context
  - assert sync state transitions to `ready`
  - assert repo snapshot exists

---

### Task 3: Remove Catalog Drift Between DB, Demo Seeding, and Local Fixtures

**User story:** As a developer, I can bootstrap local demo data without silently overwriting the curated public repo catalog.

**Files**
- Modify: `apps/public/services/local_reconciliation.py`
- Modify: `apps/public/management/commands/reconcile_public_repo_local_data.py`
- Create: `apps/public/management/commands/bootstrap_public_repo_fixtures.py`
- Modify: `apps/public/services/local_fixture_manifest.py`
- Modify: `apps/metrics/seeding/real_projects.py`
- Create: `apps/public/tests/test_local_catalog_bootstrap.py`

**Implementation requirements**
- `real_projects.py` remains demo seeding config only.
- `local_fixture_manifest.py` remains bootstrap-only fixture config only.
- `reconcile_public_repo_local_data` must stop treating the manifest as the active catalog.
- Add `bootstrap_public_repo_fixtures`:
  - create missing `PublicRepoProfile` rows from the fixture manifest
  - never overwrite existing curated fields unless `--force-overwrite` is passed
- `reconcile_public_repo_local_data` must:
  - resolve repos from DB rows
  - never overwrite `display_name`, `description`, `is_public`, `is_flagship`, `sync_enabled`, `insights_enabled`
  - only repair missing data and snapshots

**Acceptance criteria**
- Running local reconciliation no longer resets curated repo profile edits.
- Fixture bootstrap can create missing local rows for `polar` and `posthog`.
- Public recurring behavior no longer depends on Python manifests.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_local_catalog_bootstrap.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_local_reconciliation_command.py -n 0`
- Manual local scenario:
  - edit `display_name` in Admin
  - run reconciliation
  - confirm the edit remains intact

---

### Task 4: Redesign `/open-source/` Into Benchmark-First + Sortable Table

**User story:** As a CTO comparing OSS teams, I land on `/open-source/`, see the market-level story immediately, and then sort the table by the metric I care about.

**Files**
- Modify: `apps/public/views/directory_views.py`
- Modify: `apps/public/services/analytics.py`
- Modify: `templates/public/directory.html`
- Modify: `templates/public/_directory_list.html`
- Create: `apps/public/tests/test_directory_benchmarks.py`
- Create: `apps/public/tests/test_directory_sorting.py`

**Implementation requirements**
- Keep `/open-source/` indexable and canonical.
- Page order:
  1. headline + citable benchmark sentence
  2. three benchmark charts
  3. sortable comparison table
  4. CTA
- Required charts:
  - 12-week dual-axis global trend: AI adoption % + median cycle time
  - industry benchmark bars: average AI adoption and cycle time by industry
  - org quadrant/scatter: AI adoption on X, cycle time on Y, point size by PR volume
- Table sorting must be server-side.
- Header click behavior:
  - clicking a sortable header toggles asc/desc
  - active header shows direction indicator
  - filters persist
  - URL params remain the source of truth
- Keep dropdown sort only as mobile fallback.
- Directory summary text must remain server-rendered even if charts load via HTMX.

**Acceptance criteria**
- `/open-source/` is no longer just a table page.
- Users can sort by clicking column headers.
- Sorting preserves filters and pagination reset behavior is correct.
- Directory charts show real public benchmark data, not placeholder values.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_directory_benchmarks.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_directory_sorting.py -n 0`
- Playwright:
  - click `AI Adoption` header twice and verify desc/asc toggle
  - verify query string changes
  - verify table order changes

---

### Task 5: Normalize Public Org and Repo Chart Experience

**User story:** As a visitor, I can compare AI adoption and delivery speed at a glance because public charts are aligned, readable, and scoped correctly.

**Files**
- Modify: `apps/public/views/chart_views.py`
- Modify: `apps/public/repo_snapshot_service.py`
- Modify: `templates/public/org_analytics.html`
- Modify: `templates/public/repo_detail.html`
- Create: `templates/public/partials/public_chart_card.html`
- Create: `apps/public/tests/test_public_chart_layout_contract.py`

**Implementation requirements**
- Add one reusable chart card layout contract:
  - fixed title area height
  - fixed subtitle area height
  - fixed chart body min-height
  - same canvas height for paired charts
- Org analytics support page must include:
  - combined AI adoption + cycle time trend
  - AI vs non-AI delivery impact comparison
  - PR size distribution
  - top AI tools detected
  - team health indicators
- Repo detail page must include:
  - combined repo-scoped AI adoption + cycle time trend
  - repo-scoped AI vs non-AI impact block
  - repo-scoped AI tools breakdown
  - recent PR proof block
- Do not add internal-only public charts in this phase:
  - reviewer correlations
  - Jira/story-point correlation
  - Copilot seat utilization
- All public charts must respect repo filtering where applicable.

**Acceptance criteria**
- In paired chart rows, chart titles and chart canvases align to the same top baseline.
- Repo charts are repo-scoped, not org-scoped.
- The combined trend chart is present on both repo pages and analytics support pages.
- No internal-only charts leak into public pages.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_chart_layout_contract.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_repo_snapshot_service.py -n 0`
- Playwright visual checks:
  - `/open-source/polar/analytics/`
  - `/open-source/polar/repos/polar/`
  - confirm chart rows start at same vertical position
  - confirm combined chart renders with both series and legend

---

### Task 6: Reposition `/analytics/` Pages and Fix Metadata/Structured Data

**User story:** As a search engine or AI crawler, I understand which page is canonical and I never see “read-only dashboard” framing on public benchmark pages.

**Files**
- Modify: `apps/public/views/analytics_views.py`
- Modify: `apps/public/views/org_views.py`
- Modify: `apps/public/views/repo_views.py`
- Modify: `templates/public/org_analytics.html`
- Modify: `templates/web/base.html`
- Create: `apps/public/tests/test_public_metadata_strategy.py`

**Implementation requirements**
- Primary indexable pages:
  - `/open-source/`
  - `/open-source/<org>/`
  - `/open-source/<org>/repos/<repo>/`
- Support-only pages:
  - `/open-source/<org>/analytics/`
  - `/open-source/<org>/repos/<repo>/pull-requests/`
- Support-only pages must emit:
  - `<meta name="robots" content="noindex,follow">`
  - canonical to the primary org or repo page
- Remove “Read-only analytics” from:
  - visible copy
  - title
  - description
  - Twitter description
  - OG description
  - JSON-LD description
- Remove generic `meta keywords` from public pages entirely.
- Metadata formulas:
  - directory description: `Compare AI adoption, cycle time, and pull request velocity across {org_count}+ open source teams. Updated daily from public GitHub data.`
  - org description: `See {org} engineering benchmarks from {prs} merged PRs: {ai}% AI-assisted, {cycle}h median cycle time, and flagship repo performance.`
  - repo description: `Track {org}/{repo} delivery benchmarks from {prs} merged PRs: {ai}% AI-assisted, {cycle}h median cycle time, {review}h median review time. Updated daily.`
  - analytics support description: `Detailed {org} delivery and AI adoption trends across public GitHub pull requests.`
- Keep JSON-LD concise and page-specific.

**Acceptance criteria**
- No public metadata contains the phrase “read-only”.
- Support pages do not compete with canonical pages in search.
- Public page metadata is entity-specific and metric-specific.
- Public pages omit generic site-wide keywords.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_metadata_strategy.py -n 0`
- `curl -sL http://localhost:8000/open-source/polar/analytics/ | grep -E "<title>|description|canonical|robots|og:description|twitter:description"`
- expected:
  - no `read-only`
  - analytics page has `noindex,follow`
  - canonical points to primary page

---

### Task 7: Add Dynamic Per-Page OG Images

**User story:** As a visitor sharing a public page, I get a branded image with the org/repo identity and real benchmark numbers instead of a generic fallback image.

**Files**
- Modify: `pyproject.toml`
- Create: `apps/public/services/og_image_service.py`
- Create: `apps/public/views/og_views.py`
- Modify: `apps/public/urls.py`
- Modify: `templates/web/base.html`
- Create: `apps/public/tests/test_public_og_images.py`

**Implementation requirements**
- Add `Pillow` as a runtime dependency.
- Add OG routes:
  - `/og/open-source/<org_slug>.png`
  - `/og/open-source/<org_slug>/<repo_slug>.png`
- Render images with:
  - org logo from `PublicOrgProfile.logo_url` or GitHub avatar fallback
  - org name
  - repo name where applicable
  - AI adoption %
  - median cycle time
  - PR count
  - Tformance branding
- Cache generated images under `MEDIA_ROOT/public_og/`.
- Invalidate cached OG files when:
  - repo stats update
  - org stats update
  - org logo changes
  - repo display name changes
- Use page-specific OG image URLs in `og:image` and `twitter:image`.

**Acceptance criteria**
- Org pages and repo pages no longer use the generic site OG image.
- Generated images persist across container restarts.
- Missing org logos fall back cleanly.
- Regenerated images reflect updated metrics after refresh.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_og_images.py -n 0`
- Open:
  - `/og/open-source/polar.png`
  - `/og/open-source/polar/polar.png`
- Confirm images render and reflect the correct entity names and metrics

---

### Task 8: Make Unraid a Production-Ready Public Pipeline Runtime

**User story:** As an operator, I can move the existing local data to Unraid, keep parsing working there daily, and recover from missed syncs or rate limits without manual firefighting.

**Files**
- Modify: `docker-compose.unraid.yml`
- Modify: `.env.unraid.example`
- Modify: `dev/guides/UNRAID-DEPLOYMENT.md`
- Create: `apps/public/management/commands/bootstrap_site_domain.py`
- Create: `apps/public/management/commands/init_public_repo_sync_state.py`
- Create: `apps/public/management/commands/rebuild_public_catalog_snapshots.py`

**Implementation requirements**
- Update Unraid env template with:
  - `GITHUB_SEEDING_TOKENS`
  - `SITE_DOMAIN`
  - `SITE_NAME`
- Update web startup sequence:
  1. migrate
  2. `bootstrap_site_domain`
  3. `bootstrap_celery_tasks --remove-stale`
  4. start gunicorn
- Add persistent media volume for `MEDIA_ROOT` so OG images survive restarts.
- Split workers in Unraid compose:
  - `worker-sync` for `sync` queue, concurrency `3`
  - `worker-compute` for `compute,celery` queues, concurrency `4`
  - `worker-llm` for `llm` queue, concurrency `2`
  - keep separate `beat`
- Pass `GITHUB_SEEDING_TOKENS` to the sync worker.
- Migration from local DB to Unraid must use DB restore, not full public reparse.
- Migration order:
  1. backup local DB with `pg_dump -Fc`
  2. restore to Unraid Postgres
  3. run migrations
  4. run `init_public_repo_sync_state`
  5. run `rebuild_public_catalog_snapshots`
  6. run one controlled daily sync
  7. verify public routes and scheduled tasks
- Rate-limit policy:
  - use PAT pool from `GITHUB_SEEDING_TOKENS`
  - sync worker concurrency fixed at `3`
  - initial backfills are resumable
  - token exhaustion marks sync as deferred/retryable, not fatal
- Keep weekly Groq insight generation limited to flagship repos only.

**Acceptance criteria**
- Unraid has everything needed to run the public pipeline end-to-end.
- Existing local parsed data is reused after restore.
- Public sync works on Unraid without manual repo-code edits.
- New repos added later in Admin are picked up automatically on the next sync.
- Missed syncs recover by widening the window or resuming backfill.

**Verification**
- `docker compose -f docker-compose.unraid.yml config`
- `docker compose -f docker-compose.unraid.yml up -d`
- `docker ps | grep tformance`
- `docker logs tformance-worker-sync --tail 200`
- `docker exec -it tformance-web python manage.py check --deploy`
- `docker exec -it tformance-web python manage.py init_public_repo_sync_state`
- `docker exec -it tformance-web python manage.py rebuild_public_catalog_snapshots`

---

## Final Regression And Sign-Off Matrix
- `.venv/bin/python manage.py check`
- `.venv/bin/pytest apps/public/tests -n 0`
- `.venv/bin/pytest apps/metrics/tests/test_repo_filter.py -n 0`
- `.venv/bin/pytest apps/metrics/tests/dashboard/test_ai_impact.py -n 0`
- Playwright desktop/mobile:
  - `/open-source/`
  - `/open-source/polar/`
  - `/open-source/polar/repos/polar/`
  - `/open-source/polar/analytics/`
  - `/open-source/polar/repos/polar/pull-requests/`
- Metadata checks:
  - canonical roles
  - `noindex,follow` on support pages
  - no `read-only`
  - page-specific OG images
- Unraid checks:
  - sync worker consumes scheduled public sync jobs
  - compute worker rebuilds snapshots
  - llm worker handles weekly flagship insights only

## Assumptions And Explicit Non-Goals
- This plan changes the catalog/source-of-truth model, but does not remove demo seeding support.
- Public GitHub sync continues to use PATs, not GitHub App auth, in this phase.
- Public pages do not add Jira-based public charts in this phase.
- Public pages do not add reviewer correlation or seat-utilization charts in this phase.
- Public main pages stay focused on 90-day trends even though the ingestion depth becomes 180 days.
- The local DB is the migration source for the first Unraid rollout.
