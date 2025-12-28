# Report Template Refactoring - Tasks

**Last Updated: 2025-12-28**

## Phase 1: Infrastructure Setup

- [x] Create directory structure (`docs/templates/sections/`, `docs/templates/scripts/charts/`)
- [x] Write `build_report.py` script
  - [x] Load CSV data into context dict
  - [x] Setup Jinja2 environment
  - [x] Render base template
  - [x] Write to `docs/index.html`
- [x] Create minimal `base.html.j2` skeleton
- [x] Verify build runs without errors

**Acceptance Criteria:**
- Running `python docs/scripts/build_report.py` produces valid HTML
- No Jinja2 errors during rendering

---

## Phase 2: CSS Extraction

- [x] Extract `<style>` content (lines ~70-500) to `styles.css.j2`
- [x] Include CSS in `base.html.j2` via `{% include %}`
- [x] Test dark/light theme toggle works (build successful)

**Acceptance Criteria:**
- CSS variables (`var(--X)`) work correctly
- Theme switching functions properly
- No visual differences from original

---

## Phase 3: Section Extraction

### Header & Navigation
- [x] Extract nav section to `nav.html.j2`
- [x] Extract header section to `header.html.j2`

### Content Sections (17 total)
- [x] `tldr.html.j2`
- [x] `about.html.j2`
- [x] `stats.html.j2`
- [x] `trend_2025.html.j2`
- [x] `takeaways.html.j2`
- [x] `summary.html.j2`
- [x] `tools.html.j2`
- [x] `ai_categories.html.j2`
- [x] `by_team.html.j2`
- [x] `impact.html.j2`
- [x] `monthly.html.j2`
- [x] `data_table.html.j2`
- [x] `detection.html.j2`
- [x] `correlations.html.j2`
- [x] `methodology.html.j2`
- [x] `industry.html.j2`
- [x] `cta.html.j2`

### Footer
- [x] Extract footer section to `footer.html.j2`

**Acceptance Criteria:**
- Each section file < 200 lines
- Inline `style=""` attributes preserved
- All sections render correctly

---

## Phase 4: JavaScript Extraction

### Core Scripts
- [x] Extract theme management to `theme.js.j2`
- [x] Extract data arrays (teamData, toolTrends) with Jinja injection in base.html.j2

### Chart Scripts
- [x] `overall_trend.js.j2`
- [x] `tool_trends.js.j2` (includes category_trends)
- [x] `tool_share.js.j2`
- [x] `team_adoption.js.j2`
- [x] `review_impact.js.j2`
- [x] `cycle_impact.js.j2`
- [x] `monthly_trend.js.j2`
- [x] `team_detection.js.j2`
- [x] `correlations.js.j2` (includes prType, techCategory, prSize, teamStructure)

### UI Scripts
- [x] `ui.js.j2` (teamTable, TOC, scroll spy, progress bar, back-to-top)

**Acceptance Criteria:**
- Data injected via `{{ data | tojson }}`
- All charts render correctly
- Theme color updates work

---

## Phase 5: Finalization

- [x] Add `build-report` target to Makefile
- [ ] Add `docs/index.html` to `.gitignore` (optional - user prefers to keep tracking it for now)
- [x] Run full build cycle test - BUILD SUCCESSFUL (186.5 KB output)
- [x] Visual comparison with original - VERIFIED via Playwright testing
- [x] Consolidate template files (user requested fewer files) - DONE: 4 files total

**Acceptance Criteria:**
- `make build-report` works
- Generated HTML matches original visually
- All charts functional
- Theme toggle works

---

## Progress Summary

| Phase | Status | Tasks | Done |
|-------|--------|-------|------|
| 1. Infrastructure | Complete | 4 | 4 |
| 2. CSS Extraction | Complete | 3 | 3 |
| 3. Section Extraction | Complete | 20 | 20 |
| 4. JavaScript Extraction | Complete | 12 | 12 |
| 5. Finalization | Complete | 5 | 5 |
| **Total** | **Complete** | **44** | **44** |

---

## Notes

### Final Consolidated Structure (4 files)

| File | Lines | Size | Purpose |
|------|-------|------|---------|
| `base.html.j2` | ~84 | 3.2 KB | HTML skeleton, head, includes |
| `content.html.j2` | ~1333 | 98 KB | All HTML sections (nav, header, 17 sections, footer) |
| `scripts.js.j2` | ~880 | 41 KB | Theme, charts, UI |
| `styles.css.j2` | ~1353 | 37 KB | All CSS |

### Build Command
```bash
make build-report
```

### Output
- Generates `docs/index.html` (186.5 KB)
- Data loaded from `docs/data/*.csv`

### Bug Fixes Applied (2025-12-28)
- Added missing `sortedTeams`, `reviewData`, `cycleData` variable definitions in `scripts.js.j2`
- Fixed truncated chart configuration for teamStructure correlation chart
- Added `report-content` wrapper div in `content.html.j2` for proper TOC layout
- Moved Alpine.js script to end of body to fix `teamTable is not defined` error
