# Public Repo Pages GTM Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build repo-first public pages as Tformance's primary SEO/GEO acquisition surface, with org pages as discovery hubs and PR explorer pages as secondary proof.

**Architecture:** Reuse the current `apps/public` foundation and existing metrics/integration mechanisms rather than building a parallel system. Canonical repo pages must be server-rendered from stored repo snapshots and weekly stored insights; org pages must route traffic into flagship repos; PR explorer pages must remain secondary and non-canonical.

**Tech Stack:** Django 5.2.9, Python 3.12, PostgreSQL, Celery + Redis, HTMX + Alpine.js + Tailwind/DaisyUI, Chart.js, GitHub GraphQL seeding fetchers, GitHub PAT token pooling, Groq Batch API.

---

## 1. Product Intent

### What this must do
- Turn the current public prototype into a repo-first acquisition system.
- Make `/open-source/<org_slug>/repos/<repo_slug>/` the primary indexable page type.
- Make `/open-source/<org_slug>/` a hub that helps visitors discover flagship repos.
- Keep `/open-source/<org_slug>/repos/<repo_slug>/pull-requests/` as secondary proof, not the main story.
- Reuse existing internals where they already solve the problem:
  - GitHub PAT-based fetchers
  - `GitHubTokenPool`
  - repo-filtered dashboard/PR services
  - Groq batch infrastructure
  - cache purge
  - public SEO plumbing
  - PR explorer mechanics

### What this must not do
- Do not build a second raw ingestion platform just for public pages.
- Do not make HTMX the source of truth for canonical content.
- Do not keep the current org overview / analytics / pull requests tabs as the primary GTM information architecture.
- Do not put weekly insight generation on live page render paths.

### Primary audience
- CTOs
- VPEs
- engineering managers
- technical founders
- open source maintainers evaluating whether Tformance can show meaningful engineering intelligence

### Acquisition intent
- Search and AI citation first
- shareable benchmark pages second
- product proof third

---

## 2. Starting Point In This Branch

The current branch already contains an `apps/public` prototype. Treat it as a usable foundation, not as the final product shape.

### Existing assets worth reusing
- [apps/public/models.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/models.py)
- [apps/public/services.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/services.py)
- [apps/public/tasks.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tasks.py)
- [apps/public/urls.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/urls.py)
- [apps/public/views/helpers.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/helpers.py)
- [apps/public/views/org_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/org_views.py)
- [apps/public/views/chart_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/chart_views.py)
- [apps/public/sitemaps.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/sitemaps.py)
- [templates/public/org_detail.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_detail.html)
- [templates/public/org_analytics.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_analytics.html)
- [templates/public/org_pr_list.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_pr_list.html)

### Current branch defects to fix first
- `compute_public_stats_task` exists but is not scheduled in [tformance/settings.py](/Users/yanchuk/Documents/GitHub/tformance/tformance/settings.py).
- Directory full-page caching can leak full HTML into HTMX partial requests.
- The current public UX is org-first and tab-first.
- Hero/summary metrics and chart sections use inconsistent time windows.
- Canonical content still leans too hard on live HTMX-loaded fragments.

### Existing shared mechanisms to reuse
- GitHub fetchers:
  - [apps/metrics/seeding/github_graphql_fetcher.py](/Users/yanchuk/Documents/GitHub/tformance/apps/metrics/seeding/github_graphql_fetcher.py)
  - [apps/metrics/seeding/github_token_pool.py](/Users/yanchuk/Documents/GitHub/tformance/apps/metrics/seeding/github_token_pool.py)
- Shared metrics services:
  - [apps/metrics/services/dashboard_service.py](/Users/yanchuk/Documents/GitHub/tformance/apps/metrics/services/dashboard_service.py)
  - [apps/metrics/services/pr_list_service.py](/Users/yanchuk/Documents/GitHub/tformance/apps/metrics/services/pr_list_service.py)
- Groq batch:
  - [apps/integrations/services/groq_batch.py](/Users/yanchuk/Documents/GitHub/tformance/apps/integrations/services/groq_batch.py)
- Current SEO docs:
  - [docs/plans/public-pages-seo-geo-requirements.md](/Users/yanchuk/Documents/GitHub/tformance/docs/plans/public-pages-seo-geo-requirements.md)
  - [docs/plans/public-page-marketing-review.md](/Users/yanchuk/Documents/GitHub/tformance/docs/plans/public-page-marketing-review.md)

---

## 3. Experience Contract

### Canonical URL model
- Directory: `/open-source/`
- Org hub: `/open-source/<org_slug>/`
- Canonical repo page: `/open-source/<org_slug>/repos/<repo_slug>/`
- Repo proof page: `/open-source/<org_slug>/repos/<repo_slug>/pull-requests/`

### Canonical page rules
- Repo page is canonical and indexable.
- Org page is indexable and should link prominently into flagship repos.
- Repo proof page must be `noindex,follow` and canonical back to the canonical repo page.
- Canonical repo pages must remain meaningful with JavaScript disabled.

### Time window rules
- Summary window: last 30 days
- Trend window: last 90 days
- All-time counts: trust/context only

### CTA rules
- Primary CTA: self-serve signup
- Secondary CTA: book demo
- Every canonical repo page needs both CTAs above the fold.

### Required narrative order for repo pages
1. Repo identity + updated timestamp + CTAs
2. One citable paragraph with explicit numbers
3. Main proof metrics
4. Trend section
5. Best signal and watchout signal
6. Technology / AI tools / PR type breakdown
7. Recent PR proof block
8. Methodology / source / freshness

### ASCII mockups

```text
Repo Page
+----------------------------------------------------------------------------------+
| Repo name / org / updated-at / primary CTA / demo CTA                            |
| "X% of PRs are AI-assisted... based on N merged PRs... faster/slower than peers" |
+---------------------------+---------------------------+--------------------------+
| Hero metric               | Best signal               | Watchout signal          |
| Cadence change            | Delivery speed            | Review pressure          |
+--------------------------------------+-------------------------------------------+
| Trend: cadence + AI adoption         | Trend: cycle time + review time          |
+--------------------------------------+-------------------------------------------+
| Tech breakdown                        | AI tools / PR types / critical details   |
+----------------------------------------------------------------------------------+
| Recent PR proof block -> "View repo PR explorer"                                 |
+----------------------------------------------------------------------------------+
| CTA / methodology / source / last refreshed                                      |
+----------------------------------------------------------------------------------+

Org Hub
+----------------------------------------------------------------------------------+
| Org summary / benchmark sentence / CTA                                            |
+----------------------------------------------------------------------------------+
| Flagship repo card | Flagship repo card | Flagship repo card                      |
| Repo insight       | Repo insight       | Repo insight                            |
+----------------------------------------------------------------------------------+
| View all qualifying repos / methodology / source                                  |
+----------------------------------------------------------------------------------+
```

---

## 4. Technical Guardrails

The implementation team must follow all of these.

- Use `.venv/bin/python` and `.venv/bin/pytest` for Django and test commands.
- Keep function-based views in `apps/public`.
- No inline `<script>` tags in HTMX partials.
- Do not call `asyncio.run()` in Django or Celery runtime code.
- Prefer reuse of `apps/metrics/services/*` over copy-pasted aggregations.
- If anything under `apps/metrics/prompts/templates/*` changes, get approval first and bump `PROMPT_VERSION`.
- Keep public-specific files small. Create focused modules instead of bloating `apps/public/services.py`.
- Do not create separate raw public PR/review/commit tables.
- Public orchestration may be separate; public mechanisms must be shared.
- Local QA must use `http://localhost:8000`, not `127.0.0.1`.

### Important not to forget
- Schedule public stats refresh.
- Fix HTMX/full-page cache separation.
- Keep repo pages meaningful without JS.
- Put the citable paragraph above the fold.
- Use weekly stored Groq Batch insights, not request-time insight generation.
- Use PAT pooling through `GITHUB_SEEDING_TOKENS`.
- Keep explorer pages secondary and non-canonical.

---

## 5. Definition Of Done

The work is done only when all of the following are true:

- Repo-first public pages exist and are reachable by canonical URLs.
- Org pages function as discovery hubs, not generic dashboard tabs.
- Public data refreshes automatically without manual operator intervention.
- Weekly stored repo insights are generated through Groq Batch.
- Canonical repo pages are fully meaningful with JS disabled.
- Sitemap and robots rules are correct for repo pages and org pages.
- PR explorer pages are clearly secondary and non-indexable.
- Public tests pass and targeted Playwright checks pass on one org and one flagship repo page.

---

## 6. Execution Order

Execute in this order. Do not skip ahead.

1. Stabilize the current public foundations.
2. Add repo-level public models and canonical routing.
3. Build stored repo snapshots from shared metric services.
4. Add PAT-based public sync orchestration using shared fetchers.
5. Add weekly Groq Batch repo insight generation.
6. Build the canonical repo landing page.
7. Rebuild org pages as discovery hubs.
8. Reuse PR explorer as secondary proof.
9. Harden SEO/GEO.
10. Run full QA and update dev docs for localhost preview.

---

## 7. Task 1: Stabilize Public Foundations

**Story:** As the team shipping public GTM pages, we need the current public app to behave consistently before we expand it.

**Files:**
- Modify: [tformance/settings.py](/Users/yanchuk/Documents/GitHub/tformance/tformance/settings.py)
- Modify: [apps/public/views/directory_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/directory_views.py)
- Modify: [apps/public/views/helpers.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/helpers.py)
- Modify: [apps/public/views/chart_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/chart_views.py)
- Modify: [templates/public/org_detail.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_detail.html)
- Modify: [templates/public/org_analytics.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_analytics.html)
- Test: [apps/public/tests/test_directory_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tests/test_directory_views.py)
- Test: [apps/public/tests/test_chart_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tests/test_chart_views.py)
- Test: [apps/public/tests/test_foundations.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tests/test_foundations.py)

**Acceptance criteria:**
- `compute_public_stats_task` is scheduled daily.
- HTMX directory partials are never polluted by cached full-page HTML.
- Public summary window is fixed at 30 days.
- Public trend window is fixed at 90 days.
- Current public test suite passes after the fixes.

**Technical requirements:**
- Do not add a second scheduler.
- Cache either full pages and partials separately or leave the HTMX directory partial uncached.
- Keep chart partials reusable, but make their default window explicit.

**Step 1: Write the failing tests**

```python
def test_public_stats_task_is_scheduled():
    scheduled = [
        config for config in SCHEDULED_TASKS.values()
        if config["task"] == "apps.public.tasks.compute_public_stats_task"
    ]
    assert len(scheduled) == 1


def test_directory_htmx_partial_not_poisoned_by_cached_full_page(client):
    client.get(reverse("public:directory"))
    response = client.get(reverse("public:directory"), HTTP_HX_REQUEST="true")
    assert "<!DOCTYPE" not in response.content.decode()
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_foundations.py apps/public/tests/test_directory_views.py::PublicDirectoryViewsTests::test_directory_htmx_partial_not_poisoned_by_cached_full_page -n 0
```

Expected:
- schedule test fails because `compute_public_stats_task` is missing from `SCHEDULED_TASKS`
- cache regression fails because cached full HTML is returned to HTMX

**Step 3: Write minimal implementation**
- Add the scheduled task entry in `SCHEDULED_TASKS`.
- Add public window constants/helpers.
- Remove or separate `@cache_page` behavior on the directory route.
- Update current org pages to use explicit 30-day summary URLs and 90-day trend URLs.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_foundations.py apps/public/tests/test_directory_views.py apps/public/tests/test_chart_views.py -n 0
```

Expected:
- all targeted tests pass

**Step 5: Commit**

```bash
git add tformance/settings.py apps/public/views/directory_views.py apps/public/views/helpers.py apps/public/views/chart_views.py templates/public/org_detail.html templates/public/org_analytics.html apps/public/tests/test_directory_views.py apps/public/tests/test_chart_views.py apps/public/tests/test_foundations.py
git commit -m "fix: stabilize public page scheduling and cache behavior"
```

---

## 8. Task 2: Add Repo-Level Public Models And Canonical Routing

**Story:** As a visitor, I need a stable repo page, not a loose org dashboard tab.

**Files:**
- Modify: [apps/public/models.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/models.py)
- Create: `apps/public/migrations/0003_public_repo_pages.py`
- Modify: [apps/public/urls.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/urls.py)
- Modify: [apps/public/decorators.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/decorators.py)
- Create: `apps/public/tests/test_repo_models.py`
- Create: `apps/public/tests/test_repo_urls.py`

**Acceptance criteria:**
- `PublicRepoProfile`, `PublicRepoStats`, and `PublicRepoInsight` exist.
- Repo routes resolve under `/open-source/<org_slug>/repos/<repo_slug>/`.
- Only public flagship repos are allowed on canonical repo pages.
- Repo proof pages exist under `/pull-requests/`.

**Technical requirements:**
- Keep repo identity tied to existing `team` plus `github_repo`.
- `repo_slug` must be unique per org.
- Do not add a parallel org model; build on `PublicOrgProfile`.

**Step 1: Write the failing tests**

```python
def test_repo_slug_must_be_unique_within_org():
    PublicRepoProfile.objects.create(org_profile=org, team=team, github_repo="org/a", repo_slug="repo")
    with pytest.raises(IntegrityError):
        PublicRepoProfile.objects.create(org_profile=org, team=team, github_repo="org/b", repo_slug="repo")


def test_repo_detail_route_resolves():
    match = resolve("/open-source/posthog/repos/posthog/")
    assert match.url_name == "repo_detail"
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_models.py apps/public/tests/test_repo_urls.py -n 0
```

Expected:
- model imports fail or route resolution fails because repo models and repo URLs do not exist

**Step 3: Write minimal implementation**
- Add repo models to `apps/public/models.py`.
- Generate and inspect migration.
- Add repo and repo proof URLs.
- Add a decorator/helper for resolving a public repo from org slug + repo slug.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_models.py apps/public/tests/test_repo_urls.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/models.py apps/public/migrations/0003_public_repo_pages.py apps/public/urls.py apps/public/decorators.py apps/public/tests/test_repo_models.py apps/public/tests/test_repo_urls.py
git commit -m "feat: add public repo models and canonical routing"
```

---

## 9. Task 3: Build Repo Snapshot Services From Shared Metrics

**Story:** As a visitor, I need one coherent repo story built from stored metrics, not live tab fragments.

**Files:**
- Create: `apps/public/repo_snapshot_service.py`
- Create: `apps/public/repo_benchmark_service.py`
- Modify: [apps/public/models.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/models.py)
- Test: `apps/public/tests/test_repo_snapshot_service.py`

**Acceptance criteria:**
- `PublicRepoStats` stores the payload required to render the repo page.
- Summary metrics are based on the last 30 days.
- Trend payloads are based on the last 90 days.
- Benchmark comparison, best signal, watchout signal, cadence change, and tool/type breakdowns are precomputed.

**Technical requirements:**
- Reuse existing dashboard services for repo-filtered metrics.
- Store page-driving payloads in JSON fields instead of recomputing everything at page render.
- Keep all-time counts as trust/context only.

**Step 1: Write the failing tests**

```python
def test_snapshot_builder_uses_30_day_summary_window():
    snapshot = build_repo_snapshot(repo_profile)
    assert snapshot.summary_window_days == 30


def test_snapshot_builder_stores_best_and_watchout_signals():
    snapshot = build_repo_snapshot(repo_profile)
    assert snapshot.best_signal
    assert snapshot.watchout_signal
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_snapshot_service.py -n 0
```

**Step 3: Write minimal implementation**
- Create a snapshot builder that:
  - computes 30-day summary metrics
  - computes 90-day trend series
  - computes benchmark/rank context
  - serializes page payloads into `PublicRepoStats`
- Use `dashboard_service` and repo filters instead of custom query duplication.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_snapshot_service.py apps/metrics/tests/test_repo_filter.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/repo_snapshot_service.py apps/public/repo_benchmark_service.py apps/public/models.py apps/public/tests/test_repo_snapshot_service.py
git commit -m "feat: add stored public repo snapshots"
```

---

## 10. Task 4: Add PAT-Based Public Sync Orchestration Using Shared Fetchers

**Story:** As an operator, I need public OSS refreshes isolated from customer sync health without a duplicate ingestion stack.

**Files:**
- Modify: [apps/public/tasks.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tasks.py)
- Create: `apps/public/public_sync.py`
- Modify: [tformance/settings.py](/Users/yanchuk/Documents/GitHub/tformance/tformance/settings.py)
- Test: `apps/public/tests/test_public_sync_tasks.py`

**Acceptance criteria:**
- A daily public sync task exists for public flagship repos.
- The task uses `GITHUB_SEEDING_TOKENS`.
- The task reuses `GitHubGraphQLFetcher` and `GitHubTokenPool`.
- The task writes into existing metrics/member/PR storage for public/demo teams.

**Technical requirements:**
- Do not create parallel public raw data tables.
- Keep orchestration in `apps/public`, but use shared fetcher logic from `apps/metrics/seeding/*`.
- Make failure handling explicit when all PATs are exhausted.

**Step 1: Write the failing tests**

```python
@patch("apps.public.tasks.GitHubTokenPool")
@patch("apps.public.tasks.GitHubGraphQLFetcher")
def test_public_sync_uses_pat_pool(mock_fetcher, mock_pool):
    sync_public_oss_repositories_task()
    mock_pool.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_public_sync_tasks.py -n 0
```

**Step 3: Write minimal implementation**
- Add a public sync task that loops over `PublicRepoProfile` records.
- Use the shared PAT pool and shared GraphQL fetcher.
- Persist into the existing public/demo team data path.
- Schedule the task before snapshot recomputation.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_public_sync_tasks.py apps/metrics/tests/test_github_graphql_fetcher.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/tasks.py apps/public/public_sync.py tformance/settings.py apps/public/tests/test_public_sync_tasks.py
git commit -m "feat: add public PAT sync orchestration"
```

---

## 11. Task 5: Generate Weekly Repo Insights Via Groq Batch

**Story:** As a visitor, I want one high-signal narrative insight on the repo page, but the business needs low LLM cost.

**Files:**
- Modify: [apps/public/tasks.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tasks.py)
- Create: `apps/public/repo_insight_service.py`
- Modify: [apps/public/models.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/models.py)
- Test: `apps/public/tests/test_repo_insight_tasks.py`

**Acceptance criteria:**
- Weekly repo insights are generated through `GroqBatchProcessor`.
- Input payloads are built from stored repo snapshots.
- `PublicRepoInsight` stores the latest successful insight.
- If a generation run fails, the previous successful insight remains available.

**Technical requirements:**
- Reuse `GroqBatchProcessor`.
- Do not use per-request live LLM calls.
- Avoid prompt template changes unless separately approved.

**Step 1: Write the failing tests**

```python
@patch("apps.public.tasks.GroqBatchProcessor")
def test_weekly_repo_insight_generation_uses_batch(mock_processor):
    generate_public_repo_insights_weekly()
    mock_processor.assert_called_once()


def test_repo_page_uses_previous_successful_insight_when_latest_fails():
    ...
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_insight_tasks.py -n 0
```

**Step 3: Write minimal implementation**
- Build a batch input payload from `PublicRepoStats`.
- Submit the batch.
- Persist success/failure state in `PublicRepoInsight`.
- Schedule weekly insight generation.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_insight_tasks.py apps/integrations/tests/test_llm_batch_task.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/tasks.py apps/public/repo_insight_service.py apps/public/models.py apps/public/tests/test_repo_insight_tasks.py
git commit -m "feat: add weekly public repo insights via groq batch"
```

---

## 12. Task 6: Build The Canonical Repo Landing Page

**Story:** As a CTO landing from search, I need to immediately see why this repo matters and what Tformance reveals.

**Files:**
- Create: `apps/public/views/repo_views.py`
- Modify: [apps/public/views/__init__.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/__init__.py)
- Modify: [apps/public/urls.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/urls.py)
- Create: `templates/public/repo_detail.html`
- Create: `templates/public/partials/repo_metric_cards.html`
- Create: `templates/public/partials/repo_breakdowns.html`
- Test: `apps/public/tests/test_repo_views.py`
- Test: `apps/public/tests/test_repo_geo.py`

**Acceptance criteria:**
- Repo identity, timestamp, signup CTA, and demo CTA appear above the fold.
- A citable paragraph appears before charts or deep detail.
- The page renders from stored snapshot data.
- The page remains meaningful with JS disabled.
- The page does not look like a copied internal dashboard.

**Technical requirements:**
- Reuse shared styling patterns but do not preserve the tab-first layout.
- Server-render all canonical content.
- Use HTMX only for optional enhancement, never for required narrative content.

**Step 1: Write the failing tests**

```python
def test_repo_detail_renders_citable_summary_and_primary_cta(client):
    response = client.get(reverse("public:repo_detail", kwargs={"slug": "posthog", "repo_slug": "posthog"}))
    assert "Start Free Trial" in response.content.decode()
    assert "based on" in response.content.decode()


def test_repo_detail_is_meaningful_without_js(client):
    response = client.get(...)
    assert "<table" in response.content.decode() or "Methodology" in response.content.decode()
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_views.py apps/public/tests/test_repo_geo.py -n 0
```

**Step 3: Write minimal implementation**
- Add repo detail view.
- Build the template around stored snapshot and insight content.
- Add methodology/source/freshness line.
- Add link to repo proof page.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_views.py apps/public/tests/test_repo_geo.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/views/repo_views.py apps/public/views/__init__.py apps/public/urls.py templates/public/repo_detail.html templates/public/partials/repo_metric_cards.html templates/public/partials/repo_breakdowns.html apps/public/tests/test_repo_views.py apps/public/tests/test_repo_geo.py
git commit -m "feat: add canonical public repo landing pages"
```

---

## 13. Task 7: Rebuild Org Pages As Discovery Hubs

**Story:** As a visitor exploring an OSS company, I need the org page to help me discover flagship repos instead of decoding a generic dashboard.

**Files:**
- Modify: [apps/public/views/org_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/org_views.py)
- Modify: [templates/public/org_detail.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_detail.html)
- Delete or demote usage in: [templates/public/org_analytics.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_analytics.html)
- Test: `apps/public/tests/test_org_hub_views.py`
- Modify: [apps/public/tests/test_navigation.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tests/test_navigation.py)

**Acceptance criteria:**
- Org page leads with an org-level benchmark sentence.
- Flagship repo cards are the main content.
- Repo cards surface a clear hook such as adoption, cadence, or watchout.
- The old overview/analytics tabs are removed or visibly demoted.

**Technical requirements:**
- Reuse current public org profile/stat data.
- Use stored repo snapshots to populate cards.
- Do not send users into an org analytics dead-end.

**Step 1: Write the failing tests**

```python
def test_org_hub_prioritizes_flagship_repo_cards():
    response = client.get(reverse("public:org_detail", kwargs={"slug": "posthog"}))
    assert "Explore Flagship Repositories" in response.content.decode()
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_org_hub_views.py apps/public/tests/test_navigation.py -n 0
```

**Step 3: Write minimal implementation**
- Replace the tab-first org page with a discovery-hub layout.
- Demote or remove the analytics tab pattern.
- Link org cards directly to repo landing pages.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_org_hub_views.py apps/public/tests/test_navigation.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/views/org_views.py templates/public/org_detail.html templates/public/org_analytics.html apps/public/tests/test_org_hub_views.py apps/public/tests/test_navigation.py
git commit -m "feat: turn public org pages into discovery hubs"
```

---

## 14. Task 8: Reuse PR Explorer As Secondary Proof

**Story:** As a skeptical buyer, I want to drill into the PR evidence behind the repo story.

**Files:**
- Modify: [apps/public/views/org_views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views/org_views.py)
- Create or modify: `apps/public/views/repo_views.py`
- Modify: [templates/public/org_pr_list.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/org_pr_list.html)
- Create: `templates/public/repo_pr_list.html`
- Test: `apps/public/tests/test_repo_pr_explorer.py`

**Acceptance criteria:**
- Repo proof page reuses current PR explorer mechanics.
- The page is linked from the canonical repo page.
- The page defaults to the selected repo scope.
- The page is not the primary SEO surface.

**Technical requirements:**
- Reuse `get_prs_queryset`, `get_pr_stats`, and filter option helpers.
- Add `noindex,follow` and canonical tags.
- Keep the UX useful but visually secondary.

**Step 1: Write the failing tests**

```python
def test_repo_proof_page_is_noindex_and_canonicalizes_to_repo_detail():
    response = client.get(reverse("public:repo_pr_list", kwargs={...}))
    assert "noindex,follow" in response.content.decode()
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_pr_explorer.py -n 0
```

**Step 3: Write minimal implementation**
- Add repo-scoped PR explorer view/template.
- Reuse existing PR table/filtering logic.
- Add SEO metadata.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_pr_explorer.py apps/metrics/tests/test_pr_list_service.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/views/org_views.py apps/public/views/repo_views.py templates/public/org_pr_list.html templates/public/repo_pr_list.html apps/public/tests/test_repo_pr_explorer.py
git commit -m "feat: add repo-scoped public PR proof page"
```

---

## 15. Task 9: Harden SEO/GEO

**Story:** As the growth team, we need public repo pages that rank well, get cited by AI tools, and share cleanly.

**Files:**
- Modify: [apps/public/sitemaps.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/sitemaps.py)
- Modify: [tformance/urls.py](/Users/yanchuk/Documents/GitHub/tformance/tformance/urls.py)
- Modify: [templates/robots.txt](/Users/yanchuk/Documents/GitHub/tformance/templates/robots.txt)
- Modify: [templates/public/app_base.html](/Users/yanchuk/Documents/GitHub/tformance/templates/public/app_base.html)
- Modify: `templates/public/repo_detail.html`
- Modify: `templates/public/repo_pr_list.html`
- Test: `apps/public/tests/test_repo_geo.py`
- Test: [apps/public/tests/test_geo.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/tests/test_geo.py)

**Acceptance criteria:**
- Repo pages have canonical tags, JSON-LD, breadcrumb schema, and a citable paragraph.
- Repo pages appear in sitemap output.
- Repo proof pages do not compete with canonical pages.
- AI bots remain explicitly allowed for `/open-source/`.

**Technical requirements:**
- Reuse existing sitemap/robots plumbing.
- Add repo sitemaps instead of inventing a second sitemap path.
- Keep metadata server-rendered.

**Step 1: Write the failing tests**

```python
def test_repo_sitemap_includes_canonical_repo_pages():
    response = client.get("/sitemap.xml")
    assert "/open-source/posthog/repos/posthog/" in response.content.decode()


def test_repo_proof_page_is_not_indexable():
    response = client.get(...)
    assert "noindex,follow" in response.content.decode()
```

**Step 2: Run test to verify it fails**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_geo.py apps/public/tests/test_geo.py -n 0
```

**Step 3: Write minimal implementation**
- Add repo sitemap entries.
- Add repo breadcrumb/schema markup.
- Set canonical/meta robots correctly on proof pages.

**Step 4: Run tests to verify it passes**

Run:

```bash
.venv/bin/pytest apps/public/tests/test_repo_geo.py apps/public/tests/test_geo.py -n 0
```

**Step 5: Commit**

```bash
git add apps/public/sitemaps.py tformance/urls.py templates/robots.txt templates/public/app_base.html templates/public/repo_detail.html templates/public/repo_pr_list.html apps/public/tests/test_repo_geo.py apps/public/tests/test_geo.py
git commit -m "feat: harden seo and geo for public repo pages"
```

---

## 16. Task 10: QA, Local Preview, And Executor Docs

**Story:** As the implementation team, we need reproducible QA and a reliable localhost preview workflow.

**Files:**
- Modify: [dev/DEV-ENVIRONMENT.md](/Users/yanchuk/Documents/GitHub/tformance/dev/DEV-ENVIRONMENT.md)
- Create: `tests/e2e/public-repo-pages.spec.ts` if Playwright coverage belongs there
- Test: Playwright manual QA notes in this plan

**Acceptance criteria:**
- Dev docs explicitly instruct QA to use `http://localhost:8000`.
- Manual QA checklist includes one org hub, one repo page, and one repo proof page.
- Playwright smoke coverage exists for repo page and org hub navigation.

**Technical requirements:**
- If Vite host mismatch remains a risk, document the workaround clearly.
- Do not document `127.0.0.1` as the primary QA hostname.

**Step 1: Write the failing test or smoke spec**

```ts
test("public repo page renders hero and CTA", async ({ page }) => {
  await page.goto("/open-source/posthog/repos/posthog/");
  await expect(page.getByText("Start Free Trial")).toBeVisible();
});
```

**Step 2: Run test to verify it fails**

Run:

```bash
make e2e
```

Expected:
- the spec fails until the page and route exist

**Step 3: Write minimal implementation**
- Add smoke test coverage.
- Update local preview docs to use localhost and explain Vite expectations.

**Step 4: Run test to verify it passes**

Run:

```bash
make e2e
```

**Step 5: Commit**

```bash
git add dev/DEV-ENVIRONMENT.md tests/e2e/public-repo-pages.spec.ts
git commit -m "docs: add localhost qa workflow for public repo pages"
```

---

## 17. Verification Commands

Run these during the implementation sequence, not only at the end.

```bash
.venv/bin/python manage.py check
.venv/bin/pytest apps/public/tests -n 0
.venv/bin/pytest apps/integrations/tests -n 0
.venv/bin/pytest apps/metrics/tests -n 0
make e2e
make dev
```

### Manual Playwright QA checklist
- Visit `http://localhost:8000/open-source/`
- Visit one org hub page
- Visit one flagship repo page
- Visit the repo proof page
- Disable JS once to confirm canonical repo page still makes sense
- Confirm CTAs appear above the fold on desktop and mobile
- Confirm repo proof page is linked but visually secondary

---

## 18. Release Notes For The Execution Team

### Product-quality bar
- These pages must feel like shareable benchmark reports, not internal dashboards made public.
- The opening paragraph must be quotable and numerically specific.
- Every repo page must tell a single coherent story in one screen.

### Engineering-quality bar
- Test-first for every story.
- Small commits after each task.
- Reuse before inventing.
- No prompt changes without explicit approval.

### Launch scope for v1
- Only flagship repos
- Only qualifying repos with enough recent activity
- Org hubs only where flagship repo pages exist

### Default repo eligibility rule
- manually marked flagship
- meaningful all-time PR volume
- meaningful 90-day activity

If a repo cannot support a credible public story, do not index it in v1.

