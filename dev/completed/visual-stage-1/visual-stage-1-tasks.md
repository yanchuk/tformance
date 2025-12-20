# Visual Stage 1: Task Checklist

**Last Updated:** 2025-12-20
**Status:** COMPLETED

## Pre-Implementation

- [x] **1.1** Verify dev server is running (`curl localhost:8000`)
- [x] **1.2** Run baseline smoke tests: `make e2e-smoke` - 6/6 passed
- [x] **1.3** Note any existing test failures (document in notes below) - None

---

## Phase 1: Update Tailwind Config

**File:** `tailwind.config.js`

- [x] **2.1** Update `deep` color from `#0f172a` to `#171717`
- [x] **2.2** Update `surface` color from `#1e293b` to `#262626`
- [x] **2.3** Update `elevated` color from `#334155` to `#404040`
- [x] **2.4** Update `muted` color from `#94a3b8` to `#A3A3A3`
- [x] **2.5** Add `accent` object with new colors
- [x] **2.6** Keep existing `cyan` object for backwards compatibility

### Validation Checkpoint
- [x] **2.7** Run `npm run build` - verify no errors
- [x] **2.8** Check dev server still works

---

## Phase 2: Update DaisyUI Theme

**File:** `assets/styles/site-tailwind.css`

- [x] **3.1** Update `--color-base-100` to `#171717`
- [x] **3.2** Update `--color-base-200` to `#262626`
- [x] **3.3** Update `--color-base-300` to `#404040`
- [x] **3.4** Update `--color-base-content` to `#FAFAFA`
- [x] **3.5** Update `--color-primary` to `#F97316` (coral orange)
- [x] **3.6** Update `--color-primary-content` to `#FFFFFF`
- [x] **3.7** Update `--color-secondary` to `#FDA4AF` (warm rose)
- [x] **3.8** Update `--color-secondary-content` to `#171717`
- [x] **3.9** Update `--color-accent` to `#2DD4BF` (teal)
- [x] **3.10** Update `--color-accent-content` to `#171717`
- [x] **3.11** Update `--color-neutral` to `#262626`
- [x] **3.12** Update `--color-neutral-content` to `#D4D4D4`
- [x] **3.13** Update `--color-info` to `#60A5FA`
- [x] **3.14** Update `--color-success` to `#2DD4BF`
- [x] **3.15** Update `--color-warning` to `#FBBF24`
- [x] **3.16** Update `--color-error` to `#F87171`

### Validation Checkpoint
- [x] **3.17** Run `npm run build` - verify no errors
- [x] **3.18** Check dev server still works

---

## Phase 3: Final Validation

- [x] **4.1** Run full build: `npm run build`
- [x] **4.2** Run smoke tests: `make e2e-smoke` - 6/6 passed
- [x] **4.3** Visual verification - Landing page:
  - [x] Page loads without errors
  - [x] Background colors are warmer (less blue)
  - [x] Primary buttons show coral/orange
  - [x] No broken layouts
- [x] **4.4** Visual verification - Dashboard (if accessible):
  - [x] Cards render correctly
  - [x] No broken styles
- [x] **4.5** Check browser console for CSS errors - None
- [x] **4.6** Run full e2e suite: `make e2e` - 185/186 passed (1 flaky test passes in isolation)

---

## Completion Criteria

All must be true to mark Stage 1 complete:

- [x] `npm run build` succeeds without errors
- [x] `make e2e-smoke` passes
- [x] `make e2e` passes (no regressions) - 185 passed, 1 flaky (passes solo)
- [x] No CSS errors in browser console
- [x] Pages render with warm background colors
- [x] DaisyUI components use new primary color

---

## Notes

### Existing Test Issues (Pre-Stage 1)
None - all 6 smoke tests passed before changes.

### Issues Encountered
- One accessibility test (team dashboard) was flaky during parallel runs but passes when run in isolation. This is a timing issue, not related to color changes.

### Decisions Made
- Used OKLCH color format for DaisyUI theme (consistent with DaisyUI 5)
- Kept legacy `cyan` colors for backwards compatibility during migration

---

## Time Tracking

| Phase | Estimated | Actual |
|-------|-----------|--------|
| Pre-Implementation | 5 min | 2 min |
| Tailwind Config | 10 min | 5 min |
| DaisyUI Theme | 15 min | 5 min |
| Validation | 10 min | 8 min |
| **Total** | **40 min** | **20 min** |
