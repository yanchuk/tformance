# Data Model

> Part of [PRD Documentation](README.md)

## Overview

All tables are in our PostgreSQL database, with team isolation enforced via `team_id` foreign keys. Django models extend `BaseTeamModel` which automatically adds the team relationship.

---

## Tables

### Core Entities

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    display_name TEXT,
    github_username TEXT,
    github_id TEXT,
    jira_account_id TEXT,
    slack_user_id TEXT,
    role TEXT DEFAULT 'developer', -- developer, lead, admin
    team_id UUID REFERENCES teams(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    github_team_slug TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### GitHub Metrics

```sql
CREATE TABLE pull_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_pr_id BIGINT NOT NULL,
    github_repo TEXT NOT NULL,
    title TEXT,
    author_id UUID REFERENCES users(id),
    state TEXT, -- open, merged, closed
    created_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    first_review_at TIMESTAMPTZ,
    cycle_time_hours NUMERIC,
    review_time_hours NUMERIC,
    additions INTEGER,
    deletions INTEGER,
    is_revert BOOLEAN DEFAULT FALSE,
    is_hotfix BOOLEAN DEFAULT FALSE,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(github_pr_id, github_repo)
);

CREATE TABLE pr_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pr_id UUID REFERENCES pull_requests(id),
    reviewer_id UUID REFERENCES users(id),
    state TEXT, -- approved, changes_requested, commented
    submitted_at TIMESTAMPTZ
);

CREATE TABLE commits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_sha TEXT NOT NULL,
    github_repo TEXT NOT NULL,
    author_id UUID REFERENCES users(id),
    message TEXT,
    additions INTEGER,
    deletions INTEGER,
    committed_at TIMESTAMPTZ,
    pr_id UUID REFERENCES pull_requests(id),
    UNIQUE(github_sha)
);
```

---

### Jira Metrics

```sql
CREATE TABLE jira_issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jira_key TEXT NOT NULL,
    jira_id TEXT NOT NULL,
    summary TEXT,
    issue_type TEXT,
    status TEXT,
    assignee_id UUID REFERENCES users(id),
    story_points NUMERIC,
    sprint_id TEXT,
    sprint_name TEXT,
    created_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    cycle_time_hours NUMERIC,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(jira_id)
);
```

---

### AI Usage Metrics

```sql
CREATE TABLE ai_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    date DATE NOT NULL,
    source TEXT NOT NULL, -- copilot (cursor in v2)
    active_hours NUMERIC,
    suggestions_shown INTEGER,
    suggestions_accepted INTEGER,
    acceptance_rate NUMERIC,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, date, source)
);
```

---

### Survey Responses

```sql
CREATE TABLE pr_surveys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pr_id UUID REFERENCES pull_requests(id),

    -- Author response
    author_id UUID REFERENCES users(id),
    author_ai_assisted BOOLEAN,
    author_responded_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pr_id)
);

CREATE TABLE pr_survey_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    survey_id UUID REFERENCES pr_surveys(id),
    reviewer_id UUID REFERENCES users(id),
    quality_rating INTEGER, -- 1=could be better, 2=ok, 3=super
    ai_guess BOOLEAN,
    guess_correct BOOLEAN,
    responded_at TIMESTAMPTZ,
    UNIQUE(survey_id, reviewer_id)
);
```

---

### Aggregated Metrics

Pre-computed weekly aggregates for faster dashboard queries.

```sql
CREATE TABLE weekly_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    team_id UUID REFERENCES teams(id),
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

    UNIQUE(user_id, week_start)
);
```

---

## Access Control

Layered visibility is enforced at the Django application layer:

### Team Isolation
- All models extend `BaseTeamModel` which adds `team` FK
- `for_team` manager automatically filters by current team context
- Views use `@login_and_team_required` decorator

### Role-Based Visibility
```python
# Developers see only their own data
if user.role == 'developer':
    queryset = queryset.filter(author=user.team_member)

# Leads see their team's data
elif user.role == 'lead':
    queryset = queryset.filter(team=user.current_team)

# Admins see all data in their team
elif user.role == 'admin':
    queryset = queryset.filter(team=user.current_team)
```

### Implementation Notes
- Team context set via URL (`/a/<team_slug>/...`)
- Membership checked via `Membership` model
- Role stored on `Membership` (user can have different roles per team)

---

## Indexes

```sql
-- For dashboard queries
CREATE INDEX idx_prs_merged_at ON pull_requests(merged_at);
CREATE INDEX idx_prs_author ON pull_requests(author_id);
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
