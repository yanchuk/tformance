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

## Production-Like Local Testing

This guide walks you through testing the full app locally with real OAuth integrations and webhooks.

### Prerequisites

- [ ] Local dev environment running (`make start-bg && make dev`)
- [ ] ngrok installed (`brew install ngrok` or https://ngrok.com/download)
- [ ] GitHub account with access to an organization
- [ ] Jira Cloud account (optional, for Jira integration)

---

## Step 1: Expose Local Server with ngrok

Webhooks require a public URL. Use ngrok to tunnel to your local server:

```bash
# Start ngrok tunnel (in a separate terminal)
ngrok http 8000
```

You'll get a URL like: `https://abc123.ngrok-free.app`

**Important:** Copy this URL - you'll need it for OAuth callbacks and webhooks.

Add the ngrok URL to your `.env`:
```bash
# Add to .env
ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app
CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app
```

Restart the dev server after updating `.env`.

---

## Step 2: Create GitHub OAuth App

1. Go to: **GitHub → Settings → Developer settings → OAuth Apps → New OAuth App**
   - Or use this link: https://github.com/settings/applications/new

2. Fill in the form:
   | Field | Value |
   |-------|-------|
   | **Application name** | `tformance-dev` |
   | **Homepage URL** | `https://abc123.ngrok-free.app` |
   | **Authorization callback URL** | `https://abc123.ngrok-free.app/a/TEAM_SLUG/integrations/github/callback/` |

   > **Note:** Replace `abc123.ngrok-free.app` with your actual ngrok URL.
   > Replace `TEAM_SLUG` with your team's slug (you'll create this after signup).

3. After creation, you'll see:
   - **Client ID** (public)
   - **Client Secret** (click "Generate a new client secret")

4. Add to your `.env`:
   ```bash
   GITHUB_CLIENT_ID=your_client_id_here
   GITHUB_CLIENT_SECRET=your_client_secret_here
   ```

5. Restart the dev server.

---

## Step 3: Create Jira OAuth App (Optional)

1. Go to: https://developer.atlassian.com/console/myapps/
   - Click **Create** → **OAuth 2.0 integration**

2. Fill in the form:
   | Field | Value |
   |-------|-------|
   | **Name** | `tformance-dev` |

3. Configure OAuth 2.0 (3LO):
   - Go to **Authorization** → **Add**
   - **Callback URL:** `https://abc123.ngrok-free.app/a/TEAM_SLUG/integrations/jira/callback/`

4. Configure Permissions (APIs):
   - Go to **Permissions** → **Add**
   - Add **Jira platform REST API** with scopes:
     - `read:jira-work`
     - `read:jira-user`
     - `offline_access`

5. Copy credentials from **Settings**:
   - **Client ID**
   - **Secret** (generate one)

6. Add to your `.env`:
   ```bash
   JIRA_CLIENT_ID=your_jira_client_id_here
   JIRA_CLIENT_SECRET=your_jira_client_secret_here
   ```

7. Restart the dev server.

---

## Step 4: Sign Up and Create a Team

1. Open your ngrok URL in browser: `https://abc123.ngrok-free.app`

2. **Sign Up** with a new account:
   - Click "Sign Up" (or go to `/accounts/signup/`)
   - Fill in email and password
   - Verify email if required (check terminal for verification link in dev mode)

3. **Create a Team:**
   - After login, you'll be prompted to create a team
   - Choose a name (e.g., "My Dev Team")
   - Note the **team slug** (e.g., `my-dev-team`) - you'll need this

4. **Update OAuth Callback URLs:**
   - Go back to GitHub OAuth App settings
   - Update callback URL: `https://abc123.ngrok-free.app/a/my-dev-team/integrations/github/callback/`
   - Do the same for Jira if configured

---

## Step 5: Connect GitHub Integration

1. Go to **Integrations** in the app sidebar

2. Click **Connect GitHub**

3. You'll be redirected to GitHub to authorize the app:
   - Select your **organization** to grant access
   - Approve requested permissions

4. After redirect back, select your organization if prompted

5. **Configure Members:**
   - Click **Members** on the GitHub card
   - Sync organization members
   - Toggle which members to track

6. **Configure Repositories:**
   - Click **Repositories** on the GitHub card
   - Toggle which repos to track
   - Webhooks will be automatically registered

---

## Step 6: Test GitHub Webhooks

1. **Create a test PR** in one of your tracked repositories

2. **Check webhook delivery:**
   - Go to your GitHub OAuth App → **Advanced** → **Recent Deliveries**
   - Or check: `GitHub Repo → Settings → Webhooks → Recent Deliveries`

3. **Verify in database:**
   ```bash
   # Open Django shell
   make shell

   # Check if PR was recorded
   from apps.metrics.models import PullRequest
   PullRequest.objects.order_by('-created_at')[:5]
   ```

4. **Check webhook logs in terminal** for incoming requests

---

## Step 7: Connect Jira Integration (Optional)

1. Go to **Integrations** in the app

2. Click **Connect Jira**

3. Authorize access to your Jira site

4. Select which Jira site to connect (if you have multiple)

5. **Configure Projects:**
   - Click **Projects** on the Jira card
   - Toggle which projects to track

---

## Step 8: Manual Sync (For Testing)

Instead of waiting for scheduled Celery tasks, trigger syncs manually:

### Sync GitHub Data
```bash
make shell
```
```python
from apps.integrations.models import TrackedRepository
from apps.integrations.services.github_sync import sync_repository_history

# Get a tracked repo
repo = TrackedRepository.objects.first()
print(f"Syncing: {repo.full_name}")

# Run historical sync
result = sync_repository_history(repo)
print(result)
```

### Sync Jira Data
```python
from apps.integrations.models import TrackedJiraProject
from apps.integrations.services.jira_sync import sync_project_issues

# Get a tracked project
project = TrackedJiraProject.objects.first()
print(f"Syncing: {project.jira_project_key}")

# Run full sync
result = sync_project_issues(project, full_sync=True)
print(result)
```

### Sync Jira Users
```python
from apps.teams.models import Team
from apps.integrations.models import JiraIntegration
from apps.integrations.services.jira_user_matching import sync_jira_users

team = Team.objects.first()
integration = JiraIntegration.objects.get(team=team)
credential = integration.credential

result = sync_jira_users(team, credential)
print(f"Matched: {result['matched_count']}, Unmatched: {result['unmatched_count']}")
```

---

## Step 9: Run Celery Workers (For Background Tasks)

For scheduled syncs and background processing:

```bash
# Terminal 1: Celery worker
celery -A tformance worker --loglevel=info

# Terminal 2: Celery beat (scheduler)
celery -A tformance beat --loglevel=info
```

Or run both together (for dev):
```bash
celery -A tformance worker --beat --loglevel=info
```

---

## Environment Variables Summary

Your `.env` should include these for full testing:

```bash
# Required
SECRET_KEY="your-secret-key"
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,abc123.ngrok-free.app
CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tformance
REDIS_URL=redis://localhost:6379
INTEGRATION_ENCRYPTION_KEY="your-fernet-key"

# GitHub Integration
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# Jira Integration (optional)
JIRA_CLIENT_ID=your_jira_client_id
JIRA_CLIENT_SECRET=your_jira_client_secret

# Webhook Secret (for verifying GitHub webhooks)
GITHUB_WEBHOOK_SECRET=your_webhook_secret
```

Generate keys:
```bash
# Generate SECRET_KEY
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# Generate INTEGRATION_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate GITHUB_WEBHOOK_SECRET
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Testing Checklist

- [ ] ngrok tunnel running and accessible
- [ ] `.env` configured with all required variables
- [ ] Dev server restarted after `.env` changes
- [ ] Signed up and created a team
- [ ] GitHub OAuth app callback URL updated with correct team slug
- [ ] GitHub connected successfully
- [ ] Organization members synced
- [ ] At least one repository tracked
- [ ] Webhook registered (check GitHub repo settings)
- [ ] Test PR created and webhook received
- [ ] PR data visible in database/admin
- [ ] (Optional) Jira connected and projects tracked
- [ ] (Optional) Manual sync executed successfully

---

## Common Issues

### "Invalid redirect_uri" from GitHub/Jira
- Ensure callback URL in OAuth app matches exactly (including trailing slash)
- Check that your ngrok URL hasn't changed (free tier rotates URLs)

### Webhook not received
- Check ngrok terminal for incoming requests
- Verify webhook is registered in GitHub repo settings
- Check for errors in Django terminal output

### "CSRF verification failed"
- Ensure ngrok URL is in `ALLOWED_HOSTS`
- Ensure ngrok URL (with `https://`) is in `CSRF_TRUSTED_ORIGINS`
  ```bash
  # In .env
  CSRF_TRUSTED_ORIGINS=https://abc123.ngrok-free.app
  ```

### OAuth tokens expired
- Jira tokens expire after 1 hour - the app handles refresh automatically
- GitHub tokens don't expire but can be revoked

### ngrok URL changed
- Free ngrok gives new URL each time you restart
- Update: OAuth app callback URLs, `.env` ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS
- Consider ngrok paid plan for stable URLs, or use a custom domain
