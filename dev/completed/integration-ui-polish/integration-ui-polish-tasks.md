# Integration Page UI Polish - Tasks

**Last Updated:** 2026-01-03

---

## Phase 1: RED - Write Failing Tests

- [ ] **1.1** Add Slack Coming Soon tests to `tests/e2e/integration-flags.spec.ts`
  - [ ] `test_slack_shows_coming_soon_when_disabled`
  - [ ] `test_slack_shows_benefits_when_disabled`
  - [ ] `test_slack_shows_interested_button_when_disabled`

- [ ] **1.2** Add Copilot Coming Soon tests
  - [ ] `test_copilot_shows_coming_soon_when_disabled`
  - [ ] `test_copilot_shows_benefits_when_disabled`
  - [ ] `test_copilot_shows_interested_button_when_disabled`

- [ ] **1.3** Add icon background test
  - [ ] `test_icons_have_no_background`

- [ ] **1.4** Run E2E tests - confirm new tests FAIL
  ```bash
  npx playwright test integration-flags.spec.ts --reporter=list
  ```

---

## Phase 2: GREEN - Implement Changes

- [ ] **2.1** Remove icon backgrounds from all cards
  - Lines: ~82 (GitHub), ~152 (Jira), ~245 (Slack), ~332 (Copilot), ~393 (Google)
  - Remove: `bg-base-300 rounded-lg p-3`

- [ ] **2.2** Update Slack card with Coming Soon state
  - Add `{% if not slack_status.enabled %}` conditional
  - Add Coming Soon badge
  - Add benefits list from `slack_status.benefits`
  - Add "I'm Interested" button (proper btn styling)

- [ ] **2.3** Update Copilot card with Coming Soon state
  - Add `{% if not copilot_status.enabled %}` conditional
  - Add Coming Soon badge
  - Add benefits list from `copilot_status.benefits`
  - Add "I'm Interested" button (proper btn styling)

- [ ] **2.4** Replace Google Workspace icon
  - Change from SVG globe to `<i class="fa-brands fa-google">`

- [ ] **2.5** Improve Coming Soon badge contrast
  - Use `badge badge-warning` or custom high-contrast styling

---

## Phase 3: VERIFY - Run Tests

- [ ] **3.1** Run full E2E test suite
  ```bash
  npx playwright test integration-flags.spec.ts --reporter=list
  ```

- [ ] **3.2** Visual verification
  ```bash
  npx playwright test integration-flags.spec.ts --headed
  ```

- [ ] **3.3** Test I'm Interested → Thanks! swap on all cards

---

## Completion Criteria

- [ ] All E2E tests pass
- [ ] No icon backgrounds visible
- [ ] Slack shows Coming Soon + benefits + I'm Interested button
- [ ] Copilot shows Coming Soon + benefits + I'm Interested button
- [ ] Google has proper brand icon
- [ ] Coming Soon badge has good contrast
- [ ] All I'm Interested buttons work (HTMX swap)
