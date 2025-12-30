# PRD: Unified CTO Dashboard

**Last Updated:** 2024-12-30
**Status:** Draft
**Owner:** Product

---

## Executive Summary

Merge `/app/` (home) and `/app/metrics/dashboard/team/` into a single, unified CTO dashboard that answers three core questions at a glance:

1. **"Is AI making my team faster?"** - AI Impact metrics with comparison
2. **"What needs my attention?"** - Prioritized actionable issues
3. **"How are we trending?"** - Key metrics with sparklines

### Problem Statement

Current state has two separate pages with duplicated data:
- `/app/` shows basic 7-day stats with a link to "View Analytics"
- `/app/metrics/dashboard/team/` shows detailed 30-day metrics with charts

This creates:
- **Two-step friction** to get actionable data
- **Cognitive overhead** navigating between similar views
- **Maintenance burden** of two codepaths for similar data

### Solution

Consolidate into a single `/app/` page that provides:
- High-level KPIs with trends (answering "how are we doing?")
- Actionable exception list (answering "what needs attention?")
- AI impact visualization (answering "is AI helping?")
- Team velocity insights (answering "who's contributing?")

---

## User Stories

### Primary Persona: CTO / Engineering Manager

**US-1: Quick Health Check**
> As a CTO, I want to see my team's key metrics immediately upon login so I can quickly assess team health without clicking through multiple pages.

**Acceptance Criteria:**
- [ ] 4 key metric cards visible above the fold (PRs Merged, Cycle Time, AI Adoption, Review Time)
- [ ] Each card shows current value + 12-week trend sparkline
- [ ] Trend indicator shows % change vs previous period
- [ ] Page loads in < 2 seconds (HTMX lazy loading for charts)

**US-2: Exception-Based Management**
> As a CTO, I want to see PRs that need attention so I can proactively address quality issues before they escalate.

**Acceptance Criteria:**
- [ ] "Needs Attention" section shows prioritized list of flagged PRs
- [ ] Issues are detected: reverts, hotfixes, long cycle time, large PRs
- [ ] Each item shows: PR title, issue type, author, time ago
- [ ] Fixed height container with pagination (10 items per page)
- [ ] Empty state shows "All clear!" message when no issues

**US-3: AI Impact Visibility**
> As a CTO, I want to see if AI tools are actually improving my team's velocity so I can justify AI investments.

**Acceptance Criteria:**
- [ ] AI Impact card shows: adoption %, cycle time with AI vs without AI
- [ ] Clear comparison visualization (e.g., "-42% faster with AI")
- [ ] Links to detailed AI Analytics view

**US-4: Team Velocity Insight**
> As a CTO, I want to see top contributors and their metrics so I can recognize high performers and identify coaching opportunities.

**Acceptance Criteria:**
- [ ] Team Velocity card shows top 5 contributors by PR count
- [ ] Each entry shows: name, PR count, avg cycle time
- [ ] Links to full team member analytics

**US-5: Review Bottleneck Detection**
> As a CTO, I want to know when code reviews are becoming a bottleneck so I can redistribute workload.

**Acceptance Criteria:**
- [ ] Review Distribution chart shows reviews per team member
- [ ] Bottleneck alert appears when imbalance detected (e.g., 1 person has 4x avg)
- [ ] Fixed height container with pagination for large teams

---

## Information Architecture

### Page Layout (Desktop)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ HEADER                                                                  │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ Your Team                                    [7d] [30d*] [90d]      │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ KEY METRICS (4 cards - responsive grid)                                 │
│ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │
│ │ PRs Merged    │ │ Cycle Time    │ │ AI Adoption   │ │ Review Time   │ │
│ │     42        │ │    12.3h      │ │     67%       │ │     2.1h      │ │
│ │ [sparkline]   │ │ [sparkline]   │ │ [sparkline]   │ │ [sparkline]   │ │
│ │ ↑ +12%        │ │ ↓ -8% (good)  │ │ ↑ +5pp        │ │ → stable      │ │
│ └───────────────┘ └───────────────┘ └───────────────┘ └───────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ ROW 2 (2-column)                                                        │
│ ┌─────────────────────────────────┐ ┌─────────────────────────────────┐ │
│ │ 🚨 NEEDS ATTENTION              │ │ 🤖 AI IMPACT                    │ │
│ │                                 │ │                                 │ │
│ │ 1. 🔴 PR #123 - Revert          │ │ AI-Assisted PRs: 67% (↑12%)    │ │
│ │ 2. 🔴 PR #456 - Hotfix          │ │                                 │ │
│ │ 3. 🟡 PR #789 - 48h cycle       │ │ Avg Cycle Time:                 │ │
│ │ 4. 🟡 PR #101 - 623 lines       │ │   With AI:    8.2h              │ │
│ │ 5. ⚪ PR #102 - No Jira         │ │   Without AI: 14.1h             │ │
│ │                                 │ │   Difference: -42% faster       │ │
│ │ [1] [2] [3] ← Page 1 of 3       │ │                                 │ │
│ │                                 │ │ [View AI Analytics →]           │ │
│ │ Height: 320px (fixed)           │ │ Height: 320px (fixed)           │ │
│ └─────────────────────────────────┘ └─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ ROW 3 (2-column)                                                        │
│ ┌─────────────────────────────────┐ ┌─────────────────────────────────┐ │
│ │ 👥 REVIEW DISTRIBUTION          │ │ 🚀 TEAM VELOCITY                │ │
│ │                                 │ │                                 │ │
│ │ ⚠️ Bottleneck: Bob has 8        │ │ Top Contributors (30d):         │ │
│ │    pending (team avg: 2)        │ │                                 │ │
│ │                                 │ │ 1. Alice - 12 PRs (4.2h avg)    │ │
│ │ [horizontal bar chart]          │ │ 2. Bob - 9 PRs (6.1h avg)       │ │
│ │ Alice: ████████ 8               │ │ 3. Carol - 8 PRs (5.8h avg)     │ │
│ │ Bob:   ████ 4                   │ │ 4. Dave - 7 PRs (7.2h avg)      │ │
│ │ Carol: ███ 3                    │ │ 5. Eve - 6 PRs (5.1h avg)       │ │
│ │                                 │ │                                 │ │
│ │ [1] [2] ← Page 1 of 2           │ │ [View All Members →]            │ │
│ │                                 │ │                                 │ │
│ │ Height: 320px (fixed)           │ │ Height: 320px (fixed)           │ │
│ └─────────────────────────────────┘ └─────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ INTEGRATION HEALTH (conditional - only shows when issues exist)         │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ ⚠️ GitHub sync paused - API rate limit exceeded. Resumes in 42 min │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────────────┤
│ FOOTER ACTIONS                                                          │
│ ┌─────────────────────────────────────────────────────────────────────┐ │
│ │ [Explore: Cycle Time Trends] [AI Analytics] [Team Members] [PRs]   │ │
│ └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

### Mobile Layout (< 768px)

Single column, stacked:
1. Key Metrics (2x2 grid)
2. Needs Attention
3. AI Impact
4. Team Velocity
5. Review Distribution
6. Integration Health (if applicable)

---

## Issue Detection Logic

### "Needs Attention" Prioritization

Issues are detected and prioritized in this order:

| Priority | Type | Icon | Detection Logic | Color |
|----------|------|------|-----------------|-------|
| 1 (Critical) | Revert | 🔴 | `is_revert = True` | `text-error` |
| 2 (Critical) | Hotfix | 🔴 | `is_hotfix = True` | `text-error` |
| 3 (Warning) | Long Cycle | 🟡 | `cycle_time > team_avg * 2` | `text-warning` |
| 4 (Warning) | Large PR | 🟡 | `lines_changed > 500` | `text-warning` |
| 5 (Info) | Missing Jira | ⚪ | `jira_issue IS NULL` AND Jira connected | `text-base-content/60` |

### Bottleneck Detection Logic

```python
# Trigger alert if any reviewer has > 3x the team average pending reviews
team_avg = total_pending_reviews / num_reviewers
bottleneck_threshold = team_avg * 3

for reviewer in reviewers:
    if reviewer.pending_reviews > bottleneck_threshold:
        show_bottleneck_alert(reviewer)
```

---

## Empty States

### Needs Attention - No Issues

```
┌────────────────────────────────────────┐
│ 🎉 ALL CLEAR                           │
│                                        │
│ No issues detected in the last 30 days │
│                                        │
│ ✓ No reverts or hotfixes              │
│ ✓ Cycle times within normal range     │
│ ✓ PR sizes look healthy               │
└────────────────────────────────────────┘
```

### AI Impact - No AI Data

```
┌────────────────────────────────────────┐
│ 🤖 AI IMPACT                           │
│                                        │
│ AI Adoption: 0%                        │
│                                        │
│ No AI-assisted PRs detected yet.       │
│ As your team uses AI tools, we'll      │
│ show the impact on velocity here.      │
│                                        │
│ [Learn about AI Detection →]           │
└────────────────────────────────────────┘
```

### Team Velocity - No PRs

```
┌────────────────────────────────────────┐
│ 🚀 TEAM VELOCITY                       │
│                                        │
│ No PRs merged in this period.          │
│                                        │
│ Activity will appear here as           │
│ team members merge pull requests.      │
└────────────────────────────────────────┘
```

### Review Distribution - No Reviews

```
┌────────────────────────────────────────┐
│ 👥 REVIEW DISTRIBUTION                 │
│                                        │
│ No code reviews in this period.        │
│                                        │
│ Review data will appear after          │
│ your team completes code reviews.      │
└────────────────────────────────────────┘
```

### Full Page - No GitHub Integration

Keep existing setup wizard behavior from `/app/` (no change).

### Full Page - Syncing

Keep existing sync progress indicator (no change).

---

## Technical Specifications

### URL Changes

| Current | New | Action |
|---------|-----|--------|
| `/app/` | `/app/` | Enhance with merged dashboard |
| `/app/metrics/dashboard/team/` | - | **DELETE** (redirect to `/app/` for 30 days) |

### API Endpoints (HTMX)

| Endpoint | Purpose | New? |
|----------|---------|------|
| `GET /app/metrics/cards/` | Key metrics cards | Existing (reuse) |
| `GET /app/metrics/needs-attention/` | Flagged PRs list | **NEW** |
| `GET /app/metrics/ai-impact/` | AI comparison stats | **NEW** |
| `GET /app/metrics/team-velocity/` | Top contributors | **NEW** |
| `GET /app/metrics/review-distribution/` | Review chart + alert | Existing (enhance) |

### Service Layer

```python
# apps/metrics/services/dashboard_service.py

def get_needs_attention_prs(team, start_date, end_date, page=1, per_page=10):
    """Get PRs flagged for attention, prioritized by issue severity."""

def get_ai_impact_stats(team, start_date, end_date):
    """Get AI vs non-AI cycle time comparison."""

def get_team_velocity(team, start_date, end_date, limit=5):
    """Get top contributors by PR count with avg cycle time."""

def detect_review_bottleneck(team, start_date, end_date):
    """Detect if any reviewer has > 3x avg pending reviews."""
```

### Data Models

No new models required. All data derives from existing:
- `PullRequest` (is_revert, is_hotfix, cycle_time, lines_changed, jira_issue)
- `PRReview` (reviewer, created_at)
- `TeamMember` (display_name, avatar_url)

### Performance Requirements

| Metric | Target |
|--------|--------|
| Initial page load | < 2s |
| HTMX partial load | < 500ms per section |
| Database queries | < 10 per page load |
| Cache TTL | 5 minutes for aggregate stats |

---

## Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Pages to reach actionable data | 2 | 1 | User flow analysis |
| Time to first insight | ~8s (load + click + load) | < 3s | Performance monitoring |
| Bounce rate on `/app/` | TBD | -20% | Analytics |
| Feature engagement (Needs Attention clicks) | N/A | > 30% of sessions | Event tracking |

---

## Out of Scope

The following are explicitly NOT part of this PRD:

1. **AI Detective Leaderboard** - Removed, may return in future iteration
2. **Custom date ranges** - Preset options only (7d, 30d, 90d)
3. **Per-repository filtering** - Global team view only
4. **Export functionality** - No CSV/PDF export
5. **Email notifications** - No digest emails for issues
6. **Mobile app** - Web responsive only

---

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Performance degradation with large teams | High | Medium | Aggressive caching, pagination |
| Missing issue types users care about | Medium | Low | Start with clear priorities, iterate based on feedback |
| Empty states feel hollow | Low | Medium | Positive messaging, clear next actions |
| Users miss old dashboard features | Medium | Low | 30-day redirect with deprecation notice |

---

## Rollout Plan

1. **Phase 1: Build** - Implement new components, service layer
2. **Phase 2: Shadow** - Deploy behind feature flag, internal testing
3. **Phase 3: Redirect** - Redirect old dashboard to new with notice
4. **Phase 4: Remove** - Delete old dashboard code after 30 days

---

## Appendix: Existing Code to Modify

See `dashboard-merge-context.md` for detailed file mapping.
