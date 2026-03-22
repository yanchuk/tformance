# Plan: Public App-Reuse PoC for OSS Analytics Pages

## Alignment Status (2026-02-16)

Implemented route set (public, anonymous):

- `/open-source/`
- `/open-source/<slug>/` (`public:org_detail`, alias `public:org_overview`)
- `/open-source/<slug>/analytics/` (`public:org_analytics`)
- `/open-source/<slug>/pull-requests/`

Implemented read-only matrix (public mode):

- Enabled: dashboard/analytics chart exploration, PR filtering/sorting/pagination.
- Disabled/hidden: POST actions, notes, feedback, insight dismissal, export writes.
- Team-sensitive protection: no per-contributor breakdown surfaced on public analytics page.

## Context

We already have a PoC on branch `feature/public-oss-analytics` that builds **dedicated public views** (Approach A). Now we want to implement a second PoC (Approach B) that **reuses the actual authenticated app views** in read-only mode at `/open-source/{slug}/`, so we can compare both experiences side-by-side.

Additionally, we need to evaluate which approach better supports **GEO (Generative Engine Optimization)** — the Princeton-backed framework for getting cited by AI search engines (ChatGPT, Perplexity, Google AI Overviews). The GEO research (`.claude/skills/seo-geo/references/geo-research.md`) identifies 9 optimization methods, with the top 4 being: Cite Sources (+40%), Statistics Addition (+37%), Quotation Addition (+30%), and Authoritative Tone (+25%).

---

## GEO Comparison: Approach A vs Approach B

### Approach A: Dedicated Public Views (existing PoC)
Custom templates with hand-crafted content blocks optimized for SEO/GEO.

**GEO Strengths:**
- Full control over HTML structure — can craft "answer-first" paragraphs optimized for RAG chunking (40-60 word paragraphs)
- Can embed citable summary sentences directly: "As of Feb 2026, 21% of PostHog's pull requests are AI-assisted, based on Tformance analysis of 4,521 PRs."
- Easy to add JSON-LD `Dataset` + `FAQPage` schema in every template
- Can inline chart DATA as text/tables (not just canvas elements) — critical because Googlebot and AI crawlers can't read `<canvas>` charts
- Prose content blocks with statistics naturally satisfy GEO methods 1-4 (citations, stats, authoritative tone, easy-to-understand)
- Self-contained pages — each page is a complete, citable source

**GEO Weaknesses:**
- Less product depth = less time-on-page = fewer engagement signals
- Simpler pages may appear less authoritative than a full dashboard

### Approach B: App View Reuse (this PoC)
Reuses the actual product views in read-only mode.

**GEO Strengths:**
- More pages indexed (60+ orgs × 3 tabs = 180+ URLs vs 60+ orgs × 1 page)
- Richer content per page = more internal linking opportunities
- Interactive charts show product depth (good for human visitors who then share links)
- PR list with real data provides massive unique content per org

**GEO Weaknesses:**
- HTMX-loaded chart partials are **invisible to AI crawlers** (they see skeleton `<div>` with `hx-trigger="load"`)
- Product-oriented UI lacks the citable prose paragraphs AI systems prefer
- Dashboard layout doesn't naturally produce 40-60 word extractable paragraphs
- No "answer-first" format — AI crawlers see stat cards, not sentences
- JSON-LD schema harder to add to reused templates without modification

### GEO Verdict: **Hybrid approach needed**

The PoC B wrapper views give us the perfect hook: since public templates are NEW files (not modifying existing ones), we can **prepend GEO-optimized content blocks** above the reused dashboard content. This combines Approach B's product depth with Approach A's GEO content structure:

```
[GEO-optimized citable summary paragraph]  ← NEW: for AI crawlers (from PublicOrgStats)
[JSON-LD Dataset + FAQPage schema]          ← NEW: for AI crawlers
[Inline stats table (plain HTML)]           ← NEW: for AI crawlers (from PublicOrgStats)
[Reused dashboard charts + filters]         ← REUSED: for human visitors (from dashboard_service)
[CTA bar]                                   ← NEW: for conversion
```

**Key data source split:** GEO content block uses pre-computed `PublicOrgStats` (fast single-row read, computed by Celery task). Interactive charts use live `dashboard_service.*` queries (lazy-loaded via HTMX). This ensures fast server-side render for AI crawlers while humans get interactive charts.

This hybrid is only possible with Approach B's wrapper template pattern, because we control the public template while leaving auth templates untouched.

---

## Review Decisions (16 items resolved)

| # | Issue | Decision |
|---|-------|----------|
| 1 | 2 chart partials have auth URLs | Create public copies of `pr_size_chart.html` and `review_distribution_chart.html` |
| 2 | PR table has 3 layers of auth deps | Build minimal ~80-line public table from scratch |
| 3 | Decorator doesn't cleanup `set_current_team` token | Add try/finally with `unset_current_team(token)` |
| 4 | 5 chart wrapper views are near-identical | Accept duplication for PoC |
| 5 | Tests are Step 9 (violates TDD) | Interleave tests with each implementation phase |
| 6 | Context processor uses clever `and` pattern | Use explicit conditional |
| 7 | 12+ views in one file | Pre-split into `views/` package from start |
| 8 | No handling for empty/stale org data | Add `has_sufficient_data` check in decorator |
| 9 | 13 missing test cases | Add all 13 (total: 25 tests) |
| 10 | No HTMX URL verification in tests | Add `assertContains` for `hx-get` URL strings |
| 11 | GEO test assertions too weak | Strengthen: verify `@type`, real stats, no unrendered vars |
| 12 | Test files don't mirror views structure | 6 test files mirroring views/ package |
| 13 | No Django-level caching | Add `@cache_page(3600)` to all public views |
| 14 | GEO stats source unclear | GEO from `PublicOrgStats`, charts from `dashboard_service` |
| 15 | Profile lookup runs per HTMX partial | Accept for PoC (~6ms total, negligible) |
| 16 | Staleness not communicated | Display actual `last_computed` date in template |

---

## Implementation Plan

### Phase 0: Branch Setup & Data Layer Cherry-Pick

**Create new branch** from `main`:
```
git checkout -b feature/public-app-reuse
```

**Cherry-pick data layer files** from `feature/public-oss-analytics` (single commit `355ecda`). Use `git checkout` to pull specific files:

Cherry-pick these files from the PoC branch:
- `apps/public/__init__.py`
- `apps/public/apps.py`
- `apps/public/models.py` — PublicOrgProfile, PublicOrgStats, PublicRepoRequest
- `apps/public/admin.py` — Admin registration for all 3 models
- `apps/public/migrations/__init__.py`
- `apps/public/migrations/0001_initial.py` — Creates models
- `apps/public/migrations/0002_populate_public_org_profiles.py` — Seeds from REAL_PROJECTS
- `apps/public/aggregations.py` — 600+ lines of pure aggregation functions
- `apps/public/services.py` — PublicAnalyticsService with caching
- `apps/public/tasks.py` — compute_public_stats_task, clear_public_cache_task
- `apps/public/forms.py` — RepoRequestForm
- `apps/public/sitemaps.py` — PublicDirectorySitemap, PublicOrgSitemap, PublicIndustrySitemap
- `apps/public/cloudflare.py` — purge_all_cache()
- `apps/public/middleware.py` — AIBotLoggingMiddleware
- `apps/public/templatetags/__init__.py`

**DO NOT cherry-pick** (we rewrite these):
- `apps/public/views.py`
- `apps/public/urls.py`
- `templates/public/*`

**Modify `tformance/settings.py`:**
- Add `"apps.public"` to `INSTALLED_APPS`
- Add `"apps.public.context_processors.public_mode"` to `TEMPLATES[0]['OPTIONS']['context_processors']`

**Run migrations:** `.venv/bin/python manage.py migrate public`

---

### Phase 1: Public Decorator — `apps/public/decorators.py` (NEW)

Create a **separate** decorator (not modifying existing auth decorators):

```python
from functools import wraps
from django.http import Http404
from apps.teams.context import set_current_team, unset_current_team
from apps.public.models import PublicOrgProfile

def public_org_required(view_func):
    """Sets request.team from PublicOrgProfile.public_slug URL kwarg.
    Works for anonymous users. Sets request.is_public_view = True.
    Manages set_current_team lifecycle with try/finally."""
    @wraps(view_func)
    def _inner(request, *args, **kwargs):
        slug = kwargs.pop("public_slug", None)
        try:
            profile = PublicOrgProfile.objects.select_related("team").get(
                public_slug=slug, is_public=True
            )
        except PublicOrgProfile.DoesNotExist:
            raise Http404

        # Gate: require sufficient data to avoid empty/broken public pages
        if not profile.has_sufficient_data:
            raise Http404

        request.team = profile.team
        request.is_public_view = True
        request.public_profile = profile

        # Set team context for for_team manager queries
        token = set_current_team(profile.team)
        try:
            return view_func(request, *args, **kwargs)
        finally:
            unset_current_team(token)

    return _inner
```

**`has_sufficient_data` property** — Add to `PublicOrgProfile` model (or check `PublicOrgStats`):
```python
@property
def has_sufficient_data(self):
    """Require minimum 10 PRs to show public page."""
    stats = getattr(self, 'stats', None)  # reverse FK from PublicOrgStats
    if not stats:
        return False
    return stats.total_prs >= 10
```

**Key files referenced:**
- `apps/teams/decorators.py` (lines 17-31 for pattern)
- `apps/teams/context.py` (for `set_current_team` / `unset_current_team` / `current_team` context manager)

---

### Phase 2: Context Processor — `apps/public/context_processors.py` (NEW)

```python
def public_mode(request):
    _profile = getattr(request, "public_profile", None)
    return {
        "is_public_view": getattr(request, "is_public_view", False),
        "public_profile": _profile,
        "public_slug": _profile.public_slug if _profile else None,
    }
```

Makes `is_public_view` and `public_slug` available in all templates without passing through every view context.

---

### Phase 3: URL Routing — `apps/public/urls.py` (REWRITE)

```python
app_name = "public"

urlpatterns = [
    # Directory (standalone, not reusing app views)
    path("", views.directory, name="directory"),

    # Org-scoped pages (wrapper views that reuse service layer)
    path("<slug:public_slug>/", views.org_overview, name="org_overview"),
    path("<slug:public_slug>/pull-requests/", views.org_pr_list, name="org_pr_list"),

    # HTMX chart/card partials (public equivalents using same service functions)
    path("<slug:public_slug>/charts/ai-adoption/", views.public_ai_adoption_chart, name="chart_ai_adoption"),
    path("<slug:public_slug>/charts/cycle-time/", views.public_cycle_time_chart, name="chart_cycle_time"),
    path("<slug:public_slug>/charts/pr-size/", views.public_pr_size_chart, name="chart_pr_size"),
    path("<slug:public_slug>/charts/review-distribution/", views.public_review_distribution_chart, name="chart_review_distribution"),
    path("<slug:public_slug>/cards/metrics/", views.public_key_metrics_cards, name="cards_metrics"),

    # PR list HTMX partial
    path("<slug:public_slug>/pull-requests/table/", views.public_pr_list_table, name="pr_list_table"),

    # Industry comparison (standalone)
    path("industry/<slug:industry>/", views.industry_comparison, name="industry"),

    # Request repo form (standalone)
    path("request/", views.request_repo, name="request_repo"),
    path("request/success/", views.request_success, name="request_success"),
]
```

**Mount in `tformance/urls.py`:** Add `path("open-source/", include("apps.public.urls"))` to urlpatterns.

---

### Phase 4: Public Views — `apps/public/views/` Package (REWRITE)

**Pre-split into package structure** (CLAUDE.md: files > 300 lines → split):

```
apps/public/views/
├── __init__.py           # Re-exports all views
├── directory_views.py    # directory, industry_comparison, request_repo, request_success
├── org_views.py          # org_overview, org_pr_list, public_pr_list_table
└── chart_views.py        # 5 chart/card partial wrapper views
```

**Architecture:** Thin wrapper views that:
1. Use `@cache_page(3600)` + `@public_org_required` decorator stack
2. Call the **same service functions** as authenticated views
3. Build context with public-specific additions
4. Render **new public templates** (not modifying existing ones)

**Views to create:**

| View | Data Source | Template |
|------|-----------|----------|
| `directory` | `PublicAnalyticsService.get_directory_data()` | `public/directory.html` (from PoC) |
| `org_overview` | **GEO block:** `PublicOrgStats` (pre-computed). **Charts:** `dashboard_service.*` via HTMX | `public/org_overview.html` (NEW) |
| `org_pr_list` | `pr_list_service.get_prs_queryset()`, `get_pr_stats()`, `get_filter_options()` | `public/org_pr_list.html` (NEW) |
| `public_ai_adoption_chart` | `dashboard_service.get_ai_adoption_trend()` | `metrics/partials/ai_adoption_chart.html` (REUSE) |
| `public_cycle_time_chart` | `dashboard_service.get_cycle_time_trend()` | `metrics/partials/cycle_time_chart.html` (REUSE) |
| `public_pr_size_chart` | `dashboard_service.get_pr_size_distribution()` | `public/partials/pr_size_chart.html` (PUBLIC COPY) |
| `public_review_distribution_chart` | `dashboard_service.get_review_distribution()` | `public/partials/review_distribution_chart.html` (PUBLIC COPY) |
| `public_key_metrics_cards` | `dashboard_service.get_key_metrics()`, `get_sparkline_data()` | `metrics/partials/key_metrics_cards.html` (REUSE) |
| `public_pr_list_table` | `pr_list_service.get_prs_queryset()` | `public/partials/pr_table.html` (NEW — built from scratch) |
| `industry_comparison` | `PublicAnalyticsService.get_industry_comparison()` | `public/industry.html` (from PoC) |

**Template reuse verification (from code review):**

| Template | Auth URLs? | Safe to Reuse? |
|----------|-----------|----------------|
| `ai_adoption_chart.html` | None | ✅ REUSE directly |
| `cycle_time_chart.html` | None | ✅ REUSE directly |
| `key_metrics_cards.html` | None | ✅ REUSE directly |
| `pr_size_chart.html` | `{% url 'pullrequests:pr_list' %}` | ❌ Needs PUBLIC COPY |
| `review_distribution_chart.html` | `{% url 'metrics:pr_list' %}` | ❌ Needs PUBLIC COPY |
| `pull_requests/partials/table.html` | 7 auth URLs + notes + feedback + expanded_row | ❌ BUILD FROM SCRATCH |

**Service function safety (verified by code review):** All `dashboard_service.*` and `pr_list_service.*` functions are pure read-only, take `team` parameter (not `request.user`), have no write side effects, and no `track_event()` calls.

---

### Phase 5: Templates

#### 5a. `templates/public/app_base.html` (NEW)
Public-specific base that replaces sidebar with:
- Org hero section (logo, name, industry badge, GitHub link, **actual last_computed date**)
- Horizontal tab navigation (Overview / Pull Requests)
- Breadcrumbs: Open Source → {Industry} → {Org Name}
- Sticky CTA bar at bottom
- Extends `web/base.html` (same root as auth pages)

#### 5b. `templates/public/org_overview.html` (NEW)
Extends `public/app_base.html`. Contains:

**GEO Content Block (top of page, from `PublicOrgStats`):**
```html
<!-- Citable summary for AI crawlers (GEO Methods 1-4) -->
<div class="prose max-w-3xl mb-8">
  <p>As of {{ public_stats.last_computed|date:"F Y" }}, {{ public_stats.ai_assisted_pct }}% of {{ org_name }}'s
  pull requests are AI-assisted, based on Tformance analysis of
  {{ public_stats.total_prs|intcomma }} merged pull requests. The median PR cycle time is
  {{ public_stats.median_cycle_time_hours }}h, with {{ public_stats.active_contributors }} active contributors in the
  last 90 days. Data source: public GitHub repositories,
  updated {{ public_stats.last_computed|timesince }} ago.</p>
</div>

<!-- Inline stats table (AI crawlers can extract this) -->
<table class="table">
  <tr><th>Metric</th><th>Value</th><th>Industry Median</th></tr>
  <tr><td>AI-Assisted PRs</td><td>{{ public_stats.ai_assisted_pct }}%</td><td>{{ industry_avg_ai }}%</td></tr>
  <tr><td>Median Cycle Time</td><td>{{ public_stats.median_cycle_time_hours }}h</td><td>{{ industry_avg_cycle }}h</td></tr>
  ...
</table>
```

**Dashboard Content (reused via HTMX, for human visitors):**
```html
<!-- Key Metrics Cards (HTMX lazy-load via public: namespace) -->
<div hx-get="{% url 'public:cards_metrics' public_slug=public_slug %}?days={{ days }}"
     hx-trigger="load" hx-swap="innerHTML">
  <!-- skeleton -->
</div>

<!-- Charts grid (HTMX lazy-load via public: namespace) -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <div class="card">
    <h2>AI Adoption Trend</h2>
    <div hx-get="{% url 'public:chart_ai_adoption' public_slug=public_slug %}?days={{ days }}"
         hx-trigger="load"><!-- spinner --></div>
  </div>
  ...
</div>
```

**JSON-LD Schema (in head block):**
- `Dataset` schema with variableMeasured
- `FAQPage` schema with 3 auto-generated Q&As

#### 5c. `templates/public/org_pr_list.html` (NEW)
Extends `public/app_base.html`. PR explorer with:
- Filters (AI/date/size/author) — reusing the same filter pattern
- Sort headers pointing to `{% url 'public:pr_list_table' public_slug=public_slug %}`
- Export button: visible but disabled with tooltip CTA
- No notes UI
- Banner: "Exploring X PRs. Want to see yours? [Start Free Trial]"

#### 5d. `templates/public/partials/pr_table.html` (NEW — built from scratch)
Minimal ~80-line table purpose-built for public view:
- Sort headers with `hx-get="{% url 'public:pr_list_table' public_slug=public_slug %}"` + `hx-push-url`
- Columns: Title, Author, Size, AI-Assisted badge, Cycle Time, Merged Date
- Pagination with public namespace URLs
- **NO** notes column, expanded row, feedback thumbs, or note_icon include
- **NO** transitive includes from notes/ or feedback/ apps

#### 5e. `templates/public/partials/pr_size_chart.html` (PUBLIC COPY)
Copy of `metrics/partials/pr_size_chart.html` with:
- `{% url 'pullrequests:pr_list' %}` → `{% url 'public:org_pr_list' public_slug=public_slug %}` (or remove link)

#### 5f. `templates/public/partials/review_distribution_chart.html` (PUBLIC COPY)
Copy of `metrics/partials/review_distribution_chart.html` with:
- `{% url 'metrics:pr_list' %}` → `{% url 'public:org_pr_list' public_slug=public_slug %}` (or remove link)

#### 5g. `templates/public/partials/sticky_cta.html` (NEW)
Fixed bottom bar with org input + "Connect Repos" button.

#### 5h. `templates/web/components/top_nav_public.html` (NEW)
Simplified nav: logo + "Open Source" link + "Get this for your team" CTA button. No user menu.

#### 5i. Cherry-pick from PoC branch:
- `templates/public/directory.html` — adapt to extend `public/app_base.html` or keep as-is
- `templates/public/_directory_list.html` — HTMX partial for directory
- `templates/public/industry.html`
- `templates/public/request_repo.html`
- `templates/public/request_success.html`

---

### Phase 6: SEO/GEO Integration

These apply to BOTH approaches equally (shared infrastructure):

1. **Update `tformance/urls.py` sitemaps dict** — add public sitemaps from `apps/public/sitemaps.py`
2. **Update `templates/robots.txt`** — add AI crawler Allow rules for `/open-source/`
3. **llms.txt upgrade** — convert to dynamic view, add org links section
4. **Canonical URLs** — add `<link rel="canonical">` in public base template
5. **Meta tags** — add `{% block meta_description %}` and `{% block og_tags %}` in org templates

**GEO-specific for Approach B (app-reuse):**
- GEO content block uses **`PublicOrgStats`** (pre-computed, fast) — NOT live `dashboard_service` queries
- Inline HTML `<table>` with key stats (AI crawlers can extract this even if charts are HTMX-loaded)
- JSON-LD `Dataset` schema in every org page `<head>`
- JSON-LD `FAQPage` schema with 3 questions per org
- Source attribution at page bottom uses actual date: "Source: Tformance Open Source Analytics, updated {{ public_stats.last_computed|timesince }} ago."
- `@cache_page(3600)` on all public views for Django-level caching (safety net behind CDN)

---

### Tests — Interleaved Per Phase (TDD)

Tests are written **alongside each implementation phase**, not at the end.

**6 test files mirroring views/ package:**

```
apps/public/tests/
├── __init__.py
├── test_decorators.py        # Decorator unit tests (Phase 1)
├── test_directory_views.py   # Directory + industry views (Phase 4)
├── test_org_views.py         # Overview + PR list views (Phase 4)
├── test_chart_views.py       # Chart/card partial views (Phase 4)
├── test_security.py          # Cross-cutting security assertions
└── test_geo.py               # GEO content + JSON-LD assertions
```

**25 test cases:**

**test_decorators.py** (write with Phase 1):
1. `test_decorator_sets_request_team`
2. `test_decorator_sets_is_public_view_flag`
3. `test_decorator_404_invalid_slug`
4. `test_decorator_404_is_public_false`
5. `test_decorator_404_insufficient_data` (has_sufficient_data gate)
6. `test_decorator_cleans_up_team_context` (try/finally token cleanup)

**test_directory_views.py** (write with Phase 4 directory):
7. `test_directory_loads_200_anonymous`
8. `test_private_team_never_in_directory`

**test_org_views.py** (write with Phase 4 org views):
9. `test_org_overview_200_valid_slug`
10. `test_org_overview_htmx_urls_correct` (assertContains on `hx-get` URLs)
11. `test_pr_list_200_with_filters`
12. `test_pr_list_table_htmx_urls_correct`
13. `test_no_export_link_in_public_view`
14. `test_no_notes_ui_in_public_view`
15. `test_no_feedback_thumbs_in_pr_table`

**test_chart_views.py** (write with Phase 4 charts):
16. `test_chart_partials_return_html_fragment` (no `<html>` or `<body>` tags)
17. `test_cache_control_header_set`
18. `test_chart_partial_200_valid_slug`

**test_security.py** (write with Phase 4):
19. `test_post_request_returns_405`
20. `test_no_session_team_set` (decorator doesn't write session)
21. `test_authenticated_user_sees_public_view` (logged-in user at `/open-source/` gets public data, not their own team)

**test_geo.py** (write with Phase 5-6):
22. `test_json_ld_dataset_schema` (verify `@type: Dataset`, `variableMeasured`)
23. `test_json_ld_faq_schema` (verify `@type: FAQPage`)
24. `test_citable_paragraph_contains_real_stats` (not `None%`, not unrendered `{{ ai_pct }}`)
25. `test_inline_stats_table_present` (plain HTML `<table>` with metrics)

---

## Files Summary

| Action | File | Purpose |
|--------|------|---------|
| Cherry-pick | `apps/public/models.py` | PublicOrgProfile, PublicOrgStats, PublicRepoRequest |
| Cherry-pick | `apps/public/aggregations.py` | Pure aggregation functions (600+ lines) |
| Cherry-pick | `apps/public/services.py` | PublicAnalyticsService with caching |
| Cherry-pick | `apps/public/tasks.py` | Celery tasks for stats computation |
| Cherry-pick | `apps/public/admin.py` | Django admin registration |
| Cherry-pick | `apps/public/forms.py` | RepoRequestForm |
| Cherry-pick | `apps/public/sitemaps.py` | Sitemap classes |
| Cherry-pick | `apps/public/cloudflare.py` | CDN cache purge |
| Cherry-pick | `apps/public/middleware.py` | AI bot logging |
| Cherry-pick | `apps/public/migrations/*` | DB migrations |
| **CREATE** | `apps/public/decorators.py` | `@public_org_required` with try/finally cleanup + `has_sufficient_data` |
| **CREATE** | `apps/public/context_processors.py` | `is_public_view` template context (explicit conditional) |
| **REWRITE** | `apps/public/urls.py` | Public URL patterns with `public:` namespace |
| **CREATE** | `apps/public/views/__init__.py` | Re-exports all views |
| **CREATE** | `apps/public/views/directory_views.py` | directory, industry, request views |
| **CREATE** | `apps/public/views/org_views.py` | org_overview, org_pr_list, pr_list_table |
| **CREATE** | `apps/public/views/chart_views.py` | 5 chart/card partial wrapper views |
| **CREATE** | `templates/public/app_base.html` | Public base with hero + tabs + CTA |
| **CREATE** | `templates/public/org_overview.html` | Overview with GEO content (from PublicOrgStats) + reused charts |
| **CREATE** | `templates/public/org_pr_list.html` | PR list with filters, no notes |
| **CREATE** | `templates/public/partials/pr_table.html` | Minimal ~80-line table built from scratch |
| **CREATE** | `templates/public/partials/pr_size_chart.html` | Public copy with fixed URLs |
| **CREATE** | `templates/public/partials/review_distribution_chart.html` | Public copy with fixed URLs |
| **CREATE** | `templates/public/partials/sticky_cta.html` | Conversion CTA bar |
| **CREATE** | `templates/web/components/top_nav_public.html` | Public-only nav |
| Cherry-pick | `templates/public/directory.html` | Directory page |
| Cherry-pick | `templates/public/_directory_list.html` | Directory HTMX partial |
| Cherry-pick | `templates/public/industry.html` | Industry page |
| **MODIFY** | `tformance/urls.py` | Add `path("open-source/", ...)` + sitemaps |
| **MODIFY** | `tformance/settings.py` | Add app + context processor |
| **MODIFY** | `apps/public/models.py` | Add `has_sufficient_data` property to PublicOrgProfile |
| **CREATE** | `apps/public/tests/test_decorators.py` | 6 decorator unit tests |
| **CREATE** | `apps/public/tests/test_directory_views.py` | 2 directory view tests |
| **CREATE** | `apps/public/tests/test_org_views.py` | 7 org view tests |
| **CREATE** | `apps/public/tests/test_chart_views.py` | 3 chart partial tests |
| **CREATE** | `apps/public/tests/test_security.py` | 3 security tests |
| **CREATE** | `apps/public/tests/test_geo.py` | 4 GEO content tests |

**Existing files NOT modified:** All `apps/metrics/views/*.py`, `apps/teams/decorators.py`, `apps/teams/middleware.py`, all existing templates in `templates/metrics/`.

---

## Verification

1. **Start dev server:** `make dev`
2. **Run migrations:** `.venv/bin/python manage.py migrate public`
3. **Compute stats:** `.venv/bin/python manage.py shell -c "from apps.public.tasks import compute_public_stats_task; compute_public_stats_task()"`
4. **Run tests:** `.venv/bin/pytest apps/public/tests/ -v`
5. **Test pages in browser:**
   - `http://localhost:8000/open-source/` — directory loads, shows org cards
   - `http://localhost:8000/open-source/posthog/` — overview with GEO block + charts loading via HTMX
   - `http://localhost:8000/open-source/posthog/pull-requests/` — PR list with filters, no notes
6. **Test anonymous access:** Use incognito window
7. **Test auth pages still work:** `http://localhost:8000/app/metrics/analytics/` — unchanged
8. **Verify GEO content:** View source of org overview:
   - Citable paragraph with real stats (not `None%`)
   - JSON-LD `Dataset` + `FAQPage` schemas in `<head>`
   - Inline HTML `<table>` with metrics
   - Actual `last_computed` date (not "updated daily")
9. **Verify no data leak:** Navigate to `/open-source/nonexistent-slug/` → 404
10. **Verify insufficient data gate:** Org with < 10 PRs → 404

---

## Implementation Sequence (TDD-interleaved)

```
Step 1:  Branch setup + cherry-pick data layer + run migrations (Phase 0)
Step 2:  Add has_sufficient_data property to PublicOrgProfile model
Step 3:  Write decorator tests → implement decorator + context processor (Phase 1-2)
Step 4:  Create URL routing + mount in root urls.py (Phase 3)
Step 5:  Write directory tests → implement directory views (Phase 4 partial)
Step 6:  Create public base template (Phase 5a)
Step 7:  Write org view tests → implement org_overview + org_pr_list views (Phase 4 partial)
Step 8:  Create org_overview + org_pr_list templates with GEO blocks (Phase 5b-c)
Step 9:  Write chart tests → implement chart wrapper views (Phase 4 partial)
Step 10: Create public copies of pr_size_chart + review_distribution_chart (Phase 5e-f)
Step 11: Build public PR table from scratch (Phase 5d)
Step 12: Write security tests (Phase tests)
Step 13: Write GEO tests → add JSON-LD, meta tags, sitemap (Phase 6)
Step 14: Add @cache_page to all public views
Step 15: Manual verification in browser
```
