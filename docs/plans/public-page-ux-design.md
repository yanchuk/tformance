# Public Org Detail Page -- UX Design Specification

**Date:** 2026-02-15
**Author:** UX Designer (Task #2)
**Status:** Design Complete
**Target Template:** `templates/public/org_detail.html`

---

## Table of Contents

1. [Page Structure Overview](#1-page-structure-overview)
2. [Section 1: Hero (existing, unchanged)](#2-section-1-hero)
3. [Section 2: Health Overview (sparkline cards)](#3-section-2-health-overview)
4. [Section 3: Charts Row (AI Adoption + Cycle Time Trend)](#4-section-3-charts-row)
5. [Section 4: Last 10 PRs Table](#5-section-4-last-10-prs-table)
6. [Section 5: Team Member Breakdown](#6-section-5-team-member-breakdown)
7. [Section 6: Quality & Review (side by side)](#7-section-6-quality--review)
8. [Section 7: Engineering Insights](#8-section-7-engineering-insights)
9. [Section 8: AI Tools + Methodology + Similar (existing, adjusted)](#9-section-8-ai-tools--methodology--similar)
10. [Responsive Breakpoints Summary](#10-responsive-breakpoints-summary)
11. [Color & Typography Reference](#11-color--typography-reference)
12. [Data Dependencies](#12-data-dependencies)

---

## 1. Page Structure Overview

The enhanced page flows top-to-bottom through these visual sections, each separated by `mb-8`:

```
+-------------------------------------------------------+
|  Breadcrumb (existing base.html)                      |
+-------------------------------------------------------+
|  Hero: Name, Badge, GitHub link, Description          |
+-------------------------------------------------------+
|  Health Overview: 4 sparkline metric cards             |
+-------------------------------------------------------+
|  Charts: AI Adoption (line) | Cycle Time Trend (bar)  |
+-------------------------------------------------------+
|  Last 10 PRs: Compact table                           |
+-------------------------------------------------------+
|  Team Member Breakdown: Sortable contributor table     |
+-------------------------------------------------------+
|  Quality & Review: Side-by-side cards                 |
+-------------------------------------------------------+
|  Engineering Insights: Priority-colored cards          |
+-------------------------------------------------------+
|  AI Tools Table (existing)                            |
+-------------------------------------------------------+
|  Methodology (existing)                               |
+-------------------------------------------------------+
|  Similar Orgs (existing)                              |
+-------------------------------------------------------+
|  CTA Banner (existing base.html)                      |
+-------------------------------------------------------+
```

**Visual hierarchy principle:** Each section uses a consistent `card bg-base-100 border border-base-300` wrapper with `card-body p-5` inner spacing (matching the existing charts pattern). The Health Overview cards are the exception -- they use the `stat bg-base-200 rounded-box p-4` pattern consistent with the current key metrics cards.

---

## 2. Section 1: Hero

**No changes to the existing hero section.** It already handles:
- Organization name (h1, `text-3xl font-bold`)
- Industry badge (`badge badge-primary badge-outline`)
- GitHub link (`btn btn-ghost btn-xs`)
- Description (`text-base-content/70 max-w-2xl`)
- Last updated timestamp (`text-xs text-base-content/40`)

---

## 3. Section 2: Health Overview (Sparkline Cards)

**Pattern source:** `templates/metrics/partials/key_metrics_cards.html`

### Layout

```html
<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
  <!-- 4 cards -->
</div>
```

### Card Structure (repeated 4x)

```html
<div class="stat bg-base-200 rounded-box p-4">
  <div class="stat-title text-xs">{METRIC_TITLE}</div>
  <div class="font-bold text-{COLOR} text-2xl md:text-3xl tabular-nums">
    {VALUE}
  </div>
  {% if sparkline_data %}
  <div class="h-12 mt-2">
    <canvas
      data-sparkline
      data-sparkline-values="{JSON_ARRAY}"
      data-sparkline-trend="{up|down|flat}"
      data-sparkline-metric="{METRIC_KEY}"
    ></canvas>
  </div>
  {% endif %}
  <div class="stat-desc flex items-center gap-2 mt-1 text-xs">
    {% if trend == "up" %}
      <span class="text-success">+{CHANGE}%</span>
    {% elif trend == "down" %}
      <span class="text-error">{CHANGE}%</span>
    {% else %}
      <span class="text-base-content/50">0%</span>
    {% endif %}
    <span class="text-base-content/50">monthly trend</span>
  </div>
</div>
```

### Card Definitions

| # | Title | Value Format | Color Class | Trend Inversion | Metric Key |
|---|-------|-------------|-------------|-----------------|------------|
| 1 | PRs Merged | `{N}` (integer, commaformatted) | `text-primary` | up=good | `prs_merged` |
| 2 | Median Cycle Time | `{N}h` (1 decimal) | `text-secondary` | down=good (invert) | `cycle_time` |
| 3 | AI Adoption | `{N}%` (1 decimal) | `text-accent` | up=good | `ai_adoption` |
| 4 | Median Review Time | `{N}h` (1 decimal) | `text-info` | down=good (invert) | `review_time` |

**Trend inversion note:** For Cycle Time and Review Time, a downward trend is positive (faster). The color logic is inverted:
- `trend == "down"` -> `text-success` (green, good)
- `trend == "up"` -> `text-error` (red, bad)

**Sparkline data source:** `monthly_trends` list, one value per month. The sparkline canvas is drawn by the existing `data-sparkline` JS handler from the dashboard. For the public page, this can either reuse the same JS or use a lightweight inline Chart.js sparkline.

**Label:** "monthly trend" (NOT "12-week trend" -- public data is monthly granularity).

### Responsive Behavior

| Breakpoint | Layout |
|-----------|--------|
| < 1024px (mobile/tablet) | 2 columns (`grid-cols-2`) |
| >= 1024px (desktop) | 4 columns (`lg:grid-cols-4`) |

The `stat` class with the DaisyUI overflow fix from `design-system.css` ensures values scale down on small screens via `clamp(1rem, 4vw, 1.5rem)`.

---

## 4. Section 3: Charts Row

**Pattern source:** Existing charts section in `org_detail.html`

### Layout

```html
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
  <!-- AI Adoption Over Time (existing, unchanged) -->
  <div class="card bg-base-100 border border-base-300">
    <div class="card-body p-5">
      <h2 class="card-title text-sm">AI Adoption Over Time</h2>
      <div class="h-64">
        <canvas id="public-ai-trend-chart"></canvas>
      </div>
    </div>
  </div>

  <!-- NEW: Cycle Time Trend -->
  <div class="card bg-base-100 border border-base-300">
    <div class="card-body p-5">
      <h2 class="card-title text-sm">Cycle Time Trend (Monthly)</h2>
      <div class="h-64">
        <canvas id="public-cycle-time-chart"></canvas>
      </div>
    </div>
  </div>
</div>
```

### Cycle Time Trend Chart Spec

- **Type:** `bar` (Chart.js)
- **Data:** Monthly median cycle time hours from `monthly_trends`
- **Bar color:** `#F97316` (primary/coral orange) -- consistent with brand
- **Y-axis:** Hours, `beginAtZero: true`, tick callback: `v + 'h'`
- **X-axis:** Month labels (e.g., "Jan 2026"), `grid: { display: false }`
- **Legend:** Hidden (`plugins: { legend: { display: false } }`)
- **Responsive:** `responsive: true, maintainAspectRatio: false`

```javascript
// Chart.js config for Cycle Time Trend
{
  type: 'bar',
  data: {
    labels: months,  // ["Jan 2026", "Feb 2026", ...]
    datasets: [{
      label: 'Median Cycle Time',
      data: cycleTimeValues,  // [24.5, 18.2, ...]
      backgroundColor: '#F97316',
      borderRadius: 4,
    }]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: {
        beginAtZero: true,
        ticks: { callback: function(v) { return v + 'h'; } }
      },
      x: { grid: { display: false } }
    }
  }
}
```

### Note on Existing PR Velocity Chart

The existing PR Velocity (stacked bar) chart is **replaced** by the Cycle Time Trend chart. The velocity data (total PRs, AI PRs by month) is already captured in the Health Overview sparklines for "PRs Merged". Having both a velocity bar chart and a PRs Merged sparkline is redundant. The Cycle Time Trend provides a new, non-redundant data dimension.

If the team wants to keep PR Velocity as well, it can be placed in a third card below the two-column chart row as a full-width chart.

---

## 5. Section 4: Last 10 PRs Table

**Pattern source:** `templates/metrics/partials/recent_prs_table.html` (simplified -- no Quality column, no dismiss button, no feedback modal)

### Layout

```html
<div class="card bg-base-100 border border-base-300 mb-8">
  <div class="card-body p-5">
    <h2 class="card-title text-sm mb-3">Recent Pull Requests</h2>
    <div class="overflow-x-auto">
      <table class="table table-sm">
        <thead>
          <tr>
            <th>Title</th>
            <th>Author</th>
            <th class="text-center">AI</th>
            <th class="text-right">Cycle Time</th>
            <th class="text-right">Merged</th>
          </tr>
        </thead>
        <tbody>
          {% for pr in recent_prs %}
          <tr>
            <td class="max-w-xs">
              <a href="{{ pr.url }}" target="_blank" rel="noopener noreferrer"
                 class="link link-hover line-clamp-1" title="{{ pr.title }}">
                {{ pr.title }}
              </a>
            </td>
            <td>
              <div class="flex items-center gap-2">
                <div class="avatar placeholder">
                  <div class="bg-neutral text-neutral-content rounded-full w-6">
                    <span class="text-xs">{{ pr.author_initials }}</span>
                  </div>
                </div>
                <span class="text-sm">{{ pr.author }}</span>
              </div>
            </td>
            <td class="text-center">
              {% if pr.is_ai_assisted %}
              <span class="badge badge-primary badge-sm">AI</span>
              {% else %}
              <span class="badge badge-ghost badge-sm">--</span>
              {% endif %}
            </td>
            <td class="text-right font-mono text-sm">
              {% if pr.cycle_time_hours %}
                {{ pr.cycle_time_hours|floatformat:1 }}h
              {% else %}
                --
              {% endif %}
            </td>
            <td class="text-right text-sm text-base-content/80 whitespace-nowrap">
              {{ pr.merged_at|timesince }} ago
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
</div>
```

### Column Definitions

| Column | Alignment | Content | Mobile Behavior |
|--------|-----------|---------|-----------------|
| Title | left | Linked PR title, `line-clamp-1`, `max-w-xs` | Horizontal scroll |
| Author | left | Avatar placeholder (initials) + name | Horizontal scroll |
| AI | center | `badge badge-primary badge-sm` "AI" or `badge badge-ghost badge-sm` "--" | Horizontal scroll |
| Cycle Time | right | `font-mono`, `{N}h` or "--" | Horizontal scroll |
| Merged | right | `timesince` ago, `whitespace-nowrap` | Horizontal scroll |

### Key Differences from Authenticated Table

- **No Quality column** -- not relevant for public view
- **No dismiss/feedback button** -- public pages are read-only
- **No filters** -- fixed to last 10 merged PRs
- **No `table-zebra`** -- using `table-sm` for compact density
- **AI column simplified** -- single badge instead of tool detection breakdown (tools are already shown in the AI Tools table below)

### Mobile

The `overflow-x-auto` wrapper enables horizontal scrolling on mobile. No columns are hidden; the table simply scrolls horizontally. This is the simplest approach for a 5-column table.

---

## 6. Section 5: Team Member Breakdown

**Pattern source:** `templates/metrics/partials/team_breakdown_table.html` (adapted for client-side sorting via Alpine.js)

### Layout

```html
<div class="card bg-base-100 border border-base-300 mb-8">
  <div class="card-body p-5">
    <h2 class="card-title text-sm mb-3">Team Member Breakdown</h2>
    <div class="overflow-x-auto"
         x-data="publicContributorSort()"
         x-init="init()">
      <table class="table table-sm">
        <thead>
          <tr>
            <th class="cursor-pointer hover:bg-base-300 select-none"
                @click="sortBy('name')">
              Contributor
              <span x-show="col === 'name'" x-text="dir === 'asc' ? '\u25B2' : '\u25BC'" class="ml-1"></span>
            </th>
            <th class="text-right cursor-pointer hover:bg-base-300 select-none"
                @click="sortBy('prs_merged')">
              PRs Merged
              <span x-show="col === 'prs_merged'" x-text="dir === 'asc' ? '\u25B2' : '\u25BC'" class="ml-1"></span>
            </th>
            <th class="text-right cursor-pointer hover:bg-base-300 select-none"
                @click="sortBy('avg_cycle_time')">
              Avg Cycle Time
              <span x-show="col === 'avg_cycle_time'" x-text="dir === 'asc' ? '\u25B2' : '\u25BC'" class="ml-1"></span>
            </th>
            <th class="text-right cursor-pointer hover:bg-base-300 select-none"
                @click="sortBy('ai_pct')">
              AI %
              <span x-show="col === 'ai_pct'" x-text="dir === 'asc' ? '\u25B2' : '\u25BC'" class="ml-1"></span>
            </th>
            <th class="text-right cursor-pointer hover:bg-base-300 select-none hidden md:table-cell"
                @click="sortBy('reviews_given')">
              Reviews Given
              <span x-show="col === 'reviews_given'" x-text="dir === 'asc' ? '\u25B2' : '\u25BC'" class="ml-1"></span>
            </th>
          </tr>
        </thead>
        <tbody>
          <template x-for="row in sorted" :key="row.name">
            <tr>
              <td>
                <div class="flex items-center gap-2">
                  <div class="avatar placeholder">
                    <div class="bg-neutral text-neutral-content rounded-full w-7">
                      <span class="text-xs" x-text="row.initials"></span>
                    </div>
                  </div>
                  <span class="text-sm font-medium" x-text="row.name"></span>
                </div>
              </td>
              <td class="text-right font-mono" x-text="row.prs_merged"></td>
              <td class="text-right font-mono">
                <span x-text="row.avg_cycle_time ? row.avg_cycle_time.toFixed(1) + 'h' : '--'"></span>
              </td>
              <td class="text-right">
                <template x-if="row.ai_pct !== null">
                  <span class="badge badge-info badge-sm" x-text="Math.round(row.ai_pct) + '%'"></span>
                </template>
                <template x-if="row.ai_pct === null">
                  <span class="text-base-content/70">--</span>
                </template>
              </td>
              <td class="text-right font-mono hidden md:table-cell" x-text="row.reviews_given || 0"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</div>
```

### Alpine.js Sort Component

```javascript
// Register in alpine.js or inline in page_js block
function publicContributorSort() {
  return {
    col: 'prs_merged',
    dir: 'desc',
    rows: [],
    init() {
      var el = document.getElementById('public-contributor-data');
      if (el) this.rows = JSON.parse(el.textContent);
    },
    get sorted() {
      var c = this.col, d = this.dir;
      return [...this.rows].sort(function(a, b) {
        var va = a[c], vb = b[c];
        if (typeof va === 'string') {
          va = va.toLowerCase(); vb = vb.toLowerCase();
        }
        if (va === null || va === undefined) return 1;
        if (vb === null || vb === undefined) return -1;
        if (va < vb) return d === 'asc' ? -1 : 1;
        if (va > vb) return d === 'asc' ? 1 : -1;
        return 0;
      });
    },
    sortBy(column) {
      if (this.col === column) {
        this.dir = this.dir === 'asc' ? 'desc' : 'asc';
      } else {
        this.col = column;
        this.dir = column === 'name' ? 'asc' : 'desc';
      }
    }
  };
}
```

Data is passed via `json_script`:
```html
{{ contributor_breakdown|json_script:"public-contributor-data" }}
```

### Column Definitions

| Column | Alignment | Mobile | Sort Default |
|--------|-----------|--------|-------------|
| Contributor | left | always visible | asc (A-Z) |
| PRs Merged | right | always visible | desc (highest first) |
| Avg Cycle Time | right | always visible | asc (fastest first) |
| AI % | right | always visible | desc (highest first) |
| Reviews Given | right | `hidden md:table-cell` | desc (most first) |

### Avatar Placeholder

Uses the DaisyUI `avatar placeholder` pattern with initials:
```html
<div class="avatar placeholder">
  <div class="bg-neutral text-neutral-content rounded-full w-7">
    <span class="text-xs">JD</span>
  </div>
</div>
```
This matches the existing dashboard pattern from `team_breakdown_table.html` and `recent_prs_table.html`.

---

## 7. Section 6: Quality & Review (Side by Side)

### Layout

```html
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
  <!-- Left: Quality Indicators -->
  <div class="card bg-base-100 border border-base-300">
    <div class="card-body p-5">
      <h2 class="card-title text-sm mb-3">Code Quality Indicators</h2>
      <!-- 3 stat cards in a column -->
    </div>
  </div>

  <!-- Right: Review Distribution -->
  <div class="card bg-base-100 border border-base-300">
    <div class="card-body p-5">
      <h2 class="card-title text-sm mb-3">Top Reviewers</h2>
      <!-- Reviewer table -->
    </div>
  </div>
</div>
```

### Left: Quality Indicators

```html
<div class="space-y-3">
  <!-- Revert Rate -->
  <div class="stat bg-base-200 rounded-lg p-3">
    <div class="flex items-center justify-between">
      <div>
        <div class="stat-title text-xs">Revert Rate</div>
        <div class="font-bold text-lg font-mono">
          {{ quality.revert_pct|floatformat:1 }}%
        </div>
      </div>
      {% if quality.revert_pct > 10 %}
        <span class="badge badge-error badge-sm">High</span>
      {% elif quality.revert_pct > 5 %}
        <span class="badge badge-warning badge-sm">Medium</span>
      {% else %}
        <span class="badge badge-success badge-sm">Low</span>
      {% endif %}
    </div>
  </div>

  <!-- Hotfix Rate -->
  <div class="stat bg-base-200 rounded-lg p-3">
    <div class="flex items-center justify-between">
      <div>
        <div class="stat-title text-xs">Hotfix Rate</div>
        <div class="font-bold text-lg font-mono">
          {{ quality.hotfix_pct|floatformat:1 }}%
        </div>
      </div>
      {% if quality.hotfix_pct > 10 %}
        <span class="badge badge-error badge-sm">High</span>
      {% elif quality.hotfix_pct > 5 %}
        <span class="badge badge-warning badge-sm">Medium</span>
      {% else %}
        <span class="badge badge-success badge-sm">Low</span>
      {% endif %}
    </div>
  </div>

  <!-- CI Pass Rate -->
  <div class="stat bg-base-200 rounded-lg p-3">
    <div class="flex items-center justify-between">
      <div>
        <div class="stat-title text-xs">CI Pass Rate</div>
        <div class="font-bold text-lg font-mono">
          {% if quality.ci_pass_rate is not None %}
            {{ quality.ci_pass_rate|floatformat:1 }}%
          {% else %}
            --
          {% endif %}
        </div>
      </div>
      {% if quality.ci_pass_rate >= 95 %}
        <span class="badge badge-success badge-sm">Excellent</span>
      {% elif quality.ci_pass_rate >= 80 %}
        <span class="badge badge-info badge-sm">Good</span>
      {% elif quality.ci_pass_rate is not None %}
        <span class="badge badge-warning badge-sm">Needs work</span>
      {% endif %}
    </div>
  </div>
</div>
<div class="text-center text-xs text-base-content/50 mt-2">
  Based on {{ quality.total_prs }} merged PRs
</div>
```

### Right: Review Distribution

Adapted from `review_distribution_chart.html` -- uses a table format instead of progress bars for the public page (more data-dense, consistent with other tables on the page).

```html
<div class="overflow-x-auto">
  <table class="table table-sm">
    <thead>
      <tr>
        <th>Reviewer</th>
        <th class="text-right">Reviews</th>
        <th class="text-right">Avg Response</th>
        <th class="text-right">Approval %</th>
      </tr>
    </thead>
    <tbody>
      {% for reviewer in review_distribution %}
      <tr>
        <td>
          <div class="flex items-center gap-2">
            <div class="avatar placeholder">
              <div class="bg-neutral text-neutral-content rounded-full w-6">
                <span class="text-xs">{{ reviewer.initials }}</span>
              </div>
            </div>
            <span class="text-sm">{{ reviewer.name }}</span>
          </div>
        </td>
        <td class="text-right font-mono">{{ reviewer.review_count }}</td>
        <td class="text-right font-mono text-sm">
          {% if reviewer.avg_response_hours %}
            {{ reviewer.avg_response_hours|floatformat:1 }}h
          {% else %}
            --
          {% endif %}
        </td>
        <td class="text-right">
          {% if reviewer.approval_rate %}
            <span class="text-sm font-mono">{{ reviewer.approval_rate|floatformat:0 }}%</span>
          {% else %}
            --
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
```

### Responsive Behavior

| Breakpoint | Layout |
|-----------|--------|
| < 1024px | Single column, quality stacks above review distribution |
| >= 1024px | Side by side (`lg:grid-cols-2`) |

---

## 8. Section 7: Engineering Insights

**Pattern source:** `templates/metrics/partials/insights_panel.html` (read-only adaptation)

### Layout

```html
{% if insights %}
<div class="card bg-base-100 border border-base-300 mb-8">
  <div class="card-body p-5">
    <h2 class="card-title text-sm mb-3">Engineering Insights (Last 30 Days)</h2>
    <div class="space-y-3">
      {% for insight in insights|slice:":5" %}
      <div class="alert {% if insight.priority == 'high' %}alert-warning{% elif insight.priority == 'medium' %}alert-info{% else %}alert-success{% endif %}">
        <div class="flex-1">
          <h3 class="font-semibold text-sm">{{ insight.title }}</h3>
          <p class="text-sm mt-1 text-base-content/80">{{ insight.description }}</p>
          <div class="flex gap-2 mt-2">
            <span class="badge badge-sm badge-outline">{{ insight.category }}</span>
          </div>
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
</div>
{% endif %}
```

### Key Differences from Authenticated Insights

- **No dismiss button** -- public pages are read-only
- **No AI Summary card** -- requires authenticated context
- **No Q&A form** -- public visitors cannot ask questions
- **Max 5 insights** -- via `|slice:":5"` filter
- **Section title:** "Engineering Insights (Last 30 Days)"
- **Priority badge removed** -- color already encodes priority:
  - `high` -> `alert-warning` (amber background)
  - `medium` -> `alert-info` (blue background)
  - `low` -> `alert-success` (teal/green background)
- **Category badge kept** as `badge-outline` for context without visual weight

### Empty State

When no insights are available, the entire section is hidden (`{% if insights %}`). No empty state message needed.

---

## 9. Section 8: AI Tools + Methodology + Similar

These three existing sections remain unchanged in structure. They follow the enhanced sections:

1. **AI Tools Table** -- `{% if ai_tools %}` card with tool/count/percentage table
2. **Methodology** -- `{% include "public/_methodology.html" %}`
3. **Similar Orgs** -- Link to industry page

No design changes needed.

---

## 10. Responsive Breakpoints Summary

| Breakpoint | Width | Affected Sections |
|-----------|-------|-------------------|
| Default (mobile) | < 768px | All grids collapse to 1 col; tables scroll horizontally; Health Overview is 2 cols |
| `md` (768px) | >= 768px | Reviews Given column visible; stat values slightly larger |
| `lg` (1024px) | >= 1024px | Health Overview -> 4 cols; Charts -> 2 cols; Quality/Review -> 2 cols |

### Mobile-Specific Patterns

- **Tables:** `overflow-x-auto` wrapper, no column hiding (except Reviews Given at < md)
- **Cards:** Full width, natural stacking
- **Charts:** Full width, h-64 height maintained
- **Sparklines:** h-12 maintained, touch-friendly

---

## 11. Color & Typography Reference

### DaisyUI Semantic Colors Used

| Token | Usage in This Page |
|-------|--------------------|
| `primary` (#F97316) | PRs Merged value, AI badge, chart bars, links |
| `secondary` (#ffe96e dark / #FDA4AF light) | Cycle Time value |
| `accent` (#5a9997 dark / #10B981 light) | AI Adoption value |
| `info` (#60A5FA) | Review Time value, medium-priority insights, AI % badges |
| `success` | Positive trends, low revert/hotfix rate, low-priority insights |
| `warning` | Medium revert/hotfix rate, high-priority insights |
| `error` | Negative trends, high revert/hotfix rate |
| `base-100` | Card backgrounds |
| `base-200` | Stat card backgrounds, footer rows |
| `base-300` | Borders |
| `base-content` | Primary text |
| `base-content/70` | Muted text |
| `base-content/50` | Trend labels, footnotes |
| `neutral` | Avatar placeholder backgrounds |
| `neutral-content` | Avatar placeholder text |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Section titles (`card-title`) | DM Sans | `text-sm` (0.875rem) | semibold |
| Stat values | DM Sans | `text-2xl md:text-3xl` | bold |
| Table headers | DM Sans | Inherited from `table-sm` | semibold |
| Data values | JetBrains Mono (`font-mono`) | `text-sm` | normal |
| Stat labels (`stat-title`) | DM Sans | `text-xs` (0.7rem via override) | normal |
| Trend percentages | DM Sans | `text-xs` | normal |
| Timestamps | DM Sans | `text-sm` | normal |

---

## 12. Data Dependencies

Each new section requires data from the view context. Here is what the view must provide:

### New Context Variables Needed

| Variable | Type | Section | Source |
|----------|------|---------|--------|
| `sparklines` | dict of sparkline objects | Health Overview | New: compute from `monthly_trends` |
| `recent_prs` | list of 10 PR dicts | Last 10 PRs | New: query last 10 merged PRs |
| `contributor_breakdown` | list of contributor dicts | Team Breakdown | New: aggregate by author |
| `quality` | dict with revert_pct, hotfix_pct, ci_pass_rate, total_prs | Quality | New: compute from PR data |
| `review_distribution` | list of reviewer dicts | Review Distribution | New: aggregate review data |
| `insights` | list of insight objects | Insights | New: generate/fetch insights |

### Existing Context Variables (unchanged)

| Variable | Type | Section |
|----------|------|---------|
| `profile` | PublicOrgProfile | Hero |
| `summary` | dict | Hero + Health Overview |
| `monthly_trends` | list of month dicts | Charts + Sparklines |
| `ai_tools` | list of tool dicts | AI Tools table |

### Sparkline Data Shape

Each sparkline in the `sparklines` dict should match the existing dashboard format:

```python
{
    "prs_merged": {
        "values": "[10, 15, 12, 18, 22, ...]",  # JSON array string
        "trend": "up",       # "up", "down", or "flat"
        "change_pct": 12.5,  # percentage change
    },
    "cycle_time": { ... },
    "ai_adoption": { ... },
    "review_time": { ... },
}
```

### Contributor Breakdown Data Shape

```python
[
    {
        "name": "Jane Doe",
        "initials": "JD",
        "prs_merged": 42,
        "avg_cycle_time": 18.5,  # hours, nullable
        "ai_pct": 65.0,         # percentage, nullable
        "reviews_given": 28,     # integer
    },
    ...
]
```

### Quality Data Shape

```python
{
    "revert_pct": 2.1,
    "hotfix_pct": 4.3,
    "ci_pass_rate": 94.5,  # nullable if no CI data
    "total_prs": 1234,
}
```

### Review Distribution Data Shape

```python
[
    {
        "name": "John Smith",
        "initials": "JS",
        "review_count": 45,
        "avg_response_hours": 3.2,  # nullable
        "approval_rate": 87.0,      # percentage, nullable
    },
    ...  # top 8 reviewers
]
```

### Recent PRs Data Shape

```python
[
    {
        "title": "Fix authentication flow for SSO",
        "url": "https://github.com/org/repo/pull/123",
        "author": "janedoe",
        "author_initials": "JD",
        "is_ai_assisted": True,
        "cycle_time_hours": 18.5,  # nullable
        "merged_at": datetime(...),
    },
    ...  # 10 items
]
```

---

## Implementation Notes

1. **No `{% trans %}` or `gettext_lazy`** -- per CLAUDE.md, i18n is disabled. Use plain strings.

2. **No inline `<script>` in HTMX partials** -- per FRONTEND-PATTERNS.md. However, the public page is a full page (not an HTMX partial), so the `{% block page_js %}` approach used currently is fine. The Alpine.js sort component should be registered via `Alpine.data()` if possible, or defined in the page_js block as a standalone function.

3. **Chart.js CDN** -- the existing page already loads Chart.js from CDN in `{% block page_js %}`. The Cycle Time chart initialization should be added alongside the existing AI Adoption and Velocity chart code.

4. **Data serialization** -- use Django's `|json_script` filter for all data passed to JavaScript (sparklines, contributor breakdown, chart data). This prevents XSS and is the established pattern.

5. **Empty states** -- sections with no data should be hidden entirely (`{% if variable %}`), not show empty state messages. This keeps the public page clean and only shows what data is available.

6. **No HTMX** -- the public org detail page is fully server-rendered on initial load. No HTMX partial loading. All sorting is client-side via Alpine.js. This ensures the page is fully indexable by search engines and fast to load.
