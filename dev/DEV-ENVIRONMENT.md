# Development Environment Guide

## Quick Start

```bash
# Start everything
make start-bg    # Start Postgres + Redis in background
make dev         # Start Django + Vite dev servers
```

## Access Points

| Service | URL | Notes |
|---------|-----|-------|
| **App** | http://localhost:8000 | Main application |
| **Admin** | http://localhost:8000/admin/ | Django admin interface |
| **Vite** | http://localhost:5173/static/ | Asset server (auto-started with `make dev`) |

## Admin Credentials

```
Email:    admin@example.com
Password: admin123
```

To create a new superuser:
```bash
uv run python manage.py shell << 'EOF'
from apps.users.models import CustomUser
user = CustomUser.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='admin123'
)
print(f'Created: {user.email}')
EOF
```

## Verification Checklist

Run after each phase to confirm everything works:

### 1. Services Running
```bash
docker ps  # Should show tformance-db-1 and tformance-redis-1
```

### 2. Migrations Applied
```bash
make migrate  # Should say "No migrations to apply" if up to date
```

### 3. Tests Passing
```bash
make test  # All tests should pass
```

### 4. Admin Accessible
1. Go to http://localhost:8000/admin/
2. Login with credentials above
3. Verify all expected models appear in sidebar

### 5. No Console Errors
- Check browser dev tools console for JavaScript errors
- Check terminal for Django errors

## Demo Data

Seed realistic demo data for development and UI preview.

### Scenario-Based Seeding (Recommended)

Use predefined scenarios that create coherent, story-driven data:

```bash
# List available scenarios
python manage.py seed_demo_data --list-scenarios

# Seed with a specific scenario (reproducible with --seed)
python manage.py seed_demo_data --scenario ai-success --seed 42
python manage.py seed_demo_data --scenario review-bottleneck --seed 123
python manage.py seed_demo_data --scenario baseline
python manage.py seed_demo_data --scenario detective-game

# Scenario without GitHub API (offline mode)
python manage.py seed_demo_data --scenario ai-success --no-github

# Clear and reseed
python manage.py seed_demo_data --clear --scenario ai-success
```

**Available Scenarios:**

| Scenario | Description | Key Pattern |
|----------|-------------|-------------|
| `ai-success` | Progressive AI adoption success story | AI: 10%→75%, Cycle time: 72h→24h |
| `review-bottleneck` | High AI output, bottlenecked reviews | 1 reviewer handles 60%, times worsen |
| `baseline` | Steady-state for comparison | AI: 15%, stable metrics |
| `detective-game` | Survey engagement focus | Varied guess accuracy 30-70% |

**Scenario Features:**
- **Deterministic**: Same `--seed` produces identical data
- **Hybrid sourcing**: 25% real GitHub PR metadata + 75% factory data
- **8 weeks of history**: Weekly progression matching scenario pattern
- **Member archetypes**: Different team member behaviors (early adopters, skeptics, etc.)

### Legacy Mode

For simple data generation without scenarios:

```bash
# Seed default demo data (1 team, 5 members, ~50 PRs, etc.)
python manage.py seed_demo_data

# Seed with custom amounts
python manage.py seed_demo_data --teams 2 --members 10 --prs 100

# Clear existing data before seeding
python manage.py seed_demo_data --clear

# Seed specific existing team by slug
python manage.py seed_demo_data --team-slug my-team
```

### Real Project Seeding

Seed demo data from real open source GitHub projects (Gumroad, Polar, PostHog, FastAPI):

```bash
# List available projects
python manage.py seed_real_projects --list-projects

# Recommended: Use progress script with resume capability
GITHUB_SEEDING_TOKEN="ghp_xxx" python scripts/seed_with_progress.py --project gumroad --clear

# Seed all projects with progress
GITHUB_SEEDING_TOKEN="ghp_xxx" python scripts/seed_with_progress.py --clear

# Resume from checkpoint if interrupted
python scripts/seed_with_progress.py --resume

# Management command (alternative)
python manage.py seed_real_projects --project posthog --max-prs 200 --days-back 60
```

**Requires GitHub PAT**: Set `GITHUB_SEEDING_TOKEN` environment variable.
Create token at https://github.com/settings/tokens with `public_repo` scope.

**Available Projects:**

| Project | Repository | Mode | Max PRs | Max Members | Notes |
|---------|------------|------|---------|-------------|-------|
| `gumroad` | antiwork/gumroad | Full | 1000 | 50 | Complete team picture |
| `polar` | polarsource/polar | Full | 1000 | 50 | Complete team picture |
| `posthog` | posthog/posthog | Sampled | 200 | 25 | Very active repo |
| `fastapi` | tiangolo/fastapi | Sampled | 300 | 15 | Framework repo |

**Rate Limit Handling:**
- Processes PRs in batches of 10 with 1s delay between batches
- Retry logic with exponential backoff for 403 errors (5s → 10s → 20s)
- Uses 3 parallel workers to stay within GitHub's secondary rate limits

**Features:**
- Fetches real GitHub data: PRs, commits, reviews, files, check runs
- Progress tracking script with resume capability
- Simulates Jira issues from PR metadata (extracts keys or generates)
- Simulates surveys with AI-assisted probability based on PR size
- Generates AI usage records per team member
- Calculates WeeklyMetrics aggregates

### Generated Data

All seeding modes create:
- Team members with GitHub/Jira/Slack identities
- Pull requests with realistic cycle times
- PR reviews (1-3 per PR)
- Commits linked to PRs
- Jira issues with story points
- AI usage records (Copilot/Cursor)
- PR surveys with reviewer responses
- Weekly aggregated metrics

## Current Models in Admin

### Metrics App (Phase 1)
- **Team Members** - Integration identities (GitHub, Jira, Slack)
- **Pull Requests** - GitHub PRs with cycle time metrics
- **PR Reviews** - GitHub PR reviews
- **Commits** - GitHub commits
- **Jira Issues** - Jira issues with sprint tracking
- **AI Usage Daily** - Daily Copilot/Cursor metrics
- **PR Surveys** - Author AI disclosure
- **PR Survey Reviews** - Reviewer feedback
- **Weekly Metrics** - Pre-computed aggregates

## Stopping Services

```bash
make stop  # Stop Postgres + Redis containers
# Ctrl+C to stop dev server if running in foreground
```

## Troubleshooting

### Port already in use
```bash
lsof -i :8000  # Find process using port
kill -9 <PID>  # Kill it
```

### Database connection error
```bash
make start-bg  # Ensure containers are running
docker logs tformance-db-1  # Check Postgres logs
```

### Missing migrations
```bash
make migrations  # Create new migrations
make migrate     # Apply them
```

### Reset database (nuclear option)
```bash
make stop
docker volume rm tformance_postgres-data
make start-bg
make migrate
# Recreate superuser (see above)
```

---

## Real-World Integration Testing

For testing with real GitHub, Jira, and Slack integrations using ngrok, see the comprehensive guide:

**[Real-World Testing Guide](guides/REAL-WORLD-TESTING.md)**

The guide covers:
- ngrok setup and configuration
- Creating OAuth apps for GitHub, Jira, and Slack
- Step-by-step testing checklists for each integration
- End-to-end PR survey flow testing
- Troubleshooting common issues
