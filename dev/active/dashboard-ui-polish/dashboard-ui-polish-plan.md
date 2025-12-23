# Dashboard UI Polish - Plan

**Last Updated:** 2025-12-23
**Status:** IN PROGRESS

## Overview

Fix UI overflow and spacing issues identified on the CTO Overview dashboard. Issues affect stat cards, charts, and category displays.

## Issues Identified

### 1. AI Bot Reviews Card - Text Overflow
- **Location:** `templates/metrics/partials/ai_bot_reviews_card.html`
- **Problem:** "From automated reviewers" text and numbers overflow container on smaller screens
- **Root Cause:** `stat-desc` has no truncation, grid cells too narrow at `md:grid-cols-3`

### 2. AI Detection vs Self-Reported Card - Text Overflow
- **Location:** `templates/metrics/partials/survey_ai_detection_card.html`
- **Problem:** Description text overflows in `grid-cols-2 md:grid-cols-4` layout
- **Root Cause:** `stat-desc text-xs` too wide for small grid cells

### 3. Cycle Time Trend Chart - Excess Spacing
- **Location:** `templates/metrics/partials/cycle_time_chart.html`
- **Problem:** Large gap between header description and chart canvas
- **Root Cause:** Extra margin/padding on description text

### 4. CI/CD Pass Rate Card - Number Overflow
- **Location:** `templates/metrics/partials/cicd_pass_rate_card.html`
- **Problem:** Large numbers (e.g., "3026") overflow their containers
- **Root Cause:** `text-2xl font-mono` too large for multi-digit numbers

### 5. File Category Chart - Insufficient Spacing
- **Location:** `templates/metrics/partials/file_category_card.html`
- **Problem:** Category names too close to progress bars
- **Root Cause:** `gap-3` insufficient, `w-24` category width too narrow

## Solution Strategy

Apply consistent CSS patterns across all affected components:

1. **Text Overflow:** Add `truncate` class or `line-clamp-1` for descriptions
2. **Number Overflow:** Use responsive font sizing (`text-lg md:text-xl lg:text-2xl`)
3. **Spacing:** Increase gap values and adjust widths
4. **Chart Spacing:** Remove unnecessary margins

## Implementation Order

1. Fix stat card text overflow (systematic pattern)
2. Fix number overflow in stat cards
3. Adjust chart spacing
4. Adjust category chart spacing
5. Verify all fixes visually

## Success Criteria

- All text fits within containers without overflow
- Numbers display completely without clipping
- Charts have appropriate spacing to headers
- Visual consistency across all dashboard cards
