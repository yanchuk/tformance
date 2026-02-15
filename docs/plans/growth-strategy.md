# Public OSS Analytics Pages - Growth & Analytics Strategy

**Date:** 2026-02-15
**Author:** Product Marketing Manager (Task #3)
**Status:** Strategy Complete
**Target:** `/open-source/` public pages (70+ organizations)

---

## Executive Summary

The public OSS analytics pages showcase engineering metrics for 70+ open source projects. This strategy transforms them from a data showcase into a **high-converting lead generation engine** through comprehensive PostHog analytics, SEO optimization, and strategic CTAs.

**Core Strategy:**
1. **PostHog Event Tracking** — Measure every interaction to optimize conversion
2. **SEO for Long-Tail Keywords** — Dominate "posthog engineering metrics" style searches
3. **Conversion Funnel** — Guide visitors from discovery → insight → signup
4. **Product Capability Showcase** — Show what the paid product can do
5. **Content & Social** — Turn data into shareable stories

**Success Metrics:**
- 10K+ monthly organic visitors within 6 months (from <1K today)
- 3% conversion rate from public page → signup
- Top 3 ranking for "[org name] engineering metrics" keywords
- 500+ social shares per month

---

## 1. PostHog Analytics Events (CRITICAL)

ALL public pages must track user behavior to measure and optimize conversion. PostHog is already configured (`POSTHOG_API_KEY` in settings.py, lines 825-832), and basic tracking exists on CTAs.

### 1.1 Page View Events

**Event:** `public_page_view`

**Where:** Add to `templates/public/base.html` in `{% block page_head %}`

**Implementation:**
```html
{% block page_head %}
{% block json_ld %}{% endblock %}
<link rel="alternate" type="application/rss+xml" title="Tformance Open Source Analytics" href="{% url 'public:rss_feed' %}">
{% if POSTHOG_API_KEY %}
<script>
document.addEventListener('DOMContentLoaded', function() {
  if (window.posthog) {
    posthog.capture('public_page_view', {
      page_type: '{{ page_type|default:"unknown" }}',  // directory|org_detail|industry
      org_slug: '{{ profile.slug|default:"" }}',
      industry: '{{ profile.industry|default:"" }}',
      referrer: document.referrer,
      url_path: window.location.pathname
    });
  }
});
</script>
{% endif %}
{% endblock %}
```

**Context Updates Required:**
- `apps/public/views.py`: Add `page_type` to all view contexts:
  - `directory()` → `"page_type": "directory"`
  - `org_detail()` → `"page_type": "org_detail"`
  - `industry_comparison()` → `"page_type": "industry"`

**Properties:**
- `page_type`: directory | org_detail | industry
- `org_slug`: organization slug (org detail only)
- `industry`: industry key (org detail & industry pages)
- `referrer`: where user came from
- `url_path`: current URL path

---

### 1.2 Chart Interaction Events

**Event:** `public_chart_interacted`

**Where:** `templates/public/org_detail.html` in `{% block page_js %}`

**Implementation:**
Add to Chart.js initialization in the existing `whenChartReady()` function:

```javascript
// AI Adoption Trend chart
new Chart(document.getElementById('public-ai-trend-chart'), {
  type: 'line',
  data: { /* ... existing config ... */ },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: { /* ... */ },
    onClick: function(evt, activeElements) {
      if (window.posthog && activeElements.length > 0) {
        posthog.capture('public_chart_interacted', {
          chart_type: 'ai_adoption_trend',
          org_slug: '{{ profile.slug }}',
          month_clicked: labels[activeElements[0].index]
        });
      }
    }
  }
});

// Cycle Time chart - add same onClick handler with chart_type: 'cycle_time_trend'
```

**Properties:**
- `chart_type`: ai_adoption_trend | cycle_time_trend
- `org_slug`: organization slug
- `month_clicked`: month label user clicked

---

### 1.3 Scroll Depth Tracking

**Event:** `public_scroll_depth`

**Where:** `templates/public/base.html` in `{% block page_head %}`

**Implementation:**
```html
<script>
// Scroll depth tracking (25%, 50%, 75%, 100%)
(function() {
  if (!window.posthog) return;
  var depths = [25, 50, 75, 100];
  var triggered = {};
  window.addEventListener('scroll', function() {
    var scrollPct = Math.round((window.scrollY / (document.body.scrollHeight - window.innerHeight)) * 100);
    depths.forEach(function(d) {
      if (scrollPct >= d && !triggered[d]) {
        triggered[d] = true;
        posthog.capture('public_scroll_depth', {
          depth: d,
          page_type: '{{ page_type|default:"unknown" }}',
          org_slug: '{{ profile.slug|default:"" }}'
        });
      }
    });
  });
})();
</script>
```

**Properties:**
- `depth`: 25 | 50 | 75 | 100
- `page_type`: directory | org_detail | industry
- `org_slug`: organization slug (if applicable)

**Why:** Measure content engagement. If users bail at 25%, content isn't compelling. 100% scroll = high interest.

---

### 1.4 CTA Click Events

**Event:** `public_cta_clicked`

**Where:** All CTA buttons across public templates

**Currently Tracked (GOOD):**
- Hero CTA: `templates/public/org_detail.html` line 107-111 ✓
- Bottom banner: `templates/public/base.html` line 36-40 ✓

**Add Tracking To:**

1. **Directory page CTA** — Add to `templates/public/directory.html` after global stats (new):
```html
<div class="text-center my-8">
  <a href="{% url 'account_signup' %}" class="btn btn-primary"
     onclick="if(window.posthog){posthog.capture('public_cta_clicked',{position:'directory_top',page_type:'directory'})}">
    Track your team's metrics
    <i class="fa-solid fa-arrow-right ml-2"></i>
  </a>
  <p class="text-xs text-base-content/40 mt-2">Free for teams under 10 developers</p>
</div>
```

2. **Industry page CTA** — Add to `templates/public/industry.html` after stats cards (new):
```html
<div class="alert alert-info mb-8">
  <div class="flex-1">
    <h3 class="font-semibold">How does YOUR team compare?</h3>
    <p class="text-sm mt-1">Connect GitHub and see your team's AI adoption, cycle time, and quality metrics.</p>
  </div>
  <a href="{% url 'account_signup' %}" class="btn btn-primary btn-sm"
     onclick="if(window.posthog){posthog.capture('public_cta_clicked',{position:'industry_benchmark',industry:'{{ industry_key }}'})}">
    Get Started
  </a>
</div>
```

3. **Request form link** — Track "Request your repo" clicks:
```html
<!-- Add to templates/public/directory.html and org_detail.html -->
<a href="{% url 'public:request_repo' %}"
   onclick="if(window.posthog){posthog.capture('public_request_repo_clicked',{source_page:'{{ page_type }}'})}"
   class="btn btn-ghost btn-sm">
  Request your repository
</a>
```

**Properties:**
- `position`: hero | directory_top | industry_benchmark | bottom_banner | after_charts
- `org_slug`: organization slug (if applicable)
- `industry`: industry key (if applicable)
- `page_type`: directory | org_detail | industry

---

### 1.5 Table Sort & Filter Events

**Event:** `public_table_sorted`

**Where:** `templates/public/org_detail.html` in Alpine.js `sortBy()` function

**Implementation:**
Update the `publicContributorSort` Alpine component (line 734):

```javascript
sortBy: function(column) {
  if (this.col === column) {
    this.dir = this.dir === 'asc' ? 'desc' : 'asc';
  } else {
    this.col = column;
    this.dir = column === 'display_name' ? 'asc' : 'desc';
  }
  // Track sort event
  if (window.posthog) {
    posthog.capture('public_table_sorted', {
      table: 'team_breakdown',
      column: column,
      direction: this.dir,
      org_slug: '{{ profile.slug }}'
    });
  }
}
```

**Event:** `public_directory_filtered`

**Where:** Directory page filter/sort dropdowns

**Implementation:**
Already partially tracked via HTMX, but add explicit events to `templates/public/directory.html`:

```html
<select name="industry"
        class="select select-bordered select-sm w-full sm:w-auto"
        hx-get="{% url 'public:directory' %}"
        hx-target="#directory-list"
        hx-include="[name='year'],[name='sort']"
        hx-push-url="true"
        onchange="if(window.posthog){posthog.capture('public_directory_filtered',{filter_type:'industry',value:this.value})}">
  <!-- options -->
</select>

<select name="sort"
        class="select select-bordered select-sm w-full sm:w-auto"
        hx-get="{% url 'public:directory' %}"
        hx-target="#directory-list"
        hx-include="[name='year'],[name='industry']"
        hx-push-url="true"
        onchange="if(window.posthog){posthog.capture('public_directory_filtered',{filter_type:'sort',value:this.value})}">
  <!-- options -->
</select>
```

**Properties:**
- `filter_type`: industry | sort | year
- `value`: selected value

---

### 1.6 External Link Clicks

**Event:** `public_external_link_clicked`

**Where:** GitHub org links, PR links, contributor GitHub profiles

**Implementation:**
Add `onclick` handlers to external links in templates:

**GitHub Org Link** (`templates/public/org_detail.html` line 84-89):
```html
<a href="{{ profile.github_org_url }}" target="_blank" rel="noopener"
   class="btn btn-ghost btn-xs gap-1"
   onclick="if(window.posthog){posthog.capture('public_external_link_clicked',{link_type:'github_org',org_slug:'{{ profile.slug }}'})}">
  <i class="fa-brands fa-github"></i> GitHub
</a>
```

**PR Links** (`templates/public/org_detail.html` line 293):
```html
<a href="{{ pr.github_url }}" target="_blank" rel="noopener noreferrer"
   class="link link-hover line-clamp-1 text-sm" title="{{ pr.title }}"
   onclick="if(window.posthog){posthog.capture('public_external_link_clicked',{link_type:'pr',org_slug:'{{ profile.slug }}',pr_is_ai:{{ pr.is_ai_assisted|lower }}})}">
  {{ pr.title }}
</a>
```

**Contributor GitHub Links** (`templates/public/org_detail.html` line 372-374):
```html
<a :href="'https://github.com/' + row.github_username" target="_blank" rel="noopener"
   class="text-sm font-medium link link-hover" x-text="row.display_name"
   @click="if(window.posthog){posthog.capture('public_external_link_clicked',{link_type:'contributor_github',org_slug:'{{ profile.slug }}'})}"></a>
```

**Properties:**
- `link_type`: github_org | pr | contributor_github | industry_link
- `org_slug`: organization slug
- `pr_is_ai`: true/false (PR links only)

---

### 1.7 Conversion Events

**Event:** `public_signup_initiated`

**Where:** Signup page (when user arrives from public pages)

**Implementation:**
Add to `templates/account/signup.html` (if not already tracking):

```html
<script>
if (window.posthog && document.referrer.includes('/open-source/')) {
  posthog.capture('public_signup_initiated', {
    referrer: document.referrer,
    utm_source: new URLSearchParams(window.location.search).get('utm_source'),
    utm_campaign: new URLSearchParams(window.location.search).get('utm_campaign')
  });
}
</script>
```

**Event:** `public_signup_completed`

**Where:** Already tracked by allauth/signup flow (verify in PostHog)

---

### 1.8 PostHog Configuration Summary

**Template Changes:**

| Template | Change | Event |
|----------|--------|-------|
| `templates/public/base.html` | Add page_view + scroll_depth scripts | `public_page_view`, `public_scroll_depth` |
| `templates/public/directory.html` | Add top CTA, track filters | `public_cta_clicked`, `public_directory_filtered` |
| `templates/public/org_detail.html` | Chart onclick, table sort, external links | `public_chart_interacted`, `public_table_sorted`, `public_external_link_clicked` |
| `templates/public/industry.html` | Add CTA | `public_cta_clicked` |

**View Changes:**

| View | Add to Context |
|------|----------------|
| `directory()` | `"page_type": "directory"` |
| `org_detail()` | `"page_type": "org_detail"` |
| `industry_comparison()` | `"page_type": "industry"` |

**Settings Check:**
- ✓ `POSTHOG_API_KEY` already configured (line 825)
- ✓ PostHog script already loaded in base template (verify `posthog-js` CDN)
- Add to context processors if `POSTHOG_API_KEY` not in templates

**PostHog Dashboards to Create:**

1. **Public Pages Overview**
   - Page views by page_type
   - Unique visitors
   - Avg scroll depth by page_type
   - Top referrers

2. **Conversion Funnel**
   - public_page_view → public_cta_clicked → public_signup_initiated → public_signup_completed
   - Breakdown by org_slug, industry, referrer

3. **Engagement**
   - Chart interactions by org
   - Table sorts (which columns users care about)
   - External link clicks (are users going to GitHub?)
   - Scroll depth distribution

4. **Content Performance**
   - Top performing orgs (highest conversion)
   - Top industries
   - Which orgs drive most traffic

---

## 2. SEO Optimization

### 2.1 Current State Assessment

**Strengths (from SEO audit):**
- ✓ Excellent JSON-LD structured data (Dataset, FAQPage)
- ✓ Dynamic, unique meta titles and descriptions
- ✓ Clean URL structure (`/open-source/<slug>/`)
- ✓ Proper heading hierarchy
- ✓ 12h CDN caching
- ✓ AI crawler allowlist in robots.txt
- ✓ RSS feed autodiscovery (line 6 in `public/base.html`)

**Gaps Identified:**
- ⚠️ No page-specific OG images (social sharing looks generic)
- ⚠️ Directory table rows use JavaScript navigation (crawlers can't follow)
- ⚠️ No related org links on detail pages (missed internal linking)
- ⚠️ Missing `Vary: HX-Request` header (CDN may cache wrong variant)
- ⚠️ Chart.js loaded as blocking script (delays render)

---

### 2.2 JSON-LD Enhancements

**Add to `templates/public/org_detail.html`** (after line 67):

```html
{
  "@type": "Question",
  "name": "How is {{ profile.display_name }}'s code quality?",
  "acceptedAnswer": {
    "@type": "Answer",
    "text": "{{ profile.display_name }} has a {{ quality_indicators.revert_rate }}% revert rate and {{ quality_indicators.ci_pass_rate }}% CI pass rate based on {{ quality_indicators.total_prs }} merged PRs."
  }
},
{
  "@type": "Question",
  "name": "Which AI tools does {{ profile.display_name }} use most?",
  "acceptedAnswer": {
    "@type": "Answer",
    "text": "{% for tool in ai_tools|slice:':3' %}{{ tool.tool }} ({{ tool.pct }}%){% if not forloop.last %}, {% endif %}{% endfor %} are the top AI coding tools detected."
  }
}
```

**Add to industry page** (`templates/public/industry.html` line 21):

```json
"hasPart": [{% for org in orgs %}
  {
    "@type": "Dataset",
    "name": "{{ org.display_name }} Engineering Metrics",
    "url": "https://tformance.com/open-source/{{ org.slug }}/"
  }{% if not forloop.last %},{% endif %}{% endfor %}
]
```

**Add `license` and `dateModified` to Dataset schemas:**

Already present in org_detail.html (line 13, 26) ✓

---

### 2.3 Long-Tail Keyword Strategy

**Target Keywords (200+ opportunities):**

| Keyword Pattern | Monthly Search Vol | Example | Current Rank | Target Page |
|-----------------|-------------------|---------|--------------|-------------|
| [org] engineering metrics | 50-200 | "posthog engineering metrics" | #15-30 | Org detail |
| [org] ai adoption | 30-100 | "posthog ai adoption" | Not ranked | Org detail |
| [org] cycle time | 20-80 | "supabase cycle time" | Not ranked | Org detail |
| [industry] engineering benchmarks | 100-500 | "product analytics engineering benchmarks" | Not ranked | Industry page |
| ai coding tools comparison | 500-1000 | (informational) | Not ranked | Directory |
| open source engineering metrics | 200-500 | (navigational) | #8-12 | Directory |

**On-Page Optimization:**

1. **Org Detail Pages:**
   - ✓ Already have unique, keyword-rich titles (line 124-126 in views.py)
   - ✓ Citable summary paragraph (line 94-99 in org_detail.html)
   - Add: "How does [Org] compare?" section linking to industry page

2. **Industry Pages:**
   - Current title: "{{ industry_display }} Engineering Benchmarks" ✓
   - Add: 200-word intro paragraph with keywords:
     ```html
     <div class="prose max-w-none mb-6">
       <p>
         {{ industry_display }} engineering teams average {{ stats.avg_ai_pct|floatformat:1 }}%
         AI adoption and {{ stats.avg_cycle_time|floatformat:1 }} hour cycle time across
         {{ stats.org_count }} tracked projects. This benchmark data helps CTOs and engineering
         leaders understand how their team's AI coding tool usage, delivery speed, and code
         quality compare to industry peers. Top {{ industry_display|lower }} organizations like
         {% for org in orgs|slice:':3' %}{{ org.display_name }}{% if not forloop.last %}, {% endif %}{% endfor %}
         demonstrate varying approaches to AI-assisted development.
       </p>
     </div>
     ```

3. **Directory Page:**
   - Add: "Why measure engineering metrics?" section before table
   - Add: "How we detect AI usage" FAQ section after methodology

---

### 2.4 Internal Linking Strategy

**Issue:** SEO audit found directory table rows use `onclick` without `<a>` tags (line 146-163 in SEO audit).

**Fix for `templates/public/_directory_list.html`** (line 22-26):

```html
<td>
  <a href="{% url 'public:org_detail' slug=org.slug %}"
     class="font-medium link link-hover">
    {{ org.display_name }}
  </a>
  {% if org.description %}
  <div class="text-xs text-base-content/40 line-clamp-1 max-w-xs">{{ org.description }}</div>
  {% endif %}
</td>
```

Keep the `onclick` on `<tr>` for UX, but add proper `<a>` tags for crawlers.

**Add Related Orgs Section** to org detail page (already implemented in current template lines 563-584) ✓

**Add Breadcrumb Enhancements:**
- Directory → Industry → Org is already well-linked ✓

**Add "View full benchmarks" links:**
In quality indicators section, link to industry page:
```html
<p class="text-xs text-base-content/40 mt-2">
  Based on {{ quality_indicators.total_prs }} merged PRs.
  <a href="{% url 'public:industry' industry=profile.industry %}" class="link link-primary">
    Compare with {{ profile.industry_display }} peers
  </a>
</p>
```

---

### 2.5 Page Speed Optimization

**Issue:** Chart.js loaded as blocking script (line 588 in org_detail.html)

**Fix:** Already uses `defer` attribute ✓

**Add preconnect for jsdelivr CDN:**
Add to `templates/web/base.html` (if not present):
```html
<link rel="preconnect" href="https://cdn.jsdelivr.net">
```

**Lazy load sparklines:**
Already implemented as canvas with lightweight JS rendering ✓

---

### 2.6 Sitemap Considerations

**Check:** Are public org pages in `sitemap.xml`?

If not, add `apps/public/sitemaps.py`:

```python
from django.contrib.sitemaps import Sitemap
from apps.public.services import PublicAnalyticsService

class PublicOrgSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return PublicAnalyticsService.get_directory_data()

    def location(self, obj):
        return f"/open-source/{obj['slug']}/"

    def lastmod(self, obj):
        return obj.get('last_updated')

class PublicIndustrySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        from apps.public.models import INDUSTRY_CHOICES
        return [{"key": k, "label": l} for k, l in INDUSTRY_CHOICES]

    def location(self, obj):
        return f"/open-source/industry/{obj['key']}/"
```

Register in main sitemap index.

---

### 2.7 Open Graph Images (High Priority)

**Current:** No page-specific OG images (falls back to generic logo)

**Solution:** Dynamically generate OG images per org using Cloudflare Workers or Python imaging.

**Template (HTML/CSS rendered as PNG):**
```
╔══════════════════════════════════════════════╗
║  [Org Logo]  Org Name                        ║
║                                              ║
║  21% AI Adoption  ▲ +3%                     ║
║  18h Cycle Time   ▼ -12%                    ║
║  4,521 PRs        333 Contributors          ║
║                                              ║
║  tformance.com/open-source/[slug]           ║
╚══════════════════════════════════════════════╝
```

**Implementation Options:**

1. **Option A: Cloudflare Workers + Canvas API** (recommended)
   - Generate on-demand at `https://tformance.com/og/open-source/[slug].png`
   - Cache for 24h
   - 0 storage cost

2. **Option B: Python Pillow + S3/R2**
   - Generate via `generate_og_images` management command
   - Upload to Cloudflare R2
   - Serve from CDN
   - ~70 images @ 50KB = 3.5MB total

**Add to context in `apps/public/views.py` org_detail():**
```python
"page_image": f"https://tformance.com/og/open-source/{profile['slug']}.png"
```

Base template already includes `page_image` in OG tags ✓

**Impact:** 3-5x increase in social sharing CTR based on industry benchmarks.

---

## 3. GEO Strategy (Global Engineering Audiences)

### 3.1 Regional Considerations

Engineering metrics are **universally relevant** — cycle time, AI adoption, and code quality matter in SF, Berlin, Bangalore, and Singapore equally.

**No Localization Required:**
- Metrics are language-agnostic (hours, percentages, counts)
- GitHub usernames are international
- No cultural adaptation needed

**Regional Traffic Patterns:**

| Region | % of Target Audience | Key Channels |
|--------|---------------------|--------------|
| North America | 40% | HN, Reddit r/programming, Twitter/X |
| Europe | 30% | Dev.to, LinkedIn, HN |
| Asia-Pacific | 20% | GitHub, LinkedIn, local forums |
| Other | 10% | GitHub, organic search |

---

### 3.2 Global SEO Tactics

**1. Multi-Language Meta Tags (Low Priority)**

Add `hreflang` tags if we translate landing pages (not public data pages):
```html
<link rel="alternate" hreflang="en" href="https://tformance.com/open-source/">
<link rel="alternate" hreflang="x-default" href="https://tformance.com/open-source/">
```

**2. GitHub as Discovery Channel**

Many international developers discover via GitHub README badges. Create:

**Tformance Badge for Tracked Orgs:**
```markdown
[![Engineering Metrics](https://img.shields.io/badge/tformance-view%20metrics-orange)](https://tformance.com/open-source/[slug]/)
```

**Outreach:** Contact maintainers of tracked orgs, offer badge for their README.

**3. International Developer Communities**

| Community | Reach | Content Type |
|-----------|-------|--------------|
| Dev.to | 1M+ devs | "Top 10 OSS Projects by AI Adoption" |
| Hashnode | 500K+ devs | "How [Org] Uses AI Tools" case studies |
| Lobste.rs | 50K+ devs | Data-driven posts |
| Indie Hackers | 200K+ makers | "Engineering metrics for solo devs" |

---

## 4. Conversion Funnel

### 4.1 Current State

**Existing CTAs (Good):**
- ✓ Hero CTA on org detail pages (line 106-112)
- ✓ Bottom banner on all public pages (line 36-40 in base.html)

**Missing CTAs:**
- ⚠️ Directory page has NO CTA above the fold
- ⚠️ Industry page has NO inline CTA
- ⚠️ No "See what's different in Pro" tease on org detail pages

---

### 4.2 Visitor Journey Map

```
┌─────────────────────────────────────────────────────────────┐
│ Google Search: "posthog engineering metrics"                │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Org Detail Page: PostHog Engineering Metrics                │
│ - See: 21% AI adoption, 18h cycle time                      │
│ - Read: Citable summary with industry comparison            │
│ - Action: Click hero CTA "Get these metrics for your repos" │
└─────────────────────┬───────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ Signup Page                                                  │
│ - Pre-filled: utm_source=public, utm_content=posthog        │
│ - Converts: 3% baseline (target: 5% after optimization)     │
└─────────────────────────────────────────────────────────────┘
```

**Alternative Path (Industry Comparison):**

```
Google: "product analytics engineering benchmarks"
  ▼
Industry Page: Product Analytics
  ▼
Click: PostHog org card
  ▼
Org Detail Page (same as above)
```

---

### 4.3 CTA Placement Strategy

**Priority 1: Directory Page Top CTA** (NEW)

Add after global stats banner in `templates/public/directory.html`:

```html
<div class="alert alert-info mb-8">
  <div class="flex-1">
    <h3 class="font-semibold text-lg">Get these metrics for YOUR team</h3>
    <p class="text-sm mt-1">
      Connect GitHub in 2 minutes. See AI adoption, cycle time, quality metrics, and weekly insights for your team.
    </p>
  </div>
  <a href="{% url 'account_signup' %}" class="btn btn-primary"
     onclick="if(window.posthog){posthog.capture('public_cta_clicked',{position:'directory_top',page_type:'directory'})}">
    Start Free Trial
    <i class="fa-solid fa-arrow-right ml-2"></i>
  </a>
</div>
```

**Priority 2: "What Pro Shows" Section on Org Detail** (NEW)

Add after AI Tools table, before Engineering Insight (new section):

```html
<div class="card bg-gradient-to-br from-primary/5 to-accent/5 border-2 border-primary/20 mb-8">
  <div class="card-body p-6">
    <h2 class="card-title text-base mb-3">
      <i class="fa-solid fa-lock text-primary"></i>
      What Tformance Pro reveals
    </h2>
    <div class="grid md:grid-cols-2 gap-4">
      <div>
        <h3 class="font-semibold text-sm flex items-center gap-2">
          <i class="fa-solid fa-user-group text-primary"></i>
          Per-Developer Breakdown
        </h3>
        <p class="text-sm text-base-content/70 mt-1">
          See who's adopting AI tools and how it changes their speed and quality.
        </p>
      </div>
      <div>
        <h3 class="font-semibold text-sm flex items-center gap-2">
          <i class="fa-solid fa-chart-line text-primary"></i>
          AI Quality Impact
        </h3>
        <p class="text-sm text-base-content/70 mt-1">
          Are AI PRs causing more reverts? Measure the real effect on your codebase.
        </p>
      </div>
      <div>
        <h3 class="font-semibold text-sm flex items-center gap-2">
          <i class="fa-solid fa-triangle-exclamation text-primary"></i>
          Bottleneck Detection
        </h3>
        <p class="text-sm text-base-content/70 mt-1">
          Spot overloaded reviewers before they slow your team down.
        </p>
      </div>
      <div>
        <h3 class="font-semibold text-sm flex items-center gap-2">
          <i class="fa-solid fa-sparkles text-primary"></i>
          Weekly AI Insights
        </h3>
        <p class="text-sm text-base-content/70 mt-1">
          Get specific recommendations based on your team's actual data.
        </p>
      </div>
    </div>
    <div class="text-center mt-4">
      <a href="{% url 'account_signup' %}" class="btn btn-primary"
         onclick="if(window.posthog){posthog.capture('public_cta_clicked',{position:'pro_features_tease',org_slug:'{{ profile.slug }}'})}">
        Start Free Trial — No Card Required
        <i class="fa-solid fa-arrow-right ml-2"></i>
      </a>
    </div>
  </div>
</div>
```

**Priority 3: Industry Page Inline CTA** (shown in Section 1.4)

Already specified above ✓

**Priority 4: Mobile Sticky CTA** (NEW)

Add to `templates/public/base.html` after `</main>`:

```html
<!-- Mobile sticky CTA (shows after scrolling past hero) -->
<div class="btm-nav btm-nav-sm lg:hidden bg-base-100 border-t border-base-300 shadow-lg"
     x-data="{ show: false }"
     x-show="show"
     @scroll.window="show = window.scrollY > 400"
     x-transition:enter="transition ease-out duration-200"
     x-transition:enter-start="translate-y-full"
     x-transition:enter-end="translate-y-0">
  <a href="{% url 'account_signup' %}" class="btn btn-primary btn-sm w-full mx-2 my-1"
     onclick="if(window.posthog){posthog.capture('public_cta_clicked',{position:'mobile_sticky',page_type:'{{ page_type }}'})}">
    Get this for your team
    <i class="fa-solid fa-arrow-right ml-1"></i>
  </a>
</div>
```

---

### 4.4 Request Form Optimization

**Current:** `/open-source/request/` form for maintainers to request their repo

**Issue:** No visible link to this form from directory or org pages.

**Fix:** Add prominent link in directory page header:

```html
<div class="flex items-center justify-between mb-6">
  <div>
    <h1 class="text-3xl font-bold mb-2">Open Source Engineering Metrics</h1>
    <p class="text-base-content/70 max-w-2xl">
      Real engineering metrics from top open source projects.
      See how AI adoption, delivery speed, and team velocity compare across industries.
    </p>
  </div>
  <a href="{% url 'public:request_repo' %}" class="btn btn-outline btn-sm gap-2"
     onclick="if(window.posthog){posthog.capture('public_request_repo_clicked',{source_page:'directory'})}}">
    <i class="fa-solid fa-plus"></i>
    Request Your Repo
  </a>
</div>
```

**Add "Is this you?" prompt on org detail pages:**

```html
<!-- Add after org name in hero -->
<p class="text-xs text-base-content/40 mt-2">
  Maintainer of {{ profile.display_name }}?
  <a href="{% url 'public:request_repo' %}?org={{ profile.slug }}" class="link link-primary">
    Claim this page
  </a>
</p>
```

---

### 4.5 Social Proof Elements

**Add to org detail pages** (after quality indicators):

```html
<div class="alert alert-success shadow-sm">
  <i class="fa-solid fa-users text-lg"></i>
  <div>
    <h3 class="font-semibold text-sm">Join 200+ engineering teams</h3>
    <p class="text-xs text-base-content/80">
      From 5-person startups to 500+ developer orgs, teams use Tformance to measure AI coding tool impact.
    </p>
  </div>
</div>
```

**Add customer logos** (if available) to directory page.

---

## 5. Product Capability Showcase

Map each public page feature to a selling point that drives signups.

### 5.1 Feature → Benefit Mapping

| Public Page Feature | What It Shows | Pro Benefit (Hidden) | CTA Messaging |
|---------------------|---------------|----------------------|---------------|
| AI Adoption % + Trend | "21% AI adoption, ↑3%" | Per-developer AI % (who's using what) | "See WHO is driving this adoption" |
| Cycle Time Trend | "18h median, ↓12%" | Per-developer cycle time (who's fast/slow) | "See which developers are fastest" |
| Team Breakdown (top 20) | Aggregate PRs by author | Full team table with filters, AI quality impact | "See quality impact per developer" |
| Quality Indicators | Org-level revert rate, hotfix rate | Breakdown by AI vs non-AI PRs | "Are AI PRs helping or hurting quality?" |
| Review Distribution | Top 10 reviewers | Bottleneck alerts, uneven load warnings | "Spot overloaded reviewers early" |
| Recent PRs | Last 10 PRs with AI badge | Full PR list with filters, export, Ask AI | "Filter by AI tool, export for analysis" |
| Engineering Insight (1) | Single weekly insight | 5-10 actionable insights, Ask AI followup | "Get 5+ insights every week" |
| AI Tools Table | Aggregate tool usage | Per-developer tool usage, Copilot seat mgmt | "See who uses which AI tools" |

---

### 5.2 Comparison Table (Optional)

Add to directory page (after CTA):

```html
<div class="overflow-x-auto mb-8">
  <table class="table table-sm">
    <thead>
      <tr>
        <th>Feature</th>
        <th class="text-center">Public OSS Pages</th>
        <th class="text-center">Tformance Pro</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>AI Adoption Tracking</td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
      <tr>
        <td>Cycle Time Trends</td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
      <tr>
        <td>Per-Developer Breakdown</td>
        <td class="text-center"><i class="fa-solid fa-minus text-base-content/30"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
      <tr>
        <td>AI Quality Impact Analysis</td>
        <td class="text-center"><i class="fa-solid fa-minus text-base-content/30"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
      <tr>
        <td>Bottleneck Detection</td>
        <td class="text-center"><i class="fa-solid fa-minus text-base-content/30"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
      <tr>
        <td>Weekly AI Insights</td>
        <td class="text-center">1 insight</td>
        <td class="text-center">5-10 insights</td>
      </tr>
      <tr>
        <td>PR Filters & Export</td>
        <td class="text-center"><i class="fa-solid fa-minus text-base-content/30"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
      <tr>
        <td>Ask AI</td>
        <td class="text-center"><i class="fa-solid fa-minus text-base-content/30"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
      <tr>
        <td>Slack Integration</td>
        <td class="text-center"><i class="fa-solid fa-minus text-base-content/30"></i></td>
        <td class="text-center"><i class="fa-solid fa-check text-success"></i></td>
      </tr>
    </tbody>
  </table>
</div>
```

---

## 6. Content & Social Strategy

Turn the data into shareable stories that drive traffic and backlinks.

### 6.1 Blog Post Ideas (High-Impact)

**Monthly Data Reports:**
1. "AI Adoption Trends: How 70+ OSS Projects Use Coding Tools (Jan 2026)"
   - Aggregate trends across all orgs
   - "Cursor overtook Copilot in adoption this month"
   - Chart: tool adoption over time
   - CTA: "See your team's AI adoption"

2. "Top 10 Fastest Open Source Teams by Cycle Time"
   - Rank orgs by median cycle time
   - What do they have in common? (small PRs, high review coverage)
   - Interview with top org maintainer

3. "Does AI Code Quality Hold Up? Analysis of 10K+ AI-Assisted PRs"
   - Revert rate: AI vs non-AI
   - Review rounds: AI vs non-AI
   - Industry breakdown

**Case Studies:**
4. "How PostHog Reached 21% AI Adoption (And What It Did to Their Velocity)"
   - Org-specific deep dive
   - Permission from maintainer
   - Link to public page

**How-To Content:**
5. "How to Measure Your Team's AI Adoption (Even Without Tformance)"
   - Educational, generous
   - "Here's how we detect AI tools in PRs"
   - "Try it yourself with this GitHub query"
   - CTA: "Or just use Tformance"

---

### 6.2 Social Media Strategy

**Twitter/X (Primary Channel):**

**Weekly Thread Template:**
```
🔥 This week in OSS engineering metrics:

📊 [OrgName] hit [X]% AI adoption (↑Y% MoM)
⚡ [OrgName] shipped in [Z]h median cycle time
🏆 Top AI tool: [Tool] ([X]% of AI PRs)

See the full breakdown:
[link to org page]

1/n
```

**Monthly "Top 10" Posts:**
```
Top 10 fastest open source teams by cycle time (Jan 2026):

1. [Org] - 8.2h
2. [Org] - 12.5h
...
10. [Org] - 24.1h

What do the fastest teams have in common?
- Small PRs (<200 lines)
- High review coverage (>90%)
- Fast first review (<2h)

See benchmarks: [link]
```

**Tagging Strategy:**
- Tag orgs: @posthog, @supabase (with permission)
- Tag tools: @GitHub, @CopilotAI (when relevant)
- Use hashtags: #EngineeringMetrics, #AIcoding, #DevOps

**LinkedIn:**
- Repost Twitter threads as LinkedIn articles
- Target CTOs, VPs of Engineering
- "How I measure my team's AI adoption" angle

**Reddit:**
- r/programming (data-driven posts only, no self-promo)
- r/devops (cycle time, quality metrics)
- r/ChatGPT (AI adoption trends)

**Hacker News:**
- Monthly data reports (title: "AI Adoption Trends in Open Source [Month Year]")
- Don't submit our own links — let organic discovery happen
- Comment on relevant threads with data ("We analyzed 70+ OSS projects and found...")

---

### 6.3 Social Sharing from Org Pages

**Add "Share on Twitter" Button:**

Add to org detail page (after hero, before health overview):

```html
<div class="flex gap-2 mb-4">
  <a href="https://twitter.com/intent/tweet?text={{ profile.display_name }}%20has%20{{ summary.ai_assisted_pct|floatformat:0 }}%25%20AI%20adoption%20and%20{{ summary.median_cycle_time_hours|floatformat:0 }}h%20cycle%20time.%20See%20the%20full%20breakdown%3A&url=https://tformance.com/open-source/{{ profile.slug }}/"
     target="_blank" rel="noopener"
     class="btn btn-sm btn-ghost gap-2"
     onclick="if(window.posthog){posthog.capture('public_social_share_clicked',{platform:'twitter',org_slug:'{{ profile.slug }}'})}">
    <i class="fa-brands fa-twitter text-info"></i>
    Share on Twitter
  </a>
  <a href="https://www.linkedin.com/sharing/share-offsite/?url=https://tformance.com/open-source/{{ profile.slug }}/"
     target="_blank" rel="noopener"
     class="btn btn-sm btn-ghost gap-2"
     onclick="if(window.posthog){posthog.capture('public_social_share_clicked',{platform:'linkedin',org_slug:'{{ profile.slug }}'})}">
    <i class="fa-brands fa-linkedin text-primary"></i>
    Share on LinkedIn
  </a>
</div>
```

---

### 6.4 Outreach to Tracked Orgs

**Email Template for Maintainers:**

Subject: "We added [OrgName] to our OSS engineering metrics tracker"

```
Hi [Name],

I'm reaching out from Tformance — we analyze engineering metrics for open source projects.

We added [OrgName] to our public analytics page, which shows:
- AI adoption trends (you're at [X]%)
- Cycle time benchmarks
- Team velocity
- Comparison with [Industry] peers

See it here: https://tformance.com/open-source/[slug]/

The data is public and refreshed daily. If you'd like to:
- Request changes or removal
- Add this page to your README
- Get a custom badge

Just reply to this email.

[Signature]
```

**Badge Offer:**
```markdown
[![Engineering Metrics](https://img.shields.io/badge/tformance-view%20metrics-orange)](https://tformance.com/open-source/[slug]/)
```

**Incentive:** Maintainers who add badge to README get featured in our monthly "Top OSS Projects" blog post.

---

## 7. Implementation Roadmap

### Phase 1: Analytics Foundation (Week 1)
- [ ] Add PostHog page_view event to base.html
- [ ] Add page_type to all view contexts
- [ ] Add scroll_depth tracking
- [ ] Add CTA click tracking to all buttons
- [ ] Create PostHog dashboards (Overview, Funnel, Engagement)

### Phase 2: Conversion Optimization (Week 2)
- [ ] Add directory top CTA
- [ ] Add "What Pro Shows" section to org detail pages
- [ ] Add industry page inline CTA
- [ ] Add mobile sticky CTA
- [ ] Add "Request Repo" link to directory header
- [ ] Add social proof alerts

### Phase 3: SEO Enhancements (Week 3)
- [ ] Fix directory table links (add proper `<a>` tags)
- [ ] Add FAQ entries for quality & AI tools
- [ ] Add `hasPart` to industry JSON-LD
- [ ] Generate OG images (Cloudflare Workers)
- [ ] Add industry intro paragraphs
- [ ] Verify sitemap includes public pages

### Phase 4: Engagement Features (Week 4)
- [ ] Add chart interaction tracking
- [ ] Add table sort tracking
- [ ] Add external link tracking
- [ ] Add social share buttons
- [ ] Add comparison table to directory

### Phase 5: Content Launch (Week 5-6)
- [ ] Write "AI Adoption Trends" monthly report
- [ ] Write "Top 10 Fastest Teams" post
- [ ] Write "AI Code Quality" analysis
- [ ] Create Twitter thread templates
- [ ] Outreach to top 20 tracked orgs

---

## 8. Success Metrics & KPIs

### 8.1 Traffic Goals

| Metric | Baseline (Today) | 3 Months | 6 Months | 12 Months |
|--------|------------------|----------|----------|-----------|
| Monthly Visitors | <1K | 3K | 10K | 25K |
| Organic Search Traffic | <100 | 1K | 5K | 15K |
| Social Referrals | <50 | 500 | 2K | 5K |
| Direct Traffic | <500 | 1K | 2K | 4K |

### 8.2 Engagement Goals

| Metric | Target (6mo) |
|--------|--------------|
| Avg Session Duration | 2:30 min |
| Bounce Rate | <50% |
| Pages per Session | 2.5 |
| Chart Interactions | 15% of visitors |
| Table Sorts | 10% of visitors |
| External Link Clicks (GitHub) | 20% of visitors |

### 8.3 Conversion Goals

| Metric | Baseline | Target (3mo) | Target (6mo) |
|--------|----------|--------------|--------------|
| Public Page → Signup | 1-2% | 3% | 5% |
| Request Repo Submissions | <5/mo | 20/mo | 50/mo |
| Social Shares | <10/mo | 100/mo | 500/mo |
| Backlinks from Orgs | 0 | 10 | 30 |

### 8.4 SEO Goals

| Metric | Baseline | Target (6mo) |
|--------|----------|--------------|
| "[org] engineering metrics" rankings | Not ranked | Top 3 for 50+ orgs |
| "engineering metrics" (generic) | Not ranked | Top 10 |
| "[industry] benchmarks" | Not ranked | Top 5 for all industries |
| Domain Authority | 20 | 35 |

---

## 9. PostHog Dashboard Specifications

### Dashboard 1: Public Pages Overview

**Widgets:**
1. **Total Page Views (last 30 days)**
   - Event: `public_page_view`
   - Breakdown by `page_type`

2. **Unique Visitors**
   - Event: `public_page_view`
   - Unique by `distinct_id`

3. **Top Orgs by Traffic**
   - Event: `public_page_view`
   - Filter: `page_type = "org_detail"`
   - Group by: `org_slug`
   - Top 10

4. **Top Referrers**
   - Event: `public_page_view`
   - Group by: `referrer`
   - Exclude: tformance.com domain

5. **Avg Scroll Depth by Page Type**
   - Event: `public_scroll_depth`
   - Avg `depth` by `page_type`

### Dashboard 2: Conversion Funnel

**Funnel:**
```
public_page_view
  ↓ (dropoff)
public_cta_clicked
  ↓ (dropoff)
public_signup_initiated
  ↓ (dropoff)
public_signup_completed
```

**Breakdown by:**
- `org_slug` (which orgs convert best?)
- `industry` (which industries convert best?)
- `referrer` (which traffic sources convert?)
- `cta_position` (which CTA placement converts?)

### Dashboard 3: Engagement

**Widgets:**
1. **Chart Interactions**
   - Event: `public_chart_interacted`
   - Count by `chart_type`, `org_slug`

2. **Table Sorts**
   - Event: `public_table_sorted`
   - Count by `column`

3. **External Link Clicks**
   - Event: `public_external_link_clicked`
   - Count by `link_type`

4. **Filter Usage**
   - Event: `public_directory_filtered`
   - Count by `filter_type`, `value`

---

## 10. Next Steps

**Immediate (This Week):**
1. Implement PostHog page_view tracking (2 hours)
2. Add directory top CTA (1 hour)
3. Fix directory table links for crawlers (30 min)
4. Create PostHog dashboards (1 hour)

**Short-term (Next 2 Weeks):**
1. Add all CTA positions (4 hours)
2. Implement chart/table interaction tracking (2 hours)
3. Generate OG images (8 hours, or skip if Cloudflare Workers)
4. Add FAQ/industry content (4 hours)

**Medium-term (Next Month):**
1. Write first blog post (8 hours)
2. Outreach to top 20 orgs (4 hours)
3. Set up social media automation (4 hours)
4. Monitor PostHog, optimize based on data (ongoing)

**Measurement Cadence:**
- Weekly: Review PostHog dashboards, identify drop-off points
- Monthly: Traffic report, conversion rate analysis
- Quarterly: SEO rankings, adjust strategy

---

## Appendix: Quick Reference

### Essential PostHog Events

| Event | Trigger | Key Properties |
|-------|---------|----------------|
| `public_page_view` | Page load | page_type, org_slug, industry, referrer |
| `public_cta_clicked` | CTA click | position, org_slug, page_type |
| `public_chart_interacted` | Chart click | chart_type, org_slug, month_clicked |
| `public_scroll_depth` | Scroll milestones | depth, page_type, org_slug |
| `public_table_sorted` | Table header click | table, column, direction, org_slug |
| `public_directory_filtered` | Filter change | filter_type, value |
| `public_external_link_clicked` | GitHub/PR link | link_type, org_slug, pr_is_ai |
| `public_signup_initiated` | Signup page from public | referrer, utm params |

### Template Changes Checklist

- [ ] `templates/public/base.html` — page_view, scroll_depth scripts
- [ ] `templates/public/directory.html` — top CTA, request repo link, filter tracking
- [ ] `templates/public/org_detail.html` — "What Pro Shows" section, social share buttons, chart tracking
- [ ] `templates/public/industry.html` — inline CTA, intro paragraph
- [ ] `templates/public/_directory_list.html` — fix table links

### View Changes Checklist

- [ ] `apps/public/views.py` — add `page_type` to all contexts
- [ ] `apps/public/views.py` — add `page_image` for OG images (if implemented)

### Settings Checklist

- [ ] Verify `POSTHOG_API_KEY` is set in production
- [ ] Add `POSTHOG_API_KEY` to template context (or use context processor)

---

**End of Growth Strategy Document**

This strategy provides a complete roadmap to transform the public OSS analytics pages from a showcase into a high-performing lead generation engine. All implementations are specific, actionable, and tied to measurable outcomes.
