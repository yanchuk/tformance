# Feature Showcase Slider - Tasks

**Last Updated**: 2025-01-15

## Phase 1: Component Development

### 1.1 Create Alpine.js Component
- [ ] Create `assets/javascript/components/feature-slider.js`
- [ ] Implement state: `slides`, `currentSlide`, `isPaused`, `autoplayActive`
- [ ] Implement `init()` with data parsing
- [ ] Implement `preloadImages()` for smooth transitions
- [ ] Implement promise-based `startAutoplay()`
- [ ] Implement `next()`, `prev()`, `goToSlide(index)`
- [ ] Implement `pauseAutoplay()`, `resumeAutoplay()`
- [ ] Implement `destroy()` for cleanup
- [ ] Add `prefers-reduced-motion` check
- **Effort**: M
- **Acceptance**: Component registers without errors

### 1.2 Register Component
- [ ] Import in `assets/javascript/alpine.js`
- [ ] Call `registerFeatureSlider()` in init
- [ ] Verify Vite build succeeds
- **Effort**: S
- **Acceptance**: `Alpine.data('featureSlider')` available

## Phase 2: Template Development

### 2.1 Create Template Partial
- [ ] Create `templates/web/components/feature_showcase.html`
- [ ] Build two-column grid layout
- [ ] Left column: Feature cards with click handlers
- [ ] Right column: Screenshot with x-transition
- [ ] Add hover handlers for pause/resume
- [ ] Style active card state
- **Effort**: M
- **Acceptance**: Renders correctly with test data

### 2.2 Add Accessibility
- [ ] Add `role="region"` and `aria-roledescription="carousel"`
- [ ] Add `aria-label="Feature showcase"`
- [ ] Add `aria-live="polite"` (dynamic)
- [ ] Add `role="tablist"` on cards container
- [ ] Add `role="tab"` + `aria-selected` on cards
- [ ] Add keyboard navigation (`@keydown.left`, `@keydown.right`)
- [ ] Add focus visible styles
- **Effort**: S
- **Acceptance**: Passes accessibility audit

### 2.3 Add Responsive Behavior
- [ ] Mobile: Stack vertically
- [ ] Tablet+: Side-by-side grid
- [ ] Ensure touch-friendly card sizes
- **Effort**: S
- **Acceptance**: Works on 375px+ viewports

## Phase 3: Asset Setup

### 3.1 Create Directory Structure
- [ ] Create `static/images/features/` directory
- [ ] Document image requirements (1200×800, WebP+PNG)
- **Effort**: S
- **Acceptance**: Directory exists

### 3.2 Add Placeholder Images (temporary)
- [ ] Add placeholder images for development
- [ ] Or use existing dashboard screenshots
- **Effort**: S
- **Acceptance**: Slider displays images

### 3.3 Final Screenshots (user provides)
- [ ] Receive PNGs from user
- [ ] Convert to WebP
- [ ] Add to `static/images/features/`
- **Effort**: S
- **Depends on**: User action

## Phase 4: Integration

### 4.1 Update Landing Page
- [ ] Add include after `pain_points.html`
- [ ] Pass feature data as JSON
- [ ] Test full page load
- **Effort**: S
- **Acceptance**: Slider appears on homepage

### 4.2 Build & Test
- [ ] Run `npm run build` (Vite)
- [ ] Test on `localhost:8000`
- [ ] Test HTMX navigation (component cleanup)
- **Effort**: S
- **Acceptance**: No console errors

## Phase 5: Verification (Playwright)

### 5.1 Functional Tests
- [ ] Navigate to homepage
- [ ] Verify slider visible
- [ ] Wait 6s, verify auto-rotation
- [ ] Hover, verify pause
- [ ] Click card, verify selection
- [ ] Check screenshot changes
- **Effort**: M
- **Acceptance**: All behaviors work

### 5.2 Accessibility Tests
- [ ] Check ARIA attributes present
- [ ] Test keyboard navigation
- [ ] Verify focus management
- **Effort**: S
- **Acceptance**: Accessible

### 5.3 Responsive Tests
- [ ] Test mobile viewport (375px)
- [ ] Test tablet viewport (768px)
- [ ] Test desktop viewport (1280px)
- **Effort**: S
- **Acceptance**: Responsive

---

## Progress Summary

| Phase | Status | Tasks |
|-------|--------|-------|
| 1. Component | Not Started | 0/2 |
| 2. Template | Not Started | 0/3 |
| 3. Assets | Not Started | 0/3 |
| 4. Integration | Not Started | 0/2 |
| 5. Verification | Not Started | 0/3 |

**Total Progress**: 0/13 tasks complete
