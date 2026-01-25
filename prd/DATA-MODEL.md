# Tformance Data Model

> Part of [PRD Documentation](README.md)

## Overview

All tables are in our PostgreSQL database, with team isolation enforced via `team_id` foreign keys. Django models extend `BaseTeamModel` which automatically adds the team relationship.

**Key Distinction:**
- `users` = People who log in (CTOs, admins)
- `team_members` = Developers being tracked (may have no login account)
- `memberships` = Links users to teams with roles

---

## Tables

### Core Entities

```sql
-- Authentication users (Django CustomUser)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    username TEXT UNIQUE,
    first_name TEXT,
    last_name TEXT,
    avatar TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Organizations/tenants
CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User membership in teams (with role)
CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'admin' or 'member'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, team_id)
);

-- Developer identities across integrations (GitHub/Jira/Slack)
CREATE TABLE team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    email TEXT,
    display_name TEXT NOT NULL,
    github_username TEXT,
    github_id TEXT,
    jira_account_id TEXT,
    slack_user_id TEXT,
    role TEXT DEFAULT 'developer', -- developer, lead, admin
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, github_id) WHERE github_id IS NOT NULL,
    UNIQUE(team_id, email) WHERE email IS NOT NULL
);
```

**Relationship Notes:**
- A `user` can belong to multiple `teams` via `memberships`
- A `team_member` is discovered from GitHub org and tracks metrics
- `team_members` are NOT the same as `users` - most developers don't log in

---

### GitHub Metrics

```sql
CREATE TABLE pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    github_pr_id BIGINT NOT NULL,
    github_repo TEXT NOT NULL,
    title TEXT,
    author_id UUID REFERENCES team_members(id),
    state TEXT, -- open, merged, closed
    pr_created_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    first_review_at TIMESTAMPTZ,
    cycle_time_hours NUMERIC,
    review_time_hours NUMERIC,
    additions INTEGER,
    deletions INTEGER,
    is_revert BOOLEAN DEFAULT FALSE,
    is_hotfix BOOLEAN DEFAULT FALSE,
    -- AI Detection
    is_ai_assisted BOOLEAN,
    ai_tools_detected JSONB, -- ["cursor", "copilot"]
    ai_detection_version TEXT,
    llm_summary JSONB, -- Full LLM analysis (ai, tech, summary, health)
    llm_summary_version TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, github_pr_id, github_repo)
);

CREATE TABLE pr_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    pr_id UUID REFERENCES pull_requests(id) ON DELETE CASCADE,
    reviewer_id UUID REFERENCES team_members(id),
    state TEXT, -- approved, changes_requested, commented
    submitted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    github_sha TEXT NOT NULL,
    github_repo TEXT NOT NULL,
    author_id UUID REFERENCES team_members(id),
    message TEXT,
    additions INTEGER,
    deletions INTEGER,
    committed_at TIMESTAMPTZ,
    pr_id UUID REFERENCES pull_requests(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(github_sha)
);

CREATE TABLE pr_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pr_id UUID REFERENCES pull_requests(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    additions INTEGER DEFAULT 0,
    deletions INTEGER DEFAULT 0,
    file_category TEXT, -- backend, frontend, devops, etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### Jira Metrics

```sql
CREATE TABLE jira_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    jira_key TEXT NOT NULL,
    jira_id TEXT NOT NULL,
    summary TEXT,
    issue_type TEXT,
    status TEXT,
    assignee_id UUID REFERENCES team_members(id),
    story_points NUMERIC,
    sprint_id TEXT,
    sprint_name TEXT,
    issue_created_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    cycle_time_hours NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, jira_id)
);
```

---

### AI Usage Metrics (Copilot)

```sql
CREATE TABLE ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    member_id UUID REFERENCES team_members(id),
    date DATE NOT NULL,
    source TEXT NOT NULL DEFAULT 'copilot', -- copilot, cursor (v2)
    suggestions_shown INTEGER DEFAULT 0,
    suggestions_accepted INTEGER DEFAULT 0,
    acceptance_rate NUMERIC,
    lines_suggested INTEGER DEFAULT 0,
    lines_accepted INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0, -- For team-level metrics
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, member_id, date, source)
);
```

---

### Survey Responses

```sql
CREATE TABLE pr_surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    pr_id UUID REFERENCES pull_requests(id) ON DELETE CASCADE,

    -- Author response
    author_id UUID REFERENCES team_members(id),
    author_ai_assisted BOOLEAN,
    author_responded_at TIMESTAMPTZ,
    author_channel TEXT, -- 'slack', 'github', 'web'

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pr_id)
);

CREATE TABLE pr_survey_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    survey_id UUID REFERENCES pr_surveys(id) ON DELETE CASCADE,
    reviewer_id UUID REFERENCES team_members(id),
    quality_rating INTEGER, -- 1=could be better, 2=ok, 3=super
    ai_guess BOOLEAN,
    guess_correct BOOLEAN,
    responded_at TIMESTAMPTZ,
    response_channel TEXT, -- 'slack', 'github', 'web'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(survey_id, reviewer_id)
);
```

---

### Aggregated Metrics

Pre-computed weekly aggregates for faster dashboard queries.

```sql
CREATE TABLE weekly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    member_id UUID REFERENCES team_members(id), -- NULL for team-level aggregates
    week_start DATE NOT NULL,

    -- Delivery
    prs_merged INTEGER DEFAULT 0,
    avg_cycle_time_hours NUMERIC,
    avg_review_time_hours NUMERIC,
    commits_count INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,

    -- Quality
    revert_count INTEGER DEFAULT 0,
    hotfix_count INTEGER DEFAULT 0,

    -- Jira
    story_points_completed NUMERIC DEFAULT 0,
    issues_resolved INTEGER DEFAULT 0,

    -- AI
    ai_assisted_prs INTEGER DEFAULT 0,

    -- Survey
    avg_quality_rating NUMERIC,
    surveys_completed INTEGER DEFAULT 0,
    guess_accuracy NUMERIC,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(team_id, member_id, week_start)
);
```

---

## Access Control

Layered visibility is enforced at the Django application layer:

### Team Isolation
- All metric models extend `BaseTeamModel` which adds `team` FK
- `for_team` manager automatically filters by current team context
- Views use `@login_and_team_required` or `@team_admin_required` decorators

### Two Role Systems

**1. Membership Role** (for logged-in users):
```python
# Stored on Membership model, checked via decorator
class Membership:
    role: 'admin' | 'member'  # Controls access to team settings
```

**2. TeamMember Role** (for metrics visibility):
```python
# Stored on TeamMember model, used for filtering dashboards
class TeamMember:
    role: 'developer' | 'lead' | 'admin'  # Controls data visibility
```

### Role-Based Visibility
```python
# Current user's membership determines access level
membership = Membership.objects.get(user=request.user, team=team)

# Admins (membership role) see all team data
if membership.is_admin():
    queryset = PullRequest.objects.filter(team=team)

# Members see based on their linked TeamMember (if any)
else:
    team_member = TeamMember.objects.filter(team=team, email=request.user.email).first()
    if team_member:
        queryset = PullRequest.objects.filter(author=team_member)
    else:
        queryset = PullRequest.objects.none()
```

### Implementation Notes
- Team context set via middleware (`/app/...` URLs)
- `request.team` available after `@login_and_team_required` decorator
- A user can be in multiple teams with different roles
- A TeamMember may not have a corresponding User (no login needed)

---

## Indexes

```sql
-- Team-scoped query indexes
CREATE INDEX idx_prs_team_merged ON pull_requests(team_id, merged_at);
CREATE INDEX idx_prs_team_author ON pull_requests(team_id, author_id, merged_at);
CREATE INDEX idx_prs_team_created ON pull_requests(team_id, pr_created_at);

-- Team member lookup indexes
CREATE INDEX idx_members_team_github ON team_members(team_id, github_username);
CREATE INDEX idx_members_team_active ON team_members(team_id, is_active);

-- Dashboard queries
CREATE INDEX idx_commits_date ON commits(committed_at);
CREATE INDEX idx_jira_resolved ON jira_issues(resolved_at);
CREATE INDEX idx_weekly_metrics_week ON weekly_metrics(week_start);
CREATE INDEX idx_surveys_pr ON pr_surveys(pr_id);
```

---

## Migrations

Django migrations handle all schema changes:

```bash
# Create new migrations after model changes
make migrations

# Apply migrations
make migrate
```
