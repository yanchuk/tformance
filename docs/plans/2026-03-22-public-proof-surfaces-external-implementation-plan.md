# Public Proof Surfaces Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn the public OSS pages into proof-first acquisition surfaces for CTOs by showing AI adoption next to delivery outcomes, with canonical SEO/GEO-safe pages and clear conversion paths.

**Architecture:** Reuse the existing public data model, repo/org snapshots, and internal trends/chart stack. Canonical pages must render their core narrative and primary trend chart from server-side page context. Support pages remain deeper analysis surfaces and must not compete in search.

**Tech Stack:** Django function-based views, HTMX, Alpine.js, Tailwind/DaisyUI, Chart.js, Pillow OG generation, existing metrics service layer, existing public snapshot models.

---

## Summary

This plan is aligned to:
- `prd/dna_codex.md`
- `prd/icp_target_audience_codex.md`
- `prd/gtm_go_to_market_codex.md`

The target buyer is a CTO, VP Engineering, or Engineering Director at a GitHub-first 15-75 engineer company. The public pages must answer one question clearly:

**Is AI adoption actually helping delivery, or is it increasing review load without improving flow?**

Non-negotiable product rules:
- Canonical public pages must lead with outcomes, not vanity metrics.
- AI adoption is context, not the hero claim by itself.
- Do not show CI/CD, check-run quality, deployment metrics, Copilot seat utilization, Jira planning metrics, Slack survey metrics, or individual developer rankings on public pages.
- Public pages must feel like proof surfaces, not copied internal dashboards.
- Support pages must be `noindex,follow` and canonical back to the primary org or repo page.

Primary public pages:
- `/open-source/`
- `/open-source/<org>/`
- `/open-source/<org>/repos/<repo>/`

Support pages:
- `/open-source/<org>/analytics/`
- `/open-source/<org>/pull-requests/`
- `/open-source/<org>/repos/<repo>/pull-requests/`

Default windows:
- Summary window: 30 days
- Trend window: 90 days rendered as 12 completed weekly buckets

Primary CTA:
- `See Your Team's Benchmarks`

Secondary CTA:
- `Book Demo`

Freshness copy:
- `Updated daily from public GitHub pull requests.`

---

## Target Layouts

### `/open-source/`

```text
+----------------------------------------------------------------------------------+
| Open Source Engineering Benchmarks                                               |
| Public GitHub data shows where AI adoption is rising, where cycle time improves, |
| and where review burden is growing.              [See Your Team's Benchmarks]    |
+-----------------------------------+----------------------------------------------+
| 12-week AI adoption vs cycle time | Org benchmark scatter                        |
+-----------------------------------+----------------------------------------------+
| Industry benchmark bars                                                          |
+----------------------------------------------------------------------------------+
| Sortable comparison table                                                        |
| Org | PRs | AI adoption | Cycle time | Review time | Contributors | Flagship     |
+----------------------------------------------------------------------------------+
| Methodology / freshness / CTA                                                    |
+----------------------------------------------------------------------------------+
```

### `/open-source/<org>/`

```text
+----------------------------------------------------------------------------------+
| Polar Engineering Benchmarks                                                     |
| Summary paragraph with PR count, AI adoption, cycle time, review time, benchmark |
| vs industry, and a direct CTA.                                                   |
+----------------------------------------------------------------------------------+
| Combined trend chart: AI adoption + cycle time                                   |
+-----------------------------------+----------------------------------------------+
| AI vs non-AI impact               | "What changed recently" narrative            |
+----------------------------------------------------------------------------------+
| Flagship repo cards                                                              |
+----------------------------------------------------------------------------------+
| Repo comparison mini-table                                                       |
+----------------------------------------------------------------------------------+
| Methodology / support links / CTA                                                |
+----------------------------------------------------------------------------------+
```

### `/open-source/<org>/repos/<repo>/`

```text
+----------------------------------------------------------------------------------+
| Polar / polar                                                                    |
| Citable summary + weekly insight + CTA                                           |
+----------------------+----------------------+------------------------------------+
| Median cycle time    | Median review time   | AI adoption                         |
+----------------------+----------------------+------------------------------------+
| Best signal          | Watchout signal      | Repo vs org average                 |
+----------------------------------------------------------------------------------+
| Combined trend chart: AI adoption + cycle time                                   |
+-----------------------------------+----------------------------------------------+
| Correlation scatter               | AI vs non-AI impact                          |
+----------------------------------------------------------------------------------+
| AI tools                          | PR type breakdown                            |
+----------------------------------------------------------------------------------+
| Recent PR proof block                                                            |
+----------------------------------------------------------------------------------+
| Methodology / freshness / CTA                                                    |
+----------------------------------------------------------------------------------+
```

### `/open-source/<org>/analytics/`

```text
+----------------------------------------------------------------------------------+
| Polar Delivery & AI Trends                                                       |
| Support page only. noindex,follow. Canonical to the org page.                    |
+----------------------------------------------------------------------------------+
| Combined AI adoption + cycle time trend                                          |
+-----------------------------------+----------------------------------------------+
| Combined AI adoption + review time | AI vs non-AI impact                         |
+----------------------------------------------------------------------------------+
| Top AI tools                       | PR type trend                               |
+----------------------------------------------------------------------------------+
| Tech category trend                | Team health indicators                      |
+----------------------------------------------------------------------------------+
```

---

## Public Data Exposure Rules

Expose now:
- AI adoption %
- Median cycle time
- Median review time
- Review rounds
- PR cadence / merged PR volume
- Active contributors
- AI vs non-AI comparison
- AI tools detected
- PR type breakdown
- Tech category breakdown
- Repo vs org averages
- Org benchmark percentile
- Recent PR proof

Do not expose:
- CI/CD pass rate or deployment quality
- Check-run health
- Copilot seat usage or acceptance telemetry
- Slack survey metrics
- Jira planning or story-point metrics
- Developer-level ranking or individual scorecards
- Reviewer identity leaderboard
- Any metric that feels like surveillance rather than flow analysis

---

## Task 1: Fix Metadata, Canonicals, Titles, and Social Images

**User story:** As a search engine, AI crawler, or social sharer, I get clean entity-specific metadata and a strict canonical hierarchy.

**Files**
- Modify: `templates/web/base.html`
- Modify: `apps/public/views/org_views.py`
- Modify: `apps/public/views/repo_views.py`
- Modify: `apps/public/views/analytics_views.py`
- Extend: `apps/public/tests/test_public_metadata_strategy.py`
- Extend: `apps/public/tests/test_repo_views.py`
- Extend: `apps/public/tests/test_org_views.py`

**Implementation**
- Remove default `<meta name="keywords">` emission from the base template.
- Only render keywords if a view explicitly passes `page_keywords`.
- Public views must never set `page_keywords`.
- Repo views must set `page_image` to the repo-specific OG route.
- Org views must set `page_image` to the org-specific OG route.
- Repo titles must not append `Tformance` in the view; the base template owns brand suffixing.
- Canonical rules:
  - org analytics -> canonical to org page
  - org PR explorer -> canonical to org page
  - repo PR explorer -> canonical to repo page
- Support pages must render `robots=noindex,follow`.
- Remove the phrase `read-only` from all public metadata and visible copy.

**Acceptance criteria**
- Given a canonical org or repo page, when rendered, then it contains no `keywords` tag.
- Given a repo page, when rendered, then `og:image` and `twitter:image` point to the repo OG route.
- Given an org PR support page, when rendered, then its canonical target is the org page.
- Given any public page, when rendered, then the title contains `Tformance` exactly once.
- Given any public page, when rendered, then metadata contains no `read-only` wording.

**TDD**
- Write failing metadata tests first in `apps/public/tests/test_public_metadata_strategy.py`.
- Add one view test per support-page canonical target.
- Add one repo view test asserting `page_image` is set.
- Run the narrowest tests first, then the full public metadata suite.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_metadata_strategy.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_repo_views.py apps/public/tests/test_org_views.py -n 0`
- `curl -sL` checks for `/open-source/`, `/open-source/polar/`, `/open-source/polar/repos/polar/`, `/open-source/polar/analytics/`, `/open-source/polar/pull-requests/`

---

## Task 2: Reuse the Existing Trends Stack for Public Combined Trend and Correlation Charts

**User story:** As a CTO, I can see whether AI adoption and delivery outcomes are moving together using the same trend logic Tformance uses inside the app.

**Files**
- Create: `apps/public/services/public_trends.py`
- Modify: `apps/public/services/analytics.py`
- Modify: `apps/public/repo_snapshot_service.py`
- Modify: `apps/public/views/chart_views.py`
- Reuse: `apps/metrics/views/trends_views.py`
- Reuse: `assets/javascript/dashboard/trend-charts.js`
- Create: `apps/public/tests/test_public_trend_builders.py`

**Implementation**
- Reuse existing trend services:
  - `get_ai_adoption_trend`
  - `get_cycle_time_trend`
  - `get_review_time_trend`
  - `get_ai_impact_stats`
  - `get_weekly_pr_type_trend`
  - `get_weekly_tech_trend`
  - `get_team_health_indicators`
  - `benchmark_service.get_benchmark_for_team` for org pages only
- Create one shared public chart-data builder for:
  - AI adoption + cycle time
  - AI adoption + review time
- Create one weekly correlation builder:
  - X = AI adoption %
  - Y = median cycle time
  - minimum threshold = 6 weekly buckets
  - use Pearson correlation
- Store canonical repo/org primary trend data in snapshots so canonical pages do not depend on live heavy HTMX computation.
- Do not create a second public-only chart engine.
- Do not include CI/CD or check-run metrics in any public chart.

**Acceptance criteria**
- Given a repo page with enough data, when rendered, then the primary combined trend chart can be built from stored snapshot data.
- Given an org page with enough data, when rendered, then it can render one server-side trend chart without HTMX.
- Given fewer than 6 valid weekly points, when the page renders, then the correlation narrative and scatter chart are hidden.
- Given public charts, when rendered, then none include CI/CD or check-run series.

**TDD**
- Write unit tests for:
  - combined trend chart-data builder
  - weekly correlation pair generation
  - correlation classification
  - insufficient-data hiding
- Add one integration test that repo view context contains canonical trend data.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_trend_builders.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_repo_snapshot_service.py apps/public/tests/test_chart_views.py -n 0`

---

## Task 3: Redesign `/open-source/` Into a Benchmark-First Page With Clickable Header Sorting

**User story:** As a CTO comparing OSS teams, I see the market story first and can then sort the table by the metric I care about.

**Files**
- Modify: `apps/public/views/directory_views.py`
- Modify: `apps/public/services/analytics.py`
- Modify: `templates/public/directory.html`
- Modify: `templates/public/_directory_list.html`
- Extend: `apps/public/tests/test_directory_views.py`
- Extend: `apps/public/tests/test_directory_sorting.py`
- Create: `tests/e2e/public-pages.spec.ts`

**Implementation**
- Replace the current table-first layout with the benchmark-first layout from the ASCII mockup.
- Add three benchmark charts above the table:
  - 12-week dual-axis trend: AI adoption + median cycle time
  - org benchmark scatter: X AI adoption, Y median cycle time, bubble size by PR volume, color by industry
  - industry grouped bars: AI adoption, cycle time, review time
- Keep the table below the charts.
- Add header-click sorting on desktop for:
  - organization
  - PRs
  - AI adoption
  - cycle time
  - review time
  - contributors
- Keep the dropdown sort only as mobile fallback.
- Sorting must stay server-side, preserve filters, and use URL params as source of truth.
- Directory copy must explicitly bridge to product value and CTA.

**Acceptance criteria**
- Given `/open-source/`, when loaded on desktop, then at least two benchmark charts appear above the table.
- Given a sortable header, when clicked twice, then the table order toggles `desc` then `asc`.
- Given filters are active, when sort changes, then the filters remain in the URL.
- Given JavaScript is disabled, when `/open-source/` renders, then the summary paragraph and table remain useful.

**TDD**
- Add failing view tests for chart context.
- Add failing sort-param tests for header sorting.
- Add Playwright test coverage for header clicks and table ordering.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_directory_views.py apps/public/tests/test_directory_sorting.py -n 0`
- `npx playwright test tests/e2e/public-pages.spec.ts --grep "directory"`

---

## Task 4: Upgrade the Canonical Org Page Into a Proof Hub

**User story:** As a buyer evaluating an OSS company, I can tell whether the org is improving and which repos are driving that result.

**Files**
- Modify: `apps/public/views/org_views.py`
- Modify: `templates/public/org_detail.html`
- Extend: `apps/public/tests/test_org_views.py`
- Extend: `apps/public/tests/test_org_hub_views.py`

**Implementation**
- Replace the current thin org page with the layout from the ASCII mockup.
- Required sections:
  - citable summary paragraph
  - org-vs-industry benchmark callout
  - combined AI adoption + cycle time trend chart
  - AI-vs-non-AI impact block
  - flagship repo cards
  - repo comparison mini-table
  - methodology + CTA
- Keep analytics and PR explorer as support links, not primary CTAs.
- The org page must answer whether AI adoption and delivery are moving together.
- Do not show CI/CD, Jira, or private team-management data.

**Acceptance criteria**
- Given an org page, when loaded, then it contains a visible summary paragraph with live metrics.
- Given an org page, when loaded, then it contains one visible trend chart without HTMX.
- Given an org with multiple repos, when loaded, then flagship repos appear as cards and all public repos appear in the mini-table.
- Given the org page, when scanned above the fold, then the primary CTA is `See Your Team's Benchmarks`.

**TDD**
- Add failing org view tests for new sections.
- Add one snapshot-data test for benchmark context.
- Add one template render test ensuring flagship repo cards exist.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_org_views.py apps/public/tests/test_org_hub_views.py -n 0`
- `npx playwright test tests/e2e/public-pages.spec.ts --grep "org page"`

---

## Task 5: Make the Repo Page the Strongest AI-vs-Delivery Proof Surface

**User story:** As a CTO, I can decide whether this repo’s AI usage is helping or hurting delivery in one screen.

**Files**
- Modify: `apps/public/views/repo_views.py`
- Modify: `templates/public/repo_detail.html`
- Extend: `apps/public/tests/test_repo_views.py`
- Extend: `apps/public/tests/test_repo_snapshot_service.py`

**Implementation**
- Keep repo pages as the primary proof surface.
- Use the layout from the ASCII mockup.
- Required sections:
  - citable summary
  - weekly insight
  - outcome-first hero metrics
  - best signal / watchout signal
  - combined trend chart
  - correlation scatter
  - AI-vs-non-AI impact block
  - AI tools
  - PR type breakdown
  - recent PR proof
  - methodology + CTA
- Add `repo vs org average` callouts for cycle time and AI adoption.
- Correlation narrative must use fixed labels:
  - `strong negative`
  - `moderate negative`
  - `weak or no clear relationship`
  - `moderate positive`
  - `strong positive`
- Do not put benchmark percentile or DORA-style team-size benchmark panels on repo pages.

**Acceptance criteria**
- Given a repo page, when loaded, then it leads with cycle time, review time, and AI adoption, not AI adoption alone.
- Given enough weekly data, when loaded, then the page shows both a combined trend chart and a correlation scatter.
- Given not enough data, when loaded, then the correlation section is hidden cleanly.
- Given a repo page, when loaded, then it contains recent PR proof and a repo-specific OG image.

**TDD**
- Add failing repo view tests for new sections and OG image.
- Add snapshot tests for repo-vs-org comparison helpers.
- Add correlation classification tests.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_repo_views.py apps/public/tests/test_repo_snapshot_service.py -n 0`
- `npx playwright test tests/e2e/public-pages.spec.ts --grep "repo page"`

---

## Task 6: Reframe `/analytics/` as a Deeper Support Layer

**User story:** As a skeptical buyer, I can click deeper for richer trends without confusing the support page for the canonical page.

**Files**
- Modify: `templates/public/org_analytics.html`
- Modify: `apps/public/views/chart_views.py`
- Extend: `apps/public/tests/test_analytics_views.py`
- Extend: `apps/public/tests/test_public_chart_layout_contract.py`

**Implementation**
- Keep the analytics page live, `noindex,follow`, and canonical to the org page.
- Replace the current top row with:
  - combined AI adoption + cycle time trend first
  - combined AI adoption + review time trend second
- Keep deeper support charts:
  - AI-vs-non-AI impact
  - top AI tools
  - PR type trend
  - tech category trend
  - team health indicators
- Enforce one reusable card-height contract so paired charts align vertically.
- Remove dashboard-style framing that makes the page feel like the primary acquisition surface.

**Acceptance criteria**
- Given the analytics page, when loaded, then the first chart is the combined AI adoption + cycle time trend.
- Given paired charts, when rendered, then their top baselines align.
- Given the analytics page, when rendered, then it contains `robots=noindex,follow` and canonical points to the org page.
- Given any analytics support content, when rendered, then it contains no CI/CD content.

**TDD**
- Add failing analytics view tests for canonical/robots behavior.
- Add failing layout-contract tests for chart card classes and fixed heights.
- Add one Playwright visual test for aligned charts.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_analytics_views.py apps/public/tests/test_public_chart_layout_contract.py -n 0`
- `npx playwright test tests/e2e/public-pages.spec.ts --grep "analytics"`

---

## Task 7: Wire Dynamic Org and Repo OG Images Into Canonical Pages

**User story:** As someone sharing a public page, I see a branded image with the org/repo name and live benchmark numbers instead of a generic fallback.

**Files**
- Modify: `apps/public/views/repo_views.py`
- Modify: `apps/public/views/org_views.py`
- Extend: `apps/public/tests/test_public_og_images.py`
- Reuse: `apps/public/services/og_image_service.py`
- Reuse: `apps/public/views/og_views.py`

**Implementation**
- Canonical org pages must use `/og/open-source/<org_slug>.png`.
- Canonical repo pages must use `/og/open-source/<org_slug>/<repo_slug>.png`.
- Support pages reuse the canonical page’s OG image.
- OG images must show:
  - org name
  - repo name for repo pages
  - AI adoption
  - median cycle time
  - PR count
  - Tformance branding
- Do not use the generic site-wide OG image on canonical public pages.

**Acceptance criteria**
- Given an org page, when rendered, then `og:image` points to the org OG route.
- Given a repo page, when rendered, then `og:image` points to the repo OG route.
- Given an OG route, when requested, then it returns `200` and renders the correct entity name.

**TDD**
- Add failing OG image route tests first.
- Add one repo view metadata test and one org view metadata test.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_og_images.py -n 0`
- Browser check:
  - `/og/open-source/polar.png`
  - `/og/open-source/polar/polar.png`

---

## Final QA and Sign-Off Matrix

**Unit and view tests**
- `.venv/bin/python manage.py check`
- `.venv/bin/pytest apps/public/tests/test_public_metadata_strategy.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_public_trend_builders.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_directory_views.py apps/public/tests/test_directory_sorting.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_org_views.py apps/public/tests/test_repo_views.py -n 0`
- `.venv/bin/pytest apps/public/tests/test_analytics_views.py apps/public/tests/test_public_og_images.py -n 0`

**E2E**
- `npx playwright test tests/e2e/public-pages.spec.ts`

**Manual routes**
- `/open-source/`
- `/open-source/polar/`
- `/open-source/polar/repos/polar/`
- `/open-source/polar/analytics/`
- `/open-source/polar/pull-requests/`
- `/open-source/polar/repos/polar/pull-requests/`

**Manual checks**
- No `keywords` tag on canonical public pages
- No `read-only` phrasing anywhere
- Repo page uses repo-specific OG image
- Org PR explorer canonical points to the org page
- Directory has charts above the table
- Header-click sorting works on desktop
- No CI/CD content appears anywhere on public pages

---

## Assumptions

- `prd/dna_codex.md`, `prd/icp_target_audience_codex.md`, and `prd/gtm_go_to_market_codex.md` are the product guardrails for this workstream.
- The repo page remains the strongest proof surface.
- The org page becomes a better hub and benchmark surface, not a full internal dashboard clone.
- The analytics page remains a support page only.
- Canonical public charts use the existing 90-day trend window rendered as 12 completed weekly buckets.
- CI/CD and check-run metrics are explicitly out of scope for public pages in this phase.
