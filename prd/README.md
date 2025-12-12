# PRD Documentation Structure

## Overview

Product Requirements Documentation for AI Impact Analytics Platform MVP.

## Documents

| Document | Description |
|----------|-------------|
| [PRD-MVP.md](PRD-MVP.md) | Main PRD - overview, features, target customer, pricing |
| [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) | High-level build phases and dependencies |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical architecture, integrations, security |
| [DATA-MODEL.md](DATA-MODEL.md) | Database schema, RLS policies, migrations |
| [SLACK-BOT.md](SLACK-BOT.md) | Slack bot specification, message templates |
| [DASHBOARDS.md](DASHBOARDS.md) | Dashboard views (Chart.js + HTMX) |
| [ONBOARDING.md](ONBOARDING.md) | User onboarding flow |

## Quick Summary

| Aspect | Decision |
|--------|----------|
| **Target Customer** | CTOs of teams with 10-50 developers |
| **Core Value** | Answer "Is AI actually helping my team?" |
| **MVP Integrations** | GitHub, Jira, GitHub Copilot, Slack |
| **Data Storage** | BYOS - Client's Supabase |
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

- **Version:** 1.0
- **Date:** December 2025
- **Status:** Draft for Review
