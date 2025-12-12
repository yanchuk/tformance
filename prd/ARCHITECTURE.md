# Technical Architecture

> Part of [PRD Documentation](README.md)

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         OUR SERVICE                              │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL Database                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │   users     │  │   metrics   │  │   surveys   │        │  │
│  │  │   table     │  │   tables    │  │   table     │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  │                         │                                  │  │
│  │              All tables have team_id FK                    │  │
│  │              (application-level isolation)                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↑                                   │
│                              │                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Auth &    │  │    Sync     │  │   Slack     │              │
│  │  Accounts   │  │   Workers   │  │    Bot      │              │
│  │             │  │             │  │             │              │
│  │ - Users     │  │ - GitHub    │  │ - Surveys   │              │
│  │ - Billing   │  │ - Jira      │  │ - Leaderbd  │              │
│  │ - OAuth     │  │ - Copilot   │  │ - Reveals   │              │
│  │   tokens    │  │             │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                              │                                   │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Dashboard Layer                         │  │
│  │  Django Views + Chart.js + HTMX + DaisyUI                 │  │
│  │  Native charts rendered server-side with lazy loading      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                               ↑
                               │ API calls
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │  GitHub  │  │   Jira   │  │  Slack   │                      │
│  │   API    │  │   API    │  │   API    │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Metrics Sync

**Frequency: Daily** (scheduled Celery job)

```
1. Scheduled job runs daily for each team
2. For each connected team:
   a. Fetch new/updated PRs from GitHub API
   b. Fetch new/updated issues from Jira API
   c. Fetch usage data from Copilot API (if available)
   d. Transform to standard schema
   e. Write to database with team_id
```

**Why daily (not hourly):**
- Analytics don't need real-time data
- Reduces API rate limit concerns
- Simpler implementation
- Lower infrastructure costs

---

## Data Flow: PR Survey (Real-time)

```
1. GitHub webhook: PR merged
2. Our service receives webhook
3. Look up author and reviewers in TeamMember table
4. Send Slack DMs via Slack API
5. User clicks button in Slack
6. Our service receives interaction
7. Write response to database
8. If both parties responded, send reveal message
```

---

## Data Storage Model

| Data Type | Location | Why |
|-----------|----------|-----|
| OAuth tokens (GitHub, Jira) | Our database (Fernet encrypted) | Needed for API sync |
| Account/billing info | Our database | Standard SaaS |
| All metrics & analytics | Our database (team-isolated) | Centralized management |
| Survey responses | Our database (team-isolated) | Part of metrics |
| User/team member data | Our database (team-isolated) | Needed for matching |

### Data Isolation

All metric tables have a `team_id` foreign key. The Django application enforces team isolation:
- `BaseTeamModel` base class adds `team` FK automatically
- `for_team` model manager filters by current team context
- Views use `@login_and_team_required` decorator

---

## Integrations

### GitHub Integration

**OAuth Scopes Required:**
- `read:org` - Read org members, teams
- `repo` - Read repository data, PRs, commits
- `read:user` - Read user profile data
- `manage_billing:copilot` - Copilot metrics (optional)

**Webhooks:**
- `pull_request` - PR opened, closed, merged
- `pull_request_review` - Review submitted

**API Endpoints Used:**
| Endpoint | Purpose |
|----------|---------|
| `GET /orgs/{org}/members` | List org members (auto-discovery) |
| `GET /orgs/{org}/teams` | List teams |
| `GET /repos/{owner}/{repo}/pulls` | List PRs |
| `GET /repos/{owner}/{repo}/commits` | List commits |
| `GET /orgs/{org}/copilot/metrics` | Copilot usage (if 5+ licensed users) |

**Sync Frequency:** Daily

---

### Jira Integration

**OAuth Scopes Required:**
- `read:jira-work` - Read issues, projects
- `read:jira-user` - Read user data

**API Endpoints Used:**
| Endpoint | Purpose |
|----------|---------|
| `GET /rest/api/3/users/search` | List users |
| `GET /rest/api/3/search` | Search issues (JQL) |
| `GET /rest/agile/1.0/board/{boardId}/sprint` | Sprint data |

**JQL for Sync:**
```
project IN ({configured_projects}) AND updated >= -{sync_window}
```

**Sync Frequency:** Daily

---

### GitHub Copilot Integration

**Authentication:** GitHub OAuth token with `manage_billing:copilot` scope

**API Endpoints Used:**
| Endpoint | Purpose |
|----------|---------|
| `GET /orgs/{org}/copilot/metrics` | Team usage metrics |

**Data Available:**
- Active users count
- Suggestions shown/accepted by language
- IDE breakdown
- Model usage

**Limitation:** Requires 5+ licensed users to return data. For teams without Copilot metrics, rely on self-reported AI attribution via PR surveys.

**Sync Frequency:** Daily

---

### Slack Integration

**OAuth Scopes Required:**
- `chat:write` - Send DMs and channel messages
- `users:read` - Read user list for matching
- `users:read.email` - Read emails for matching

**Bot Features:**
| Feature | Implementation |
|---------|----------------|
| PR Survey | Interactive message with buttons |
| Reveal | Follow-up message in thread |
| Leaderboard | Scheduled message to channel |

**Interaction Flow:**
```
1. Bot sends interactive message
2. User clicks button
3. Slack sends interaction payload to our webhook
4. We process and respond with acknowledgment
5. Update original message or send follow-up
```

---

## Security & Privacy

### Security Approach
- OAuth tokens encrypted at rest using Fernet (AES-256)
- All data isolated by team at application layer
- Role-based access control (developer, lead, admin)
- Data export available on request

### Privacy by Design
| Principle | Implementation |
|-----------|----------------|
| Data minimization | Only collect what's needed for metrics |
| Purpose limitation | Data used only for agreed analytics |
| User control | Devs see own data, can request deletion |
| Team isolation | All queries scoped by team_id |

### GDPR Considerations
- We are data controller and processor
- DPA (Data Processing Agreement) provided on request
- Data deletion available via support request
- Data export in standard formats (CSV, JSON)

### For Future (v2+)
- SOC 2 Type II certification
- Audit log of all data access
- EU-specific data processing options
- BYOS (Bring Your Own Storage) for enterprise
