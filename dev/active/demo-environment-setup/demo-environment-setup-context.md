# Demo Environment Setup - Context

**Last Updated: 2026-01-02**

## Key Files

### Management Commands

| File | Purpose |
|------|---------|
| `apps/users/management/commands/setup_demo_users.py` | Create demo users with passwords |
| `apps/metrics/management/commands/run_llm_analysis.py` | Run LLM analysis on PRs |
| `apps/metrics/management/commands/generate_insights.py` | Generate dashboard insights |
| `apps/metrics/management/commands/seed_real_projects.py` | Seed data from GitHub |

### Services

| File | Purpose |
|------|---------|
| `apps/metrics/services/insight_llm.py` | LLM-based insight generation |
| `apps/metrics/services/llm_prompts.py` | PR analysis prompts |
| `apps/metrics/services/dashboard_service.py` | Dashboard data aggregation |

### Models

| File | Purpose |
|------|---------|
| `apps/metrics/models.py` | PullRequest, DailyInsight, TeamMember |
| `apps/teams/models.py` | Team, Membership |
| `apps/users/models.py` | CustomUser |

### Configuration

| File | Purpose |
|------|---------|
| `apps/metrics/seeding/real_projects.py` | Project configs (polar, posthog) |
| `.env.unraid.example` | Unraid environment template |
| `docker-compose.unraid.yml` | Unraid Docker stack |

## Key Decisions

### 1. Static Demo (No Daily Sync)
- **Decision:** No IntegrationCredential needed
- **Rationale:** Simpler setup, no token management, data stays consistent for demos
- **Trade-off:** Data won't update automatically

### 2. Email/Password Authentication
- **Decision:** Use email/password login instead of GitHub OAuth
- **Rationale:** Demo users don't need real GitHub accounts
- **Implementation:** AUTH_MODE=all on Unraid

### 3. Fun Passwords
- **Decision:** Use memorable passwords like `show_me_posthog_data`
- **Rationale:** Easy to remember and type during demos
- **Security:** Acceptable for demo environment

### 4. Local Processing → Export → Import
- **Decision:** Process LLM locally, export, import to Unraid
- **Rationale:** Faster processing, cheaper (local Groq calls), one-time setup
- **Alternative:** Could run processing on Unraid (slower, uses production resources)

## Database Queries

### Check LLM Processing Status
```sql
SELECT
    t.name,
    COUNT(*) as total_prs,
    COUNT(*) FILTER (WHERE pr.llm_summary IS NOT NULL) as with_llm,
    COUNT(*) FILTER (WHERE pr.llm_summary IS NULL) as missing_llm
FROM teams_team t
JOIN metrics_pullrequest pr ON pr.team_id = t.id
WHERE t.slug IN ('posthog-demo', 'polar-demo')
GROUP BY t.name;
```

### Check Demo Users
```sql
SELECT u.email, m.role, t.name as team
FROM users_customuser u
JOIN teams_membership m ON m.user_id = u.id
JOIN teams_team t ON t.id = m.team_id
WHERE u.email LIKE 'demo@%';
```

### Check Insights
```sql
SELECT t.name, COUNT(*) as insight_count
FROM metrics_dailyinsight di
JOIN teams_team t ON t.id = di.team_id
WHERE t.slug IN ('posthog-demo', 'polar-demo')
GROUP BY t.name;
```

## Environment Variables

### Required for LLM Processing
```bash
GROQ_API_KEY=gsk_...  # Groq API key for LLM calls
```

### Unraid Configuration
```bash
AUTH_MODE=all  # Enable email/password login
DEBUG=False    # Production mode
```

## Dependencies

### Python Packages
- `groq` - LLM API client
- `factory-boy` - For seeding (dev only)
- `PyGithub` - GitHub API client

### External Services
- **Groq API** - LLM inference (llama-3.3-70b-versatile)
- **GitHub API** - PR data (already fetched)

## URLs

### Local Development
- App: http://localhost:8000
- Admin: http://localhost:8000/admin/

### Unraid Production
- App: https://dev2.ianchuk.com
- Login: https://dev2.ianchuk.com/accounts/login/

## Related Documentation

- [CLAUDE.md](/CLAUDE.md) - Coding guidelines
- [prd/DASHBOARDS.md](/prd/DASHBOARDS.md) - Dashboard specs
- [prd/AI-DETECTION-TESTING.md](/prd/AI-DETECTION-TESTING.md) - LLM analysis docs
