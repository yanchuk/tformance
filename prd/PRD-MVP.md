# Tformance Product Requirements Document

## MVP v1.1

**Document Version:** 1.1
**Date:** January 2026
**Status:** Updated to reflect current implementation

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
- **Multi-layer AI detection** - LLM analysis + pattern matching + surveys for comprehensive AI usage tracking
- **AI correlation analysis** - Connect AI tool usage with delivery outcomes
- **Two-phase onboarding** - Dashboard accessible in ~5 min, historical data loads in background
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
| GitHub | PRs, commits, reviews, org members | Daily (4AM UTC) + webhooks |
| Jira | Issues, story points, sprints | Daily (4:30AM UTC) - Feature-flagged |
| GitHub Copilot | Usage metrics (5+ licensed users required) | Manual/On-demand |
| Slack | Bot authentication, web-based surveys | Real-time auth |

> **Note:** Jira, Slack, and Copilot integrations are controlled by feature flags and can be skipped during onboarding. Cursor integration moved to v2 (requires Enterprise tier).

### Features

| Feature | Description |
|---------|-------------|
| **AI Correlation Dashboard** | Visualize AI usage vs delivery metrics |
| **PR Survey System** | Web-based surveys for author AI disclosure and reviewer quality ratings |
| **Multi-Layer AI Detection** | LLM analysis + pattern matching + signal aggregation (see Section 5.5) |
| **Layered Visibility** | Dev sees own, Lead sees team, CTO sees all |
| **Auto User Discovery** | Import team from GitHub org automatically |
| **Two-Phase Onboarding** | Fast dashboard access (30 days), background historical sync |

### Not MVP (v2+)

- Cursor integration (Enterprise API)
- Calendar/Slack communication metrics
- Work type detection (backend/frontend)
- Time tracking
- Comparison views
- Alerts & notifications
- AI Detective Game (weekly leaderboard, gamification UI)
- Slack survey delivery (currently web-only)

---

## 5. Key Metrics Tracked

| Category | Metric | Source |
|----------|--------|--------|
| **Delivery** | PR Throughput | GitHub |
| | Cycle Time (PR open → merge) | GitHub |
| | Review Time | GitHub |
| | Change Failure Rate (reverts) | GitHub |
| | Review Rounds (iterations) | GitHub |
| | Fix Response Time | GitHub |
| **Jira** | Velocity (story points/sprint) | Jira |
| | Issue Cycle Time | Jira |
| **AI Usage** | Copilot metrics | GitHub API (manual) |
| | AI-assisted PRs | LLM + Pattern detection |
| | AI Tool Breakdown | LLM analysis |
| **Quality** | PR Quality Rating (1-3) | Web surveys |
| **Tech** | Category Breakdown | LLM + file analysis |

---

## 5.5 AI Detection System

Our core differentiator: multi-layer AI detection that goes beyond simple surveys.

### Detection Layers (Priority Order)

| Layer | Method | Confidence | Source |
|-------|--------|------------|--------|
| 1. LLM Analysis | Groq/Llama analyzes full PR | High (≥0.5 threshold) | PR body, files, commits |
| 2. Pattern Detection | Regex signatures | Medium | "Generated with Claude", co-authors |
| 3. Signal Aggregation | Config file presence | Low | .cursorrules, CLAUDE.md |
| 4. Survey Data | Author self-report | Ground truth | PR surveys |

### LLM Priority Rule

The `effective_is_ai_assisted` property prioritizes LLM detection when confidence ≥ 0.5, falling back to pattern detection. This ensures highest accuracy while maintaining coverage.

### Detected Tools

- **Code generation:** Copilot, Claude, Cursor, ChatGPT, Codeium, Tabnine
- **Review tools:** CodeRabbit, Codiumate, PR-Agent
- **AI authors:** Devin, Dependabot (bots)

### Why This Matters

Competitors rely on either ML-only detection (expensive, requires training data) or survey-only (low response rates). Our hybrid approach combines:
- High accuracy from LLM analysis
- Comprehensive coverage from pattern matching
- Ground truth validation from optional surveys

---

## 6. User Stories

### CTO
- View dashboard correlating AI usage with delivery metrics
- See if AI-assisted PRs have different quality ratings
- Prepare for 1:1s with individual developer data
- Configure team settings and user mapping
- Monitor AI detection accuracy and tool adoption trends

### Developer
- Receive survey after PR merge (web-based)
- See only my own metrics and team aggregates
- View my quality ratings and trends

### Reviewer
- Rate PR quality after merge (Could be better / OK / Super)
- Optionally guess if PR was AI-assisted (for AI Detective v2)

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

### LLM Data Handling
- PR content (title, body, file paths) sent to Groq API for AI detection analysis
- No source code content stored by LLM provider
- Prompt versions tracked for audit trail
- Fallback to pattern detection if LLM unavailable

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
- **Task Queue:** Celery + Redis (separate queues for sync, LLM, compute)
- **Sync:** Daily batch (4AM UTC) + GitHub webhooks for real-time PR events

### Two-Phase Onboarding Pipeline

**Phase 1 (Fast Start - ~5 min):**
1. Sync GitHub members (auto-discover team)
2. Sync recent 30 days of PRs
3. LLM analysis for AI detection
4. Aggregate metrics
5. **Dashboard accessible** ✓

**Phase 2 (Background):**
1. Sync historical 31-90 days
2. LLM analysis for older PRs
3. Re-aggregate metrics
4. Mark complete

This ensures teams can start using the dashboard quickly while comprehensive historical data loads in the background.

### LLM Processing
- **Provider:** Groq (Llama models) for cost-effective batch analysis
- **Batch processing:** With retry logic and rate limiting
- **Prompt versioning:** Tracked for experiment tracking and audit trail
- **Separate queue:** Dedicated Celery queue prevents blocking sync tasks

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
| Low survey response rate | Web-based surveys, minimal friction (gamification in v2) |
| "Surveillance" perception | Privacy-first messaging, layered visibility |
| GitHub API rate limits | Daily sync, caching, GraphQL batching |
| LLM API availability | Fallback to pattern detection, retry logic |
| AI detection accuracy | Multi-layer approach, confidence thresholds |
| Onboarding slow for large orgs | Two-phase pipeline, dashboard accessible early |

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
| **AI code detection** | **LLM + Pattern + Survey** | Yes | Partial | Partial | 95% ML | 94% ML |
| Fast onboarding | ✅ Two-phase | ✅ | ✅ | ✅ | ✅ | ✅ |
| GitHub/Jira metrics | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Free tier | Trial | ❌ | 8 users | 9 devs | ❌ | 5 devs |
| Price/seat | **$10-25** | ~$50+ | $35-46 | €22-42 | Custom | $50 |

### Updated Differentiation Strategy

1. **Hybrid AI detection** - LLM analysis + pattern matching + optional surveys (comprehensive coverage)
2. **Two-phase onboarding** - Dashboard accessible in ~5 min, historical data loads in background
3. **Price accessibility** - 50-70% cheaper than all competitors
4. **SMB focus** - 10-50 dev teams (competitors chasing enterprise)

### Emerging Threats
- **Span**: 95% AI code detection accuracy (our hybrid approach achieves similar with lower cost)
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
*Last updated: January 2026*
