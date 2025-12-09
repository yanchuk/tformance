# Dashboard Views (Metabase)

> Part of [PRD Documentation](README.md)

## Overview

Dashboards are built in Metabase and embedded in our app. Metabase connects directly to the client's Supabase database.

**Why Metabase:**
- No custom UI development for MVP
- Built-in filtering, drill-downs
- Supports embedding with row-level permissions
- Open source option available

---

## Dashboard Structure

| Dashboard | Audience | Access |
|-----------|----------|--------|
| CTO Overview | CTO/Admin | Full org data |
| Team Dashboard | Team Lead | Their team only |
| Individual Dashboard | Developer | Their own data only |
| AI Correlation Deep Dive | CTO/Admin | Full org data |

---

## 1. CTO Overview Dashboard

**Purpose:** High-level health check and AI impact

### Widgets

#### 1.1 AI Adoption Trend (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** % of PRs marked AI-assisted
- **Overlay:** Team avg Copilot suggestions accepted (if available)

#### 1.2 AI vs Delivery Correlation (Scatter Plot)
- **X-axis:** AI-assisted PRs per week (per developer)
- **Y-axis:** Total PRs merged per week
- **Points:** One per developer
- **Trend line:** Show correlation direction

#### 1.3 Quality by AI Status (Bar Chart)
- **Bars:** AI-assisted PRs vs Non-AI PRs
- **Y-axis:** Average quality rating (1-3)
- **Goal:** Show if AI-assisted code has different quality perception

#### 1.4 Key Metrics Cards
| Card | Value | Comparison |
|------|-------|------------|
| PRs Merged | This week count | vs last week % |
| Avg Cycle Time | Hours | vs last week % |
| Avg Quality Rating | x/3 | vs last week |
| AI-Assisted PR % | % | vs last week |

#### 1.5 Team Breakdown Table
| Column | Description |
|--------|-------------|
| Team | Team name |
| Members | Count |
| PRs Merged | This week |
| Avg Cycle Time | Hours |
| AI Adoption % | % of PRs AI-assisted |

---

## 2. Team Dashboard

**Purpose:** Team lead view of their team's performance

### Widgets

#### 2.1 Team Velocity (Line Chart)
- **X-axis:** Sprints or weeks
- **Y-axis:** Story points completed

#### 2.2 PR Cycle Time Trend (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** Average cycle time (hours)

#### 2.3 Review Distribution (Pie Chart)
- **Slices:** Team members
- **Value:** Number of reviews done
- **Goal:** Identify if review load is balanced

#### 2.4 AI Detective Leaderboard (Table)
| Column | Description |
|--------|-------------|
| Rank | 1, 2, 3... |
| Name | Team member |
| Correct Guesses | x/y |
| Accuracy | % |

#### 2.5 Recent PRs (Table)
| Column | Description |
|--------|-------------|
| PR Title | Linked to GitHub |
| Author | Name |
| Cycle Time | Hours |
| Quality Rating | Could be better / OK / Super |
| AI Status | Yes/No (if revealed) |

---

## 3. Individual Dashboard

**Purpose:** Developer's personal view (visible only to themselves + CTO)

### Widgets

#### 3.1 My Activity (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** PRs merged, commits (dual axis)

#### 3.2 My Quality Ratings (Distribution)
- **Chart:** Histogram or bar chart
- **Buckets:** Could be better / OK / Super
- **Shows:** How my PRs are rated over time

#### 3.3 My AI Usage (Line Chart)
- **X-axis:** Weeks
- **Y-axis:** AI-assisted PR count
- **Note:** Copilot metrics if available

#### 3.4 My Stats Cards
| Card | Value |
|------|-------|
| Total PRs | This month |
| Avg Quality Rating | x/3 |
| AI Guess Accuracy | % (as reviewer) |

#### 3.5 My Recent PRs (Table)
| Column | Description |
|--------|-------------|
| PR Title | Linked to GitHub |
| Merged | Date |
| Quality Rating | Rating received |
| AI-Assisted | Self-reported |

---

## 4. AI Correlation Deep Dive

**Purpose:** Detailed analysis for CTO decision-making

### Widgets

#### 4.1 Correlation Matrix (Heatmap)
- **Rows/Cols:** Various metrics
- **Values:** Correlation coefficients
- **Metrics:** AI-assisted %, Cycle time, Quality rating, PRs merged, Story points

#### 4.2 Before/After Analysis (Comparison Table)
| Metric | Before AI Adoption | After AI Adoption | Change |
|--------|-------------------|-------------------|--------|
| Avg Cycle Time | x hrs | y hrs | -z% |
| PRs/Week | x | y | +z% |
| Quality Rating | x | y | +z |

**Note:** Requires 8+ weeks of data with clear adoption inflection point

#### 4.3 High AI Users vs Low AI Users (Comparison)
- **Split:** Top 50% AI usage vs Bottom 50%
- **Compare:** Cycle time, quality, throughput
- **Goal:** See if heavy AI users perform differently

#### 4.4 AI by Repository (Table)
| Column | Description |
|--------|-------------|
| Repository | Repo name |
| Total PRs | Count |
| AI-Assisted | % |
| Avg Quality | Rating |

#### 4.5 Quality Trend by AI Adoption (Line Chart)
- **X-axis:** Weeks
- **Y-axis (dual):** AI adoption %, Avg quality rating
- **Goal:** See if quality changed as AI adoption increased

---

## Filters (Global)

Available on all dashboards:

| Filter | Options |
|--------|---------|
| Date Range | Last 7 days, 30 days, 90 days, custom |
| Team | All teams, specific team |
| Repository | All repos, specific repo |

CTO-only filters:
| Filter | Options |
|--------|---------|
| Individual | All, specific person (for 1:1 prep) |

---

## Metabase Embedding

### Setup

1. Enable embedding in Metabase settings
2. Generate signed JWT for each user with their permissions
3. Embed dashboard iframe with signed URL

### Row-Level Filtering

Metabase supports passing parameters to filter queries:

```javascript
// Embed URL with user context
const embedUrl = signEmbedUrl({
  dashboard: 'cto-overview',
  params: {
    user_id: currentUser.id,
    role: currentUser.role,
    team_id: currentUser.team_id
  }
});
```

Queries use these params to filter:
```sql
WHERE (
  {{role}} = 'admin' OR
  ({{role}} = 'lead' AND team_id = {{team_id}}) OR
  user_id = {{user_id}}
)
```
