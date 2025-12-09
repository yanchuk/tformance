# High-Level Implementation Plan

> Part of [PRD Documentation](README.md)

## Overview

This document outlines the logical order of building the MVP, focusing on dependencies and milestones rather than specific technologies.

---

## Guiding Principles

1. **Validate core hypothesis early** - Get to "AI correlation visible" as fast as possible
2. **Minimize custom UI** - Leverage existing tools for dashboards
3. **Integration-first** - Each integration should be independently testable
4. **Data flows before features** - Ensure data pipeline works before building features on top

---

## Phase 0: Foundation

**Goal:** Basic infrastructure to build on

### 0.1 Project Setup
- Repository structure
- Development environment
- CI/CD pipeline basics

### 0.2 Authentication & Accounts
- User registration/login
- Organization (company) entity
- Admin role assignment
- Session management

### 0.3 Encrypted Secret Storage
- Secure storage for OAuth tokens
- Encryption at rest
- Key rotation capability

**Milestone:** Can create account, login, see empty dashboard shell

---

## Phase 1: Client Database Connection (BYOS)

**Goal:** Client can connect their own database

### 1.1 Database Connection Flow
- Accept connection credentials from client
- Test connection validity
- Store connection info securely

### 1.2 Schema Provisioning
- Migration scripts for all required tables
- Run migrations on client database
- Verify schema is correct

### 1.3 Connection Health
- Periodic connection health check
- Alert if connection lost
- Reconnection handling

**Milestone:** Client connects Supabase, tables are created, connection verified

**Why first:** Everything else writes to client database - need this working before any integration

---

## Phase 2: GitHub Integration

**Goal:** Import team and PR data from GitHub

### 2.1 OAuth Flow
- GitHub OAuth app setup
- Authorization flow
- Token storage (encrypted)
- Token refresh handling

### 2.2 Organization Discovery
- Fetch org members on connect
- Create user records in client DB
- Fetch team structure (if GitHub Teams used)

### 2.3 Repository Selection
- List available repositories
- Allow selection of repos to track
- Store repo configuration

### 2.4 Webhook Setup
- Register webhooks for selected repos
- Handle `pull_request` events
- Handle `pull_request_review` events

### 2.5 Historical Data Sync
- Fetch existing PRs (last N days)
- Fetch commits per PR
- Calculate cycle time, review time
- Detect reverts/hotfixes

### 2.6 Incremental Sync
- Daily sync job
- Fetch only updated PRs since last sync
- Update metrics in client DB

**Milestone:** GitHub connected, team imported, PRs visible in database, webhooks working

**Why second:** GitHub provides user discovery (team import) which all other integrations depend on for user matching

---

## Phase 3: Jira Integration

**Goal:** Import project management data

### 3.1 OAuth Flow
- Atlassian OAuth setup
- Authorization flow
- Token storage and refresh

### 3.2 Project Selection
- List available Jira projects
- Allow selection of projects to track
- Store project configuration

### 3.3 User Matching
- Fetch Jira users
- Match to GitHub users by email
- Flag unmatched users for manual resolution

### 3.4 Historical Data Sync
- Fetch issues from selected projects
- Extract story points, sprint data
- Calculate issue cycle time

### 3.5 Incremental Sync
- Daily sync job
- JQL query for recently updated issues
- Update metrics in client DB

**Milestone:** Jira connected, issues synced, matched to GitHub users

**Why third:** Depends on GitHub users existing to match against

---

## Phase 4: Basic Dashboard

**Goal:** First visible value - CTO can see metrics

### 4.1 Dashboard Tool Setup
- Install/configure BI tool
- Connect to client database template
- Set up embedding mechanism

### 4.2 Core Metrics Dashboard
- PR throughput chart
- Cycle time trend
- Review time trend
- Jira velocity (if connected)

### 4.3 User Context Filtering
- Pass user role to dashboard
- Filter data based on permissions
- Layered visibility working

### 4.4 Dashboard Embedding
- Embed dashboard in app
- Handle authentication/authorization
- Basic navigation between views

**Milestone:** CTO can login and see real metrics from their GitHub/Jira

**Why fourth:** This is first "value delivered" moment - everything before was setup

---

## Phase 5: Slack Integration & Surveys

**Goal:** Enable the AI Detective game

### 5.1 Slack OAuth Flow
- Slack app setup
- Authorization flow
- Bot token storage

### 5.2 User Matching
- Fetch Slack workspace users
- Match to GitHub/Jira users by email
- Flag unmatched for resolution

### 5.3 PR Survey - Author
- Trigger on PR merge (webhook from Phase 2)
- Look up author's Slack ID
- Send DM with "AI assisted?" question
- Handle button response
- Store response in client DB

### 5.4 PR Survey - Reviewer
- Identify reviewers from PR data
- Send DM with quality rating + AI guess
- Handle button responses
- Store responses in client DB

### 5.5 Reveal Mechanism
- Detect when both author and reviewer responded
- Calculate if guess was correct
- Send reveal message to reviewer
- Update guess accuracy stats

**Milestone:** PR merges trigger surveys, responses collected, reveals sent

**Why fifth:** Depends on GitHub webhooks (Phase 2) and user matching (Phase 3)

---

## Phase 6: AI Correlation Dashboard

**Goal:** The unique value - see AI impact

### 6.1 Survey Data Visualization
- Add AI-assisted % to dashboards
- Quality rating distribution
- AI detection accuracy stats

### 6.2 Correlation Views
- AI-assisted PRs vs cycle time
- AI-assisted PRs vs quality ratings
- AI adoption trend over time

### 6.3 Individual AI Attribution
- Per-developer AI usage (from surveys)
- Correlation with their output metrics

**Milestone:** CTO can answer "Is AI helping?" with data

**Why sixth:** Needs survey data (Phase 5) to correlate

---

## Phase 7: Weekly Aggregation & Leaderboard

**Goal:** Polish and engagement

### 7.1 Weekly Metrics Aggregation
- Scheduled job to compute weekly rollups
- Store in aggregated metrics table
- Faster dashboard queries

### 7.2 Weekly Slack Leaderboard
- Scheduled job (configurable day/time)
- Compute rankings
- Post to configured channel

### 7.3 Leaderboard Configuration
- Admin can set channel
- Admin can set schedule
- Admin can enable/disable

**Milestone:** Weekly leaderboard posting, engagement loop complete

---

## Phase 8: Copilot Metrics (Enhancement)

**Goal:** Add API-based AI usage data

### 8.1 Copilot API Integration
- Check if org has 5+ Copilot licenses
- Fetch team-level metrics
- Handle "not available" gracefully

### 8.2 Dashboard Enhancement
- Add Copilot metrics to dashboards
- Correlate with delivery metrics

**Milestone:** Teams with Copilot see richer AI usage data

**Why eighth:** Optional enhancement - MVP works without it (surveys provide AI data)

---

## Phase 9: Onboarding Polish

**Goal:** Smooth self-service setup

### 9.1 Guided Setup Flow
- Step-by-step wizard
- Progress indicator
- Skip options for optional integrations

### 9.2 User Mapping Resolution
- Admin UI for manual matching
- Bulk actions
- Exclude option (for bots)

### 9.3 First-Run Experience
- Helpful empty states
- "What to expect" messaging
- Email after setup complete

**Milestone:** New customer can self-onboard without support

---

## Phase 10: Billing & Launch Prep

**Goal:** Ready for paying customers

### 10.1 Seat Counting
- Count active users from client DB
- Exclude inactive (no activity 30 days)
- Exclude admin accounts

### 10.2 Billing Integration
- Payment provider integration
- Subscription management
- Trial → paid conversion

### 10.3 Usage Limits
- Enforce trial limits (5 seats, 14 days)
- Upgrade prompts
- Grace period handling

### 10.4 Admin Dashboard
- Your own metrics (signups, conversions)
- Customer health monitoring
- Support tooling

**Milestone:** Can accept payments, trial limits enforced

---

## Dependency Graph

```
Phase 0: Foundation
    │
    ▼
Phase 1: Client DB (BYOS)
    │
    ▼
Phase 2: GitHub ─────────────────┐
    │                            │
    ▼                            │
Phase 3: Jira                    │
    │                            │
    ▼                            ▼
Phase 4: Basic Dashboard    Phase 5: Slack & Surveys
    │                            │
    └────────────┬───────────────┘
                 │
                 ▼
          Phase 6: AI Correlation Dashboard
                 │
                 ▼
          Phase 7: Leaderboard
                 │
                 ▼
          Phase 8: Copilot (optional)
                 │
                 ▼
          Phase 9: Onboarding Polish
                 │
                 ▼
          Phase 10: Billing & Launch
```

---

## Minimum Viable Product Checkpoint

**After Phase 6, you have an MVP:**
- ✅ Client can connect their database
- ✅ GitHub and Jira data syncing
- ✅ Dashboard showing metrics
- ✅ PR surveys working
- ✅ AI correlation visible

Phases 7-10 are polish and monetization.

**First "wow" moment:** Phase 6 completion
**First paying customer possible:** Phase 10 completion

---

## Risk-Ordered Alternatives

If timeline is tight, consider:

| Original | Alternative | Trade-off |
|----------|-------------|-----------|
| BYOS (client Supabase) | We host everything | Simpler but less differentiation |
| Metabase embedding | Simple tables/charts | Less powerful but faster to build |
| Slack bot | Email surveys | Lower engagement but simpler |
| Daily sync | Manual sync button | Less automated but works |

---

## Parallel Work Opportunities

These can happen in parallel with different people/streams:

| Stream A | Stream B |
|----------|----------|
| Phase 1 (BYOS) | Phase 0.2 (Auth) |
| Phase 2 (GitHub) | Dashboard design |
| Phase 3 (Jira) | Phase 5 (Slack) prep |
| Phase 4 (Dashboard) | Phase 5 (Slack) |
| Phase 8 (Copilot) | Phase 9 (Onboarding) |

---

## Estimated Relative Effort

| Phase | Complexity | Why |
|-------|------------|-----|
| 0. Foundation | Medium | Standard but foundational |
| 1. BYOS | Medium | Novel pattern, security critical |
| 2. GitHub | High | Most complex integration, webhooks |
| 3. Jira | Medium | Similar pattern to GitHub |
| 4. Dashboard | Medium | Depends on tool choice |
| 5. Slack | High | Interactive, real-time, multiple flows |
| 6. AI Correlation | Low | Dashboard additions |
| 7. Leaderboard | Low | Scheduled job + message |
| 8. Copilot | Low | Single API integration |
| 9. Onboarding | Medium | Many edge cases |
| 10. Billing | Medium | Third-party integration |

**Heaviest lifts:** GitHub integration, Slack bot
**Quickest wins:** Copilot metrics, Leaderboard
