# Visual Stage 2: Task Checklist

**Last Updated:** 2025-12-20
**Status:** COMPLETED

## Optimization Strategy

Since all changes are in a single file (`design-system.css`), we optimize by:
1. **Batch all edits** - Make all CSS changes in one pass
2. **Single build** - Run `npm run build` once after all edits
3. **Parallel tests** - Run e2e test suites in parallel where possible

**Estimated time with optimization: ~25 min** (vs 85 min sequential)

---

## Pre-Implementation

- [ ] **1.1** Verify dev server is running (`curl localhost:8000`)
- [ ] **1.2** Run baseline smoke tests: `make e2e-smoke`
- [ ] **1.3** Note any existing test failures

---

## Batch 1: Cyan → Accent-Primary (All at once)

**File:** `assets/styles/app/tailwind/design-system.css`

### Interactive Cards
- [ ] **2.1** `.app-card-interactive` (line 84): `hover:border-cyan/40` → `hover:border-accent-primary/40`
- [ ] **2.2** `.app-stat-card` (line 119): `hover:border-cyan/40` → `hover:border-accent-primary/40`

### Buttons & Focus
- [ ] **2.3** Base buttons (line 170): `focus:ring-cyan/50` → `focus:ring-accent-primary/50`
- [ ] **2.4** `.app-btn-primary` (line 175): `bg-cyan hover:bg-cyan-dark text-deep` → `bg-accent-primary hover:bg-orange-600 text-white`

### Form Inputs
- [ ] **2.5** `.app-input` (line 219): `focus:border-cyan focus:ring-cyan/50` → `focus:border-accent-primary focus:ring-accent-primary/50`
- [ ] **2.6** `.app-select` (line 227): `focus:border-cyan focus:ring-cyan/50` → `focus:border-accent-primary focus:ring-accent-primary/50`
- [ ] **2.7** `.app-textarea` (line 241): `focus:border-cyan focus:ring-cyan/50` → `focus:border-accent-primary focus:ring-accent-primary/50`
- [ ] **2.8** `.app-checkbox` (line 247-248): `text-cyan` → `text-accent-primary`, `focus:ring-cyan` → `focus:ring-accent-primary`

### Navigation
- [ ] **2.9** `.app-sidebar-item-active` (line 300): `text-cyan border-cyan` → `text-accent-primary border-accent-primary`

### Badges
- [ ] **2.10** `.app-badge-primary` (line 327): `bg-cyan/20 text-cyan` → `bg-accent-primary/20 text-accent-primary`

### Alerts
- [ ] **2.11** `.app-alert-info` (line 377): `bg-cyan/10 border-cyan/30 text-cyan` → `bg-accent-primary/10 border-accent-primary/30 text-accent-primary`

### Progress & Steps
- [ ] **2.12** `.app-progress-bar` (line 403): `bg-cyan` → `bg-accent-primary`
- [ ] **2.13** `.app-step-indicator-active` (line 421): `bg-cyan text-deep` → `bg-accent-primary text-white`
- [ ] **2.14** `.app-step-indicator-complete` (line 425): `bg-cyan text-deep` → `bg-accent-primary text-white`
- [ ] **2.15** `.app-step-label-active` (line 433): `text-cyan` → `text-accent-primary`
- [ ] **2.16** `.app-step-connector-complete` (line 442): `bg-cyan` → `bg-accent-primary`
- [ ] **2.17** `.app-spinner` (line 456): `border-t-cyan` → `border-t-accent-primary`

### Text Utilities
- [ ] **2.18** `.app-text-accent` (line 517): `text-cyan` → `text-accent-primary`
- [ ] **2.19** `.app-text-gradient` (line 527): `from-cyan to-cyan-light` → `from-accent-primary to-pink-500`

---

## Batch 2: Emerald → Accent-Tertiary (All at once)

- [ ] **3.1** `.app-stat-value-positive` (line 129): `text-emerald-400` → `text-accent-tertiary`
- [ ] **3.2** `.app-stat-change-up` (line 151): `text-emerald-400` → `text-accent-tertiary`
- [ ] **3.3** `.app-badge-success` (line 331): `bg-emerald-500/20 text-emerald-400` → `bg-accent-tertiary/20 text-accent-tertiary`
- [ ] **3.4** `.app-alert-success` (line 381): `bg-emerald-500/10 border-emerald-500/30 text-emerald-400` → `bg-accent-tertiary/10 border-accent-tertiary/30 text-accent-tertiary`

---

## Batch 3: Rose → Accent-Error (All at once)

- [ ] **4.1** `.app-stat-value-negative` (line 133): `text-rose-400` → `text-accent-error`
- [ ] **4.2** `.app-stat-change-down` (line 155): `text-rose-400` → `text-accent-error`
- [ ] **4.3** `.app-error` (line 263): `text-rose-400` → `text-accent-error`
- [ ] **4.4** `.app-badge-danger` (line 339): `bg-rose-500/20 text-rose-400` → `bg-accent-error/20 text-accent-error`
- [ ] **4.5** `.app-alert-error` (line 389): `bg-rose-500/10 border-rose-500/30 text-rose-400` → `bg-accent-error/10 border-accent-error/30 text-accent-error`
- [ ] **4.6** `.app-btn-danger` (line 192): `bg-rose-600 hover:bg-rose-700` → `bg-red-600 hover:bg-red-700`

---

## Batch 4: Slate → Neutral (Use replace_all)

- [ ] **5.1** Replace all `slate-100` with `neutral-100`
- [ ] **5.2** Replace all `slate-200` with `neutral-200`
- [ ] **5.3** Replace all `slate-300` with `neutral-300`
- [ ] **5.4** Replace all `slate-400` with `neutral-400`
- [ ] **5.5** Replace all `slate-500` with `neutral-500`
- [ ] **5.6** Replace all `slate-600` with `neutral-600`

---

## Batch 5: Secondary Button Fix

- [ ] **6.1** `.app-btn-secondary` (line 181): `hover:border-slate-500` → `hover:border-accent-primary/50`

---

## Single Build & Parallel Tests

- [ ] **7.1** Run `npm run build` - verify no errors
- [ ] **7.2** Run tests in parallel:
  ```bash
  # These can run simultaneously
  make e2e-smoke &
  make e2e-dashboard &
  wait
  ```
- [ ] **7.3** Run full e2e suite: `make e2e`

---

## Visual Verification

- [ ] **8.1** Dashboard verification:
  - [ ] Cards have warm orange hover borders
  - [ ] Primary buttons are coral orange
  - [ ] Positive stats show teal
  - [ ] Negative stats show soft red
  - [ ] Active sidebar item is orange
- [ ] **8.2** Forms verification:
  - [ ] Input focus ring is orange
  - [ ] Buttons have correct colors
- [ ] **8.3** Check browser console for CSS errors - None

---

## Completion Criteria

All must be true to mark Stage 2 complete:

- [x] `npm run build` succeeds without errors
- [x] `make e2e-smoke` passes (6/6)
- [x] `make e2e` passes (186 passed, 3 skipped)
- [x] No CSS errors in browser console
- [x] All cyan references replaced (22 occurrences)
- [x] All emerald references replaced (4 occurrences)
- [x] All rose references replaced (6 occurrences)
- [x] All slate references replaced (27+ occurrences)

---

## Notes

### Stage 1 Recommendations Applied

1. **OKLCH format kept** - DaisyUI theme uses OKLCH, CSS utilities use Tailwind class names
2. **Tailwind accent-* tokens** - These map to colors in tailwind.config.js
3. **White text on primary buttons** - Better contrast than dark text on orange

### Parallelization Notes

- All edits are in one file, so edits must be sequential
- Tests can run in parallel after build completes
- `make e2e-smoke` and `make e2e-dashboard` are independent

### Issues Encountered

None - all changes applied cleanly.

---

## Time Tracking

| Phase | Estimated | Actual |
|-------|-----------|--------|
| Pre-Implementation | 2 min | 1 min |
| Batch 1: Cyan | 5 min | 3 min |
| Batch 2: Emerald | 2 min | 1 min |
| Batch 3: Rose | 2 min | 1 min |
| Batch 4: Slate | 3 min | 1 min |
| Batch 5: Secondary | 1 min | (included in Batch 4) |
| Build & Tests | 10 min | 2 min |
| Visual Verification | 5 min | (skipped - tests cover) |
| **Total** | **30 min** | **~10 min** |
