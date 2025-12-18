# Real-World Integration Testing Guide

This guide walks you through setting up a tunnel (Cloudflare Tunnel recommended) and creating real GitHub, Jira, and Slack apps for end-to-end integration testing.

**Example domain used throughout:** `dev.ianchuk.com` (replace with your own tunnel domain)

## Testing Progress

| Integration | Status | Date Verified | Notes |
|-------------|--------|---------------|-------|
| Tunnel | ✅ Verified | 2025-12-17 | Cloudflare Tunnel at `dev.ianchuk.com` |
| GitHub OAuth | ✅ Verified | 2025-12-17 | OAuth flow, org selection, member sync working |
| GitHub Copilot | ⏳ Pending | - | Requires org with 5+ Copilot licenses |
| Jira OAuth | ⏳ Pending | - | - |
| Slack OAuth | ⏳ Pending | - | - |

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Tunnel Setup](#phase-1-tunnel-setup)
3. [Phase 2: GitHub App Setup](#phase-2-github-app-setup)
4. [Phase 2.5: GitHub Copilot Testing](#phase-25-github-copilot-testing)
5. [Phase 3: Jira App Setup](#phase-3-jira-app-setup)
6. [Phase 4: Slack App Setup](#phase-4-slack-app-setup)
7. [Phase 5: Testing Checklist](#phase-5-testing-checklist)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- [ ] Local development environment running (`make dev`)
- [ ] Access to create apps on GitHub, Atlassian, and Slack
- [ ] A GitHub organization (free tier works - see below)
- [ ] A test Jira Cloud site (free tier available)
- [ ] A test Slack workspace (create one for free)

### Creating a Free GitHub Organization

The app requires a GitHub **organization** (personal accounts alone won't work).

1. Go to https://github.com/organizations/new
2. Choose **Free** plan (includes unlimited repos and collaborators)
3. Name it something like `yourname-test`
4. Complete setup
5. Create or fork a test repository into the organization

Free orgs include: unlimited public/private repos, unlimited collaborators, 2,000 Actions minutes/month.

---

## Phase 1: Tunnel Setup

You need a public URL to receive OAuth callbacks and webhooks. This guide uses **Cloudflare Tunnel** with domain `dev.ianchuk.com`.

### Install Cloudflared

```bash
brew install cloudflared
```

### Using the Existing Tunnel

A persistent tunnel is already configured at `dev.ianchuk.com`. To start it:

```bash
cloudflared tunnel run tformance-dev
```

The tunnel config is at `~/.cloudflared/config.yml` and routes traffic to `http://localhost:8000`.

---

### Configure Django for Your Tunnel

Add the tunnel domain to `.env`:

```bash
# Example with dev.ianchuk.com (replace with your tunnel domain)
ALLOWED_HOSTS=localhost,127.0.0.1,dev.ianchuk.com
CSRF_TRUSTED_ORIGINS=https://dev.ianchuk.com

# Trust proxy headers (required for OAuth redirect URLs to use https://)
USE_X_FORWARDED_HOST=True

# Disable Vite dev server (required for tunnel - avoids CORS errors)
DJANGO_VITE_DEV_MODE=False
```

Build static assets (required when `DJANGO_VITE_DEV_MODE=False`):
```bash
npm run build
```

Restart Django:
```bash
make dev
```

### Verify Tunnel is Working

1. Visit your tunnel URL in browser (e.g., `https://dev.ianchuk.com`)
2. You should see the app homepage with proper styling (no CORS errors in console)
3. Test health endpoint:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://dev.ianchuk.com/health/
   # Expected: 200
   ```
4. Test login page loads:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" https://dev.ianchuk.com/accounts/login/
   # Expected: 200
   ```

**Troubleshooting Tunnel:**
- If you see CORS errors in browser console, ensure `DJANGO_VITE_DEV_MODE=False` is set and you ran `npm run build`
- If you get 503 errors, check that Django is running on port 8000
- For Cloudflare Tunnel: check `~/.cloudflared/config.yml` has correct ingress rules

---

## Phase 2: GitHub App Setup

You'll create a GitHub OAuth App to enable GitHub integration.

### 2.1 Create GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click **OAuth Apps** in the left sidebar
3. Click **New OAuth App**

### 2.2 Configure OAuth App

Fill in the form:

| Field | Value |
|-------|-------|
| **Application name** | `AI Impact Analytics (Dev)` |
| **Homepage URL** | `https://dev.ianchuk.com` |
| **Authorization callback URL** | `https://dev.ianchuk.com/app/integrations/github/callback/` |

### 2.3 Get Credentials

After creating the app:
1. Copy the **Client ID**
2. Click **Generate a new client secret**
3. Copy the **Client Secret** immediately (shown only once)

### 2.4 Update .env

```bash
GITHUB_CLIENT_ID="your_client_id_here"
GITHUB_SECRET_ID="your_client_secret_here"
```

Restart Django after updating `.env`:
```bash
pkill -f runserver && make dev
```

### 2.5 Verify GitHub Setup

1. **Test OAuth flow initiates correctly:**
   - Log in to the app at `https://dev.ianchuk.com`
   - Go to **Integrations** page
   - Click **Connect GitHub**
   - You should be redirected to GitHub's authorization page
   - Authorize the app
   - You should be redirected back to the app with a success message

2. **Verify in Django logs:**
   ```
   HTTP GET /app/integrations/github/callback/?code=... 302
   ```

3. **Check database:**
   ```bash
   make dbshell
   SELECT id, organization_slug, created_at FROM integrations_githubintegration;
   ```

### 2.6 GitHub Webhook URL

For GitHub webhooks (PR events), the app uses:
```
https://dev.ianchuk.com/webhooks/github/
```

This is configured automatically when you track repositories in the app.

---

## Phase 2.5: GitHub Copilot Testing

GitHub Copilot integration requires an organization with **5+ active Copilot licenses** to return metrics data.

### Prerequisites for Copilot Testing

- GitHub integration already connected (Phase 2)
- Organization has GitHub Copilot Business or Enterprise
- At least 5 users with active Copilot licenses
- Users have IDE telemetry enabled

**Note:** If your org has <5 Copilot licenses, the API returns 403 and the app shows "Copilot metrics unavailable".

### 2.5.1 Verify OAuth Scope

The GitHub OAuth App should request `manage_billing:copilot` scope. This is configured in `apps/integrations/services/github_oauth.py`:

```python
GITHUB_OAUTH_SCOPES = " ".join([
    "read:org",
    "repo",
    "read:user",
    "manage_billing:copilot",  # Required for Copilot metrics
])
```

If you connected GitHub before this scope was added, disconnect and reconnect to get the new permissions.

### 2.5.2 Test Copilot Availability Check

```bash
# Via Django shell
make shell

from apps.integrations.models import GitHubIntegration
from apps.integrations.services.copilot_metrics import check_copilot_availability

gh = GitHubIntegration.objects.first()
available = check_copilot_availability(gh.access_token, gh.organization_slug)
print(f"Copilot available: {available}")
```

### 2.5.3 Test Metrics Fetch

```bash
# Via Django shell
make shell

from apps.integrations.models import GitHubIntegration
from apps.integrations.services.copilot_metrics import fetch_copilot_metrics, parse_metrics_response

gh = GitHubIntegration.objects.first()
try:
    raw_data = fetch_copilot_metrics(gh.access_token, gh.organization_slug)
    print(f"Days of data: {len(raw_data)}")
    parsed = parse_metrics_response(raw_data)
    for day in parsed[:3]:
        print(f"{day['date']}: {day['code_completions_accepted']}/{day['code_completions_total']} accepted")
except Exception as e:
    print(f"Error: {e}")
```

### 2.5.4 Test Seat Utilization (Future)

Once seat utilization is implemented:

```bash
# Via Django shell
make shell

from apps.integrations.models import GitHubIntegration
from apps.integrations.services.copilot_metrics import fetch_copilot_seats, get_seat_utilization

gh = GitHubIntegration.objects.first()
seats = fetch_copilot_seats(gh.access_token, gh.organization_slug)
utilization = get_seat_utilization(seats)
print(f"Utilization: {utilization['utilization_rate']}%")
print(f"Active: {utilization['active_seats']}/{utilization['total_seats']}")
```

### 2.5.5 Test Sync Task

```bash
# Via Django shell
make shell

from apps.integrations.tasks import sync_copilot_metrics_task
from apps.teams.models import Team

team = Team.objects.first()
result = sync_copilot_metrics_task(team.id)
print(f"Sync result: {result}")
```

### 2.5.6 Verify Data in Database

```sql
-- Via psql
make dbshell

SELECT date, source, suggestions_shown, suggestions_accepted, acceptance_rate
FROM metrics_aiusagedaily
WHERE source = 'copilot'
ORDER BY date DESC
LIMIT 10;
```

### Copilot Troubleshooting

**Problem:** "Copilot metrics unavailable (403)"
- Organization needs 5+ active Copilot licenses
- Check the organization's Copilot settings on GitHub
- Verify the OAuth token has `manage_billing:copilot` scope

**Problem:** Empty metrics response
- Copilot metrics are processed daily, may take 24h to appear
- Users need IDE telemetry enabled in their Copilot settings
- Check if any users have been active recently

**Problem:** "CopilotMetricsError: Failed to fetch"
- Check network connectivity to GitHub API
- Verify access token hasn't expired
- Check GitHub API status page

---

## Phase 3: Jira App Setup

You'll create an Atlassian OAuth 2.0 app for Jira integration.

### 3.1 Create Atlassian Developer Account

1. Go to https://developer.atlassian.com/console/myapps/
2. Sign in with your Atlassian account (create one if needed)

### 3.2 Create OAuth 2.0 App

1. Click **Create** -> **OAuth 2.0 integration**
2. Enter app name: `AI Impact Analytics (Dev)`
3. Check **I agree to the Terms**
4. Click **Create**

### 3.3 Configure Permissions

1. In your new app, go to **Permissions**
2. Click **Add** next to **Jira API**
3. Click **Configure** next to Jira API
4. Add these scopes:
   - `read:jira-work` - Read project, issue, and sprint data
   - `read:jira-user` - Read user information
5. Click **Save**

### 3.4 Configure Authorization

1. Go to **Authorization** in the left sidebar
2. Click **Add** next to **OAuth 2.0 (3LO)**
3. Set the **Callback URL**:
   ```
   https://dev.ianchuk.com/app/integrations/jira/callback/
   ```
4. Click **Save changes**

### 3.5 Get Credentials

1. Go to **Settings** in the left sidebar
2. Copy the **Client ID**
3. Copy the **Secret** (click reveal if needed)

### 3.6 Update .env

```bash
JIRA_CLIENT_ID="your_client_id_here"
JIRA_CLIENT_SECRET="your_client_secret_here"
```

Restart Django after updating `.env`:
```bash
pkill -f runserver && make dev
```

### 3.7 Verify Jira Setup

1. **Test OAuth flow initiates correctly:**
   - Log in to the app at `https://dev.ianchuk.com`
   - Go to **Integrations** page
   - Click **Connect Jira**
   - You should be redirected to Atlassian's authorization page
   - Select your Jira site and authorize
   - You should be redirected back to the app with a success message

2. **Verify in Django logs:**
   ```
   HTTP GET /app/integrations/jira/callback/?code=... 302
   ```

3. **Check database:**
   ```bash
   make dbshell
   SELECT id, site_name, cloud_id, created_at FROM integrations_jiraintegration;
   ```

4. **Test API access:**
   - Go to Jira Projects page in the app
   - You should see a list of projects from your Jira site

### 3.8 Create Test Jira Site (if needed)

If you don't have a Jira Cloud site:
1. Go to https://www.atlassian.com/software/jira/free
2. Click **Get it free**
3. Create a new site (e.g., `yourname-test.atlassian.net`)
4. Create a test project

---

## Phase 4: Slack App Setup

You'll create a Slack App with Bot capabilities.

### 4.1 Create Slack App

1. Go to https://api.slack.com/apps
2. Click **Create New App**
3. Choose **From scratch**
4. Enter:
   - **App Name:** `AI Impact Analytics (Dev)`
   - **Workspace:** Select your test workspace
5. Click **Create App**

### 4.2 Configure OAuth & Permissions

1. In the left sidebar, click **OAuth & Permissions**
2. Scroll to **Redirect URLs**
3. Click **Add New Redirect URL**
4. Add:
   ```
   https://dev.ianchuk.com/app/integrations/slack/callback/
   ```
5. Click **Save URLs**

### 4.3 Add Bot Scopes

Scroll down to **Scopes** -> **Bot Token Scopes** and add:

| Scope | Purpose |
|-------|---------|
| `chat:write` | Send messages and surveys |
| `users:read` | Read workspace users for matching |
| `users:read.email` | Read user emails for matching |

### 4.4 Configure Interactivity

For survey button clicks to work:

1. In left sidebar, click **Interactivity & Shortcuts**
2. Toggle **Interactivity** to **On**
3. Set **Request URL**:
   ```
   https://dev.ianchuk.com/integrations/webhooks/slack/interactions/
   ```
4. Click **Save Changes**

### 4.5 Install App to Workspace

1. Go back to **OAuth & Permissions**
2. Click **Install to Workspace**
3. Review permissions and click **Allow**

### 4.6 Get Credentials

From the **Basic Information** page:
1. Scroll to **App Credentials**
2. Copy **Client ID**
3. Copy **Client Secret**
4. Copy **Signing Secret**

### 4.7 Update .env

```bash
SLACK_CLIENT_ID="your_client_id_here"
SLACK_CLIENT_SECRET="your_client_secret_here"
SLACK_SIGNING_SECRET="your_signing_secret_here"
```

Restart Django after updating `.env`:
```bash
pkill -f runserver && make dev
```

### 4.8 Verify Slack Setup

1. **Test OAuth flow initiates correctly:**
   - Log in to the app at `https://dev.ianchuk.com`
   - Go to **Integrations** page
   - Click **Connect Slack**
   - You should be redirected to Slack's authorization page
   - Select your workspace and authorize
   - You should be redirected back to the app with a success message

2. **Verify in Django logs:**
   ```
   HTTP GET /app/integrations/slack/callback/?code=... 302
   ```

3. **Check database:**
   ```bash
   make dbshell
   SELECT id, workspace_name, team_id, created_at FROM integrations_slackintegration;
   ```

4. **Test bot token works:**
   - Go to Slack Settings page in the app
   - You should be able to configure survey settings
   - The workspace name should be displayed

---

## Phase 5: Testing Checklist

After setting up all integrations, test each flow.

### Pre-Test Setup

```bash
# 1. Ensure your tunnel is running (Cloudflare Tunnel example)
cloudflared tunnel run tformance-dev

# 2. Ensure static assets are built
npm run build

# 3. Restart Django with updated .env (Vite dev mode disabled)
DJANGO_VITE_DEV_MODE=False make dev

# 4. Verify the app is accessible
curl -s -o /dev/null -w "%{http_code}" https://dev.ianchuk.com/health/
# Expected: 200
```

### GitHub Integration Tests

- [ ] **OAuth Flow**
  1. Go to Integrations page
  2. Click "Connect GitHub"
  3. Authorize the app on GitHub
  4. Verify redirect back with success message

- [ ] **Organization Selection** (if multiple orgs)
  1. After OAuth, select your test organization
  2. Verify organization is saved

- [ ] **Member Sync**
  1. Go to GitHub Members page
  2. Click "Sync Members"
  3. Verify org members are listed

- [ ] **Repository Tracking**
  1. Go to GitHub Repos page
  2. Toggle a repo to track it
  3. Verify webhook is created (check repo Settings -> Webhooks)

- [ ] **Webhook Reception**
  1. Create or merge a PR in tracked repo
  2. Check Django logs for webhook received
  3. Verify PR data appears in database

### GitHub Copilot Tests (requires 5+ Copilot licenses)

- [ ] **Copilot Availability**
  1. Ensure GitHub is connected
  2. Run availability check in Django shell
  3. Verify returns True/False appropriately

- [ ] **Metrics Fetch** (if available)
  1. Run metrics fetch in Django shell
  2. Verify daily metrics are returned
  3. Check acceptance rates are calculated

- [ ] **Sync Task**
  1. Run `sync_copilot_metrics_task(team_id)` manually
  2. Verify AIUsageDaily records created
  3. Check `source='copilot'` in database

- [ ] **Dashboard Display** (after frontend implementation)
  1. Go to CTO Overview dashboard
  2. Verify Copilot metrics card displays
  3. Verify acceptance rate chart renders
  4. Verify per-member table shows data

### Jira Integration Tests

- [ ] **OAuth Flow**
  1. Go to Integrations page
  2. Click "Connect Jira"
  3. Authorize on Atlassian
  4. Verify redirect back with success

- [ ] **Site Selection** (if multiple sites)
  1. Select your test Jira site
  2. Verify site is saved

- [ ] **Project Listing**
  1. Go to Jira Projects page
  2. Verify projects from your site are listed

- [ ] **Project Tracking**
  1. Toggle a project to track it
  2. Verify it's marked as tracked

### Slack Integration Tests

- [ ] **OAuth Flow**
  1. Go to Integrations page
  2. Click "Connect Slack"
  3. Authorize the app
  4. Verify redirect back with success

- [ ] **Bot Token Verification**
  1. Check that bot token was saved (admin panel)
  2. Verify team_name and team_id are populated

- [ ] **Survey Settings**
  1. Go to Slack Settings page
  2. Configure survey channel and timing
  3. Save settings

- [ ] **Survey Button Interaction**
  1. Trigger a test survey (merge a PR with tracked repo)
  2. Click a button in the Slack survey
  3. Verify interaction is received (check Django logs)
  4. Verify survey response is saved

### End-to-End Flow Test

- [ ] **Full PR Survey Flow**
  1. Ensure GitHub and Slack are connected
  2. Create a PR in tracked repo
  3. Get it reviewed and merge
  4. Verify author receives Slack survey
  5. Verify reviewer receives Slack survey
  6. Complete both surveys
  7. Verify "reveal" message is sent

---

## Troubleshooting

### Cloudflare Tunnel Issues

**Problem:** 503 "Service Unavailable"
- Check Django is running on port 8000: `curl http://localhost:8000/`
- Check tunnel config has ingress rules:
  ```bash
  cat ~/.cloudflared/config.yml
  # Should have: service: http://localhost:8000
  ```
- If no config, run with URL flag: `cloudflared tunnel run --url http://localhost:8000 tformance-dev`

**Problem:** "No ingress rules defined"
- Create config file at `~/.cloudflared/config.yml`:
  ```yaml
  tunnel: tformance-dev
  credentials-file: /path/to/.cloudflared/TUNNEL_ID.json

  ingress:
    - hostname: dev.ianchuk.com
      service: http://localhost:8000
    - service: http_status:404
  ```

### Vite / CORS Issues

**Problem:** CORS errors in browser console for `/static/` files
- Set `DJANGO_VITE_DEV_MODE=False` in `.env`
- Run `npm run build` to build static assets
- Restart Django

**Problem:** Styles/JS not loading through tunnel
- Ensure `npm run build` was run after any frontend changes
- Check `static/.vite/manifest.json` exists

### GitHub OAuth Issues

**Problem:** "Redirect URI mismatch"
- Ensure callback URL exactly matches what's in GitHub OAuth App settings
- URL should be `https://dev.ianchuk.com/app/integrations/github/callback/`
- Ensure using HTTPS

**Problem:** "Bad credentials" on API calls
- Token may have expired
- Disconnect and reconnect GitHub integration

**Problem:** Webhook not received
- Check webhook is created in repo Settings -> Webhooks
- Check "Recent Deliveries" for errors
- Verify tunnel is running and URL is correct

### Jira OAuth Issues

**Problem:** "Invalid redirect_uri"
- Callback URL must exactly match Atlassian app settings
- URL should be `/app/integrations/jira/callback/`

**Problem:** "Access denied"
- Ensure required scopes are configured in Atlassian app
- User may not have access to requested resources

**Problem:** "No accessible resources"
- User hasn't granted access to any Jira sites
- Add user to a Jira site and try again

### Slack OAuth Issues

**Problem:** "Invalid redirect_uri"
- Callback URL must be in Slack app's Redirect URLs list
- URL must use HTTPS

**Problem:** "Missing scope"
- Add required scopes in OAuth & Permissions
- Reinstall app to workspace after adding scopes

**Problem:** Button clicks not working
- Verify Interactivity is enabled
- Check Request URL is correct
- Check Django logs for signature verification errors

**Problem:** "Invalid signature" on interactions
- `SLACK_SIGNING_SECRET` may be wrong
- Re-copy from Slack app Basic Information page

### General Debugging

```bash
# Watch Django logs
make dev

# Check database for saved data
make dbshell
SELECT * FROM integrations_githubintegration;
SELECT * FROM integrations_slackintegration;
SELECT * FROM integrations_jiraintegration;

# Check Celery task queue (if using)
celery -A tformance inspect active
```

---

## Quick Reference: URLs Summary

Using `dev.ianchuk.com` as the example domain:

| Service | URL Type | Full URL |
|---------|----------|----------|
| GitHub | OAuth Callback | `https://dev.ianchuk.com/app/integrations/github/callback/` |
| GitHub | Webhook | `https://dev.ianchuk.com/webhooks/github/` |
| Jira | OAuth Callback | `https://dev.ianchuk.com/app/integrations/jira/callback/` |
| Slack | OAuth Callback | `https://dev.ianchuk.com/app/integrations/slack/callback/` |
| Slack | Interactions | `https://dev.ianchuk.com/integrations/webhooks/slack/interactions/` |

---

## Quick Reference: Environment Variables

```bash
# Tunnel domain (example with dev.ianchuk.com)
ALLOWED_HOSTS=localhost,127.0.0.1,dev.ianchuk.com
CSRF_TRUSTED_ORIGINS=https://dev.ianchuk.com

# Trust proxy headers (required for OAuth redirect URLs to use https://)
USE_X_FORWARDED_HOST=True

# Disable Vite dev server for tunnel (avoids CORS errors)
DJANGO_VITE_DEV_MODE=False

# GitHub OAuth App
GITHUB_CLIENT_ID="..."
GITHUB_SECRET_ID="..."

# Jira OAuth App (Atlassian)
JIRA_CLIENT_ID="..."
JIRA_CLIENT_SECRET="..."

# Slack App
SLACK_CLIENT_ID="..."
SLACK_CLIENT_SECRET="..."
SLACK_SIGNING_SECRET="..."
```

---

## Next Steps After Testing

Once integrations are verified:

1. **Document any issues** found during testing
2. **Create seed data** for demo purposes
3. **Test the dashboard** with real synced data
4. **Verify survey flow** end-to-end
5. **Test Celery scheduled tasks** for daily sync
