# Demo Environment Setup for Polar and PostHog

**Last Updated: 2026-01-02**

## Executive Summary

Create a production-ready demo environment showcasing Tformance to Polar and PostHog teams. The demo will include real GitHub data from their public repositories, LLM-analyzed PRs, engineering insights, and dedicated demo user accounts. Data will be processed locally and exported to the Unraid deployment at `dev2.ianchuk.com`.

## Current State Analysis

### Existing Data (as of 2026-01-02)

| Team | Total PRs | LLM Processed | Missing | Team Members | Repos |
|------|-----------|---------------|---------|--------------|-------|
| **PostHog Analytics** (`posthog-demo`) | 6,385 | 6,250 (98%) | 135 | 927 | 4 |
| **Polar.sh** (`polar-demo`) | 3,265 | 2,012 (62%) | 1,253 | 153 | 4 |

### Repositories Tracked

**PostHog:**
- `PostHog/posthog` - Main product (1,755 PRs)
- `PostHog/posthog.com` - Website (3,487 PRs)
- `PostHog/posthog-js` - JS SDK (935 PRs)
- `PostHog/posthog-python` - Python SDK (208 PRs)

**Polar:**
- `polarsource/polar` - Main product (2,783 PRs)
- `polarsource/polar-adapters` - Adapters (309 PRs)
- `polarsource/polar-js` - JS SDK (103 PRs)
- `polarsource/polar-python` - Python SDK (70 PRs)

### Infrastructure

- **Local:** macOS development environment with full Django stack
- **Target:** Unraid server at `dev2.ianchuk.com`
  - Full stack: Django + Celery worker + Celery beat + Redis + Postgres
  - Cloudflare Tunnel for external access
  - AUTH_MODE=all (email/password login enabled)

## Proposed Future State

### Demo Experience

1. **Demo Users** can log in with memorable credentials:
   - `demo@posthog.com` / `show_me_posthog_data`
   - `demo@polar.sh` / `show_me_polar_data`

2. **Rich Data** available on login:
   - 90 days of real PR data with LLM analysis
   - Engineering insights (LLM-generated weekly summaries)
   - Team member data from GitHub contributors
   - All dashboard metrics functional

3. **Static Demo** (no daily sync needed):
   - Data frozen at export time
   - No IntegrationCredential required
   - Simpler maintenance

## Implementation Phases

### Phase 1: Complete LLM Processing (Local)

**Objective:** Fill in missing LLM analysis for all PRs

**Commands:**
```bash
# PostHog - 135 missing PRs (~5 min @ 2s/request)
GROQ_API_KEY=<key> python manage.py run_llm_analysis --team "PostHog Analytics" --limit 200

# Polar - 1,253 missing PRs (~45 min @ 2s/request)
GROQ_API_KEY=<key> python manage.py run_llm_analysis --team "Polar.sh" --limit 1500
```

**Verification:**
```sql
SELECT t.name, COUNT(*) as total,
       COUNT(*) FILTER (WHERE llm_summary IS NOT NULL) as with_llm
FROM metrics_pullrequest pr
JOIN teams_team t ON t.id = pr.team_id
WHERE t.slug IN ('posthog-demo', 'polar-demo')
GROUP BY t.name;
```

### Phase 2: Generate Dashboard Insights (Local)

**Objective:** Create LLM-generated engineering insights for dashboard

**Commands:**
```bash
# Generate insights for both teams
python manage.py generate_insights --team-slug posthog-demo
python manage.py generate_insights --team-slug polar-demo
```

**Alternative (for richer LLM insights):**
```python
# Via Django shell
from datetime import date, timedelta
from apps.teams.models import Team
from apps.metrics.services.insight_llm import gather_insight_data, generate_insight, cache_insight

for slug in ['posthog-demo', 'polar-demo']:
    team = Team.objects.get(slug=slug)
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    data = gather_insight_data(team, start_date, end_date)
    insight = generate_insight(data)
    cache_insight(team, insight, end_date, cadence="weekly")
    print(f"Generated insight for {team.name}")
```

### Phase 3: Create Demo Users (Local)

**Objective:** Create demo user accounts with team memberships

**Commands:**
```bash
# List available demo users and verify teams exist
python manage.py setup_demo_users --list

# Create demo users
python manage.py setup_demo_users

# Verify
python manage.py setup_demo_users --list
```

**Demo Accounts:**
| Email | Password | Team |
|-------|----------|------|
| `demo@posthog.com` | `show_me_posthog_data` | PostHog Analytics |
| `demo@polar.sh` | `show_me_polar_data` | Polar.sh |

### Phase 4: Export Demo Data (Local)

**Objective:** Export relevant database tables for Unraid import

**Tables to Export:**
```
teams_team
teams_membership
users_customuser
account_emailaddress
metrics_pullrequest
metrics_prfile
metrics_prreview
metrics_commit
metrics_prcomment
metrics_checkrun
metrics_teammember
metrics_weeklymetrics
metrics_dailyinsight
metrics_aiusagedaily
metrics_jiraissue
metrics_prsurvey
metrics_prsurveyreview
```

**Export Command:**
```bash
# Export specific tables for demo teams
pg_dump -h localhost -U tformance -d tformance \
  --data-only \
  --table=teams_team \
  --table=teams_membership \
  --table=users_customuser \
  --table=account_emailaddress \
  --table=metrics_* \
  -f demo_data.sql

# Or use Django's dumpdata for JSON format
python manage.py dumpdata \
  teams.team teams.membership \
  users.customuser \
  account.emailaddress \
  metrics \
  --indent 2 \
  -o demo_data.json
```

### Phase 5: Import on Unraid

**Objective:** Load demo data into Unraid PostgreSQL

**Steps:**
```bash
# 1. Copy export file to Unraid
scp demo_data.sql unraid:/mnt/user/appdata/tformance/

# 2. SSH into Unraid
ssh unraid

# 3. Import into Docker container
docker exec -i tformance-db psql -U tformance -d tformance < /mnt/user/appdata/tformance/demo_data.sql

# Or for JSON format:
docker cp demo_data.json tformance-web:/app/
docker exec tformance-web python manage.py loaddata /app/demo_data.json

# 4. Verify data
docker exec tformance-db psql -U tformance -d tformance -c "
SELECT t.name, COUNT(pr.id) as prs
FROM teams_team t
LEFT JOIN metrics_pullrequest pr ON pr.team_id = t.id
WHERE t.slug LIKE '%demo%'
GROUP BY t.name;"
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Groq API rate limits | Medium | Medium | Run during off-peak hours, use 2.1s delay |
| Data export size too large | Low | Low | Export only demo teams, compress file |
| User already exists on Unraid | Low | Low | Use `--clear` flag or skip existing |
| Schema mismatch | Low | High | Run migrations on Unraid first |

## Success Metrics

- [ ] 100% LLM coverage for both teams (all PRs have `llm_summary`)
- [ ] Dashboard insights visible for both teams
- [ ] Demo users can log in at `dev2.ianchuk.com`
- [ ] All dashboard pages render correctly with data
- [ ] Login works with email/password

## Required Resources

### Environment Variables (Local)
```bash
GROQ_API_KEY=<your-groq-api-key>
GITHUB_SEEDING_TOKENS=<optional-for-refresh>
```

### Time Estimates
| Task | Duration |
|------|----------|
| LLM Analysis (PostHog) | ~5 min |
| LLM Analysis (Polar) | ~45 min |
| Generate Insights | ~2 min |
| Create Demo Users | ~1 min |
| Export Data | ~5 min |
| Import on Unraid | ~10 min |
| **Total** | **~1 hour** |

## Dependencies

1. **Groq API Key** - Required for LLM analysis
2. **PostgreSQL Access** - Local and Unraid
3. **SSH Access to Unraid** - For import step
4. **Existing Team Data** - Already seeded via `seed_real_projects`
