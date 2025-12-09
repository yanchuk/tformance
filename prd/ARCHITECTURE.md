# Technical Architecture

> Part of [PRD Documentation](README.md)

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT INFRASTRUCTURE                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Supabase Project                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │   users     │  │   metrics   │  │   surveys   │        │  │
│  │  │   table     │  │   tables    │  │   table     │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  │                         │                                  │  │
│  │                    Row Level Security                      │  │
│  │                    (layered visibility)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              ↑                                   │
│                              │ Direct connection                 │
│                              ↓                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │               Metabase (Self-hosted or Cloud)              │  │
│  │               Embedded dashboards in our app               │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                               ↑
                               │ Writes metrics
                               │ (no data stored on our side)
                               ↓
┌─────────────────────────────────────────────────────────────────┐
│                       OUR SERVICE                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   Auth &    │  │    Sync     │  │   Slack     │              │
│  │  Accounts   │  │   Workers   │  │    Bot      │              │
│  │             │  │             │  │             │              │
│  │ - Users     │  │ - GitHub    │  │ - Surveys   │              │
│  │ - Billing   │  │ - Jira      │  │ - Leaderbd  │              │
│  │ - OAuth     │  │ - Copilot   │  │ - Reveals   │              │
│  │   tokens    │  │             │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  Storage: Only accounts, billing, encrypted OAuth tokens         │
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

**Frequency: Daily** (scheduled job, e.g., 2 AM in client's timezone)

```
1. Scheduled job runs daily
2. For each connected client:
   a. Fetch new/updated PRs from GitHub API
   b. Fetch new/updated issues from Jira API
   c. Fetch usage data from Copilot API (if available)
   d. Transform to standard schema
   e. Write directly to client's Supabase
3. No data persisted on our side
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
3. Look up author and reviewers in client's user table
4. Send Slack DMs via Slack API
5. User clicks button in Slack
6. Our service receives interaction
7. Write response to client's Supabase
8. If both parties responded, send reveal message
```

---

## Data Storage Model

| Data Type | Location | Why |
|-----------|----------|-----|
| OAuth tokens (GitHub, Jira) | Our service (AES-256 encrypted) | Needed for API sync |
| Account/billing info | Our service | Standard SaaS |
| All metrics & analytics | Client's Supabase | Their data, their control |
| Survey responses | Client's Supabase | Sensitive feedback |
| User mappings | Client's Supabase | PII stays with them |

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

### Security Claims
- "Your engineering data never touches our servers"
- "We only store encrypted API tokens for sync"
- "You own your database - export or delete anytime"
- "Open schema - inspect exactly what we store"

### Privacy by Design
| Principle | Implementation |
|-----------|----------------|
| Data minimization | Only collect what's needed for metrics |
| Purpose limitation | Data used only for agreed analytics |
| User control | Devs see own data, can request deletion |
| Transparency | Open schema, visible RLS policies |

### GDPR Considerations
- Client is data controller (their Supabase)
- We are data processor (sync service)
- DPA (Data Processing Agreement) provided
- Client can delete all data by dropping Supabase tables

### For Future (v2+)
- SOC 2 Type II certification
- Audit log of all data access
- EU-specific data processing options
