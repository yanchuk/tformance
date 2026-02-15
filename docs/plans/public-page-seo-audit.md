# Public Pages SEO Audit

**Date:** 2026-02-15
**Scope:** All templates and views under `apps/public/`, plus related sitemap, robots.txt, and base template infrastructure.

---

## Executive Summary

The public pages have a strong SEO foundation: JSON-LD structured data on all page types, proper `<title>` / meta description / OG tags via the base template pipeline, a well-configured `robots.txt` with AI crawler directives, and comprehensive sitemaps. The main gaps are around **canonical URL handling with query parameters**, **missing RSS autodiscovery**, **table accessibility**, and **structured data completeness for the enhanced page sections**.

---

## 1. Structured Data (JSON-LD)

### 1.1 Directory Page (`directory.html`) -- Good

- **Type:** `DataCatalog` with nested `Dataset` entries.
- **Assessment:** Well-chosen schema type. Links to individual org datasets.

**Issue (Medium): Missing `dateModified` on DataCatalog**
The directory schema lacks a `dateModified` field, even though the data is refreshed daily.

```json
"dateModified": "{{ global_stats.last_updated|date:'Y-m-d' }}"
```
*Requires adding `last_updated` to `global_stats` dict from `PublicAnalyticsService.get_global_stats()`.*

### 1.2 Org Detail Page (`org_detail.html`) -- Good

- **Types:** `Dataset` + `FAQPage` (two separate JSON-LD blocks).
- **Assessment:** Strong dual-schema approach. `variableMeasured` with `PropertyValue` entries is excellent for rich snippets.

**Issue (Low): `temporalCoverage` is hardcoded to `"2025/.."`**
Should be dynamic based on actual data range (e.g., "2025/2026"). If data extends beyond 2025, this becomes inaccurate.

**Issue (Low): Missing `license` property on Dataset**
Open data should declare its license for better data discoverability.

```json
"license": "https://creativecommons.org/licenses/by/4.0/"
```

### 1.3 Industry Page (`industry.html`) -- Good

- **Type:** `Dataset` with `variableMeasured`.
- **Assessment:** Consistent with org detail schema pattern.

**Issue (Medium): No cross-reference to child datasets**
Unlike the directory page, the industry page doesn't link to its constituent org datasets. Adding a `hasPart` array would help search engines understand the hierarchy.

```json
"hasPart": [{% for org in orgs %}
  {
    "@type": "Dataset",
    "name": "{{ org.display_name }} Engineering Metrics",
    "url": "https://tformance.com/open-source/{{ org.slug }}/"
  }{% if not forloop.last %},{% endif %}{% endfor %}
]
```

### 1.4 Methodology Section (`_methodology.html`) -- Neutral

No standalone structured data, but this is appropriate since it's an included partial. The methodology content supports the FAQ schema on the org detail page.

---

## 2. Heading Hierarchy

### 2.1 Directory Page -- Good

- `<h1>` "Open Source Engineering Metrics" -- correct, single h1.
- No h2/h3 within the stats banner (uses `<div>` with styling) -- acceptable.

**Issue (Low): No heading on the table section**
The directory list table has no semantic heading. Adding a visually-hidden `<h2>` would improve structure:
```html
<h2 class="sr-only">Organization Rankings</h2>
```

### 2.2 Org Detail Page -- Good

- `<h1>` organization name -- correct.
- `<h2>` "AI Adoption Over Time", "PR Velocity (Monthly)", "Top AI Tools Detected", "How We Measure", "Similar in ..." -- proper h2 level.
- No skipped levels.

### 2.3 Industry Page -- Good

- `<h1>` industry name -- correct.
- `<h2>` "Organization Comparison", "How We Measure" -- proper nesting.

---

## 3. Meta Tags

### 3.1 Title Tags -- Good

All three view functions set `page_title` in context, which flows through `meta_tags.py`'s `get_title` filter to produce `"Page Title | Tformance"`.

- Directory: "Open Source Engineering Analytics | Tformance"
- Org Detail: "{OrgName} Engineering Metrics: {X}% AI-Assisted PRs | Tformance"
- Industry: "{Industry} Engineering Benchmarks | Tformance"

**Assessment:** Excellent. Descriptive, keyword-rich, unique per page.

### 3.2 Meta Descriptions -- Good

All views set `page_description` with specific metrics data. These are dynamic, unique per entity, and include numeric data that stands out in SERPs.

### 3.3 Canonical URLs -- Needs Attention

**Issue (High): Canonical URL includes query parameters**

The `page_url` is set in `context_processors.py` via `absolute_url(request.path)`, which correctly uses `request.path` (not `request.get_full_path()`), so query parameters like `?industry=devtools&sort=ai_adoption` are NOT included in the canonical. This is correct behavior.

However, `page_canonical_url` is never explicitly set in any public view. The base template falls back to `page_url` which is fine for the org detail and industry pages. But for the directory page with its filter/sort parameters, the canonical correctly points to the base `/open-source/` path without params.

**Assessment:** Actually correct. No action needed -- `request.path` already strips query params.

### 3.4 Open Graph Tags -- Good

All OG tags (title, description, url, site_name) are populated via the base template.

**Issue (Medium): No page-specific OG image**

The `page_image` is never set in public views, so OG shares fall back to the global `project_meta["IMAGE"]`. For social sharing, org-specific images (e.g., a dynamically generated card with the org's key metrics) would dramatically improve click-through rates.

**Recommendation:** Generate OG images per org using a service like `satori` or a server-side template. Store in `/media/public/og/` with the org slug. Pass as `page_image` in context.

### 3.5 Twitter Card Tags -- Good

Uses `summary_large_image` card type. Same image limitation as OG above.

---

## 4. Internal Linking

### 4.1 Cross-linking Assessment -- Good Foundation, Needs Expansion

**Current links:**
- Directory -> Org detail (via table row click)
- Org detail -> Industry page (via breadcrumb + badge link + "Similar in" section)
- Industry -> Org detail (via comparison table links)
- All pages -> Directory (via breadcrumb "Open Source" link)
- CTA banner -> Signup page

**Issue (Medium): Directory table rows use JavaScript navigation, not `<a>` tags**

In `_directory_list.html` line 20, table rows use `onclick="window.location=..."` instead of wrapping the org name in an `<a>` tag. This means:
- Crawlers cannot follow these links (crawlers don't execute JavaScript)
- Users can't right-click to open in new tab
- No link preview on hover

**Fix:** The org name cell (line 22-26) should wrap in an `<a>` tag:
```html
<td>
  <a href="{% url 'public:org_detail' slug=org.slug %}" class="font-medium link link-hover">
    {{ org.display_name }}
  </a>
  {% if org.description %}
  <div class="text-xs text-base-content/40 line-clamp-1 max-w-xs">{{ org.description }}</div>
  {% endif %}
</td>
```
Keep the `onclick` on the `<tr>` for UX (clicking anywhere navigates), but the `<a>` tag gives crawlers a proper link to follow.

**Issue (Medium): Org detail "Similar in" section has no actual org links**

The "Similar in {Industry}" section at the bottom of `org_detail.html` (lines 177-186) only links to the industry page. It doesn't list any sibling organizations. Adding 3-5 related org links would:
- Improve crawl depth
- Reduce bounce rate
- Build topical authority

**Recommendation:** In `views.py:org_detail`, add related orgs to context:
```python
related_orgs = PublicAnalyticsService.get_industry_comparison(profile["industry"])
context["related_orgs"] = related_orgs["orgs"][:5] if related_orgs else []
```
Then render as links in the template.

### 4.2 RSS Feed Autodiscovery -- Missing

**Issue (Medium): No `<link rel="alternate" type="application/rss+xml">` tag**

The RSS feed exists at `/open-source/feed/` but is not discoverable via the HTML `<head>`. Browsers and feed readers won't find it automatically.

**Fix:** Add to `public/base.html` in `{% block page_head %}`:
```html
{% block page_head %}
{% block json_ld %}{% endblock %}
<link rel="alternate" type="application/rss+xml" title="Tformance Open Source Analytics" href="{% url 'public:rss_feed' %}">
{% endblock %}
```

---

## 5. URL Structure -- Excellent

- `/open-source/` -- directory
- `/open-source/<slug>/` -- org detail
- `/open-source/industry/<slug>/` -- industry comparison
- `/open-source/feed/` -- RSS
- `/open-source/request/` -- repo request form

**Assessment:** Clean, hierarchical, human-readable. Slugs are SEO-friendly. No unnecessary parameters in permanent URLs. HTMX filter/sort uses query params which are correctly excluded from canonicals.

---

## 6. Response Headers

### 6.1 Cache-Control -- Good

- HTML pages: `public, max-age=43200` (12 hours) -- appropriate for daily-refreshed data.
- LLM/RSS endpoints: `public, max-age=86400` (24 hours) -- appropriate for machine-readable content.

**Issue (Low): Missing `s-maxage` for CDN-specific caching**

If using Cloudflare or similar CDN, adding `s-maxage` allows different browser vs. CDN cache lifetimes:
```python
response["Cache-Control"] = f"public, max-age={PUBLIC_CACHE_MAX_AGE}, s-maxage=86400"
```
This lets the CDN cache for 24h while browsers revalidate every 12h.

### 6.2 Missing `Vary` Header

**Issue (Low): HTMX partial responses share the same URL as full page**

The directory view returns different content based on `HX-Request` header but doesn't set `Vary: HX-Request`. If a CDN caches the HTMX partial response, subsequent full-page requests would get the partial.

**Fix:**
```python
if request.headers.get("HX-Request"):
    response = _public_response(request, "public/_directory_list.html", context)
    response["Vary"] = "HX-Request"
    return response
```

### 6.3 Content-Type -- Good

- HTML pages: default `text/html` -- correct.
- RSS: `application/rss+xml; charset=utf-8` -- correct.
- LLM files: `text/plain; charset=utf-8` -- correct.

---

## 7. Content Quality

### 7.1 Thin Content Risk -- Low

Each org page has unique metrics data, charts, AI tools table, and dynamic FAQ. The methodology section is shared but that's appropriate.

**Issue (Low): Industry pages with few orgs may be thin**

If an industry has only 1-2 organizations, the page content is minimal. Consider:
- Setting a minimum org count (e.g., 2+) before creating an industry page
- Adding more contextual content for small industries (e.g., industry-specific descriptions)

### 7.2 Duplicate Content Risk -- Low

Each page has unique title, description, and metrics. The methodology partial is shared across pages but is supplementary content, not the main content.

---

## 8. Mobile Optimization

### 8.1 Viewport -- Good

`<meta name="viewport" content="width=device-width, initial-scale=1">` is set in base template.

### 8.2 Touch Targets -- Good

- Buttons use DaisyUI `btn` classes with adequate sizing.
- Badge links and breadcrumbs have sufficient padding.
- Table rows use `onclick` for full-row tap targets.

### 8.3 Responsive Layout -- Good

- Grid layouts use responsive breakpoints (`grid-cols-2 lg:grid-cols-4`).
- Tables have `overflow-x-auto` wrapper for horizontal scrolling.
- Filter selects use `w-full sm:w-auto` for mobile-first sizing.

---

## 9. Performance

### 9.1 Chart.js Loading

**Issue (Medium): Chart.js loaded from CDN without preconnect or preload**

In `org_detail.html` line 190, Chart.js is loaded as a blocking `<script>` tag from `cdn.jsdelivr.net`:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
```

**Recommendations:**
1. Add `<link rel="preconnect" href="https://cdn.jsdelivr.net">` to the base template (already preconnects to googleapis and cdnjs, but not jsdelivr).
2. Consider adding `async` or `defer` attribute since chart initialization waits for DOMContentLoaded anyway:
```html
<script defer src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
```

### 9.2 Font Awesome -- Good

Already uses `preload` with `onload` swap pattern for non-blocking CSS loading.

### 9.3 Google Fonts -- Good

Already uses `preload` with `onload` swap pattern.

---

## 10. AI/LLM Optimization

### 10.1 `llms.txt` -- Excellent

Well-structured with:
- Clear header and description
- Links to all org pages with key metrics inline
- Industry benchmark links
- Product pages and legal pages
- Contact information

### 10.2 `llms-full.txt` -- Excellent

Extended version with:
- Complete metrics per org
- Methodology section
- Data collection transparency

### 10.3 `robots.txt` AI Crawler Directives -- Excellent

Explicitly allows AI search crawlers (OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, PerplexityBot, Amazonbot, DuckAssistBot) and AI training crawlers (GPTBot, Google-Extended) access to `/open-source/`.

**Issue (Low): AI crawlers only allowed `/open-source/`**

The `Allow: /open-source/` directive for AI crawlers is fine for now, but consider also allowing `/report/` and other public content pages as the site grows.

### 10.4 Missing `llms.txt` Discovery

**Issue (Low): No `<link>` tag for llms.txt discovery**

While not yet a widely-adopted standard, adding a discovery link improves findability:
```html
<link rel="alternate" type="text/plain" href="/llms.txt" title="LLM Context">
```

---

## 11. Accessibility (SEO-Adjacent)

### 11.1 Directory Table

**Issue (Medium): Table uses `onclick` on `<tr>` with no keyboard accessibility**

The directory table rows (in `_directory_list.html` line 19-20) use `onclick` for navigation but:
- No `tabindex="0"` for keyboard focus
- No `role="link"` ARIA attribute
- No `onkeypress`/`onkeydown` handler for Enter key

As noted in section 4.1, the real fix is adding proper `<a>` tags. The `onclick` can remain for enhanced UX but shouldn't be the only navigation mechanism.

### 11.2 Charts -- Needs Improvement

**Issue (Medium): Canvas charts have no text fallback for screen readers**

Charts rendered via `<canvas>` are invisible to screen readers and crawlers. The `json_script` data blocks are not accessible.

**Recommendation:** Add a text summary inside a `<noscript>` or `sr-only` div near each chart:
```html
<div class="sr-only">
  AI adoption trend showing monthly percentages from the data period.
</div>
```

---

## 12. Recommendations for Enhanced Page Sections

### 12.1 Sparkline Trend Data

For the new sparkline/trend sections, add `PropertyValue` entries with trend direction:

```json
{
  "@type": "PropertyValue",
  "name": "AI Adoption Trend",
  "value": "{{ summary.ai_assisted_pct }}%",
  "description": "{% if summary.ai_trend_direction == 'up' %}Increasing{% elif summary.ai_trend_direction == 'down' %}Decreasing{% else %}Stable{% endif %} over the last 3 months"
}
```

### 12.2 Team Member / Contributor Data

If displaying top contributors, use `Person` schema within the Dataset:

```json
"contributor": [{% for c in top_contributors %}
  {
    "@type": "Person",
    "name": "{{ c.username }}",
    "url": "https://github.com/{{ c.username }}"
  }{% if not forloop.last %},{% endif %}{% endfor %}
]
```

### 12.3 Quality Metrics

For new quality metrics (review coverage, merge confidence, etc.), extend `variableMeasured`:

```json
{"@type": "PropertyValue", "name": "Review Coverage", "value": "{{ summary.review_coverage_pct }}%"},
{"@type": "PropertyValue", "name": "Median Review Time", "value": "{{ summary.median_review_time_hours }}h"},
{"@type": "PropertyValue", "name": "Bot PR Percentage", "value": "{{ summary.bot_pct }}%"}
```

### 12.4 FAQ Expansion

Add FAQ entries for the new metrics sections:

```json
{
  "@type": "Question",
  "name": "How many active contributors does {{ profile.display_name }} have?",
  "acceptedAnswer": {
    "@type": "Answer",
    "text": "{{ profile.display_name }} has {{ summary.active_contributors_90d }} active contributors in the last 90 days."
  }
},
{
  "@type": "Question",
  "name": "What AI coding tools does {{ profile.display_name }} use?",
  "acceptedAnswer": {
    "@type": "Answer",
    "text": "Based on PR analysis, {{ profile.display_name }}'s most common AI tools include {% for tool in ai_tools|slice:':3' %}{{ tool.tool }}{% if not forloop.last %}, {% endif %}{% endfor %}."
  }
}
```

---

## Priority Summary

### High Priority
| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 1 | Directory table rows use JS-only navigation (no `<a>` tags) | `_directory_list.html:19-20` | Crawlers cannot discover org pages from directory |

### Medium Priority
| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 2 | No RSS feed autodiscovery `<link>` tag | `public/base.html` | Feed readers won't find RSS |
| 3 | No page-specific OG images | `views.py` (all views) | Poor social sharing appearance |
| 4 | Chart.js loaded as blocking script | `org_detail.html:190` | Page render delay |
| 5 | Missing `Vary: HX-Request` header | `views.py:directory` | CDN may cache wrong response variant |
| 6 | No related org links on detail page | `org_detail.html:177-186` | Missed internal linking opportunity |
| 7 | Industry page missing `hasPart` dataset refs | `industry.html` JSON-LD | Weaker schema hierarchy |
| 8 | Canvas charts have no screen reader fallback | `org_detail.html` | Accessibility gap, reduced indexable content |
| 9 | Missing `dateModified` on DataCatalog | `directory.html` JSON-LD | Stale data signal to crawlers |
| 10 | Directory table keyboard inaccessible | `_directory_list.html` | Accessibility issue |

### Low Priority
| # | Issue | Location | Impact |
|---|-------|----------|--------|
| 11 | Hardcoded `temporalCoverage` "2025/.." | `org_detail.html` JSON-LD | Minor inaccuracy |
| 12 | Missing `license` on Dataset schema | `org_detail.html` JSON-LD | Data discoverability |
| 13 | No `s-maxage` for CDN caching | `views.py` | Suboptimal CDN cache control |
| 14 | AI crawlers only allowed `/open-source/` | `robots.txt` | May want to expand later |
| 15 | No hidden heading for directory table | `directory.html` | Minor heading hierarchy gap |
| 16 | Thin content risk on small industries | `industry.html` | Low content value for 1-2 org industries |
