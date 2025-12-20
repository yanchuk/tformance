# Visual Merge & Completion - Task Checklist

**Last Updated:** 2025-12-20

---

## Phase 1: Commit Pending Changes

### 1.1 Commit visual-chrome (Stages 6, 8)
- [ ] Add all modified files
- [ ] Add new chart-theme.js
- [ ] Add dev docs directory
- [ ] Commit with message
- [ ] Verify `npm run build` passes

### 1.2 Commit visual-dashboard (Stages 5, 9)
- [ ] Navigate to dashboard worktree
- [ ] Add all modified template files
- [ ] Add dev docs directory
- [ ] Commit with message
- [ ] Verify `npm run build` passes

---

## Phase 2: Merge to Main

### 2.1 Merge visual-landing → main
- [ ] Switch to main worktree
- [ ] Pull latest main
- [ ] Merge visual-landing branch
- [ ] Run `make e2e-smoke`
- [ ] Verify no merge conflicts

### 2.2 Merge visual-dashboard → main
- [ ] Merge visual-dashboard branch
- [ ] Run `make e2e-dashboard`
- [ ] Verify no merge conflicts

### 2.3 Merge visual-chrome → main
- [ ] Merge visual-chrome branch
- [ ] Run full `make e2e`
- [ ] Verify no merge conflicts

### 2.4 Clean up worktrees
- [ ] Remove visual-landing worktree
- [ ] Remove visual-dashboard worktree
- [ ] Remove visual-chrome worktree
- [ ] Delete merged branches

---

## Phase 3: Stage 7 Verification (Buttons & Forms)

### 3.1 Verify Button Classes
- [ ] Check `.app-btn-primary` in design-system.css
- [ ] Confirm uses `bg-accent-primary hover:bg-orange-600`
- [ ] Confirm focus ring uses `ring-accent-primary/50`

### 3.2 Verify Form Inputs
- [ ] Check `.app-input` focus styling
- [ ] Confirm uses `border-accent-primary` on focus
- [ ] Check `.app-error` uses `text-accent-error`

### 3.3 Visual Verification
- [ ] Test login page form styling
- [ ] Test signup page form styling
- [ ] Run `make e2e-auth`

---

## Phase 4: Stage 10 - Accessibility Audit

### 4.1 Lighthouse Audit
- [ ] Run Lighthouse on landing page
- [ ] Run Lighthouse on dashboard
- [ ] Score ≥ 90 for accessibility

### 4.2 Contrast Verification
- [ ] Primary text on deep: 15.5:1 ✓ (pre-verified)
- [ ] Accent-primary on deep: 5.2:1 ✓ (pre-verified)
- [ ] Accent-tertiary on deep: 9.3:1 ✓ (pre-verified)
- [ ] Accent-error on deep: 5.8:1 ✓ (pre-verified)

### 4.3 Keyboard Navigation
- [ ] Tab through all navigation items
- [ ] Verify focus indicators visible
- [ ] Test form field navigation

### 4.4 Reduced Motion
- [ ] Test with `prefers-reduced-motion`
- [ ] Verify animations respect preference

---

## Phase 5: Stage 11 - Final Integration

### 5.1 Full Test Suite
- [ ] Run `make test ARGS='--keepdb'`
- [ ] Run `make e2e`
- [ ] All tests pass

### 5.2 Visual Review
- [ ] Landing page hero - warm gradient, orange CTA
- [ ] Features section - warm icons
- [ ] Login/signup - warm form focus
- [ ] Dashboard - warm metric cards
- [ ] Charts - coral orange bars, purple for AI
- [ ] Navigation - warm active states
- [ ] Empty states - warm icons and CTAs

### 5.3 Documentation Cleanup
- [ ] Move visual-stage-* docs to dev/completed/
- [ ] Move visual-merge-completion to dev/completed/
- [ ] Verify dev/active/ is clean

### 5.4 Final Commit
- [ ] Commit any final changes
- [ ] Push main to origin
- [ ] Visual improvement complete

---

## Rollback Plan

If issues arise after merging:

```bash
# Find the commit before merges
git log --oneline -10

# Reset to pre-merge state
git reset --hard <commit-hash>

# Force update main
git push origin main --force  # Use with caution!
```

---

## Notes

- All color combinations pre-verified for WCAG AA compliance
- Merge order is important: landing → dashboard → chrome
- Run tests after each merge to catch issues early
- Keep worktrees until all merges verified
