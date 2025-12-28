# Report Template Refactoring Plan

**Last Updated: 2025-12-28**

## Executive Summary

Refactor the monolithic `docs/index.html` (185KB, 3766 lines) into a Jinja2-based template system. This enables:
- Claude Code to work on individual sections (each < 200 lines)
- Data-driven report generation from existing CSV exports
- Maintainable, professional template architecture

## Problem Statement

The current `docs/index.html` file exceeds Claude Code's context window (~2000 lines max), making it impossible to read the full file for edits. Previous attempt to split with Jinja templates broke styles.

## Current State Analysis

### File Structure (3766 lines total)

| Section | Lines | Size | Content |
|---------|-------|------|---------|
| Head + CSS | 1-500 | ~500 lines | Tailwind config, CSS variables, custom styles |
| Header HTML | 500-1500 | ~1000 lines | Stat cards, navigation, intro content |
| Content sections | 1500-2756 | ~1250 lines | 17 named `<section>` blocks |
| Footer | 2756-2800 | ~50 lines | Disclaimers, links, legal |
| JavaScript | 2800-3766 | ~966 lines | Theme, data arrays, 13 Chart.js charts |

### Existing Infrastructure

- **Data export**: `docs/scripts/export_report_data.py` exports to CSV
- **CSV files**: `docs/data/*.csv` (team_summary, monthly_trends, ai_tools_monthly, etc.)
- **No templates**: Previous Jinja attempt was incomplete/broken

### 17 Content Sections (by ID)

1. `tldr` - TL;DR summary
2. `about` - About the research
3. `stats` - Statistical confidence
4. `trend-2025` - AI adoption trend
5. `takeaways` - Key takeaways
6. `summary` - Executive summary
7. `tools` - AI tool evolution
8. `ai-categories` - Code AI vs Review AI
9. `by-team` - Adoption by team
10. `impact` - AI impact on metrics
11. `monthly` - Monthly trends
12. `data` - Complete team data table
13. `detection` - Detection method comparison
14. `correlations` - AI adoption correlations
15. `methodology` - Methodology details
16. `industry` - Industry context
17. `action` - CTA section

### 13 Chart.js Charts

1. `overallTrend` - Overall AI adoption %
2. `toolTrends` - Tool usage over time
3. `categoryTrends` - Category breakdown over time
4. `toolShare` - Tool market share doughnut
5. `teamAdoption` - Team adoption bar chart
6. `reviewImpact` - Review time impact
7. `cycleImpact` - Cycle time impact
8. `monthlyTrend` - Monthly team trends
9. `teamDetection` - Detection improvement by team
10. `prType` - Correlation by PR type
11. `techCategory` - Correlation by tech category
12. `prSize` - Correlation by PR size
13. `teamStructure` - Correlation by team structure

## Proposed Future State

### Directory Structure

```
docs/
├── index.html                    # GENERATED (gitignored)
├── data/                         # Existing CSV exports
│   ├── team_summary.csv
│   ├── monthly_trends.csv
│   └── ...
├── scripts/
│   ├── export_report_data.py     # Existing
│   └── build_report.py           # NEW: Template renderer
└── templates/
    ├── base.html.j2              # HTML skeleton + head
    ├── styles.css.j2             # All CSS (~500 lines)
    ├── sections/
    │   ├── header.html.j2
    │   ├── tldr.html.j2
    │   ├── about.html.j2
    │   ├── stats.html.j2
    │   ├── trend_2025.html.j2
    │   ├── takeaways.html.j2
    │   ├── summary.html.j2
    │   ├── tools.html.j2
    │   ├── ai_categories.html.j2
    │   ├── by_team.html.j2
    │   ├── impact.html.j2
    │   ├── monthly.html.j2
    │   ├── data_table.html.j2
    │   ├── detection.html.j2
    │   ├── correlations.html.j2
    │   ├── methodology.html.j2
    │   ├── industry.html.j2
    │   ├── cta.html.j2
    │   └── footer.html.j2
    └── scripts/
        ├── theme.js.j2
        ├── chart_utils.js.j2
        └── charts/
            ├── overall_trend.js.j2
            ├── tool_trends.js.j2
            ├── category_trends.js.j2
            ├── tool_share.js.j2
            ├── team_adoption.js.j2
            ├── review_impact.js.j2
            ├── cycle_impact.js.j2
            ├── monthly_trend.js.j2
            ├── team_detection.js.j2
            ├── pr_type.js.j2
            ├── tech_category.js.j2
            ├── pr_size.js.j2
            └── team_structure.js.j2
```

## Implementation Phases

### Phase 1: Infrastructure Setup (Effort: M)

Create the build script and base template structure.

**Tasks:**
1. Create directory structure
2. Write `build_report.py` with Jinja2 rendering
3. Create `base.html.j2` skeleton
4. Verify build produces valid HTML

### Phase 2: CSS Extraction (Effort: S)

Extract CSS while preserving CSS variables and avoiding breakage.

**Tasks:**
1. Extract `<style>` content to `styles.css.j2`
2. Wrap in `{% raw %}` to prevent Jinja escaping
3. Test CSS variables work correctly
4. Verify theme switching still works

### Phase 3: Section Extraction (Effort: L)

Extract 19 HTML sections (header + 17 content + footer).

**Tasks:**
1. Extract header section
2. Extract each content section (17 total)
3. Extract footer section
4. Keep inline `style=""` attributes intact

### Phase 4: JavaScript Extraction (Effort: L)

Extract theme code and 13 chart definitions.

**Tasks:**
1. Extract theme management to `theme.js.j2`
2. Extract chart utilities to `chart_utils.js.j2`
3. Extract each chart to individual file
4. Inject data via `{{ data | tojson }}`

### Phase 5: Finalization (Effort: S)

Complete integration and documentation.

**Tasks:**
1. Add `make build-report` target
2. Add `docs/index.html` to `.gitignore`
3. Test full build cycle
4. Verify visual output matches original

## CSS Handling Strategy

**Previous Issue**: Styles broke when splitting templates.

**Root Causes & Fixes:**

1. **Inline styles in sections**
   - Keep `style="..."` attributes intact in section templates
   - Don't extract to external CSS

2. **CSS variable dependencies**
   - CSS uses `var(--bg-card)`, `var(--text)`, etc.
   - Keep all variables in single `<style>` block in `<head>`
   - CSS must remain inline (not external file)

3. **Template escaping**
   - Jinja may escape `{` and `}` characters
   - Use `{% raw %}...{% endraw %}` around CSS
   - Or load CSS file as raw text

**Decision**: Keep CSS as single `styles.css.j2` file with `{% raw %}` wrapper.

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| CSS breaks again | High | Medium | Use `{% raw %}`, test incrementally |
| Chart data injection fails | High | Low | Test with simple chart first |
| Build script complexity | Medium | Low | Keep simple, use existing patterns |
| Output differs from original | High | Medium | Diff test before committing |

## Success Metrics

1. **Build works**: `make build-report` produces valid HTML
2. **Visual parity**: Generated HTML renders identically to original
3. **Template size**: Each template < 200 lines
4. **Maintainability**: Can edit single section without full file context

## Required Resources

- Python 3.12+ (existing)
- Jinja2 library (existing in Django)
- No new dependencies needed

## Dependencies

- Existing `export_report_data.py` for CSV data
- Existing CSV files in `docs/data/`
- No Django app changes required
