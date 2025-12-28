# AI Tool Categories Implementation Plan

**Last Updated:** 2025-12-27
**Status:** Planning
**Priority:** High

## Executive Summary

Implement AI tool categorization to distinguish between **Code Assistance** tools (Cursor, Copilot, Claude) and **Review Assistance** tools (CodeRabbit, Cubic, Greptile). This enables more meaningful analytics for CTOs by separating:
- **Code AI**: Tools that help write/generate code (productivity impact)
- **Review AI**: Tools that review/comment on PRs (quality/efficiency impact)

### Approach: Option A - Tool Category Mapping (No Reprocessing)

Add a simple mapping layer that categorizes existing detected tools. No LLM prompt changes or reprocessing of 109K PRs required.

## Current State Analysis

### Existing Infrastructure

| Component | Location | Current State |
|-----------|----------|---------------|
| AI Detection | `apps/metrics/services/ai_patterns.py` | 239 patterns, v2.0.0 |
| PR Model | `apps/metrics/models/github.py` | `ai_tools_detected`, `llm_summary.ai.tools` |
| PR List Filters | `apps/metrics/services/pr_list_service.py` | Filters by `ai_tool` (single tool) |
| Dashboard Charts | `apps/metrics/views/chart_views.py` | `ai_adoption_chart`, `ai_tool_breakdown_chart` |
| Template Tags | `apps/metrics/templatetags/pr_list_tags.py` | `ai_tools_display`, display name mappings |

### What Already Works

1. **Tool Detection**: Both regex patterns and LLM analysis detect AI tools
2. **Tool Display**: `ai_tools_display` template tag maps IDs to friendly names
3. **Filter Infrastructure**: PR list supports `ai_tool` filter
4. **Chart Data**: `ai_tool_breakdown_chart` shows tool counts

### What's Missing

1. **Category Mapping**: No way to classify tools as "code" vs "review"
2. **Category Filter**: Can't filter PRs by AI assistance category
3. **Category Charts**: No breakdown of code vs review AI usage
4. **Model Properties**: No computed properties for category-based queries

## Proposed Future State

### New Components

```
apps/metrics/services/ai_categories.py   # Tool category mappings
apps/metrics/models/github.py            # New model properties
apps/metrics/services/pr_list_service.py # Category filter support
apps/metrics/views/chart_views.py        # Category chart data
templates/metrics/                       # Updated UI components
```

### Category Classification

| Category | Tools | Dashboard Label |
|----------|-------|-----------------|
| **code** | cursor, copilot, claude, devin, aider, cody, etc. | "Code AI" |
| **review** | coderabbit, cubic, greptile, sourcery, etc. | "Review AI" |
| **mixed** | ellipsis, bito, qodo → Default to "code" | "Code AI" |
| **excluded** | snyk, mintlify, dependabot | Not tracked as AI |

### User-Facing Changes

1. **PR List Filter**: New "AI Category" dropdown (All / Code AI / Review AI)
2. **Dashboard Chart**: Stacked/split chart showing Code vs Review AI adoption
3. **PR Row Display**: Badge indicating category type
4. **Stats**: Separate percentages for code AI and review AI

## Implementation Phases

### Phase 1: Core Category Service (Effort: S)

Create the mapping service with no external dependencies.

**Files:**
- `apps/metrics/services/ai_categories.py` (new)

**Deliverables:**
- Tool category constants (CODE_TOOLS, REVIEW_TOOLS, MIXED_TOOLS, EXCLUDED_TOOLS)
- `get_tool_category(tool_name)` function
- `categorize_tools(tool_list)` function returning `{code: [], review: []}`
- `get_ai_category(tool_list)` → "code" | "review" | "both" | None

### Phase 2: Model Integration (Effort: S)

Add computed properties to PullRequest model.

**Files:**
- `apps/metrics/models/github.py`

**New Properties:**
- `ai_code_tools` → List of code-category tools
- `ai_review_tools` → List of review-category tools
- `ai_category` → "code" | "review" | "both" | None

### Phase 3: PR List Filter (Effort: M)

Add category filter to PR list.

**Files:**
- `apps/metrics/services/pr_list_service.py`
- `templates/metrics/analytics/pull_requests.html`

**Changes:**
- New `ai_category` filter parameter ("code" | "review" | "all")
- Filter options include `ai_categories` list
- UI dropdown for category selection

### Phase 4: Dashboard Charts (Effort: M)

Update charts to show category breakdown.

**Files:**
- `apps/metrics/services/dashboard_service.py`
- `apps/metrics/views/chart_views.py`
- `templates/metrics/partials/ai_adoption_chart.html`
- `templates/metrics/partials/ai_tool_breakdown_chart.html`

**Changes:**
- AI adoption chart with stacked code/review series
- Tool breakdown grouped by category
- Key metrics showing both code and review percentages

### Phase 5: PR Row Display (Effort: S)

Show category in PR list rows.

**Files:**
- `apps/metrics/templatetags/pr_list_tags.py`
- `templates/metrics/pull_requests/partials/table.html`

**Changes:**
- New template filters for category display
- Badge/icon indicating code vs review AI
- Updated tooltip with category info

## Detailed Tasks

### Phase 1: Core Category Service

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 1.1 | Create `ai_categories.py` with tool sets | S | All tools from research categorized |
| 1.2 | Implement `get_tool_category()` | S | Returns category for any tool name |
| 1.3 | Implement `categorize_tools()` | S | Splits tool list into code/review |
| 1.4 | Implement `get_ai_category()` | S | Returns dominant category |
| 1.5 | Add display name mappings | S | Friendly names for all categories |
| 1.6 | Write unit tests | M | 100% coverage of category service |

### Phase 2: Model Integration

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 2.1 | Add `ai_code_tools` property | S | Returns code tools from effective_ai_tools |
| 2.2 | Add `ai_review_tools` property | S | Returns review tools from effective_ai_tools |
| 2.3 | Add `ai_category` property | S | Returns category string |
| 2.4 | Write model tests | M | Properties work with various tool combinations |

### Phase 3: PR List Filter

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 3.1 | Add `ai_category` to filter options | S | Service returns available categories |
| 3.2 | Implement category filter logic | M | Query filters by category correctly |
| 3.3 | Add UI dropdown for category | S | Dropdown with All/Code AI/Review AI |
| 3.4 | Update stats to show category breakdown | S | Stats show code/review counts |
| 3.5 | Write filter tests | M | All filter combinations work |

### Phase 4: Dashboard Charts

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 4.1 | Update AI adoption trend data | M | Returns separate code/review series |
| 4.2 | Update AI adoption chart template | M | Stacked or split visualization |
| 4.3 | Group tool breakdown by category | S | Tools grouped under category headers |
| 4.4 | Update key metrics | S | Shows code_ai_pct and review_ai_pct |
| 4.5 | Write chart view tests | M | Data aggregation is correct |

### Phase 5: PR Row Display

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 5.1 | Add category template filters | S | `ai_category_display`, `ai_category_badge` |
| 5.2 | Update PR table AI column | S | Shows category indicator |
| 5.3 | Update tooltip with category | S | Tooltip includes category info |
| 5.4 | Write template tag tests | S | Filters render correctly |

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Mixed tools miscategorized | Medium | Low | Default to "code", document reasoning |
| New tools not in mapping | Low | Medium | Fallback to "unknown", add via patterns |
| Performance impact | Low | Low | Properties are computed, not stored |
| UI clutter | Medium | Low | Progressive disclosure, hover for details |

## Success Metrics

1. **Functional**: All PRs can be filtered by AI category
2. **Accuracy**: Category mapping covers 95%+ of detected tools
3. **Performance**: No measurable slowdown in PR list or dashboard
4. **Usability**: Users can distinguish code vs review AI at a glance

## Dependencies

- No external dependencies
- No database migrations required
- No reprocessing of existing data
- Builds on existing `effective_ai_tools` infrastructure

## Required Resources

- 1 developer
- Estimated total effort: 2-3 days
- No infrastructure changes needed
