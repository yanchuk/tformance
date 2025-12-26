# PR List LLM Enrichment - Task Checklist

**Last Updated: 2025-12-26**

## Phase 1: Expandable Rows (Effort: S)

- [ ] **1.1** Add Alpine.js state to table rows for expand/collapse
  - File: `templates/metrics/pull_requests/partials/table.html`
  - Add `x-data="{ expanded: false }"` to each PR row
  - Make title clickable with `@click="expanded = !expanded"`

- [ ] **1.2** Create expanded row structure below each PR
  - Add hidden `<tr>` with `x-show="expanded"` after each PR row
  - Use `x-collapse` for smooth animation
  - Span full table width with `colspan`

- [ ] **1.3** Test expand/collapse behavior
  - Verify click toggles expansion
  - Verify multiple rows can be expanded
  - Verify no server requests on toggle

## Phase 2: Expanded Row Content (Effort: M)

- [ ] **2.1** Create expanded row partial template
  - File: `templates/metrics/pull_requests/partials/expanded_row.html`
  - Three-column layout: Summary | Health | AI+Tech

- [ ] **2.2** Add LLM Summary section
  - Display `llm_summary.summary.title`
  - Display `llm_summary.summary.description`
  - Display PR type badge (`llm_summary.summary.type`)

- [ ] **2.3** Add Health Assessment section
  - Scope badge (`llm_summary.health.scope`)
  - Risk Level badge (`llm_summary.health.risk_level`)
  - Review Friction badge (`llm_summary.health.review_friction`)
  - Insights list (`llm_summary.health.insights`)

- [ ] **2.4** Add AI Details section
  - Usage type (`llm_summary.ai.usage_type`)
  - Tools list (`llm_summary.ai.tools`)
  - Confidence score (`llm_summary.ai.confidence`)

- [ ] **2.5** Add Tech Stack section
  - Languages list (`llm_summary.tech.languages`)
  - Frameworks list (`llm_summary.tech.frameworks`)

- [ ] **2.6** Add fallback for missing LLM data
  - Show "LLM analysis pending" message
  - Style appropriately (muted text)

## Phase 3: New Template Filters (Effort: S)

- [ ] **3.1** Add template filters for LLM display
  - File: `apps/metrics/templatetags/pr_list_tags.py`
  - `llm_pr_type(pr)` - Get PR type from LLM
  - `llm_risk_level(pr)` - Get risk level
  - `llm_review_friction(pr)` - Get review friction

- [ ] **3.2** Add badge class filters
  - `risk_badge_class(level)` - success/warning/error
  - `friction_badge_class(level)` - success/warning/error
  - `scope_badge_class(scope)` - Size-based coloring
  - `pr_type_badge_class(type)` - feature/bugfix/etc colors

- [ ] **3.3** Write tests for new template filters
  - File: `apps/metrics/tests/test_pr_list_tags.py`
  - Test each filter with valid input
  - Test with None/missing data
  - Test badge class mappings

## Phase 4: New Table Badges (Effort: S)

- [ ] **4.1** Add PR Type badge to title column
  - Show after title text
  - Use `pr_type_badge_class` for styling
  - Hide if no LLM data

- [ ] **4.2** Add Risk Level indicator (optional column or inline)
  - Consider adding to expanded view only to avoid clutter
  - Or add as small indicator icon in existing column

## Phase 5: New Filters (Effort: M)

- [ ] **5.1** Update service to support new filters
  - File: `apps/metrics/services/pr_list_service.py`
  - Add `pr_type` filter (JSONB query)
  - Add `risk_level` filter (JSONB query)
  - Add `review_friction` filter (JSONB query)

- [ ] **5.2** Add filter options to `get_filter_options()`
  - PR types: feature, bugfix, refactor, docs, test, chore, ci
  - Risk levels: low, medium, high
  - Friction levels: low, medium, high

- [ ] **5.3** Update view to pass new filter options
  - File: `apps/metrics/views/pr_list_views.py`
  - Add new filter params to context

- [ ] **5.4** Add filter dropdowns to template
  - File: `templates/metrics/pull_requests/partials/table.html` (or filters partial)
  - PR Type dropdown
  - Risk Level dropdown
  - Review Friction dropdown

- [ ] **5.5** Write tests for new filters
  - File: `apps/metrics/tests/test_pr_list_service.py`
  - Test filtering by pr_type
  - Test filtering by risk_level
  - Test filtering by review_friction
  - Test with null llm_summary

## Phase 6: Polish & Testing (Effort: S)

- [ ] **6.1** Add smooth expand/collapse animation
  - Verify x-collapse plugin is loaded
  - Adjust animation timing if needed

- [ ] **6.2** Test mobile responsiveness
  - Verify expanded content readable on mobile
  - Adjust layout if needed (stack vs columns)

- [ ] **6.3** Handle edge cases
  - Very long insights text
  - Many languages/frameworks
  - Empty arrays in LLM data

- [ ] **6.4** Run full test suite
  - `make test ARGS='apps/metrics/tests/test_pr_list'`
  - Verify no regressions

## Completion Criteria

- [ ] PR rows expand on click to show LLM data
- [ ] Expanded view shows summary, health, AI, tech sections
- [ ] Graceful fallback for PRs without LLM data
- [ ] New template filters for LLM display
- [ ] New filters: PR Type, Risk Level, Review Friction
- [ ] All tests passing
- [ ] Mobile responsive

---

## Notes

- Start with Phase 1-2 (expandable rows) before filters
- Template filters in Phase 3 are reusable for both table and expanded view
- Phase 4 badges are optional - may add clutter to already busy table
- Phase 5 filters are independent and can be done in parallel
