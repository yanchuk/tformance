# Rich Jira Data for LLM Correlation Analysis

## Product Specification

**Author:** Product & Engineering
**Status:** Draft
**Decision:** Premium Feature (Pro/Enterprise Tier)
**Priority:** Post-MVP - implement after initial paying customers
**Blocked By:** MVP launch and pricing tier definition
**Created:** January 2026

---

## 1. Executive Summary

### The Opportunity

Our current Jira integration captures **minimal metadata** (7 fields). Competitors like Jellyfish, Swarmia, and LinearB offer deeper Jira analysis as premium features. By enriching Jira data and leveraging our existing LLM infrastructure, we can:

1. **Answer "why" questions** CTOs actually care about
2. **Create clear feature differentiation** for premium tiers
3. **Increase LTV** through deeper insights that justify higher pricing

### The CTO's Real Questions

| Current Answer | With Rich Data |
|---------------|----------------|
| "Cycle time was 48h" | "Cycle time was 48h because it sat in Code Review for 18h - your review bottleneck" |
| "This PR linked to PROJ-123" | "PR addressed 'Add auth flow' but implementation differs from requirements - scope creep risk" |
| "5 story points delivered" | "5 story points delivered but ticket had 8 comments indicating unclear requirements" |

---

## 2. ICP Context (from PRD-MVP.md)

**Primary Buyer:** CTO of 10-50 developer teams

**Core Question:**
> "Is AI actually helping my team deliver better, or are we just generating more code that creates more review burden?"

**Stack:** GitHub + Jira + Slack + AI tools (Copilot, Cursor)

**Price Sensitivity:** Underserved by $40-60/seat enterprise tools

---

## 3. Current State vs Target State

### Current Jira Fields (7 fields)

```python
# jira_client.py - current
fields="summary,status,issuetype,assignee,created,updated,resolutiondate,customfield_10016"
```

| Field | Purpose |
|-------|---------|
| `summary` | Issue title |
| `status` | Current status |
| `issuetype` | Bug, Story, Task |
| `assignee` | Who's working on it |
| `created` | When created |
| `resolutiondate` | When resolved |
| `customfield_10016` | Story points |

### Target State: Tiered Field Access

See Section 4 for detailed field specifications.

---

## 4. Field Specifications

### Tier 1: High-Impact Fields (Implement First)

| Field | Jira API | Business Value | LLM Use Case |
|-------|----------|----------------|--------------|
| **`description`** | `fields.description` | Requirements text | "Did PR implementation match ticket requirements?" |
| **`priority`** | `fields.priority.name` | Urgency signal | "High priority tickets → faster cycle time but more bugs?" |
| **`labels`** | `fields.labels[]` | Work categorization | "Tech debt vs feature vs bug correlation with AI usage" |
| **`changelog`** | `expand=changelog` | Status transitions | Time-in-status analysis, rework detection |

#### Why These First?

1. **Description** - Enables requirement-to-implementation correlation (unique differentiator)
2. **Priority** - Simple field, immediate value for urgency vs quality analysis
3. **Labels** - Team already uses for categorization, we just surface insights
4. **Changelog** - Gold mine for bottleneck detection (where work gets stuck)

---

### Tier 2: Deep Analysis Fields (Pro Feature)

| Field | Jira API | Business Value | LLM Use Case |
|-------|----------|----------------|--------------|
| **`comments`** | `fields.comment.comments[]` | Discussion context | Scope creep detection, blockers, decision history |
| **`linked_issues`** | `fields.issuelinks[]` | Dependencies | "PRs with many linked issues are more complex" |
| **`subtasks`** | `fields.subtasks[]` | Task breakdown | Correlation with PR size, planning quality |
| **`parent`** | `fields.parent` | Epic/Story hierarchy | Epic-level AI adoption patterns |
| **`components`** | `fields.components[]` | System areas | "AI adoption varies by system component" |

#### Why These Second?

- **Comments** - High token cost for LLM but highest insight value
- **Linked Issues** - Complexity signal, helps explain long cycle times
- **Parent/Epic** - Enables roll-up reporting CTOs want

---

### Tier 3: Enterprise Fields (Enterprise Feature)

| Field | Jira API | Business Value | LLM Use Case |
|-------|----------|----------------|--------------|
| **`worklog`** | `fields.worklog` | Time tracking | Estimated vs actual hours correlation |
| **`sprint_history`** | Via changelog | Carry-over analysis | "Tickets carried over 3 sprints indicate estimation issues" |
| **`fix_versions`** | `fields.fixVersions[]` | Release planning | Release quality correlation |
| **`custom_fields`** | `customfield_*` | Team-specific | Configurable analysis |

---

## 5. Actionable Insights for CTOs

### Insight Category 1: Bottleneck Detection

**Current:** "Cycle time: 48 hours"

**With Rich Data:**
```
🔍 Bottleneck Analysis for PROJ-123
├─ Total Cycle Time: 48h
├─ Time Breakdown (from changelog):
│   ├─ To Do → In Progress: 2h
│   ├─ In Progress → Code Review: 12h
│   ├─ Code Review → QA: 18h ⚠️ BOTTLENECK
│   └─ QA → Done: 16h
└─ Recommendation: Review capacity is your constraint.
   PRs from AI-assisted developers wait 40% longer in review.
```

**CTO Value:** "Now I know WHERE to invest - we need more review capacity, not more coding speed"

---

### Insight Category 2: Requirements-to-Implementation Match

**Current:** "PR #456 linked to PROJ-123"

**With Rich Data:**
```
🎯 Implementation Alignment for PR #456
├─ Ticket: "Implement OAuth2 login with Google SSO"
├─ PR Changes: auth/views.py, auth/oauth.py, settings.py
├─ LLM Analysis:
│   ├─ ✅ OAuth2 flow implemented
│   ├─ ✅ Google provider configured
│   ├─ ⚠️ Missing: "remember me" feature mentioned in comments
│   └─ 📝 Scope note: 3 comments discussed adding GitHub SSO (not in original ticket)
└─ Risk: Potential scope creep - verify with PM
```

**CTO Value:** "Catch scope creep BEFORE it becomes tech debt"

---

### Insight Category 3: Planning Quality Correlation

**Current:** "5 story points"

**With Rich Data:**
```
📊 Planning Quality for Sprint 23
├─ Tickets with 5+ comments BEFORE work started: 12
│   └─ Avg cycle time: 72h (indicating unclear requirements)
├─ Tickets with 0-2 comments before work: 28
│   └─ Avg cycle time: 24h
├─ AI-assisted PRs on unclear tickets: 2x more rework cycles
└─ Recommendation: Invest in requirement clarity BEFORE sprint starts.
   Consider "Definition of Ready" checklist.
```

**CTO Value:** "Planning quality directly impacts delivery speed - data to show the team"

---

### Insight Category 4: AI Impact by Work Type

**Current:** "40% PRs are AI-assisted"

**With Rich Data:**
```
🤖 AI Impact by Work Type (from labels + components)
├─ Bug Fixes (label: bug)
│   ├─ AI-assisted: 65% | Non-AI: 35%
│   ├─ Avg cycle time: AI 4h vs Non-AI 8h
│   └─ Quality rating: AI 2.4/3 vs Non-AI 2.2/3
├─ New Features (label: feature)
│   ├─ AI-assisted: 35% | Non-AI: 65%
│   ├─ Avg cycle time: AI 48h vs Non-AI 36h ⚠️
│   └─ Quality rating: AI 2.1/3 vs Non-AI 2.5/3
└─ Insight: AI excels at bug fixes but may be hurting new feature quality.
   Consider: AI for boilerplate, human design for architecture.
```

**CTO Value:** "Know WHERE AI helps vs hurts - optimize tool usage policy"

---

## 6. LLM Prompt Enhancements

### Current Prompt (PR Analysis Only)

```
Analyze this PR:
- Title: {title}
- Files changed: {files}
- AI tools detected: {ai_tools}
```

### Enhanced Prompt (With Rich Jira Data)

```markdown
# PR Analysis with Jira Context

## Pull Request
- Title: {pr.title}
- Files: {pr.files}
- AI Detection: {pr.ai_tools}
- Cycle Time: {pr.cycle_time_hours}h

## Linked Jira Ticket: {jira.key}
- Summary: {jira.summary}
- Description: {jira.description[:500]}
- Priority: {jira.priority}
- Labels: {jira.labels}
- Story Points: {jira.story_points}

### Time in Status (from changelog)
{jira.time_in_status_breakdown}

### Discussion Summary (from comments)
- Total comments: {jira.comment_count}
- Before work started: {jira.pre_work_comments}
- Key topics: {jira.comment_summary}

## Analysis Required
1. Does the PR implementation match the ticket requirements?
2. Were there scope changes during development (from comments)?
3. What caused the longest delays (from status transitions)?
4. Is this ticket's AI usage pattern consistent with similar work types?

Provide actionable insights for the CTO.
```

---

## 7. Tiered Feature Design

| Tier | Jira Fields | LLM Analysis | Price Signal |
|------|-------------|--------------|--------------|
| **Free** | Current (7 fields) | PR-only | $0 |
| **Pro** | + description, priority, labels, changelog | Requirement matching, bottleneck detection | $20-25/seat |
| **Enterprise** | + comments, linked issues, subtasks, custom fields | Full delivery intelligence | $35-40/seat |

### Upsell Path

```
Free: "Your cycle time is 48h"
         ↓ Upgrade prompt
Pro: "Your bottleneck is Code Review (18h). See breakdown →"
         ↓ Upgrade prompt
Enterprise: "Here's why: 3 tickets had unclear requirements (8+ comments).
            Action: Add Definition of Ready checklist."
```

---

## 8. Implementation Plan

### Phase 1: Data Model & Sync (Week 1-2)

**Engineering Effort:** ~3-4 days

```python
# apps/metrics/models.py - JiraIssue model additions

class JiraIssue(BaseTeamModel):
    # Existing fields...

    # Tier 1 - High Impact
    description = models.TextField(blank=True, default="")
    priority = models.CharField(max_length=50, blank=True, default="")
    labels = models.JSONField(default=list)  # ["bug", "feature", "tech-debt"]

    # Tier 2 - Deep Analysis
    components = models.JSONField(default=list)  # ["auth", "api", "frontend"]
    parent_key = models.CharField(max_length=50, blank=True, null=True)  # Epic key
    linked_issue_count = models.IntegerField(default=0)
    subtask_count = models.IntegerField(default=0)
    comment_count = models.IntegerField(default=0)

    # Changelog-derived metrics
    time_in_status = models.JSONField(default=dict)  # {"In Progress": 12.5, "Code Review": 18.0}
    status_transitions = models.IntegerField(default=0)  # Rework indicator
    pre_work_comment_count = models.IntegerField(default=0)  # Comments before "In Progress"
```

**Tasks:**
1. Add fields to `JiraIssue` model
2. Create migration
3. Update `jira_client.py` to fetch expanded fields
4. Update `jira_sync.py` to process new fields
5. Add changelog parsing logic

### Phase 2: Sync Enhancement (Week 2-3)

**Engineering Effort:** ~3-4 days

```python
# apps/integrations/services/jira_client.py

def get_project_issues(credential, project_key: str, since: datetime | None = None) -> list[dict]:
    issues = jira.search_issues(
        jql,
        maxResults=False,
        expand="changelog",  # NEW: Get status history
        fields=[
            # Existing
            "summary", "status", "issuetype", "assignee", "created",
            "updated", "resolutiondate", "customfield_10016",
            # Tier 1 - New
            "description", "priority", "labels",
            # Tier 2 - New
            "components", "parent", "issuelinks", "subtasks", "comment",
        ],
    )
```

**Tasks:**
1. Update API fields request
2. Parse changelog for time-in-status
3. Calculate pre-work comment count
4. Handle API pagination for large changelogs
5. Add feature flag for tier gating

### Phase 3: LLM Integration (Week 3-4)

**Engineering Effort:** ~4-5 days

**Tasks:**
1. Create Jira context builder for LLM prompts
2. Add Jira data to PR analysis prompt
3. Create new insight types (bottleneck, alignment, planning)
4. Update dashboard to display new insights
5. Add token usage monitoring (cost control)

### Phase 4: Dashboard & UI (Week 4-5)

**Engineering Effort:** ~3-4 days

**Tasks:**
1. Add "Time in Status" breakdown chart
2. Create bottleneck detection widget
3. Build requirement alignment indicator
4. Add label/component filters to analytics
5. Create upgrade prompts for tier gating

---

## 9. Cost Analysis

### API Costs

| Source | Impact |
|--------|--------|
| Jira API | Same calls, more fields per call (negligible) |
| Changelog expansion | +1 additional data per issue (minor) |

### LLM Token Costs

| Field | Est. Tokens | Cost @ $0.003/1K |
|-------|-------------|------------------|
| Description (500 chars) | ~125 tokens | $0.0004 |
| Comments summary | ~200 tokens | $0.0006 |
| Changelog analysis | ~100 tokens | $0.0003 |
| **Total per PR** | ~425 tokens | **$0.0013** |

**Monthly Cost (1000 PRs/month team):** ~$1.30 additional

### Storage

| Field | Est. Size/Issue |
|-------|-----------------|
| description | ~2KB avg |
| time_in_status JSON | ~500B |
| labels/components | ~200B |
| **Total** | ~3KB/issue |

**For 10,000 issues:** ~30MB additional (negligible)

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Pro tier conversion | +15% | Free → Pro upgrades |
| Feature engagement | 60% | Users viewing bottleneck insights |
| NPS improvement | +10 points | "Insights are actionable" |
| Churn reduction | -20% | Pro tier retention |

---

## 11. Competitive Positioning

### vs Jellyfish/Span ($50+/seat)
"Same depth of Jira analysis at half the price, plus gamified quality data they don't have."

### vs Swarmia/LinearB ($35-45/seat)
"We correlate Jira context with AI impact - they just show metrics side by side."

### vs Free Tools
"Understand WHY delivery is slow, not just that it's slow."

---

## 12. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| LLM token costs spike | Token budgets per tier, truncate long descriptions |
| Jira API rate limits | Incremental sync, caching, pagination |
| Privacy concerns (description/comments) | Tier gating, data retention controls |
| Complexity overwhelm | Progressive disclosure, focus on top 3 insights |

---

## 13. Decision Summary

| Decision | Recommendation |
|----------|----------------|
| **When to build** | After MVP stabilization, before enterprise push |
| **Which fields first** | `description`, `priority`, `labels`, `changelog` (highest ROI) |
| **Pricing tier** | Pro ($20-25/seat) includes Tier 1; Enterprise ($35-40) includes all |
| **Engineering effort** | 3-4 weeks total for full implementation |
| **LLM cost increase** | ~$1.30/month per 1000 PRs (negligible) |

**The unique differentiator:** Requirement-to-implementation correlation using LLM. No competitor does this well.

**Recommendation:** Implement Tier 1 fields (description, priority, labels, changelog) in next sprint. Measure engagement before expanding to Tier 2.

---

## References

- [Atlassian Jira REST API - Issues](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/)
- [Atlassian Jira REST API - Fields](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-fields/)
- [Jellyfish - Jira Metrics](https://jellyfish.co/library/jira-performance-metrics/)
- [LinearB - Jira Integration](https://linearb.io/integrations/jira)
- [Swarmia vs Jellyfish](https://www.swarmia.com/alternative/jellyfish/)
- [Cycle Time Breakdown Best Practices](https://getnave.com/cycle-time-breakdown-chart-for-jira)
- [Bottleneck Analysis - Atlassian Community](https://community.atlassian.com/forums/App-Central-articles/Revealing-Operational-Excellence-Identifying-Bottlenecks-through/ba-p/2592758)

---

*Created: January 2026*
