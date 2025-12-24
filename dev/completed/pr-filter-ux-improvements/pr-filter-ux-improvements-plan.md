# PR List Filter UX Improvements Plan

**Last Updated:** 2025-12-24

## Executive Summary

This plan addresses two critical UX issues on the Pull Requests data explorer page:

1. **Filter State Visibility**: Users don't receive visual feedback when filter values change, making it unclear they need to click "Apply Filters"
2. **Button Contrast in Light Theme**: Dark text on coral orange buttons appears harsh and potentially fails perceptual accessibility standards

The solution involves implementing a "dirty state" indicator for the filter form and adjusting button text colors for better cross-theme accessibility.

## Current State Analysis

### Issue 1: Filter State Visibility

**Current Behavior:**
- Users select filter values from dropdowns
- The "Apply Filters" button remains static with no visual change
- Users must remember to click the button to see results
- No indication that unapplied changes exist

**Technical Location:**
- `templates/metrics/pull_requests/list.html` - Filter form (lines 17-110)
- Uses HTMX for form submission (`hx-get`, `hx-target="#pr-table-container"`)
- Currently no Alpine.js state management for tracking changes

**User Pain Point:**
> "As I change something with the filter, I don't see that Apply Filters button changes state and I understand I need to click it."

### Issue 2: Button Contrast

**Current Behavior:**
- Primary buttons use `btn btn-primary` (DaisyUI)
- Dark theme: `#F97316` orange background with white text
- Light theme: `#F97316` orange background with dark text (`oklch(0.15 0 0)`)
- The dark text on orange creates a jarring visual effect

**Technical Location:**
- `assets/styles/site-tailwind.css` - Theme definitions
- `assets/styles/app/tailwind/design-system.css` - Button classes
- DaisyUI's `tformance-light` theme sets `--color-primary-content: oklch(0.15 0 0)`

**Research Insight:**
Modern APCA (Accessible Perceptual Contrast Algorithm) research shows that **white text on orange is more readable** than dark text, despite WCAG2 mathematical ratios suggesting otherwise. Users, including those with color blindness, prefer white text on saturated colors.

## Proposed Future State

### Solution 1: Filter Dirty State Indicator

**Approach: Visual feedback when filters have unapplied changes**

1. Add Alpine.js state tracking to the filter form
2. Highlight the "Apply Filters" button when any filter value changes from its initial state
3. Show a visual cue (glow, color change, or badge) indicating pending changes
4. Optionally: Show count of matching results on the button (progressive enhancement)

**Visual Design Options:**

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Glow Effect** | Add `ring-2 ring-primary ring-offset-2` when dirty | Subtle, modern | May be missed |
| **B. Color Shift** | Change button to `btn-warning` when dirty | Very visible | May confuse as error |
| **C. Badge Count** | Show "Apply (3 changes)" text | Clear communication | Requires counting logic |
| **D. Pulsing Animation** | Add subtle pulse animation | Draws attention | Can be annoying |

**Recommended: Option A + Text Change**
- Add glow effect (`ring-2 ring-warning/50`)
- Change button text from "Apply Filters" to "Apply Changes" when dirty
- This combines visibility with clear communication

### Solution 2: Button Text Color Fix

**Approach: Use white text on primary buttons in light theme**

Modern research from [InclusiveColors](https://www.inclusivecolors.com/) and [UX Movement](https://uxmovement.com/buttons/the-myths-of-color-contrast-accessibility/) confirms that white text on orange buttons provides better perceptual contrast than dark text, even when WCAG2 ratios suggest otherwise.

**Implementation:**

Change light theme `primary-content` from dark to white:
```css
/* Before */
--color-primary-content: oklch(0.15 0 0);  /* Dark text */

/* After */
--color-primary-content: oklch(1 0 0);     /* White text */
```

**Alternative: Slightly Shift Primary Color**

If white text doesn't work aesthetically, consider shifting the orange toward amber:
- Current: `#F97316` (coral orange)
- Alternative: `#EA580C` (slightly deeper orange-600)
- Alternative: `#C2410C` (orange-700, darker for better dark text contrast)

**Recommended: White text** - Maintains brand consistency between themes while improving readability.

## Implementation Phases

### Phase 1: Filter Dirty State (Effort: M)
**Goal:** Users clearly see when they have unapplied filter changes

1. Add Alpine.js `x-data` to track initial filter values
2. Add `@change` handlers to detect value changes
3. Apply visual styles when form is "dirty"
4. Reset dirty state after form submission

### Phase 2: Button Color Fix (Effort: S)
**Goal:** Primary buttons are readable in light theme

1. Update `--color-primary-content` in light theme definition
2. Verify all primary buttons look correct
3. Test with WCAG contrast checkers
4. Consider secondary button text if needed

### Phase 3: Enhanced Feedback (Optional) (Effort: L)
**Goal:** Show result count on Apply button

1. Add endpoint to get count without full results
2. Debounced fetch on filter change
3. Display count on button: "Apply Filters (1,234 results)"

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Dirty state logic conflicts with HTMX | Medium | Medium | Test HTMX lifecycle events, reset on `htmx:afterRequest` |
| White text fails accessibility check | Low | High | Test with real users; APCA validates white text is superior |
| Visual changes confuse existing users | Low | Low | Changes are intuitive improvements, not workflow changes |
| Performance impact from Alpine.js | Low | Low | Minimal JS for state comparison |

## Success Metrics

1. **Reduced filter confusion**: Users apply filters on first attempt (qualitative feedback)
2. **WCAG AA compliance**: All buttons pass 4.5:1 contrast ratio
3. **No regression**: E2E tests for filter functionality pass
4. **User preference**: Light theme buttons feel natural and readable

## Dependencies

- No external dependencies
- Existing Alpine.js integration in project
- Existing DaisyUI/Tailwind setup

## References

### UX Research Sources
- [Smashing Magazine: Frustrating Design Patterns](https://www.smashingmagazine.com/2021/07/frustrating-design-patterns-broken-frozen-filters/) - Filter UX patterns
- [Smart Interface Design Patterns: Filtering UX](https://smart-interface-design-patterns.com/articles/filtering-ux/) - Apply button best practices
- [Baymard Institute: Product List Filtering](https://baymard.com/blog/horizontal-filtering-sorting-design) - Filter research

### Accessibility Research Sources
- [UX Movement: Color Contrast Myths](https://uxmovement.com/buttons/the-myths-of-color-contrast-accessibility/) - White text preference
- [InclusiveColors](https://www.inclusivecolors.com/) - APCA vs WCAG2 on orange buttons
- [AllAccessible: Color Contrast Guide 2025](https://www.allaccessible.org/blog/color-contrast-accessibility-wcag-guide-2025)

### Design System References
- [Vercel Geist Design System](https://vercel.com/geist/colors) - Modern theme handling
- [PostHog Design Guide](https://posthog.com/newsletter/vibe-designing) - SaaS dashboard inspiration
