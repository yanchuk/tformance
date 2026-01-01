# Tformance Product Requirements Document

## MVP v1.0

**Document Version:** 1.0
**Date:** December 2025
**Status:** Draft for Review

---

## Related Documents

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture, integrations, security |
| [DATA-MODEL.md](DATA-MODEL.md) | Database schema, RLS policies |
| [SLACK-BOT.md](SLACK-BOT.md) | Slack bot specification, message templates |
| [DASHBOARDS.md](DASHBOARDS.md) | Dashboard views (Chart.js) |
| [ONBOARDING.md](ONBOARDING.md) | User onboarding flow |
| [COMPETITOR-RESEARCH.md](COMPETITOR-RESEARCH.md) | Market intelligence, competitor analysis (Dec 2025) |
| [JIRA-ENRICHMENT.md](JIRA-ENRICHMENT.md) | Rich Jira data for LLM correlation (Premium feature spec) |

---

## 1. Executive Summary

An analytics platform that helps CTOs of small-to-medium engineering teams understand whether AI coding tools are actually improving their team's performance.

**Core differentiator:** We don't just show metrics. We help answer: *"Is AI actually helping my team, or are we just paying for licenses?"*

**Key innovations:**
- **AI correlation analysis** - Connect AI tool usage with delivery outcomes
- **Gamified PR surveys** - Fun "AI Detective" game to capture quality feedback
- **GitHub-first onboarding** - Connect GitHub and your team is auto-discovered

---

## 2. Problem Statement

### The AI Productivity Paradox
- AI coding assistants increase individual code output by ~21%
- But code review time has increased by 91% as PR volume overwhelms reviewers
- CTOs have no visibility into whether AI adoption correlates with better outcomes

### Validated Pain Points (CTO Community Research)
| Pain Point | Mentions |
|------------|----------|
| Difficulty measuring team performance | 35 |
| Inefficient code review processes | 30 |
| Limited visibility into team performance | 6 |

### Market Gap
- Zero awareness of SEI tools (Jellyfish, LinearB) in target market
- No platform correlates AI tool usage with delivery outcomes
- Competitors charge $40-60/seat - too expensive for smaller teams

---

## 3. Target Customer

### Primary Buyer: CTO of Small-Medium Engineering Team

**Company Profile:**
- Team size: 10-50 developers
- Using or evaluating AI coding tools (GitHub Copilot, Cursor, etc.)
- GitHub for source control
- Jira for project management
- Slack for communication

**Core Question:**
> "Is AI actually helping my team deliver better, or are we just generating more code that creates more review burden?"

---

## 4. MVP Scope

### Integrations

| Platform | Data | Sync Frequency |
|----------|------|----------------|
| GitHub | PRs, commits, reviews, org members | Daily + webhooks |
| Jira | Issues, story points, sprints | Daily |
| GitHub Copilot | Usage metrics (5+ licensed users required) | Daily |
| Slack | Bot for surveys + leaderboard | Real-time |

> **Note:** Cursor integration moved to v2 (requires Enterprise tier). MVP relies on self-reported AI attribution via PR surveys.

### Features

| Feature | Description |
|---------|-------------|
| **AI Correlation Dashboard** | Visualize AI usage vs delivery metrics |
| **PR Survey System** | Author: "AI-assisted?" / Reviewer: Quality rating + AI guess |
| **AI Detective Game** | Reveal if reviewer guessed correctly, weekly leaderboard |
| **Layered Visibility** | Dev sees own, Lead sees team, CTO sees all |
| **Auto User Discovery** | Import team from GitHub org automatically |

### Not MVP (v2+)

- Cursor integration (Enterprise API)
- Calendar/Slack communication metrics
- Work type detection (backend/frontend)
- Time tracking
- Comparison views
- Alerts & notifications

---

## 5. Key Metrics Tracked

| Category | Metric | Source |
|----------|--------|--------|
| **Delivery** | PR Throughput | GitHub |
| | Cycle Time (PR open → merge) | GitHub |
| | Review Time | GitHub |
| | Change Failure Rate (reverts) | GitHub |
| **Jira** | Velocity (story points/sprint) | Jira |
| | Issue Cycle Time | Jira |
| **AI Usage** | Copilot metrics | GitHub API |
| | AI-assisted PRs | Self-reported survey |
| **Quality** | PR Quality Rating (1-3) | Reviewer survey |
| | AI Detection Rate | Guessing game |

---

## 6. User Stories

### CTO
- View dashboard correlating AI usage with delivery metrics
- See if AI-assisted PRs have different quality ratings
- Prepare for 1:1s with individual developer data
- Configure team settings and user mapping

### Developer
- Receive quick Slack survey after PR merge (1 click)
- See only my own metrics and team aggregates
- Participate in AI Detective game
- View my quality ratings and trends

### Reviewer
- Rate PR quality after merge (Could be better / OK / Super)
- Guess if PR was AI-assisted
- See reveal and track guess accuracy
- Compete on weekly leaderboard

---

## 7. Data & Security

### Data Storage

| Data | Location |
|------|----------|
| OAuth tokens | Our service (encrypted) |
| Account/billing | Our service |
| All metrics | Our database (team-isolated) |
| Survey responses | Our database (team-isolated) |
| User data | Our database (team-isolated) |

### Security Approach
- All data isolated by team (team_id foreign key on all tables)
- OAuth tokens encrypted at rest (Fernet/AES-256)
- Role-based access control enforced at application layer
- Data export available on request

### Visibility Model
| Role | Individual Data | Team Aggregates |
|------|-----------------|-----------------|
| Developer | Own only | Their team |
| Team Lead | Their team | Their team |
| CTO/Admin | Everyone | All teams |

See [ARCHITECTURE.md](ARCHITECTURE.md) for full security details.

---

## 8. Technical Approach

### Architecture
- **Backend:** Django (sync workers, Slack bot, auth)
- **Database:** PostgreSQL (single database, team-isolated)
- **Dashboards:** Native (Chart.js + HTMX + DaisyUI)
- **Sync:** Daily batch + GitHub webhooks for real-time PR events

### Why Daily Sync (not hourly)
- Analytics don't need real-time data
- Reduces API rate limit concerns
- Simpler implementation
- Lower infrastructure costs

See [ARCHITECTURE.md](ARCHITECTURE.md) for full technical details.

---

## 9. Pricing

### Model: Per Seat

| Tier | Price | Includes |
|------|-------|----------|
| Trial | Free | Up to 5 seats, 14 days |
| Team | $X/seat/month | Full features |
| Annual | $X/seat/month | 20% discount |

### Seat Definition
- Seat = user synced from GitHub org
- Inactive users (no activity 30 days) don't count
- CTO/admin accounts are free

### Pricing TBD
- Target: $10-25/seat/month (below competitors at $40-60)

---

## 10. Success Metrics

| Metric | Target (Month 3) | Target (Month 6) |
|--------|------------------|------------------|
| Signed up companies | 20 | 100 |
| Paying customers | 5 | 30 |
| Survey response rate | 60% | 75% |
| Customer churn | <5%/month | <5%/month |

---

## 11. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Low survey response rate | Gamification, minimal friction |
| "Surveillance" perception | Privacy-first messaging, layered visibility |
| GitHub API rate limits | Daily sync, caching |

---

## 12. Open Questions

| Question | Decision Needed By |
|----------|-------------------|
| Exact pricing | Before launch |
| Product name | Before launch |

---

## 13. Competitor Comparison

> **Note:** See [COMPETITOR-RESEARCH.md](COMPETITOR-RESEARCH.md) for comprehensive analysis of 7 competitors.

### Market Evolution (Dec 2025)
All major competitors have now added AI measurement features. Our differentiation has shifted:

| Feature | Our MVP | Jellyfish | LinearB | Swarmia | Span | Workweave |
|---------|---------|-----------|---------|---------|------|-----------|
| AI usage correlation | ✅ Core | ✅ New | ✅ New | ✅ New | ✅ Core | ✅ Core |
| **Gamified surveys** | ✅ Unique | ❌ | ❌ | ❌ | ❌ | ❌ |
| AI code detection | Survey | Yes | Partial | Partial | 95% ML | 94% ML |
| GitHub-first onboarding | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| GitHub/Jira metrics | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Free tier | Trial | ❌ | 8 users | 9 devs | ❌ | 5 devs |
| Price/seat | **$10-25** | ~$50+ | $35-46 | €22-42 | Custom | $50 |

### Updated Differentiation Strategy

1. **Gamified "AI Detective" game** - Only platform making data collection fun
2. **Price accessibility** - 50-70% cheaper than all competitors
3. **SMB focus** - 10-50 dev teams (competitors chasing enterprise)

### Emerging Threats
- **Span**: 95% AI code detection accuracy (technical approach vs our survey approach)
- **Swarmia**: Similar free tier strategy, strong G2 reviews (4.4/5)
- **Workweave**: $4.2M funding, aggressive AI positioning

---

## Appendix: Research References

- CTO Community Chat Analysis (88,939 messages, Dec 2023 - Nov 2025)
- Gemini Market Research: SEI Market Analysis
- ChatGPT Research: Engineering Performance Management SaaS
- GitHub Copilot API Documentation
- Competitor Research (Dec 2025) - See [COMPETITOR-RESEARCH.md](COMPETITOR-RESEARCH.md)

---

*Document created: December 2025*
