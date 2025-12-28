# Report Template Refactoring - Context

**Last Updated: 2025-12-28**

## Key Files

### Source Files (Read-Only Reference)

| File | Purpose | Lines |
|------|---------|-------|
| `docs/index.html` | Original monolithic report | 3766 |
| `docs/scripts/export_report_data.py` | Data export script | 637 |
| `docs/data/team_summary.csv` | Team metrics (76 teams) | 76 |
| `docs/data/monthly_trends.csv` | Monthly AI adoption | - |
| `docs/data/ai_tools_monthly.csv` | Tool usage by month | - |
| `docs/data/ai_categories.csv` | Code AI vs Review AI | - |
| `docs/data/overall_stats.txt` | Headline numbers | - |

### Files to Create

| File | Purpose | Est. Lines |
|------|---------|------------|
| `docs/scripts/build_report.py` | Template renderer | ~80 |
| `docs/templates/base.html.j2` | HTML skeleton | ~100 |
| `docs/templates/styles.css.j2` | All CSS | ~500 |
| `docs/templates/sections/*.html.j2` | 19 section partials | 30-150 each |
| `docs/templates/scripts/*.js.j2` | JS partials | 50-200 each |

### Files to Modify

| File | Change |
|------|--------|
| `.gitignore` | Add `docs/index.html` |
| `Makefile` | Add `build-report` target |

## Critical Decisions

### Decision 1: Template Engine

**Choice**: Jinja2 (standalone, not Django templates)

**Rationale**:
- Already available in Python environment
- Similar syntax to Django templates (familiar)
- Supports `{% raw %}` for CSS/JS escaping
- No Django app context required

### Decision 2: CSS Handling

**Choice**: Single `styles.css.j2` file with `{% raw %}` wrapper

**Rationale**:
- Previous attempt broke styles by splitting CSS
- CSS variables (`var(--X)`) need to be in one block
- Inline `style=""` attributes stay in section templates
- No external CSS file (must be inline for hosting)

### Decision 3: Data Injection

**Choice**: Load CSVs → Python dict → Jinja context

**Rationale**:
- Data already exported to CSV by existing script
- Python handles CSV parsing naturally
- Jinja's `{{ data | tojson }}` for JS injection
- Single source of truth (CSVs)

### Decision 4: Generated File Handling

**Choice**: Gitignore `docs/index.html`

**Rationale**:
- Report hosted on public domain (not GitHub Pages)
- Templates are source of truth
- Build on deploy or locally

## Section Line Ranges (in original file)

Use these to extract sections:

| Section ID | Start Line | End Line | Approx Lines |
|------------|------------|----------|--------------|
| CSS `<style>` | ~70 | ~500 | ~430 |
| Header | ~500 | ~1500 | ~1000 |
| `tldr` | 1502 | 1593 | 91 |
| `about` | 1596 | 1627 | 31 |
| `stats` | 1630 | 1690 | 60 |
| `trend-2025` | 1693 | 1724 | 31 |
| `takeaways` | 1727 | 1760 | 33 |
| `summary` | 1762 | 1798 | 36 |
| `tools` | 1801 | 1840 | 39 |
| `ai-categories` | 1843 | 1983 | 140 |
| `by-team` | 1985 | 1998 | 13 |
| `impact` | 2000 | 2018 | 18 |
| `monthly` | 2020 | 2060 | 40 |
| `data` | 2062 | 2140 | 78 |
| `detection` | 2143 | 2410 | 267 |
| `correlations` | 2413 | 2507 | 94 |
| `methodology` | 2510 | 2554 | 44 |
| `industry` | 2557 | 2712 | 155 |
| `action` | 2715 | 2756 | 41 |
| Footer | 2757 | 2800 | ~43 |
| JavaScript | 2800 | 3766 | ~966 |

## Chart Definitions (in JavaScript section)

| Chart Name | Line | Description |
|------------|------|-------------|
| `overallTrend` | 2948 | Overall AI adoption % |
| `toolTrends` | 3003 | Tool usage by month |
| `categoryTrends` | 3041 | Category breakdown |
| `toolShare` | 3066 | Tool market share doughnut |
| `teamAdoption` | 3088 | Team adoption bar |
| `reviewImpact` | 3126 | Review time impact |
| `cycleImpact` | 3160 | Cycle time impact |
| `monthlyTrend` | 3305 | Monthly team trends |
| `teamDetection` | 3351 | Detection by team |
| `prType` | 3436 | PR type correlation |
| `techCategory` | 3482 | Tech category correlation |
| `prSize` | 3526 | PR size correlation |
| `teamStructure` | 3568 | Team structure correlation |

## Data Variables Needed

### From team_summary.csv

```python
team_data = [
    {"team": "Plane", "total": 1717, "ai_pct": 85.6, "cycle_delta": 75, ...},
    ...
]
```

### From ai_tools_monthly.csv

```python
tool_trends = {
    "2025-01": {"coderabbit": 272, "chatgpt": 5, ...},
    ...
}
```

### From overall_stats.txt

```python
overall_stats = {
    "all_teams": 100,
    "all_prs": 167000,
    "ai_pct": 12.1,
    ...
}
```

## CSS Variables Reference

The CSS uses these custom properties (defined in `:root` and theme selectors):

```css
/* Colors */
--primary: #F97316;
--secondary: #5a9997;
--success: #22c55e;
--warning: #eab308;
--error: #ef4444;
--purple: #a855f7;

/* Theme-dependent */
--bg-main, --bg-card, --text, --text-muted, --border, --grid
```

## Commands

```bash
# Export fresh data from database
.venv/bin/python docs/scripts/export_report_data.py

# Build report from templates
.venv/bin/python docs/scripts/build_report.py

# Or via Makefile (after implementation)
make build-report
```

## Related Documentation

- Original plan: `.claude/plans/transient-pondering-blanket.md`
- CLAUDE.md for coding guidelines
- Jinja2 docs: https://jinja.palletsprojects.com/
