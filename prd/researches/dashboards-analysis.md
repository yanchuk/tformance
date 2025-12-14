# Engineering Dashboards Analysis

This document describes two dashboard systems used for tracking engineering team performance and productivity.

---

## 1. Developer Dashboards

A comprehensive dashboard focused on **individual developer metrics** and **engineering team dynamics**.

### 1.1 Overview - Time Allocation

**Purpose:** Track how engineers allocate their time across different work types.

**Key Metrics:**
- **Time allocation breakdown** (stacked bar chart by month):
  - Epic Work
  - Non-Epic Work
  - Bug Fixing
- **Summary cards:**
  - Total hours
  - Work time posted (hours)
  - Time off posted (hours)

**Filters Available:**
| Filter | Description |
|--------|-------------|
| Employee | Person filter |
| Title | Job title |
| Department | Organizational unit |
| Team | Team assignment |
| Allocation area | Work allocation category |
| Project | Project filter |
| Sprint | Sprint filter |
| Epic | Epic filter |
| Issue type | Type of issue |
| Work type | Category of work |
| Date range | Time period selector |

---

### 1.2 Activity Detailed

**Purpose:** Granular view of individual contributor activity across GitHub, Jira, and time tracking.

**Sections:**

#### GitHub PRs Activity (Table)
| Column | Description |
|--------|-------------|
| Employee | Person name |
| PRs | Total PRs |
| PR cycle time | Average time from open to merge |
| PRs merged | Number of merged PRs |
| PRs opened | Number of opened PRs |
| PR comments received | Comments on their PRs |
| Unlinked PRs | PRs not linked to issue tracker |
| Unique PR files | Files touched |

#### GitHub Commits Activity (Table)
| Column | Description |
|--------|-------------|
| Employee | Person name |
| Commits | Total commits |
| Days with commits | Active coding days |
| Lines of code | LOC added |

#### Issue Tracker (Table)
| Column | Description |
|--------|-------------|
| Employee | Person name |
| Issues in Backlog | Backlog items assigned |
| Issues in Progress | WIP items |
| Issues Done | Completed items |
| Story points Done | Velocity in points |
| Points per working hour | Efficiency ratio |
| Issue cycle time | Time to complete issues |

#### Time Tracking (Table)
| Column | Description |
|--------|-------------|
| Employee | Person name |
| Working hours | Logged work hours |

---

### 1.3 Pull Requests

**Purpose:** Detailed list of all pull requests with metadata.

**Columns:**
| Column | Description |
|--------|-------------|
| Opened by | Author of PR |
| PR Title | Pull request title |
| Open date | When PR was opened |
| State | Current state (open/merged/closed) |
| Repository | Target repository |
| Issue key | Linked ticket |
| Issue type | Type of linked issue |
| Role | Author's role |

**Filters:**
- PR state
- Repository
- Issue

---

### 1.4 Issues List

**Purpose:** List of issues with current status.

**Columns:**
| Column | Description |
|--------|-------------|
| Assignee | Person assigned |
| Issue Key | Issue identifier |
| Epic | Parent epic |
| Type | Issue type (Task, Bug, etc.) |
| Status | Current status |
| Updated at | Last update timestamp |

**Filters:**
- Status category

---

### 1.5 Dynamics Stats (Time Series)

**Purpose:** Track team-wide trends over time with line charts.

**Charts Available:**
1. **Working hours** - Total team hours per week
2. **PRs opened** - New PRs created per week
3. **Commits** - Total commits per week
4. **Lines of code added** - LOC velocity
5. **PRs merged** - Merged PRs per week
6. **PRs merged - Unlinked** - PRs without issue links
7. **PR comments received** - Code review engagement
8. **PRs canceled** - Closed without merge
9. **PR reviews left** - Review activity
10. **PR comments left** - Comment activity
11. **Issues Done** - Completed issues
12. **Story points from Done tickets** - Points delivered

**Filters:**
- Charts breakdown: All / By individual
- All standard filters (Employee, Team, Sprint, etc.)

---

### 1.6 Personal View (Bar Charts)

**Purpose:** Individual performance tracking with bar charts showing weekly values.

**Same metrics as Dynamics Stats** but displayed as:
- Bar charts instead of line charts
- Values labeled on each bar
- Week-over-week comparison
- Individual contributor focus

**Use Case:** Performance reviews, 1:1 meetings, self-assessment.

---

### 1.7 Comparison View

**Purpose:** Side-by-side comparison of multiple engineers.

#### Weekly View (Table)
| Column | Description |
|--------|-------------|
| Week | Week identifier |
| [Engineer Name] - PRs merged | PRs by engineer |
| [Engineer Name] - Lines of code | LOC by engineer |
| Composite score | Combined performance score |
| LOC per working day / PRs merged | Efficiency ratio |

#### Daily View (Table)
| Column | Description |
|--------|-------------|
| Date / Day of week | Date and day |
| Lines of code | Daily LOC per engineer |
| PRs merged | Daily PRs per engineer |

**Filters:**
- Show weekends toggle
- All standard filters

---

## 2. General Performance Dashboard

A broader dashboard tracking **cross-functional activity** across multiple tools and communication channels.

### 2.1 Actions per Tool

**Purpose:** Matrix view of employee activity across all integrated tools.

**Tools Tracked:**
| Tool | Actions Measured |
|------|------------------|
| Issue Tracker | Issues created, updated |
| Version Control | Commits, PRs |
| Design Tool | Design actions |
| Documentation | Page edits, views |
| Support System | Support tickets |
| CRM | Customer interactions |
| ERP | Business operations |
| Communication | Chat/video call activity |
| Analytics | Data/BI work |

**Additional Columns:**
- Time off (hours)
- Work hours
- Absence hours
- Total score (combined)
- Team score

**Visual Coding:** Cells are color-coded (green/yellow/red) based on activity levels.

**Filters:**
- Team, Employee, Department, Title, Date range

---

### 2.2 Weekly View

**Purpose:** Track total actions per employee over weeks.

**Layout:**
- Rows: Employee names
- Columns: Week dates
- Values: Total action count for that week

**Use Case:** Spotting activity trends, identifying low-engagement periods.

---

### 2.3 Time & Allocations

**Purpose:** Track time distribution and team allocation.

**Components:**

#### Summary Cards
- Total hours
- Work time posted (h)
- Time off posted (h)

#### Allocations Table
| Column | Description |
|--------|-------------|
| Employee | Person name |
| Department | Organizational unit |
| Role | Team member / Lead / etc. |

#### Visualizations
1. **Pie Chart:** Distribution by business unit or project
2. **Stacked Bar Chart:** Hours over time by category

**Filters:**
- Time tracking project
- Exclude time off (checkbox)

---

### 2.4 Scope: Issue Tracker

**Purpose:** Issue tracker-specific activity and issue tracking.

#### Issues by Status (Table)
| Column | Description |
|--------|-------------|
| Employee | Person name |
| Issues Backlog | Backlog count |
| Issues in Progress | WIP count |
| Issues Done | Completed count |

#### Additional Columns
- Issues created
- Activities (color-coded)

#### Issues List by Assignee (Detail Table)
| Column | Description |
|--------|-------------|
| Assignee | Assigned person |
| Creator | Issue creator |
| Department | Organizational unit |
| Issue Key | Issue identifier |
| Epic | Parent epic |
| Type | Issue type |
| Status | Current status |
| Updated at | Last update |

#### Issues List by Creator
Same structure, filtered by creator instead of assignee.

**Filters:**
- Issue type
- Epic
- Status category

---

### 2.5 Scope: Other Tools

**Purpose:** Activity tracking across various integrated tools.

#### Cloud Storage Actions
- **Scatter plot:** Creates vs Edits
- **Table:** Employee, Creates, Edits, Views

#### Documentation Platform
- **Table:** Employee, Views, Creates, Edits

#### Version Control
- **Scatter plot:** Commits vs Lines of code
- **Table:** Employee, Commits, Lines of code, Commit score

#### Design Tool
- **Table:** Employee, Actions, Files, Comments

#### BI/Reporting Tool
- **Scatter plot:** Actions vs Views
- **Table:** Employee, Actions, Views

#### Data Warehouse Queries
- **Table:** Employee, Queries

#### ERP System
- **Table:** Employee, Actions

#### Support Platform
- **Table:** Employee, Replies, Notes, Documents

#### Marketing Activity
- **Table:** Employee, CRM actions, Content published

---

### 2.6 Communication

**Purpose:** Track communication activity across channels.

#### Communication Scores
- **Scatter plot:** Calls in hours (X) vs Messages in characters (Y)
- **Table:** Employee, Calls in hours, Messages in characters

#### Calls Summary
| Channel | Calls | Hours | Hours per Call |
|---------|-------|-------|----------------|
| Video calls | Count | Total | Average |
| Voice calls | Count | Total | Average |
| Grand total | Sum | Sum | Average |

**Notes:**
- Only calls with 2+ participants counted

---

### 2.7 Messages

**Purpose:** Detailed messaging analytics.

**Columns:**
| Column | Description |
|--------|-------------|
| Channel | Channel name |
| Department | Organizational unit |
| Messages | Total message count |
| Characters per Message | Average length |
| Reactions | Total reactions received |
| Reactions per Message | Engagement ratio |

**Filter:**
- Channel (dropdown)

---

## Summary: Key Differences

| Aspect | Developer Dashboards | General Dashboard |
|--------|---------------------|-------------------|
| Focus | Engineering metrics | Cross-functional activity |
| Primary tools | GitHub, Issue Tracker | 10+ tools |
| Audience | Engineering managers | Operations/Leadership |
| Time granularity | Daily/Weekly | Weekly |
| Key metric | Code output | Total actions |
| Comparison view | Engineer vs Engineer | Team overview |

---

## Common Filter Pattern

Both dashboards share a consistent filtering approach:

1. **Employee/Team filters** - Drill down by person or team
2. **Date range picker** - Standard date selection
3. **Department** - Organizational grouping
4. **Role/Title** - Position-based filtering

This allows for consistent cross-dashboard analysis and drill-down capabilities.
