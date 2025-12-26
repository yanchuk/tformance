# Report Desktop Responsiveness Fix

**Last Updated: 2025-12-26**

## Executive Summary

The research report at `docs/index.html` has layout issues at 1440px desktop width. The content container appears too narrow, leaving excessive white space on the right side of the screen. This is caused by overly conservative `max-width` constraints in the responsive CSS.

## Current State Analysis

### Problem
At 1440px viewport width (common laptop/external monitor resolution):
- Sidebar: 220px fixed width
- Container margin-left: 280px (220px sidebar + 60px gap)
- Container max-width: 1000px ← **This is the issue**
- Container padding-right: 4rem

Result: Content is constrained to 1000px while there's ~160px of unused space on the right.

### Current CSS Structure
```css
/* Line 406-412 */
@media (min-width: 1440px) {
    .container {
        margin-left: 280px;
        padding-right: 4rem;
        max-width: 1000px;  /* Too restrictive */
    }
}
```

### Visual Issue
The screenshot shows ~70-75% of available content width being used, with the right side appearing empty.

## Proposed Future State

At 1440px:
- Content should use more of the available horizontal space
- Target: ~85-90% utilization of available width
- Maintain comfortable reading line length (~80-100 characters)
- Keep proper spacing from sidebar

### Recommended Fix
```css
@media (min-width: 1440px) {
    .container {
        margin-left: 260px;  /* Reduced gap */
        padding-right: 3rem; /* Reduced padding */
        max-width: 1100px;   /* Wider content */
    }
}
```

Math: 1440px - 260px (margin-left) - 48px (padding-right) = 1132px available
With max-width: 1100px, we use ~96% of available space.

## Implementation

### Phase 1: CSS Fix
1. Update the `@media (min-width: 1440px)` breakpoint
2. Adjust container constraints for better width utilization
3. Consider adding a `@media (min-width: 1600px)` for larger monitors

### Changes Required
File: `docs/index.html` (lines ~406-412)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Line length too long | Low | Medium | Test readability at new width |
| Charts stretch oddly | Low | Low | Charts already responsive |
| Break on other sizes | Low | Medium | Test 1200-1599px range |

## Success Metrics

- Content fills ~85-90% of available width at 1440px
- No horizontal scrollbar
- Text remains readable (line length comfortable)
- Sidebar and content maintain proper spacing
