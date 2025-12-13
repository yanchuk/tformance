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

Seed realistic demo data for development and UI preview:

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

This creates:
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
