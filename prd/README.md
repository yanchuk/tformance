# PRD Documentation Structure

## Overview

Product Requirements Documentation for AI Impact Analytics Platform MVP.

## Documents

### Core Specifications
| Document | Description |
|----------|-------------|
| [PRD-MVP.md](PRD-MVP.md) | Main PRD - overview, features, target customer, pricing |
| [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) | High-level build phases and dependencies |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture, integrations, security |
| [DATA-MODEL.md](DATA-MODEL.md) | Database schema, RLS policies, migrations |
| [SLACK-BOT.md](SLACK-BOT.md) | Slack bot specification, message templates |
| [DASHBOARDS.md](DASHBOARDS.md) | Dashboard views (Chart.js + HTMX) |
| [ONBOARDING.md](ONBOARDING.md) | User onboarding flow |

### Feature Specifications
| Document | Description |
|----------|-------------|
| [PERSONAL-NOTES.md](PERSONAL-NOTES.md) | PR notes/annotations feature |
| [GITHUB-APP-MIGRATION.md](GITHUB-APP-MIGRATION.md) | Migration from OAuth App to GitHub App (draft) |
| [JIRA-ENRICHMENT.md](JIRA-ENRICHMENT.md) | Premium Jira data enrichment (draft) |

### Strategy & Research
| Document | Description |
|----------|-------------|
| [PRICING-STRATEGY.md](PRICING-STRATEGY.md) | Pricing model analysis and strategy |
| [COMPETITOR-RESEARCH.md](COMPETITOR-RESEARCH.md) | December 2025 competitive analysis |

### Reference Documentation
| Document | Description |
|----------|-------------|
| [AI-DETECTION-TESTING.md](AI-DETECTION-TESTING.md) | AI detection approaches, prompt versioning, testing workflow |
| [PROMPT-ENGINEERING.md](PROMPT-ENGINEERING.md) | LLM prompt best practices (Anthropic guidelines) |

## Quick Summary

| Aspect | Decision |
|--------|----------|
| **Target Customer** | CTOs of teams with 10-50 developers |
| **Core Value** | Answer "Is AI actually helping my team?" |
| **MVP Integrations** | GitHub, Jira, GitHub Copilot, Slack |
| **Data Storage** | Single DB (team-isolated) - BYOS deferred to Phase 12 |
| **Sync Frequency** | Daily (not hourly) |
| **Dashboards** | Native (Chart.js + HTMX) |
| **Pricing** | Per seat ($10-25/seat target) |

## v2 Scope (Not MVP)

- Cursor integration (Enterprise API only)
- Calendar/Slack communication metrics
- Work type detection (backend/frontend)
- Time tracking
- Comparison views
- Alerts & notifications

## Status

- **Version:** 1.1
- **Date:** January 2026
- **Status:** Active Development
