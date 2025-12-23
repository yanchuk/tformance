# Onboarding Page Controls Implementation Plan

**Last Updated: 2025-12-22**

## Executive Summary

Add logout button, skip control, and value-focused messaging to the onboarding flow to improve user experience and clearly communicate the value proposition to CTOs.

## Completed Implementation

### Phase 1: Navigation Controls

#### 1.1 Logout Button (All Pages)
- **File**: `templates/onboarding/base.html`
- Added logout button to top navigation bar next to user email
- Uses `app-btn-ghost` styling with `fa-right-from-bracket` icon
- Includes `aria-label` for accessibility
- Links to Django allauth's `account_logout` URL

#### 1.2 Skip Control (Start Page)
- **File**: `templates/onboarding/start.html`
- Added "Skip for now" link below GitHub connection card
- Uses subtle styling (`text-base-content/60`) to not overshadow primary action
- Includes explanatory text: "You can connect GitHub later from settings"
- Links to `web:home` (`/app/`)

### Phase 2: Scope & Value Messaging Updates

#### 2.1 GitHub Start Page (`templates/onboarding/start.html`)
**Scope alignment with actual OAuth scopes:**
- Organization members → `read:org` scope
- Pull requests & reviews → `repo` scope
- Copilot usage metrics → `manage_billing:copilot` scope

**Value messaging for ICP (CTOs):**
- "Auto-discover your team — no manual setup required"
- "Track cycle time, review time, and throughput metrics"
- "Correlate AI tool usage with delivery outcomes"

**Privacy emphasis:**
- "We never see your code — only PR metadata like titles, timestamps, and review counts."
- Shield icon for visual trust indicator

#### 2.2 Repository Selection (`templates/onboarding/select_repos.html`)
**Value messaging:**
- "Focus on what matters" — Track repos where team actively creates PRs
- "Reduce noise" — Exclude docs, infrastructure, and archived repos

**Current state:**
- Info alert: "Repository selection coming soon. For now, we'll sync all organization repos."

#### 2.3 Jira Connection (`templates/onboarding/connect_jira.html`)
**Value messaging:**
- "Sprint velocity" — Track story points delivered per sprint
- "Issue cycle time" — Measure time from start to done
- "PR-to-issue linking" — Connect code changes to business outcomes

**UI improvements:**
- Changed icon color from `text-cyan` to `text-accent` for consistency
- Added "What you'll get:" section with benefits list

#### 2.4 Slack Connection (`templates/onboarding/connect_slack.html`)
**Value messaging:**
- "PR surveys via DM" — Quick 1-click surveys to capture AI-assisted PRs
- "Weekly leaderboards" — Gamified AI Detective rankings to drive engagement
- "Higher response rates" — Meet developers in their workflow, not email

**UI improvements:**
- Changed icon color from `text-cyan` to `text-accent` for consistency
- Added "What you'll get:" section with benefits list

### Phase 3: E2E Tests

Added 4 new tests to `tests/e2e/onboarding.spec.ts`:
1. `logout button is visible on onboarding pages`
2. `logout button logs user out`
3. `skip control is visible on onboarding start page`
4. `skip link navigates to app home`

## Files Modified

| File | Changes |
|------|---------|
| `templates/onboarding/base.html` | Added logout button to nav |
| `templates/onboarding/start.html` | Added skip control, scope/value messaging, privacy statement |
| `templates/onboarding/select_repos.html` | Added icon, value messaging |
| `templates/onboarding/connect_jira.html` | Added value messaging, consistent styling |
| `templates/onboarding/connect_slack.html` | Added value messaging, consistent styling |
| `tests/e2e/onboarding.spec.ts` | Added 4 new E2E tests |

## Design Decisions

### 1. Privacy-First Messaging
- Emphasized "We never see your code" prominently
- Listed exactly what data we access (PR metadata only)
- Used shield icon for visual trust indicator

### 2. Value Proposition Structure
Each step now has:
- Clear header with icon
- "What you'll get:" or "What we'll access and why:" section
- Bullet points connecting data access to CTO value
- Optional indicator for non-required steps

### 3. Consistent Styling
- Changed from `text-cyan` to `text-accent` for DaisyUI theme consistency
- All icons use `text-accent` color
- All cards follow same structure pattern

## Test Results

- **E2E Tests**: 14 passed, 1 skipped
- **Unit Tests**: 5 passed
- **No regressions**

## Key Value Props by Step

| Step | Data Access | CTO Value |
|------|-------------|-----------|
| GitHub | Org members, PRs, Copilot | Team discovery, delivery metrics, AI correlation |
| Repos | Repository list | Focus on active development repos |
| Jira | Issues, story points, sprints | Sprint velocity, cycle time, business outcomes |
| Slack | Bot messaging | Higher survey response rates, team engagement |
