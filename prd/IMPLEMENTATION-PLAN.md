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
5. **Start simple, scale later** - Single database now, BYOS option later

---

## Architecture Decision: Single Database (MVP)

### Why Single-DB for MVP

| Factor | Single DB | BYOS (Client DB) |
|--------|-----------|------------------|
| **Time to market** | Faster | Slower (complex) |
| **Onboarding friction** | Low | High (client setup) |
| **Maintenance** | Simple | Complex (N databases) |
| **Data security pitch** | "We secure it" | "Your data, your DB" |
| **Migration path** | Can add BYOS later | N/A |

**Decision:** Start with single database. Add BYOS as premium feature in Phase 12 if customer demand exists.

### Data Isolation Strategy

Even with single database, we maintain strict team isolation:
- All metric tables have `team_id` foreign key
- Django querysets use `for_team` manager (auto-filters)
- Row-level access enforced at application layer
- Can migrate to BYOS later with data export

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

## Phase 1: Core Data Models

**Goal:** Database schema for all metrics data

### 1.1 User & Team Models
- Extend existing Team model with integration fields
- Create TeamMember model (GitHub/Jira/Slack IDs)
- User matching logic (email-based)

### 1.2 GitHub Metrics Models
- PullRequest model
- PRReview model
- Commit model
- Calculated fields (cycle_time, review_time)

### 1.3 Jira Metrics Models
- JiraIssue model
- Sprint tracking fields
- Story points, resolution time

### 1.4 AI Usage Models
- AIUsageDaily model (Copilot metrics)
- PRSurvey model (author response)
- PRSurveyReview model (reviewer response)

### 1.5 Aggregated Metrics
- WeeklyMetrics model
- Pre-computed rollups for dashboard performance

**Milestone:** All models created, migrations applied, admin accessible

**Why first:** All integrations need these models to write to

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
- Create TeamMember records
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
- Daily sync job (Celery)
- Fetch only updated PRs since last sync
- Update metrics in database

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
- Update metrics in database

**Milestone:** Jira connected, issues synced, matched to GitHub users

**Why third:** Depends on GitHub users existing to match against

---

## Phase 4: Basic Dashboard

**Goal:** First visible value - CTO can see metrics

### 4.1 Dashboard Infrastructure
- Create dashboard views and templates
- Set up Chart.js integration (already in codebase via Vite)
- Configure HTMX lazy loading pattern for charts

### 4.2 Core Metrics Dashboard
- PR throughput chart (bar chart)
- Cycle time trend (line chart)
- Review time trend (line chart)
- Jira velocity (if connected)
- Stat cards with DaisyUI styling

### 4.3 User Context Filtering
- Django view-level permission checks
- Filter data based on user role
- Layered visibility working (dev/lead/admin)

### 4.4 Dashboard Components
- Reusable chart components (line, bar, pie, scatter)
- Stat card components
- Data table components with sorting/filtering
- Date range filter component

**Milestone:** CTO can login and see real metrics from their GitHub/Jira

**Why fourth:** This is first "value delivered" moment - everything before was setup

**Technical Approach:**
- Chart.js 4.5.1 already installed via Vite
- Existing utilities in `assets/javascript/dashboard/dashboard-charts.js`
- HTMX `hx-trigger="load"` for lazy loading charts
- DaisyUI components for consistent styling

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
- Store response in database

### 5.4 PR Survey - Reviewer
- Identify reviewers from PR data
- Send DM with quality rating + AI guess
- Handle button responses
- Store responses in database

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
- Count active users from database
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

## Phase 11: AI Agent Feedback System

**Goal:** Help teams improve their AI coding assistants by collecting actionable feedback

### Why This Feature

**Value Proposition:** "We help improve your AI agent's performance"

Teams using AI coding tools (Cursor, GitHub Copilot, Claude Code, etc.) often struggle to improve their agent configurations. This feature:

1. **Captures real friction** - When devs hit issues with AI-generated code, capture what went wrong
2. **Aggregates patterns** - Identify common failure modes across the team
3. **Generates improvements** - Suggest updates to agent.md, .cursorrules, or similar config files
4. **Closes the loop** - Track if suggested improvements actually help

### Sales Pitch

> "Your AI coding assistant is only as good as its rules. We analyze your team's AI interactions to surface what's working, what's not, and suggest specific improvements to your agent configuration. Stop guessing - let data drive your AI setup."

### 11.1 Feedback Collection

**In-App Feedback Button**
- "Report AI Issue" button in dashboard
- Quick categorization (wrong code, missed context, style issue, etc.)
- Link to specific PR/commit
- Free-text description

**Slack Integration**
- Reaction-based feedback on PR survey messages
- "AI got this wrong" quick action
- Thread-based discussion capture

**PR Comment Analysis** (Future)
- Detect patterns like "AI generated but had to fix..."
- Auto-categorize common issues

### 11.2 Feedback Aggregation

**Pattern Detection**
- Group similar issues by category
- Identify file types/languages with most issues
- Surface repeated problems (e.g., "always forgets to add tests")

**Team Analytics**
- Feedback volume trends
- Most common issue categories
- Resolution rate (issues that stopped recurring)

### 11.3 Agent Rule Suggestions

**Rule Generation**
- Analyze feedback patterns
- Generate suggested additions to agent config files
- Support multiple formats:
  - `agent.md` (Claude Code)
  - `.cursorrules` (Cursor)
  - `.github/copilot-instructions.md` (Copilot)

**Example Output:**
```markdown
## Suggested Addition to agent.md

Based on 12 feedback reports about missing test coverage:

### Testing Requirements
- Always create unit tests for new functions
- Use pytest fixtures from `tests/conftest.py`
- Follow existing test patterns in `tests/` directory
```

### 11.4 Improvement Tracking

**Before/After Metrics**
- Track issue frequency before rule added
- Track issue frequency after rule added
- Calculate improvement percentage

**Rule Effectiveness Dashboard**
- Which rules had most impact
- Which rules need refinement
- Suggested rule removals (if not helping)

### 11.5 Export & Integration

**Config File Export**
- One-click export to supported formats
- Diff view showing changes
- Version history

**Integration Options**
- GitHub PR to update rules (future)
- Slack notification when new suggestion ready
- Webhook for custom integrations

**Milestone:** Teams can capture AI feedback, see aggregated patterns, and get actionable config improvements

**Why this phase:** Unique differentiator - no one else is closing the AI improvement loop. Strong upsell opportunity.

---

## Phase 12: BYOS (Premium Feature)

**Goal:** Enterprise option for client-hosted data

> Implement only if customer demand validates this need

### 12.1 Database Connection Flow
- Accept connection credentials from client
- Test connection validity
- Store connection info securely (encrypted)

### 12.2 Schema Provisioning
- Migration scripts for all required tables
- Run migrations on client database
- Verify schema is correct

### 12.3 Connection Health
- Periodic connection health check
- Alert if connection lost
- Reconnection handling

### 12.4 Data Migration
- Export existing data from shared DB
- Import into client's DB
- Verify integrity

**Milestone:** Enterprise clients can use their own Supabase

**Why last:** Complexity vs. demand tradeoff - validate need first

---

## Dependency Graph

```
Phase 0: Foundation
    │
    ▼
Phase 1: Core Data Models
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
                 │
                 ▼
          Phase 11: AI Feedback System
                 │
                 ▼
          Phase 12: BYOS (if demand)
```

---

## Minimum Viable Product Checkpoint

**After Phase 6, you have an MVP:**
- ✅ Data models for all metrics
- ✅ GitHub and Jira data syncing
- ✅ Dashboard showing metrics
- ✅ PR surveys working
- ✅ AI correlation visible

Phases 7-12 are polish, differentiation, and monetization.

**First "wow" moment:** Phase 6 completion
**First paying customer possible:** Phase 10 completion
**Key differentiator:** Phase 11 (AI Feedback System)

---

## Risk-Ordered Alternatives

If timeline is tight, consider:

| Original | Alternative | Trade-off |
|----------|-------------|-----------|
| Full Chart.js dashboards | Simple HTML tables | Less visual but faster to build |
| Slack bot | Email surveys | Lower engagement but simpler |
| Daily sync | Manual sync button | Less automated but works |
| AI Feedback System | Manual feedback form | Less sophisticated but validates demand |

---

## Parallel Work Opportunities

These can happen in parallel with different people/streams:

| Stream A | Stream B |
|----------|----------|
| Phase 1 (Models) | Phase 0.2 (Auth polish) |
| Phase 2 (GitHub) | Dashboard design |
| Phase 3 (Jira) | Phase 5 (Slack) prep |
| Phase 4 (Dashboard) | Phase 5 (Slack) |
| Phase 8 (Copilot) | Phase 9 (Onboarding) |
| Phase 10 (Billing) | Phase 11 (AI Feedback) |

---

## Estimated Relative Effort

| Phase | Complexity | Why |
|-------|------------|-----|
| 0. Foundation | Medium | Standard but foundational |
| 1. Core Models | Low | Standard Django models |
| 2. GitHub | High | Most complex integration, webhooks |
| 3. Jira | Medium | Similar pattern to GitHub |
| 4. Dashboard | Low | Chart.js already integrated |
| 5. Slack | High | Interactive, real-time, multiple flows |
| 6. AI Correlation | Low | Dashboard additions |
| 7. Leaderboard | Low | Scheduled job + message |
| 8. Copilot | Low | Single API integration |
| 9. Onboarding | Medium | Many edge cases |
| 10. Billing | Medium | Third-party integration |
| 11. AI Feedback | Medium | Novel feature, ML-adjacent |
| 12. BYOS | High | Multi-tenant DB complexity |

**Heaviest lifts:** GitHub integration, Slack bot, BYOS
**Quickest wins:** Copilot metrics, Leaderboard
**Key differentiator:** AI Feedback System (Phase 11)
