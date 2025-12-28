# Report Template System

This directory contains Jinja2 templates for generating the public AI Impact Report (`docs/index.html`).

## Quick Start

```bash
# Build the report
make build-report

# Or directly
.venv/bin/python docs/scripts/build_report.py
```

## File Structure

```
docs/
├── index.html              # Generated output (186 KB)
├── data/                   # CSV data files (source of truth)
│   ├── team_summary.csv    # Team metrics
│   ├── monthly_trends.csv  # Monthly PR counts
│   ├── ai_categories.csv   # Code AI vs Review AI breakdown
│   ├── ai_tools_monthly.csv# Tool usage by month
│   └── overall_stats.txt   # Aggregate statistics
├── scripts/
│   ├── build_report.py     # Template renderer
│   └── export_report_data.py # Exports data from DB to CSVs
└── templates/
    ├── base.html.j2        # HTML skeleton
    ├── content.html.j2     # All HTML sections
    ├── scripts.js.j2       # All JavaScript
    └── styles.css.j2       # All CSS
```

## Template Files

### `base.html.j2` (~85 lines)
The HTML skeleton containing:
- Early theme detection script (prevents flash of wrong theme)
- Tailwind CSS configuration
- Font imports
- Data injection (`teamData`, `toolTrends`)
- Includes for content, scripts, and styles

### `content.html.j2` (~1340 lines)
All HTML content including:
- Navigation sidebar (TOC)
- Header with stats cards
- 17 content sections (TL;DR, About, Stats, Charts, Data Table, etc.)
- Footer

### `scripts.js.j2` (~890 lines)
All JavaScript including:
- Theme management (`toggleTheme()`, `applyTheme()`, `getColors()`)
- 13 Chart.js chart configurations
- Alpine.js `teamTable()` component for sortable data table
- UI interactions (TOC toggle, scroll spy, progress bar, back-to-top)

### `styles.css.j2` (~1350 lines)
All CSS including:
- CSS variables for dark/light themes
- Layout styles (sidebar, main content, cards)
- Chart container styles
- Responsive breakpoints
- Print styles

## Data Context

The build script loads CSV files and passes them to templates as `data`:

```python
data = {
    "team_summary": [...],      # List of team dicts
    "monthly_trends": [...],    # Monthly PR data
    "ai_categories": [...],     # Code AI vs Review AI
    "tool_trends": {...},       # {month: {tool: count}}
    "overall_stats": {...},     # Aggregate stats
    "team_data_js": [...],      # JS-friendly team format
    "generated_at": "...",      # Timestamp
}
```

### Team Data Structure
```javascript
// Available as `teamData` in scripts.js.j2
[
  {
    "team": "Rallly",
    "total": 525,
    "ai_pct": 89.7,
    "cycle_delta": 101,  // % change vs non-AI PRs
    "review_delta": 900,
    "size_delta": -74
  },
  // ...74 teams total
]
```

### Tool Trends Structure
```javascript
// Available as `toolTrends` in scripts.js.j2
{
  "2025-01": {"coderabbit": 450, "cursor": 12, ...},
  "2025-02": {"coderabbit": 520, "cursor": 18, ...},
  // ...12 months
}
```

## Adding/Editing Charts

Charts are defined in `scripts.js.j2`. Each chart follows this pattern:

```javascript
charts.chartName = new Chart(document.getElementById('chartNameChart'), {
    type: 'bar',  // or 'line', 'doughnut', etc.
    data: {
        labels: [...],
        datasets: [{
            label: 'Label',
            data: [...],
            backgroundColor: colors.primary,  // Use theme-aware colors
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { labels: { color: colors.text } },  // Theme-aware
            datalabels: { ... }  // ChartDataLabels plugin
        },
        scales: {
            x: { ticks: { color: colors.text }, grid: { color: colors.grid } },
            y: { ticks: { color: colors.text }, grid: { color: colors.grid } }
        }
    }
});
```

### Theme-Aware Colors
Always use the `colors` object for theme compatibility:
```javascript
const colors = getColors();
// colors.text - text color (adapts to theme)
// colors.muted - secondary text
// colors.grid - chart grid lines
// colors.primary - #F97316 (orange)
// colors.success - #22c55e (green)
// colors.error - #ef4444 (red)
```

### Chart Canvas in HTML
Add the canvas element in `content.html.j2`:
```html
<div class="chart-container" style="height: 400px;">
    <canvas id="chartNameChart"></canvas>
</div>
```

## Adding New Sections

1. Add HTML in `content.html.j2`:
```html
<section id="section-id" class="content-section">
    <h2>Section Title</h2>
    <!-- Content -->
</section>
```

2. Add TOC entry (also in `content.html.j2`):
```html
<li><a href="#section-id">
    <span class="nav-number">17</span>Section Title
</a></li>
```

3. If section has a chart, add chart config to `scripts.js.j2`

## Theme System

The report supports dark/light themes via CSS variables:

```css
/* In styles.css.j2 */
:root, [data-theme="dark"] {
    --bg: #1e1e1e;
    --text: #ccc9c0;
    --card-bg: #2a2a28;
    /* ... */
}

[data-theme="light"] {
    --bg: #f8f9fa;
    --text: #1f2937;
    --card-bg: #ffffff;
    /* ... */
}
```

Theme is controlled by `data-theme` attribute on `<html>`:
- Set early in `<head>` to prevent flash
- Toggled via `toggleTheme()` function
- Persisted in `localStorage`

## Common Gotchas

### 1. Variable Scope in JavaScript
Variables used in charts must be defined before the chart configuration:
```javascript
// GOOD: Define before use
const sortedTeams = [...teamData].sort((a, b) => b.ai_pct - a.ai_pct);
charts.teamAdoption = new Chart(..., { data: sortedTeams.map(...) });

// BAD: Using undefined variable
charts.teamAdoption = new Chart(..., { data: sortedTeams.map(...) });  // Error!
const sortedTeams = ...;  // Defined too late
```

### 2. Alpine.js Load Order
Alpine.js must load AFTER functions it uses are defined:
```html
<!-- In base.html.j2 -->
<script>
    {% include 'scripts.js.j2' %}  <!-- Defines teamTable() -->
</script>
<script defer src="alpine.js"></script>  <!-- Loads after -->
```

### 3. Chart Colors on Theme Change
Charts need color updates when theme changes:
```javascript
function updateChartColors() {
    const colors = getColors();
    Object.values(charts).forEach(chart => {
        // Update axis colors, legend colors, etc.
        chart.update();
    });
}
```

### 4. Jinja2 in JavaScript
Use `{{ }}` for data injection but be careful with JSON:
```javascript
// GOOD: Use tojson filter
const data = {{ tojson(data.team_data_js) }};

// BAD: Raw output may break
const data = {{ data.team_data_js }};  // Python repr, not JSON
```

## Updating Data

To refresh data from the database:

```bash
# Export fresh data to CSVs
.venv/bin/python docs/scripts/export_report_data.py

# Rebuild report with new data
make build-report
```

## Testing Changes

1. Make template edits
2. Run `make build-report`
3. Open `docs/index.html` in browser
4. Test:
   - All charts render
   - Theme toggle works
   - Data table sorts correctly
   - TOC navigation works
   - Responsive layout on mobile

## Deployment

The `docs/index.html` is a standalone file that can be:
- Served directly from any web server
- Hosted on GitHub Pages
- Shared as a single HTML file

No build step needed for viewing - all CSS/JS is inline.
