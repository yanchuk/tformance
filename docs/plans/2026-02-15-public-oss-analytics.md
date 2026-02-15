# Public OSS Analytics Pages — Implementation Plan

**Date:** 2026-02-15
**Status:** Reviewed
**Team:** Product Manager, System Architect, UI/UX Designer, SEO/GEO Expert

## Vision

Turn Tformance into the public source of truth for open-source engineering metrics. ~60-70 qualifying OSS organizations (500+ PRs threshold), daily-updated, SEO/GEO-optimized, served from Unraid via Cloudflare tunnel with aggressive caching. Zero additional hosting cost.

## Existing Assets

- **167K+ PRs** from 101 OSS companies (defined in `apps/metrics/seeding/real_projects.py`)
- **15 industry categories** for benchmarking (in seeding config only — need DB persistence)
- **Export pipeline** (`public_report/scripts/export_report_data.py`) — aggregation logic to be extracted
- **Static report** already served at `/report/` via `apps/web/views.py`
- **llms.txt** already exists at `/llms.txt` (template: `templates/llms.txt`)
- **robots.txt** already exists at `/robots.txt`
- **Daily Celery sync** infrastructure in `apps/integrations/tasks.py`

## Architecture Decisions (Post-Review)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Org metadata storage | `PublicOrgProfile` model (OneToOne to Team) | Clean separation from core Team model. Holds industry, description, logo, public_slug, is_public |
| 2 | Public data boundary | Explicit `is_public` flag on `PublicOrgProfile` | Replaces convention-based `-demo` suffix. Self-documenting, impossible to accidentally match |
| 3 | Cache invalidation | Purge everything after sync | Simplest approach. ~120 pages, one API call, cache rebuilds within minutes |
| 4 | Shared aggregation logic | Extract into `apps/public/aggregations.py` | Both service layer and export script import from it. Single source of truth for metrics |
| 5 | Minimum data threshold | 500 PRs to appear on public pages | Matches existing report criteria. ~60-70 orgs qualify |
| 6 | Public URL slugs | Clean slugs via `PublicOrgProfile.public_slug` | `/open-source/posthog/` maps to team `posthog-demo` internally |
| 7 | Directory performance | Pre-computed `PublicOrgStats` model | Refreshed by Celery after sync. Directory queries ~70 rows, instant |
| 8 | llms-full.txt | Generate as static file during sync | Write to disk like CSV export. Always instant, even if DB is down |
| 9 | Database indexes | Compound indexes + pre-computed stats | Belt and suspenders approach |

---

## Epic 1: Data Foundation & Public Service Layer

### US-1.1: Create `apps/public` Django App with Data Models

**As a** developer
**I want** a dedicated Django app with proper models for public OSS analytics
**So that** public pages are cleanly separated from authenticated team features

**Acceptance Criteria:**
- [ ] New app `apps/public/` created with `urls.py`, `views.py`, `services.py`, `aggregations.py`, `templatetags/`
- [ ] App added to `INSTALLED_APPS`
- [ ] URL prefix: `/open-source/` registered in root `tformance/urls.py`
- [ ] **Model: `PublicOrgProfile`** (extends `BaseModel`, NOT BaseTeamModel):
  - `team` — OneToOneField to Team
  - `public_slug` — SlugField, unique (e.g., "posthog")
  - `industry` — CharField (from INDUSTRIES choices)
  - `description` — TextField (from GitHub org description)
  - `github_org_url` — URLField
  - `logo_url` — URLField (blank=True)
  - `is_public` — BooleanField (default=False)
  - `display_name` — CharField (clean org name for display)
- [ ] **Model: `PublicOrgStats`** (extends `BaseModel`):
  - `org_profile` — OneToOneField to PublicOrgProfile
  - `total_prs` — IntegerField
  - `ai_assisted_pct` — DecimalField
  - `median_cycle_time_hours` — DecimalField
  - `median_review_time_hours` — DecimalField
  - `active_contributors_90d` — IntegerField
  - `top_ai_tools` — JSONField (list of {tool, count, pct})
  - `last_computed_at` — DateTimeField
- [ ] **Model: `PublicRepoRequest`** (extends `BaseModel`):
  - `github_url` — URLField
  - `email` — EmailField
  - `role` — CharField (choices: maintainer/contributor/fan)
  - `status` — CharField (choices: pending/approved/rejected)
- [ ] Data migration: populate `PublicOrgProfile` from `REAL_PROJECTS` config
  - Set `is_public=True` for all 101 orgs
  - Set `public_slug` = team_slug minus `-demo` suffix
  - Set `industry` from config
- [ ] No `@login_and_team_required` on any view — all views are public
- [ ] All DB queries filter via `PublicOrgProfile.objects.filter(is_public=True)` — NOT `slug__endswith='-demo'`
- [ ] Add `# noqa: TEAM001` comments on PR queries (intentionally cross-team)
- [ ] Database indexes:
  - `(team_id, pr_created_at)` compound index on PullRequest
  - `(team_id, is_ai_assisted, pr_created_at)` compound index
  - `(team_id)` partial index WHERE `state = 'merged'`
- [ ] All 3 models registered in Django admin

**Test Requirements:**
- [ ] Model creation/validation tests for all 3 models
- [ ] Data migration test: verify all 101 orgs get PublicOrgProfile
- [ ] Verify `public_slug` uniqueness constraint
- [ ] Verify `is_public=False` orgs are excluded from all querysets

---

### US-1.2: Build Shared Aggregation Module + Public Data Service

**As a** developer
**I want** reusable aggregation functions and a service layer
**So that** both public pages and the export script compute metrics identically (DRY)

**Acceptance Criteria:**
- [ ] `apps/public/aggregations.py` — pure functions (no Django cache, no side effects):
  - `compute_team_summary(team_id, year=2025)` → dict with total_prs, ai_pct, cycle_time, etc.
  - `compute_monthly_trends(team_id, year=2025)` → list of monthly dicts
  - `compute_ai_tools_breakdown(team_id, year=2025)` → list of tool dicts
  - `compute_industry_stats(industry, year=2025)` → aggregate metrics for all teams in industry
- [ ] All aggregation functions use `.values().annotate()` — never load full PR objects
- [ ] Median computation: PostgreSQL `percentile_cont(0.5)` via `Func` or raw SQL
- [ ] Filter: only `state='merged'`, `pr_created_at >= 2025-01-01`, `cycle_time_hours <= 200`
- [ ] `apps/public/services.py` with `PublicAnalyticsService`:
  - `get_directory_data()` → queries `PublicOrgStats` (pre-computed, instant)
  - `get_org_detail(public_slug)` → full metrics from aggregation functions + cache
  - `get_industry_comparison(industry_key)` → filtered `PublicOrgStats` + trends
  - `get_global_stats()` → aggregate across all public orgs
- [ ] Service methods cached in Django Redis cache (1h TTL, prefix: `public:`)
- [ ] Refactor `public_report/scripts/export_report_data.py` to import from `aggregations.py`

**Test Requirements:**
- [ ] Unit tests for every aggregation function with factory data (at least 3 test cases each)
- [ ] Test with edge cases: org with exactly 500 PRs (boundary), org with 0 AI PRs, org with all AI PRs
- [ ] Test median computation returns correct values
- [ ] Test outlier filtering (>200h cycle time excluded)
- [ ] Test service methods return correct data shapes
- [ ] Test cache hits/misses with Django cache framework

---

### US-1.3: Ensure Data Covers Full 2025 + Daily Sync

**As a** product owner
**I want** all qualifying repos to have complete 2025 data, synced daily
**So that** public pages show current, comprehensive metrics

**Acceptance Criteria:**
- [ ] Verify all 101 demo teams have PRs from 2025-01-01 through today
- [ ] If gaps exist, run backfill sync with `--start-date 2025-01-01 --no-pr-limit`
- [ ] New Celery task: `sync_oss_repos_task`:
  - Runs daily at 4 AM UTC (Celery beat)
  - Queries `PublicOrgProfile.objects.filter(is_public=True)` for teams to sync
  - Calls `sync_repository_task` per tracked repo (reuses existing sync)
  - Incremental: fetches PRs since `last_sync_at`
- [ ] New Celery task: `compute_public_stats_task` (runs after sync completes):
  1. Compute aggregations for each public org
  2. Update `PublicOrgStats` records
  3. Generate `llms-full.txt` static file (write to disk)
  4. Clear Django Redis cache keys (prefix: `public:`)
  5. Call Cloudflare purge everything API
- [ ] Chain: `sync_oss_repos_task` → `compute_public_stats_task` (using Celery chord/chain)
- [ ] Monitoring: log sync duration, PR count fetched, errors per repo
- [ ] GitHub API budget: dedicated PAT for OSS sync (separate from customer tokens)
- [ ] Rate limit: 5000 req/hr — 101 repos × ~10 req/repo = ~1010 req — well within limits

**Test Requirements:**
- [ ] Test task chaining: sync completion triggers stats computation
- [ ] Test stats computation updates `PublicOrgStats` correctly
- [ ] Test Cloudflare purge is called (mock the API)
- [ ] Test error handling: one repo sync failure doesn't block others

---

## Epic 2: Public Pages & Templates

### US-2.1: Public Base Template

**As a** developer
**I want** a shared base template for all public analytics pages
**So that** they have consistent navigation, footer, and styling

**Acceptance Criteria:**
- [ ] Template: `templates/public/base.html` extending `web/base.html`
- [ ] Navigation: "Open Source" nav item in top nav (public pages only)
- [ ] Breadcrumb component: Open Source → {Industry} → {Org Name}
- [ ] Footer: links to methodology, data policy, "Powered by Tformance"
- [ ] Includes Google Analytics + PostHog tracking (same as existing pages)
- [ ] Dark/light mode toggle (reuse existing component)
- [ ] Responsive at all breakpoints
- [ ] Meta tag blocks: `{% block page_title %}`, `{% block meta_description %}`, `{% block og_tags %}`, `{% block json_ld %}`
- [ ] No auth-related UI elements in nav

**Test Requirements:**
- [ ] Template renders without errors for anonymous users
- [ ] All block placeholders have sensible defaults

---

### US-2.2: Directory Page — `/open-source/`

**As a** visitor
**I want** to browse all tracked OSS organizations
**So that** I can find engineering metrics for projects I care about

**Acceptance Criteria:**
- [ ] URL: `/open-source/` → `public:directory`
- [ ] Queries `PublicOrgStats` joined with `PublicOrgProfile` (instant, pre-computed)
- [ ] Only shows orgs where `PublicOrgProfile.is_public=True` AND `PublicOrgStats.total_prs >= 500`
- [ ] Each org card shows: display_name, industry tag, total PRs, AI adoption %, median cycle time, contributor count
- [ ] Visual: mini progress bar for AI adoption %
- [ ] Filter by industry (dropdown, 15 categories)
- [ ] Sort by: name, AI adoption, total PRs, cycle time (default: total PRs desc)
- [ ] Client-side search (Alpine.js `x-data` filter on org name)
- [ ] HTMX: sort/filter triggers partial reload of org list only (`_directory_list.html` partial)
- [ ] Global stats banner: "X PRs analyzed from Y companies across Z industries"
- [ ] Mobile responsive (cards stack)
- [ ] CTA at bottom: "Track YOUR team's metrics → Get started free"
- [ ] `Cache-Control: public, max-age=43200` header (12h)

**Test Requirements:**
- [ ] Anonymous user gets 200
- [ ] Directory shows only public orgs (private team NOT shown)
- [ ] Directory respects 500 PR threshold
- [ ] Sort/filter parameters work correctly
- [ ] Response includes correct Cache-Control header

---

### US-2.3: Org Detail Page — `/open-source/{slug}/`

**As a** visitor (CTO, developer, OSS maintainer)
**I want** to see detailed engineering metrics for a specific OSS organization
**So that** I can understand their development patterns and AI adoption

**Acceptance Criteria:**
- [ ] URL: `/open-source/<slug:public_slug>/` → `public:org_detail`
- [ ] Lookup via `PublicOrgProfile.objects.get(public_slug=slug, is_public=True)` — 404 otherwise
- [ ] Hero section: display_name, GitHub org link, industry badge, "Last updated: {date}"
- [ ] Key metrics cards (top row, from `PublicOrgStats`):
  - Total PRs (2025+)
  - AI-Assisted PR % (with trend arrow vs. previous month)
  - Median Cycle Time (hours)
  - Active Contributors (last 90 days)
- [ ] Chart: AI Adoption Over Time (line chart, monthly, Chart.js — Easy Eyes theme)
- [ ] Chart: PR Velocity (merged PRs per week, bar chart)
- [ ] Chart: Cycle Time Trend (line chart, monthly median)
- [ ] Table: Top AI Tools Detected (from `PublicOrgStats.top_ai_tools`)
- [ ] Comparison sidebar: "vs. Industry Median" for key metrics
- [ ] "Methodology" collapsible section (shared partial template)
- [ ] Related orgs: "Similar in {industry}" — 3-4 links from same industry
- [ ] CTA: "Get these metrics for YOUR private repos → Sign up"
- [ ] Charts loaded lazily via `hx-get` with `hx-trigger="load"` for fast initial HTML
- [ ] `Cache-Control: public, max-age=43200` header

**Test Requirements:**
- [ ] Anonymous user gets 200 for valid public slug
- [ ] Returns 404 for non-existent slug
- [ ] Returns 404 for private team's slug (even if it exists)
- [ ] Context contains all required chart data
- [ ] Response includes correct Cache-Control header

---

### US-2.4: Industry Comparison Page — `/open-source/industry/{industry}/`

**As a** visitor
**I want** to compare organizations within the same industry
**So that** I can benchmark engineering performance across peers

**Acceptance Criteria:**
- [ ] URL: `/open-source/industry/<slug:industry>/` → `public:industry_detail`
- [ ] Returns 404 for invalid industry slugs
- [ ] Lists all qualifying orgs in that industry with comparison table
- [ ] Table columns: Org name, Total PRs, AI Adoption %, Median Cycle Time, Review Time, Contributors
- [ ] Sortable columns (HTMX partial reload)
- [ ] Chart: industry-wide AI adoption trend (aggregate line)
- [ ] Summary text: "The {industry} industry averages X% AI adoption across Y projects"
- [ ] Links to individual org pages
- [ ] Industry directory at `/open-source/industries/` listing all 15 categories with org counts
- [ ] `Cache-Control: public, max-age=43200` header

**Test Requirements:**
- [ ] Anonymous user gets 200 for valid industry
- [ ] Returns 404 for invalid industry
- [ ] Only shows public orgs meeting threshold
- [ ] Comparison table data is correct

---

## Epic 3: SEO Optimization

### US-3.1: Technical SEO — Meta Tags, Sitemap, Schema, JSON-LD

**As a** SEO expert
**I want** every public page to have unique, optimized meta tags and structured data
**So that** Google and AI search engines index and rank these pages

**Acceptance Criteria:**
- [ ] **Unique `<title>` per page:**
  - Directory: "Open Source Engineering Analytics — Tformance"
  - Org: "{Org} Engineering Metrics: {AI%}% AI-Assisted PRs — Tformance"
  - Industry: "{Industry} Engineering Benchmarks — Tformance"
- [ ] **Unique `<meta name="description">` with real numbers:**
  - Org: "Engineering metrics for {Org}: {total_prs} PRs analyzed, {ai_pct}% AI-assisted, {cycle_time}h median cycle time. Updated daily."
- [ ] **Open Graph tags** (`og:title`, `og:description`, `og:image`, `og:url`) on every page
- [ ] **Twitter Card tags** (`twitter:card=summary_large_image`)
- [ ] `og:image`: generic branded image for MVP (dynamic per-org in V2)
- [ ] `<link rel="canonical">` on every page
- [ ] **Django sitemap** (`PublicAnalyticsSitemap`):
  - `/open-source/` (priority 1.0, weekly)
  - `/open-source/{public_slug}/` for all qualifying orgs (priority 0.8, daily)
  - `/open-source/industry/{industry}/` for all 15 industries (priority 0.7, weekly)
  - Registered at `/sitemap.xml` in `tformance/urls.py`
  - `lastmod` uses `PublicOrgStats.last_computed_at`
- [ ] **JSON-LD `Dataset` schema** on every org detail page:
  - `name`, `description`, `temporalCoverage`, `variableMeasured` (array of PropertyValue), `creator` (Tformance), `dateModified`
- [ ] **JSON-LD `FAQPage` schema** with 2-3 auto-generated questions per org:
  - "What percentage of {Org} pull requests are AI-assisted?"
  - "What is {Org}'s median PR cycle time?"
  - "What AI tools does {Org} use?"
- [ ] **Internal linking**: each org page links to its industry page + 3 related orgs

**Test Requirements:**
- [ ] Every public view has non-empty title, meta description, canonical URL
- [ ] Sitemap returns valid XML with expected number of URLs
- [ ] JSON-LD is valid JSON and contains required schema.org fields
- [ ] OG tags are present in HTML head
- [ ] Sitemap lastmod dates are accurate

---

### US-3.2: Update robots.txt for AI Crawlers

**As a** SEO/GEO expert
**I want** robots.txt to explicitly allow AI search crawlers
**So that** our data appears in AI search results

**Acceptance Criteria:**
- [ ] Update `templates/robots.txt` to add AI crawler rules:
  ```
  # AI Search Crawlers (allow — these drive citations)
  User-agent: OAI-SearchBot
  Allow: /open-source/

  User-agent: ChatGPT-User
  Allow: /open-source/

  User-agent: ClaudeBot
  Allow: /open-source/

  User-agent: Claude-SearchBot
  Allow: /open-source/

  User-agent: PerplexityBot
  Allow: /open-source/

  User-agent: Amazonbot
  Allow: /open-source/

  User-agent: DuckAssistBot
  Allow: /open-source/

  # AI Training Crawlers (allow — brand awareness from training data)
  User-agent: GPTBot
  Allow: /open-source/

  User-agent: Google-Extended
  Allow: /open-source/

  User-agent: anthropic-ai
  Allow: /open-source/
  ```
- [ ] Allow `/open-source/` in existing wildcard rules
- [ ] Keep blocking: `/admin/`, `/accounts/`, `/api/`, `/survey/`, `/app/`

**Test Requirements:**
- [ ] robots.txt renders correctly with all new rules
- [ ] Blocked paths are still blocked

---

## Epic 4: Generative Engine Optimization (GEO)

### US-4.1: Upgrade llms.txt with OSS Analytics Links

**As a** GEO expert
**I want** llms.txt to include links to all public OSS analytics pages
**So that** AI agents can discover and cite our data

**Acceptance Criteria:**
- [ ] Convert `llms.txt` from static template to dynamic view:
  - Query `PublicOrgProfile.objects.filter(is_public=True)` with `PublicOrgStats`
  - Generate org links dynamically
  - Cache output for 24h
- [ ] Add new section:
  ```
  ## Open Source Engineering Analytics
  - [Directory](https://tformance.com/open-source/): Engineering metrics for 60+ OSS companies
  - [PostHog](https://tformance.com/open-source/posthog/): PostHog engineering metrics — 21% AI adoption
  - ...
  ```
- [ ] Keep existing sections (docs, features, comparisons)
- [ ] File size stays under 10KB
- [ ] Content-Type: `text/plain; charset=utf-8`
- [ ] `Cache-Control: public, max-age=86400` (24h)

**Test Requirements:**
- [ ] llms.txt returns 200 with correct content type
- [ ] Contains all public orgs
- [ ] Does NOT contain private orgs

---

### US-4.2: Generate `llms-full.txt` as Static File

**As a** GEO expert
**I want** a comprehensive text file with all OSS metrics inline
**So that** LLMs can consume all our data in a single request

**Acceptance Criteria:**
- [ ] Generated by `compute_public_stats_task` after daily sync (not on-demand)
- [ ] Written to `static_root/llms-full.txt` (served by WhiteNoise or Django)
- [ ] Format (Markdown):
  ```markdown
  # Tformance Open Source Engineering Analytics

  > Engineering metrics and AI coding tool adoption data for 60+
  > open-source repositories. Updated daily.

  ## PostHog
  Source: https://tformance.com/open-source/posthog/
  Industry: Product Analytics & Observability
  - Total PRs Analyzed: 4,521
  - AI-Assisted PR Rate: 21%
  - Median Cycle Time: 18 hours
  - Active Contributors (90d): 142
  - Top AI Tools: GitHub Copilot (68%), Cursor (22%)
  - Data as of: February 2026
  ```
- [ ] Includes all qualifying orgs with key stats
- [ ] Content-Type: `text/plain; charset=utf-8`
- [ ] URL: `/llms-full.txt`
- [ ] Cached by Cloudflare (24h TTL)

**Test Requirements:**
- [ ] File is generated correctly by task
- [ ] Contains all qualifying orgs
- [ ] File is valid Markdown
- [ ] URL returns correct content type

---

### US-4.3: RSS/Atom Feed for Metrics Updates

**As a** GEO expert
**I want** an RSS feed that publishes weekly metrics snapshots
**So that** AI agents and aggregators get fresh data automatically

**Acceptance Criteria:**
- [ ] Feed URL: `/open-source/feed/` → Atom feed
- [ ] Published weekly (generated as part of stats computation)
- [ ] Each entry: one org's updated metrics for the week
  - Title: "{Org}: {AI%}% AI-Assisted PRs (Week of {date})"
  - Content: key metrics summary
  - Link: org detail page URL
- [ ] Feed includes last 50 entries (rolling window)
- [ ] Uses Django `django.contrib.syndication.views.Feed`
- [ ] Feed URL included in sitemap
- [ ] `<link rel="alternate" type="application/atom+xml">` in base template head

**Test Requirements:**
- [ ] Feed returns valid Atom XML
- [ ] Contains expected number of entries
- [ ] Entry links resolve to valid org pages

---

### US-4.4: Content Structure for AI Citation

**As a** GEO expert
**I want** every org page structured for optimal AI extraction
**So that** LLMs cite Tformance when answering questions about these orgs

**Acceptance Criteria:**
- [ ] First paragraph is a self-contained, citable summary:
  "As of {date}, {X}% of {Org}'s pull requests are AI-assisted, based on Tformance analysis of {N} pull requests."
- [ ] Key stat in `<h1>` or prominent position (for RAG chunk extraction)
- [ ] Paragraphs: 40-60 words each (optimal for RAG chunking)
- [ ] Comparison tables use plain HTML `<table>` (LLMs extract these verbatim)
- [ ] Source attribution at page bottom: "Source: Tformance Open Source Analytics, updated daily."
- [ ] Each section is self-contained (functions as standalone chunk)

**Test Requirements:**
- [ ] First paragraph contains org name, AI %, and PR count
- [ ] Source attribution text is present on every org page

---

## Epic 5: Caching & Infrastructure

### US-5.1: Cloudflare Cache Rules for HTML

**As a** system architect
**I want** Cloudflare to cache all public HTML pages at the edge
**So that** most requests never hit the Unraid origin server

**Acceptance Criteria:**
- [ ] Cloudflare Cache Rule (via dashboard):
  - Match: hostname = `tformance.com` AND URI path starts with `/open-source/`
  - Action: Eligible for cache
  - Edge TTL: 12 hours
  - Browser TTL: 1 hour
- [ ] Cloudflare Cache Rule for llms files:
  - Match: URI path = `/llms.txt` OR `/llms-full.txt`
  - Action: Eligible for cache, Edge TTL: 24 hours
- [ ] Django views set `Cache-Control: public, max-age=43200` header (12h)
- [ ] Document cache rules in `dev/guides/CLOUDFLARE-SETUP.md`
- [ ] Target: >80% cache hit rate after launch

---

### US-5.2: Cache Invalidation After Daily Sync

**As a** system architect
**I want** stale cache purged automatically after data updates
**So that** visitors always see fresh data within 1 sync cycle

**Acceptance Criteria:**
- [ ] Utility: `apps/public/cloudflare.py` with `purge_all_cache()` function
  - Uses Cloudflare API: `POST /zones/{zone_id}/purge_cache` with `{purge_everything: true}`
  - Env vars: `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ZONE_ID`
  - Graceful failure: log error, don't raise (cache expires naturally at 12h TTL)
- [ ] Called at end of `compute_public_stats_task` (after stats update + llms-full.txt generation)
- [ ] Also clears Django Redis cache keys (prefix: `public:`)
- [ ] Fire-and-forget: don't block pipeline on purge success
- [ ] Logging: log purge success/failure with response details

**Test Requirements:**
- [ ] Purge function handles API errors gracefully (mock tests)
- [ ] Purge function is called after stats computation (mock verify)
- [ ] Disabled gracefully when env vars not set (dev/test environments)

---

### US-5.3: Rate Limiting & Server Protection

**As a** system architect
**I want** the public pages protected from abuse
**So that** my Unraid server stays healthy under unexpected load

**Acceptance Criteria:**
- [ ] Cloudflare Rate Limiting Rule (free tier: 1 rule):
  - Match: URI path starts with `/open-source/`
  - Rate: 60 requests per minute per IP
  - Action: Block for 10 minutes
- [ ] Django `@ratelimit` decorator on public views as backup:
  - 30 req/min per IP for page views
  - 10 req/min per IP for feeds
- [ ] Cloudflare WAF free managed ruleset enabled
- [ ] DDoS protection: enabled by default (free tier)
- [ ] Run 2 `cloudflared` tunnel replicas in Docker on Unraid

---

## Epic 6: Content & Launch

### US-6.1: Content for First Launch

**As a** product manager
**I want** compelling content on directory and org pages
**So that** visitors understand the value and share the pages

**Acceptance Criteria:**
- [ ] Directory page intro: 2-3 sentences explaining the offering
- [ ] Each org page has:
  - `PublicOrgProfile.description` (populated from GitHub org API)
  - Methodology section (shared `_methodology.html` partial)
  - "Why these metrics matter" educational sidebar
- [ ] Industry pages have 1-paragraph context about the category
- [ ] CTA on every page: "Get these metrics for YOUR repos" → signup link

---

### US-6.2: "Request Your Repo" Form

**As a** OSS maintainer
**I want** to request my repository be added to the public analytics
**So that** I can get free metrics for my project

**Acceptance Criteria:**
- [ ] URL: `/open-source/request/` → `public:request_repo`
- [ ] Form fields: GitHub repo URL (required), email (required), role (choices)
- [ ] Validation: URL must match `github.com/{owner}/{repo}` pattern
- [ ] Stores in `PublicRepoRequest` model
- [ ] Rate limited: 3 requests per email per day (`@ratelimit`)
- [ ] Success page: "Thanks! We'll review your request within 48h."
- [ ] Registered in Django admin for manual review
- [ ] No auto-provisioning in MVP

**Test Requirements:**
- [ ] Valid submission creates model instance
- [ ] Invalid GitHub URL rejected
- [ ] Rate limit enforced (4th request in same day → 429)
- [ ] Success page renders correctly

---

### US-6.3: Monitoring & Analytics

**As a** product manager
**I want** to track traffic and engagement on public pages
**So that** I can measure ROI and optimize

**Acceptance Criteria:**
- [ ] PostHog events: page views on all public pages (existing tracking)
- [ ] Custom PostHog event: `public_org_viewed` with properties: `org_slug`, `industry`, `referrer`
- [ ] Custom PostHog event: `public_signup_cta_clicked` with `source_page`
- [ ] Track AI crawler visits: log `User-Agent` for known AI bots (lightweight middleware)
- [ ] Cloudflare Analytics: monitor cache hit rate, bandwidth

---

## Cross-Cutting: Security Test Suite

**File:** `apps/public/tests/test_security.py`

**Tests (run in CI on every commit):**
- [ ] Create a private team (no `PublicOrgProfile`). Verify its data NEVER appears in directory, org detail, industry, or llms.txt views.
- [ ] Create a public team AND a private team. Directory only shows public team.
- [ ] Org detail returns 404 for private team's slug.
- [ ] Service methods return zero results for private teams.
- [ ] `llms-full.txt` file contains only public org data.
- [ ] RSS feed contains only public org entries.
- [ ] All public views work for anonymous users (no auth redirect).

---

## Cross-Cutting: E2E Smoke Tests

**File:** `apps/public/tests/test_e2e.py` (or via `make e2e`)

**Tests:**
- [ ] Directory page loads, has correct H1, shows at least 1 org card
- [ ] Org detail page loads, has 3 chart containers, has JSON-LD `<script>` tag
- [ ] `sitemap.xml` returns valid XML with expected number of URLs
- [ ] `llms.txt` returns non-empty `text/plain`
- [ ] `llms-full.txt` returns non-empty `text/plain`

---

## Implementation Sequence

```
Phase 1: Foundation (Week 1)
├── US-1.1: Create apps/public + models + migrations + indexes
├── US-1.2: Shared aggregations module + PublicAnalyticsService
├── US-1.3: Verify data + daily sync + stats computation task
└── US-2.1: Public base template

Phase 2: Core Pages (Week 2)
├── US-2.2: Directory page
├── US-2.3: Org detail page (with charts)
├── US-2.4: Industry comparison page
└── Security test suite (cross-cutting)

Phase 3: SEO & GEO (Week 3)
├── US-3.1: Meta tags, sitemap, JSON-LD schema
├── US-3.2: Update robots.txt
├── US-4.1: Upgrade llms.txt (dynamic)
├── US-4.2: Generate llms-full.txt (static file)
├── US-4.3: RSS feed
└── US-4.4: Content structure for AI citation

Phase 4: Infrastructure & Launch (Week 4)
├── US-5.1: Cloudflare cache rules
├── US-5.2: Cache invalidation
├── US-5.3: Rate limiting
├── US-6.1: Content polish
├── US-6.2: Request repo form
├── US-6.3: Monitoring setup
└── E2E smoke tests (cross-cutting)
```

## Cost Analysis

| Item | Monthly Cost |
|------|-------------|
| Hosting (Unraid) | $0 (existing) |
| Cloudflare (free tier) | $0 |
| GitHub API (101 repos daily) | $0 (free with PAT) |
| LLM processing (if enabled) | ~$0.26/1000 PRs via Groq |
| Domain/DNS | $0 (existing) |
| **Total** | **~$0/month** (LLM optional) |

## Success Metrics

| Metric | Target (Month 1) | Target (Month 3) |
|--------|------------------|------------------|
| Pages indexed by Google | 30+ | 60+ org pages |
| Organic traffic (monthly) | 1,000 | 5,000-10,000 |
| AI search citations | 5+ | 50+ |
| Signup CTA clicks | 50 | 200 |
| Cache hit rate | 80% | 90%+ |
| Repo requests submitted | 10 | 50 |

## Out of Scope (V2+)

- Bounty tracking integration (separate epic)
- Expanding beyond 101 repos / lowering threshold
- Dynamic OG image generation per org
- Public API with rate-limited keys
- Embeddable badges ("Powered by Tformance")
- User accounts for OSS maintainers
- Side-by-side org comparison tool
- Historical snapshots of org metrics over time
