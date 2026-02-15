# SEO & GEO Requirements for Public OSS Analytics Pages

**Date:** 2026-02-15
**Status:** Draft
**Author:** SEO/GEO Technical Specialist (seo-geo skill)
**Related:** [Public App Reuse Design](./2026-02-15-public-app-reuse-design.md)

---

## Executive Summary

This document defines comprehensive SEO (Search Engine Optimization) and GEO (Generative Engine Optimization) requirements for Tformance's public OSS analytics pages at `/open-source/`. Based on the Princeton GEO research framework, platform-specific ranking algorithms, and audit of current implementation.

**Current state:** Strong technical SEO foundation. Key gaps in GEO optimization, dynamic OG images, and structured data completeness.

**Impact potential:**
- Traditional SEO: 500+ indexed pages, 50K impressions/month target
- GEO: Up to 40% visibility boost in AI search engines (ChatGPT, Perplexity, Google AI Overview)
- OG images: 2-3x higher social sharing click-through rate

---

## Table of Contents

1. [Current State Audit](#1-current-state-audit)
2. [GEO Requirements (AI Search Visibility)](#2-geo-requirements)
3. [Traditional SEO Requirements](#3-traditional-seo-requirements)
4. [Structured Data (JSON-LD) Requirements](#4-structured-data-requirements)
5. [Dynamic OG Image Generation](#5-dynamic-og-image-generation)
6. [Platform-Specific Optimization](#6-platform-specific-optimization)
7. [Content Strategy for AI Citability](#7-content-strategy-for-ai-citability)
8. [Technical Implementation Checklist](#8-technical-implementation-checklist)
9. [Monitoring & KPIs](#9-monitoring--kpis)

---

## 1. Current State Audit

### 1.1 What's Working Well (Keep)

| Area | Status | Details |
|------|--------|---------|
| **robots.txt** | GOOD | All major AI bots allowed (GPTBot, ClaudeBot, PerplexityBot, ChatGPT-User, etc.) |
| **AI Training Crawlers** | GOOD | GPTBot, Google-Extended allowed for `/open-source/` |
| **Dynamic Meta Tags** | GOOD | `page_title` + `page_description` passed per view, rendered via `meta_tags` templatetags |
| **JSON-LD Dataset** | GOOD | `Dataset` schema on org pages with `variableMeasured` properties |
| **JSON-LD FAQPage** | GOOD | 3-4 dynamic FAQ entries on org detail pages |
| **JSON-LD DataCatalog** | GOOD | Directory page catalogs all org datasets |
| **Django Sitemaps** | GOOD | `PublicDirectorySitemap`, `PublicOrgSitemap`, `PublicIndustrySitemap` with `lastmod` |
| **llms.txt** | GOOD | Both `llms.txt` and `llms-full.txt` with structured org data |
| **RSS Feed** | GOOD | Top 50 orgs with metrics in description |
| **Canonical URLs** | GOOD | `<link rel="canonical">` via `web/base.html` context processor |
| **OG + Twitter Cards** | PARTIAL | Tags present but use generic project image (no per-page images) |
| **Cache-Control** | GOOD | 12h CDN TTL on all public responses |
| **Rate Limiting** | GOOD | `@ratelimit` on all public views |
| **Citable Summary** | GOOD | `org_detail.html` has a prose paragraph with key stats |
| **Accessibility** | GOOD | `role="img"`, `aria-label` on chart canvases, `sr-only` data |

### 1.2 Gaps to Address (Fix)

| Gap | Priority | Impact | Details |
|-----|----------|--------|---------|
| **No BreadcrumbList schema** | P1 | Medium | Breadcrumbs exist in HTML but not in JSON-LD |
| **No SpeakableSpecification** | P2 | Medium | Missing voice search + AI extraction hints |
| **No Organization schema** | P1 | Medium | Directory/homepage lacks org schema for Tformance |
| **Generic OG images** | P1 | High | All pages share same image — no per-org differentiation |
| **No `@graph` combined schema** | P2 | Medium | Multiple `<script type="application/ld+json">` instead of single `@graph` |
| **No `datePublished` on pages** | P1 | Medium | Schema has `dateModified` but missing `datePublished` |
| **No `author` in Article/Dataset** | P2 | Low | Dataset schema credits org as creator, not Tformance as publisher |
| **Missing `og:type` specificity** | P2 | Low | All pages use `website` — could use `article` for org detail |
| **No GEO content optimization** | P1 | High | Content lacks Princeton GEO methods (citations, authoritative tone) |
| **HTMX chart invisibility** | P0 | Critical | Directory filter HTMX partial updates work, but future analytics tab charts loaded via `hx-get` will be invisible to bots |
| **No `hreflang`** | P2 | Low | English-only so low priority, but good practice |
| **Industry pages lack FAQPage** | P1 | High | Only org_detail has FAQ schema; industry pages should too |
| **Directory lacks FAQPage** | P1 | High | Directory should answer "what is open source engineering analytics?" |

### 1.3 robots.txt Audit

Current robots.txt is **well-configured**. Verified allowed bots:

| Bot | Purpose | Status |
|-----|---------|--------|
| `OAI-SearchBot` | ChatGPT search results | ALLOWED |
| `ChatGPT-User` | ChatGPT browsing mode | ALLOWED |
| `ClaudeBot` | Claude search | ALLOWED |
| `Claude-SearchBot` | Claude search | ALLOWED |
| `PerplexityBot` | Perplexity AI | ALLOWED |
| `GPTBot` | OpenAI training | ALLOWED |
| `Google-Extended` | Google AI training | ALLOWED |
| `Amazonbot` | Amazon Alexa/search | ALLOWED |
| `DuckAssistBot` | DuckDuckGo AI | ALLOWED |
| `Bingbot` | Bing/Copilot (via wildcard) | ALLOWED |
| `Googlebot` | Google (via wildcard) | ALLOWED |

**Recommendation:** Add `anthropic-ai` as a separate entry (ClaudeBot's secondary crawler).

```
User-agent: anthropic-ai
Allow: /open-source/
```

---

## 2. GEO Requirements (AI Search Visibility)

Based on the Princeton GEO research (KDD 2024), these are the 9 optimization methods ranked by effectiveness, with specific requirements for our public pages.

### 2.1 Method 1: Cite Sources (+40% visibility)

**Requirement:** Every public page must include at least 2 authoritative citations.

**Implementation for Tformance:**

```html
<!-- Org detail: add citation block after citable summary -->
<p class="text-base-content/80 max-w-3xl text-lg leading-relaxed mb-3">
  {{ summary.ai_assisted_pct }}% of {{ profile.display_name }}'s pull requests
  are AI-assisted — consistent with the industry-wide trend where
  <strong>78% of developers now use AI coding tools</strong>
  (Stack Overflow Developer Survey, 2025).
  Based on {{ summary.total_prs|intcomma }} merged PRs analyzed by Tformance.
</p>
```

**Citation sources to reference:**
- Stack Overflow Developer Survey (annual, high authority)
- GitHub Octoverse Report (annual, high authority)
- DORA State of DevOps Report (annual, high authority for cycle time/DORA metrics)
- Tformance's own dataset ("Based on analysis of X PRs across Y organizations")

**Pages to update:**
- [ ] Org detail: cite industry surveys in summary paragraph
- [ ] Industry pages: cite DORA benchmarks for cycle time context
- [ ] Directory: cite overall AI adoption trends from authoritative sources
- [ ] Methodology section: cite specific papers on AI detection methodology

### 2.2 Method 2: Statistics Addition (+37% visibility)

**Requirement:** Every section must include at least 1 specific statistic with a number.

**Current status: PARTIALLY MET.** Our pages are data-heavy by nature. However, prose sections need explicit statistics woven in.

**Gap: Content blocks.** The methodology section and introductory paragraphs use qualitative language where quantitative would be stronger.

```html
<!-- BEFORE (qualitative) -->
<p>Organizations must have enough merged PRs to appear in public analytics.</p>

<!-- AFTER (quantitative - +37% GEO boost) -->
<p>Organizations must have 500+ merged PRs to appear in public analytics,
ensuring statistical significance. The median organization in our dataset
has {{ global_stats.median_prs }} PRs across {{ global_stats.avg_repos }} repositories.</p>
```

### 2.3 Method 3: Quotation Addition (+30% visibility)

**Requirement:** Include 1 expert quote per page type.

**Implementation:** Add a rotating "Industry Perspective" block or static expert context.

```html
<!-- On directory page -->
<blockquote class="border-l-4 border-primary pl-4 my-6 text-base-content/80">
  <p>"The best engineering teams measure not just speed, but the quality
  and sustainability of their delivery."</p>
  <cite class="text-sm text-base-content/50">
    — DORA State of DevOps Report, 2025
  </cite>
</blockquote>
```

**Note:** Quotes should be from public reports/books, not fabricated. Use quotes from:
- DORA reports (Nicole Forsgren et al.)
- Accelerate book (for DORA metrics context)
- Stack Overflow survey commentary

### 2.4 Method 4: Authoritative Tone (+25% visibility)

**Requirement:** Use confident, declarative language. Avoid hedging words.

**Current status: PARTIALLY MET.** The citable summary on org pages uses authoritative tone. Methodology section is also factual.

**Gap areas:**
```
# AVOID (hedging)
"This might indicate that AI tools are becoming more popular."
"It seems like cycle time is improving."

# USE (authoritative)
"AI adoption increased 15% quarter-over-quarter, driven by Copilot and Cursor."
"Median cycle time decreased from 48h to 32h, a 33% improvement."
```

### 2.5 Method 5: Easy-to-Understand (+20% visibility)

**Requirement:** Define technical terms on first use. Use analogies where helpful.

```html
<!-- Add to methodology or first occurrence -->
<p>
  <strong>Cycle time</strong> — the elapsed time from when a developer opens a
  pull request to when it's merged into the main branch — is one of the four
  DORA metrics used to measure software delivery performance.
</p>
```

**Terms to define on first use per page:**
- Cycle time
- AI-assisted PR
- DORA metrics
- PR velocity
- Revert rate / Hotfix rate

### 2.6 Method 6: Technical Terms (+18% visibility)

**Requirement:** Include domain-specific terminology naturally.

**Current status: GOOD.** Pages already use terms like "cycle time", "AI adoption rate", "merged PRs", "revert rate", "CI pass rate".

**Enhancement:** Ensure each page includes at least 3 of these terms in prose (not just chart labels):
- DORA metrics, lead time, deployment frequency
- Pull request velocity, throughput, review latency
- AI-assisted development, AI pair programming, AI code generation
- Code review coverage, approval rate

### 2.7 Method 7: Unique Words (+15% visibility)

**Requirement:** Increase vocabulary diversity. Avoid repetitive phrasing across pages.

**Implementation:** Each org page should have unique descriptive text based on that org's characteristics:

```python
# In view, generate unique intro based on org data
def _get_org_personality(summary, industry_stats):
    """Generate unique prose for each org based on their metrics."""
    traits = []
    if summary['ai_assisted_pct'] > industry_stats.get('avg_ai_pct', 0) * 1.5:
        traits.append("an early adopter of AI coding tools")
    if summary['median_cycle_time_hours'] < 24:
        traits.append("known for rapid delivery cycles")
    if summary['active_contributors_90d'] > 50:
        traits.append("a large and active contributor community")
    return traits
```

### 2.8 Method 8: Fluency Optimization (+15-30% visibility)

**Requirement:** Improve readability. Short paragraphs (2-3 sentences). Logical flow.

**Current status: GOOD.** Templates already use short paragraphs and bullet points.

**Enhancement for new tab pages:**
- Every analytics tab should start with a 2-sentence summary
- Use transition phrases between chart sections ("Looking at delivery trends..." → "Comparing across team members...")
- Keep paragraphs to 2-3 sentences maximum

### 2.9 Method 9: Keyword Stuffing (-10% visibility) — AVOID

**Requirement:** NEVER stuff keywords. Natural language only.

**Current status: SAFE.** No keyword stuffing detected. Continue this approach.

**Risk areas to watch:**
- Auto-generated title tags (ensure they read naturally)
- Meta descriptions (temptation to cram keywords)
- Alt text on charts (describe the visualization, don't stuff keywords)

### 2.10 Best Combinations for Our Content

Per Princeton research, the optimal combinations for our content type (technology/data):

| Combination | Target Page Type |
|-------------|-----------------|
| **Technical Terms + Citations** | Org analytics tabs (academic/scientific tone) |
| **Statistics + Authoritative Tone** | Directory + Industry pages (business tone) |
| **Fluency + Statistics** | Org overview (general audience) |
| **Easy Language + Statistics** | New visitor landing (consumer-friendly) |

---

## 3. Traditional SEO Requirements

### 3.1 P0 — Critical (Must Fix Before Launch)

- [x] **P0** robots.txt allows important pages ✅
- [x] **P0** HTTPS enabled ✅
- [x] **P0** Mobile-responsive design ✅ (Tailwind responsive classes)
- [x] **P0** No critical pages blocked by `noindex` ✅
- [ ] **P0** Unique `<title>` per page — ✅ exists but needs tab-specific titles for new pages
- [x] **P0** Single H1 per page ✅
- [ ] **P0** H1 contains primary keyword — ✅ for existing, needs definition for new tab pages
- [ ] **P0** HTMX lazy-loaded chart data rendered inline for public pages (Googlebot can't execute JS)

### 3.2 P1 — Important (Fix Within Sprint 1)

- [x] **P1** XML sitemap exists and submitted ✅
- [x] **P1** Canonical tags properly implemented ✅
- [ ] **P1** `<meta description>` is compelling and includes keyword — needs review for each new tab
- [ ] **P1** Logical heading hierarchy (H1 > H2 > H3) — audit new tab pages
- [x] **P1** All images have `alt` attributes ✅ (chart canvases have `aria-label`)
- [x] **P1** Internal links to related content ✅ (related orgs, industry links)
- [ ] **P1** FAQPage schema on ALL page types (currently only org_detail)
- [ ] **P1** BreadcrumbList schema in JSON-LD
- [ ] **P1** Organization schema on directory page
- [ ] **P1** datePublished included in all schemas
- [ ] **P1** Sitemap expanded for new tab URLs (analytics/, pull-requests/)

### 3.3 P2 — Recommended (Post-Launch Enhancement)

- [x] **P2** `og:title` set ✅
- [x] **P2** `og:description` set ✅
- [ ] **P2** `og:image` set with per-page dynamic image (currently generic)
- [x] **P2** `og:url` set ✅
- [ ] **P2** `twitter:image` with per-page dynamic image
- [ ] **P2** SpeakableSpecification for voice search / AI extraction
- [x] **P2** Paragraphs are short ✅
- [x] **P2** Tables used for comparisons ✅
- [x] **P2** External links have `rel="noopener"` ✅

---

## 4. Structured Data (JSON-LD) Requirements

### 4.1 Current Schema Inventory

| Page | Current Schema | Status |
|------|---------------|--------|
| Directory | `DataCatalog` | GOOD |
| Org Detail | `Dataset` + `FAQPage` | GOOD |
| Industry | `Dataset` | GOOD, needs `FAQPage` |
| New: Analytics tabs | None yet | NEEDED |
| New: PR List | None yet | NEEDED |

### 4.2 Required Schema Updates

#### A. Directory Page — Add Organization + FAQPage

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "DataCatalog",
      "name": "Open Source Engineering Analytics",
      "description": "Engineering metrics from {{ org_count }} open source projects...",
      "url": "https://tformance.com/open-source/",
      "provider": {
        "@type": "Organization",
        "name": "Tformance",
        "url": "https://tformance.com",
        "logo": {
          "@type": "ImageObject",
          "url": "https://tformance.com/static/images/tformance-logo.png"
        },
        "sameAs": [
          "https://github.com/tformance",
          "https://x.com/tformance"
        ]
      }
    },
    {
      "@type": "WebPage",
      "name": "Open Source Engineering Analytics Directory",
      "url": "https://tformance.com/open-source/",
      "dateModified": "{{ latest_update|date:'Y-m-d' }}",
      "speakable": {
        "@type": "SpeakableSpecification",
        "cssSelector": ["h1", ".prose", ".stat-value"]
      }
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is open source engineering analytics?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Open source engineering analytics measures developer productivity metrics like AI adoption rate, cycle time, and PR velocity from public GitHub repositories. Tformance tracks {{ org_count }} organizations across {{ industry_count }} industries."
          }
        },
        {
          "@type": "Question",
          "name": "What percentage of open source PRs are AI-assisted?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Across {{ org_count }} tracked organizations, the average AI adoption rate is {{ avg_ai_pct }}%. This represents {{ total_ai_prs }} AI-assisted pull requests out of {{ total_prs }} total."
          }
        },
        {
          "@type": "Question",
          "name": "How are engineering metrics calculated?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "Metrics are computed from merged pull requests in public GitHub repositories. AI detection uses pattern matching on PR metadata combined with LLM classification. Cycle time measures duration from PR creation to merge. Data refreshes daily at 5:30 AM UTC."
          }
        }
      ]
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {
          "@type": "ListItem",
          "position": 1,
          "name": "Home",
          "item": "https://tformance.com/"
        },
        {
          "@type": "ListItem",
          "position": 2,
          "name": "Open Source Analytics",
          "item": "https://tformance.com/open-source/"
        }
      ]
    }
  ]
}
```

#### B. Org Detail Page — Consolidate into `@graph`

Merge existing separate `<script>` blocks into a single `@graph`:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Dataset",
      "name": "{{ display_name }} Engineering Metrics",
      "description": "...",
      "url": "https://tformance.com/open-source/{{ slug }}/",
      "temporalCoverage": "2025/..",
      "license": "https://creativecommons.org/licenses/by/4.0/",
      "datePublished": "{{ profile.created_at|date:'Y-m-d' }}",
      "dateModified": "{{ summary.last_computed_at|date:'Y-m-d' }}",
      "creator": {
        "@type": "Organization",
        "name": "{{ display_name }}",
        "url": "{{ github_org_url }}"
      },
      "publisher": {
        "@type": "Organization",
        "name": "Tformance",
        "url": "https://tformance.com"
      },
      "variableMeasured": [
        {"@type": "PropertyValue", "name": "Total PRs", "value": "{{ total_prs }}"},
        {"@type": "PropertyValue", "name": "AI Adoption Rate", "value": "{{ ai_pct }}%", "unitCode": "P1"},
        {"@type": "PropertyValue", "name": "Median Cycle Time", "value": "{{ cycle_time }}h"},
        {"@type": "PropertyValue", "name": "Median Review Time", "value": "{{ review_time }}h"},
        {"@type": "PropertyValue", "name": "Active Contributors (90d)", "value": "{{ contributors }}"}
      ]
    },
    {
      "@type": "FAQPage",
      "mainEntity": [...]
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://tformance.com/"},
        {"@type": "ListItem", "position": 2, "name": "Open Source", "item": "https://tformance.com/open-source/"},
        {"@type": "ListItem", "position": 3, "name": "{{ industry_display }}", "item": "https://tformance.com/open-source/industry/{{ industry }}/"},
        {"@type": "ListItem", "position": 4, "name": "{{ display_name }}", "item": "https://tformance.com/open-source/{{ slug }}/"}
      ]
    },
    {
      "@type": "WebPage",
      "name": "{{ display_name }} Engineering Metrics",
      "speakable": {
        "@type": "SpeakableSpecification",
        "cssSelector": ["h1", ".text-lg.leading-relaxed", ".stat-value", ".card-title"]
      }
    }
  ]
}
```

#### C. Industry Page — Add FAQPage + BreadcrumbList

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Dataset",
      "name": "{{ industry }} Engineering Benchmarks",
      "..."
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What is the average AI adoption rate in {{ industry }}?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "The average AI adoption rate across {{ org_count }} {{ industry|lower }} organizations is {{ avg_ai_pct }}%, based on analysis of {{ total_prs }} merged pull requests by Tformance."
          }
        },
        {
          "@type": "Question",
          "name": "What is the average cycle time in {{ industry }}?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "The average median cycle time in {{ industry|lower }} is {{ avg_cycle_time }} hours, measuring the time from pull request creation to merge."
          }
        }
      ]
    },
    {
      "@type": "BreadcrumbList",
      "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://tformance.com/"},
        {"@type": "ListItem", "position": 2, "name": "Open Source", "item": "https://tformance.com/open-source/"},
        {"@type": "ListItem", "position": 3, "name": "{{ industry }}", "item": "https://tformance.com/open-source/industry/{{ industry_key }}/"}
      ]
    }
  ]
}
```

#### D. New Analytics Tab Pages — Dataset with specific variables

Each analytics tab should have its own Dataset schema focusing on that tab's metrics:

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Dataset",
      "name": "{{ display_name }} AI Adoption Metrics",
      "description": "AI coding tool adoption data for {{ display_name }}: {{ ai_pct }}% AI-assisted PRs across {{ total_prs }} merged pull requests.",
      "url": "https://tformance.com/open-source/{{ slug }}/analytics/ai-adoption/",
      "variableMeasured": [
        {"@type": "PropertyValue", "name": "AI Adoption Rate", "value": "{{ ai_pct }}%"},
        {"@type": "PropertyValue", "name": "AI-Assisted PRs", "value": "{{ ai_pr_count }}"},
        {"@type": "PropertyValue", "name": "Top AI Tool", "value": "{{ top_ai_tool }}"}
      ]
    },
    {
      "@type": "FAQPage",
      "mainEntity": [
        {
          "@type": "Question",
          "name": "What AI coding tools does {{ display_name }} use?",
          "acceptedAnswer": {
            "@type": "Answer",
            "text": "..."
          }
        }
      ]
    },
    {
      "@type": "BreadcrumbList",
      "..."
    }
  ]
}
```

---

## 5. Dynamic OG Image Generation

### 5.1 Requirement

Each public page needs a unique, data-rich Open Graph image for social sharing. Currently all pages share the generic Tformance image.

### 5.2 Recommended Approach: `pictex` Library

Based on the [pictex library](https://pypi.org/project/pictex/) for declarative Python image generation:

**Why pictex over alternatives:**

| Approach | Speed | Dependencies | Complexity |
|----------|-------|-------------|------------|
| **pictex** | ~50ms/image | Pure Python (Pillow) | Low — declarative API |
| Playwright/Puppeteer | ~2-5s/image | Headless browser | High — browser management |
| Pillow direct | ~50ms/image | Pure Python | Medium — manual coordinates |
| External service (Vercel OG) | ~200ms/image | HTTP call | Low but adds dependency |

**Advantages for Tformance:**
- No headless browser needed (lightweight for Heroku)
- Declarative layout (readable, maintainable)
- Fast enough for on-demand generation with CDN caching
- Python-native (fits our stack)

### 5.3 Implementation Design

```python
# apps/public/og_images.py
from pictex import Canvas, Column, Row, Text, Image

def generate_org_og_image(profile, summary):
    """Generate a 1200x630 OG image for an org page."""
    card = Canvas(
        Column(
            # Header with org name
            Row(
                Text(profile["display_name"])
                    .font_size(48)
                    .font_family("Inter-Bold.ttf")
                    .color("#FFFFFF"),
            ).padding(40, 40, 20, 40),

            # Metrics row
            Row(
                _metric_block("AI Adoption", f"{summary['ai_assisted_pct']}%", "#F97316"),
                _metric_block("Cycle Time", f"{summary['median_cycle_time_hours']}h", "#3B82F6"),
                _metric_block("PRs Analyzed", f"{summary['total_prs']:,}", "#22C55E"),
            ).gap(30).padding(0, 40, 30, 40),

            # Footer
            Row(
                Text("tformance.com/open-source")
                    .font_size(20)
                    .color("#FFFFFF80"),
                Text("Updated daily")
                    .font_size(16)
                    .color("#FFFFFF40"),
            ).justify_content("space-between")
            .padding(20, 40, 40, 40),
        )
        .justify_content("space-between")
    ).size(1200, 630).background_color("#1a1a2e")

    return card.render()  # Returns PIL Image or bytes


def _metric_block(label, value, color):
    return Column(
        Text(value).font_size(56).font_family("Inter-Bold.ttf").color(color),
        Text(label).font_size(18).color("#FFFFFF80"),
    ).gap(4)
```

### 5.4 OG Image URL Strategy

```python
# apps/public/views.py
@ratelimit(key="ip", rate="30/m", method="GET", block=True)
def og_image(request, slug):
    """Generate and cache OG image for an org."""
    data = PublicAnalyticsService.get_org_detail(slug)
    if data is None:
        raise Http404

    image_bytes = generate_org_og_image(data["profile"], data["summary"])
    response = HttpResponse(image_bytes, content_type="image/png")
    response["Cache-Control"] = "public, max-age=86400"  # 24h cache
    return response

# apps/public/urls.py
path("<slug:slug>/og.png", views.og_image, name="og_image"),
```

```html
<!-- In template: dynamic OG image -->
<meta property="og:image" content="https://tformance.com/open-source/{{ profile.slug }}/og.png">
<meta name="twitter:image" content="https://tformance.com/open-source/{{ profile.slug }}/og.png">
```

### 5.5 OG Image Variants

| Page Type | Image Content | Size |
|-----------|--------------|------|
| **Org Overview** | Org name + 3 key metrics (AI%, Cycle Time, PRs) + Tformance branding | 1200x630 |
| **Org Analytics Tab** | Org name + tab-specific metric + mini sparkline graphic | 1200x630 |
| **Industry** | Industry name + org count + avg metrics + comparison bars | 1200x630 |
| **Directory** | "Open Source Engineering Analytics" + global stats + org count | 1200x630 |

### 5.6 Fallback Strategy

If pictex causes issues or isn't performant enough, fallback to pre-generating images via a management command:

```bash
# Generate all OG images as static files
python manage.py generate_og_images --output=staticfiles/og/
```

---

## 6. Platform-Specific Optimization

### 6.1 ChatGPT Optimization

**How ChatGPT decides what to cite (SE Ranking study, 129K domains):**
- Content-Answer Fit: **55%** of citation decisions
- Domain Authority (referring domains): >350K = 8.4 avg citations
- Content Recency: 30-day old content gets **3.2x** more citations

**Requirements:**
- [ ] Match ChatGPT's conversational response style in prose blocks
- [ ] Update content daily (we already do this ✅)
- [ ] Include "answer-first" format: direct answer in first sentence, details after
- [ ] Build external backlinks (GitHub readme mentions, dev.to articles, blog posts)

**Content-Answer Fit template for org pages:**

```html
<!-- Answer-first format that matches how ChatGPT would answer -->
<p>
  {{ profile.display_name }}'s engineering team has a {{ summary.ai_assisted_pct }}%
  AI adoption rate across {{ summary.total_prs|intcomma }} pull requests.
  Their median cycle time is {{ summary.median_cycle_time_hours }} hours,
  {% if summary.median_cycle_time_hours < industry_stats.avg_cycle_time %}
  faster than{% else %}compared to{% endif %} the {{ profile.industry_display|lower }}
  industry average of {{ industry_stats.avg_cycle_time }} hours.
</p>
```

### 6.2 Perplexity Optimization

**How Perplexity ranks (3-layer reranking system):**
- Authoritative Domain Lists: GitHub, academic sites get inherent boost
- FAQ Schema: Pages with FAQ blocks cited more often
- Semantic Relevance: Content similarity to query (not keyword matching)
- PDF Documents: Publicly hosted PDFs prioritized

**Requirements:**
- [x] FAQPage schema (already on org_detail ✅, need on industry + directory)
- [ ] Create downloadable PDF reports per org (V2 feature)
- [ ] Ensure semantic relevance in prose (describe metrics in natural language)
- [ ] Focus on atomic, extractable paragraphs (each paragraph = one complete thought)
- [x] PerplexityBot allowed in robots.txt ✅

### 6.3 Google AI Overview (SGE) Optimization

**How Google SGE ranks (5-stage pipeline):**
- E-E-A-T: Experience, Expertise, Authoritativeness, Trustworthiness
- Structured Data: Schema markup is critical
- Authoritative Citations: +132% visibility
- Topical Authority: Content clusters + internal linking

**Requirements:**
- [ ] Build topical authority: org page → analytics tabs → PR list (content cluster)
- [ ] Internal linking: every page links to 5+ related pages
- [ ] E-E-A-T signals: methodology section establishes expertise
- [ ] Comprehensive Schema markup (Dataset + FAQPage + BreadcrumbList + Organization)
- [ ] Author attribution: "Analyzed by Tformance" with link to methodology

### 6.4 Microsoft Copilot / Bing Optimization

**Requirements:**
- [x] Bingbot allowed (via wildcard Allow) ✅
- [ ] Submit site to Bing Webmaster Tools
- [ ] Use IndexNow for faster indexing of new org pages
- [ ] Clear entity definitions in content (define "cycle time", "AI adoption" on first use)
- [ ] Page speed < 2 seconds (current CDN performance should meet this)

### 6.5 Claude AI Optimization

**How Claude decides to cite (Brave Search-based):**
- Crawl-to-Refer Ratio: 38,065:1 (very selective)
- Factual Density: Data-rich content preferred
- Structural Clarity: Easy to extract information

**Requirements:**
- [x] ClaudeBot allowed ✅
- [x] llms.txt + llms-full.txt ✅ (excellent for Claude's content understanding)
- [ ] Maximize factual density: every paragraph should contain at least 1 data point
- [ ] Clear structural hierarchy for easy extraction
- [ ] Ensure Brave Search indexes pages (may need separate submission)

---

## 7. Content Strategy for AI Citability

### 7.1 Content Block Templates

#### Org Overview — GEO-Optimized Introduction

```html
<div class="prose prose-sm text-base-content/70 mt-6 mb-8" id="about-section">
  <h3>About {{ profile.display_name }} Engineering Metrics</h3>
  <p>
    <strong>{{ profile.display_name }}</strong> is a {{ profile.industry_display|lower }}
    organization with {{ summary.active_contributors_90d }} active contributors.
    Based on analysis of {{ summary.total_prs|intcomma }} merged pull requests,
    {{ summary.ai_assisted_pct|floatformat:1 }}% are AI-assisted —
    {% if summary.ai_assisted_pct > industry_stats.avg_ai_pct %}
    above the {{ profile.industry_display|lower }} industry average of {{ industry_stats.avg_ai_pct|floatformat:1 }}%
    {% else %}
    compared to the {{ profile.industry_display|lower }} industry average of {{ industry_stats.avg_ai_pct|floatformat:1 }}%
    {% endif %}
    (Tformance Open Source Analytics, {{ current_date|date:"F Y" }}).
  </p>
  <p>
    Their median cycle time is <strong>{{ summary.median_cycle_time_hours|floatformat:1 }} hours</strong>,
    with a median code review turnaround of {{ summary.median_review_time_hours|floatformat:1 }} hours.
    According to the DORA State of DevOps Report, elite teams maintain cycle times
    under 24 hours — {{ profile.display_name }}
    {% if summary.median_cycle_time_hours < 24 %}meets{% else %}is working toward{% endif %}
    this benchmark.
  </p>
</div>
```

**GEO methods applied:**
- Citations (+40%): DORA report reference, Tformance data attribution
- Statistics (+37%): Specific numbers for AI%, cycle time, contributor count
- Authoritative Tone (+25%): Confident, declarative statements
- Technical Terms (+18%): "cycle time", "code review turnaround", "DORA"
- Easy-to-Understand (+20%): Defines industry context, uses comparison

#### Directory — GEO-Optimized Header

```html
<div class="prose max-w-3xl mb-8">
  <p>
    Real-time engineering metrics from <strong>{{ global_stats.org_count }}
    open source organizations</strong>, covering {{ global_stats.total_prs|intcomma }}
    merged pull requests across {{ global_stats.industry_count }} industries.
    The average AI coding tool adoption rate is {{ global_stats.avg_ai_pct|floatformat:1 }}%,
    consistent with findings from the 2025 Stack Overflow Developer Survey showing
    78% of professional developers now use AI coding assistants.
  </p>
  <p>
    Each organization's metrics include AI adoption rate, median cycle time,
    PR velocity, code quality indicators, and team-level breakdowns —
    updated daily from public GitHub data.
  </p>
</div>
```

### 7.2 FAQ Content Requirements

Each page type needs FAQ content optimized for AI extraction:

| Page Type | FAQ Questions | Notes |
|-----------|--------------|-------|
| **Directory** | "What is open source engineering analytics?", "How is AI adoption measured?", "What percentage of open source PRs are AI-assisted?" | General awareness queries |
| **Org Detail** | "What % of {org} PRs are AI-assisted?", "What is {org}'s cycle time?", "How many active contributors does {org} have?", "What AI tools does {org} use?" | Brand + metrics queries |
| **Industry** | "What is the average AI adoption in {industry}?", "What is the average cycle time in {industry}?", "How many {industry} teams are tracked?" | Benchmark queries |
| **Analytics Tabs** | Tab-specific questions (e.g., "How does {org}'s AI adoption compare to {industry}?") | Detailed queries |

### 7.3 Internal Linking Requirements

**Minimum 5 internal links per page:**

| From | To (minimum links) |
|------|-------------------|
| Directory | Each org (100), each industry (10+), methodology |
| Org Overview | Analytics tabs (4-5), PR List (1), industry page (1), related orgs (4), directory (1) |
| Analytics Tab | Other tabs (3-4), overview (1), PR list (1), industry (1) |
| Industry | Each org in industry (variable), directory (1), other industries (2-3) |
| PR List | Overview (1), analytics tabs (4), industry (1) |

**Link anchor text must be descriptive** (not "click here"):
```html
<!-- GOOD -->
<a href="...">{{ org.display_name }} engineering metrics</a>
<a href="...">{{ industry }} industry benchmarks</a>

<!-- BAD -->
<a href="...">click here</a>
<a href="...">read more</a>
```

---

## 8. Technical Implementation Checklist

### Phase 1: Schema & Meta (Sprint 1)

- [ ] Consolidate org_detail JSON-LD into single `@graph` block
- [ ] Add BreadcrumbList schema to all public pages
- [ ] Add FAQPage schema to directory page (3 questions)
- [ ] Add FAQPage schema to industry pages (2 questions)
- [ ] Add Organization schema to directory page
- [ ] Add SpeakableSpecification to org_detail and directory
- [ ] Add `datePublished` field to all Dataset schemas
- [ ] Add `publisher` (Tformance) to all Dataset schemas
- [ ] Expand sitemap with new tab URLs
- [ ] Add `anthropic-ai` to robots.txt

### Phase 2: Content & GEO (Sprint 2)

- [ ] Write GEO-optimized intro paragraph for org detail pages
- [ ] Write GEO-optimized header paragraph for directory
- [ ] Add "About X Engineering Metrics" content block to org pages
- [ ] Add citation references (DORA, Stack Overflow Survey) to prose blocks
- [ ] Define technical terms on first use (cycle time, AI adoption, etc.)
- [ ] Ensure answer-first format on all summary paragraphs
- [ ] Add descriptive anchor text to all internal links
- [ ] Implement unique descriptive text generation per org (vocabulary diversity)

### Phase 3: OG Images (Sprint 3)

- [ ] Install `pictex` library
- [ ] Create `apps/public/og_images.py` with generation functions
- [ ] Create org OG image template (1200x630)
- [ ] Create industry OG image template
- [ ] Create directory OG image template
- [ ] Add `/open-source/<slug>/og.png` URL route
- [ ] Update `og:image` and `twitter:image` meta tags to use dynamic URLs
- [ ] Add 24h Cache-Control to OG image responses
- [ ] Create management command for pre-generating images (fallback)

### Phase 4: Validation & Monitoring (Sprint 4)

- [ ] Validate all schemas with Google Rich Results Test
- [ ] Validate with Schema.org Validator
- [ ] Submit updated sitemap to Google Search Console
- [ ] Submit to Bing Webmaster Tools + IndexNow
- [ ] Check Brave Search indexing for Claude visibility
- [ ] Test OG images with Twitter Card Validator + Facebook Debugger
- [ ] Set up Core Web Vitals monitoring in GSC
- [ ] Run Lighthouse audit on all page types (target 90+ performance)

---

## 9. Monitoring & KPIs

### 9.1 SEO KPIs

| Metric | Tool | Baseline | 3-Month Target |
|--------|------|----------|---------------|
| Indexed pages | GSC | ~120 | 500+ |
| Organic impressions | GSC | TBD | 50K/month |
| Organic clicks | GSC | TBD | 5K/month |
| Avg position (brand + metrics queries) | GSC | N/A | <20 |
| Core Web Vitals | PageSpeed Insights | TBD | All "Good" |
| Referring domains | Ahrefs/GSC | TBD | 20+ |
| Crawl errors on public pages | GSC | 0 | 0 |
| Rich results (FAQ, Dataset) | GSC Enhancements | 0 | All pages |

### 9.2 GEO KPIs

| Metric | How to Measure | Target |
|--------|---------------|--------|
| ChatGPT citations | Manual search for "[org] engineering metrics" | Cited for top 10 orgs |
| Perplexity citations | Search perplexity.ai for queries | Cited for top 10 orgs |
| Google AI Overview inclusion | Search Google for queries | Appearing in 5+ queries |
| llms.txt downloads | Server logs / analytics | 100+/month |

### 9.3 OG Image KPIs

| Metric | Tool | Target |
|--------|------|--------|
| Social sharing CTR | PostHog / Twitter Analytics | 2x improvement over generic |
| OG image generation time | Server monitoring | <100ms per image |
| OG image cache hit rate | Cloudflare analytics | >90% |

---

## Appendix A: Quick Audit Commands

```bash
# Check meta tags on a public page
curl -sL "https://tformance.com/open-source/" | grep -E "<title>|<meta|application/ld\+json" | head -30

# Check robots.txt
curl -s "https://tformance.com/robots.txt"

# Check sitemap
curl -s "https://tformance.com/sitemap.xml" | head -50

# Validate schema (open in browser)
# https://search.google.com/test/rich-results?url=https://tformance.com/open-source/
# https://validator.schema.org/?url=https://tformance.com/open-source/

# Test OG image rendering
# https://cards-dev.twitter.com/validator (Twitter)
# https://developers.facebook.com/tools/debug/ (Facebook)
```

## Appendix B: Priority Matrix

| Priority | Task | SEO Impact | GEO Impact | Effort |
|----------|------|-----------|-----------|--------|
| **P0** | Inline chart data for public pages | Critical (indexability) | Critical | Medium |
| **P1** | FAQPage schema on all page types | +40% rich results | +40% AI visibility | Low |
| **P1** | BreadcrumbList schema | Medium | Low | Low |
| **P1** | GEO-optimized content blocks | Low | +25-40% AI visibility | Medium |
| **P1** | Expand sitemap for new tabs | High (indexability) | Medium | Low |
| **P2** | Dynamic OG images (pictex) | Medium (social CTR) | None | Medium |
| **P2** | SpeakableSpecification | Low | Medium (voice search) | Low |
| **P2** | Organization schema | Medium | Low | Low |
| **P2** | PDF reports per org | Low | High (Perplexity) | High |
