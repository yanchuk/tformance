# Staging Deployment Plan: Unraid + Docker Hub + Watchtower

## Overview

Deploy tformance to your Unraid home lab as a staging environment with automated deployments.

**Stack:**
- Docker Hub (free registry, unlimited pulls)
- GitHub Actions (build & push image)
- Watchtower (already on Unraid, auto-pulls new images)
- Cloudflare Tunnel (already configured, exposes to internet)

---

## Code Changes Required

### New Files to Create (4 files)

| File | Purpose |
|------|---------|
| `.github/workflows/staging-deploy.yml` | GitHub Actions workflow |
| `docker-compose.staging.yml` | Staging docker compose |
| `.env.staging.example` | Environment template |
| `Makefile` additions | Convenience commands |

### Files Modified (1 file)

| File | Change |
|------|--------|
| `.gitignore` | Add `.env.staging` |

### No Changes To

- `Dockerfile.web` - Already production-ready
- `build.sh` - Not used (migrations in compose command)
- `render.yaml` - Production config unchanged
- Any application code

---

## New Files Content

### 1. `.github/workflows/staging-deploy.yml`

```yaml
name: Deploy to Staging

on:
  push:
    branches: [main]
  workflow_dispatch:  # Manual trigger

env:
  REGISTRY: docker.io
  IMAGE_NAME: ${{ secrets.DOCKERHUB_USERNAME }}/tformance

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile.web
          push: true
          tags: |
            ${{ env.IMAGE_NAME }}:staging
            ${{ env.IMAGE_NAME }}:staging-${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### 2. `docker-compose.staging.yml`

```yaml
services:
  db:
    image: postgres:17
    restart: unless-stopped
    volumes:
      - postgres_staging:/var/lib/postgresql/data/
    environment:
      POSTGRES_DB: tformance_staging
      POSTGRES_USER: tformance
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    healthcheck:
      test: pg_isready -d tformance_staging -U tformance
      interval: 10s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_staging:/data
    healthcheck:
      test: redis-cli ping
      interval: 10s
      retries: 5

  web:
    image: ${DOCKERHUB_USERNAME}/tformance:staging
    restart: unless-stopped
    ports:
      - "8080:8000"
    environment:
      DATABASE_URL: postgres://tformance:${POSTGRES_PASSWORD}@db:5432/tformance_staging
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
      ALLOWED_HOSTS: ${ALLOWED_HOSTS}
      DJANGO_SETTINGS_MODULE: tformance.settings_production
      PORT: "8000"
      # OAuth
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
      # Optional integrations
      JIRA_CLIENT_ID: ${JIRA_CLIENT_ID:-}
      JIRA_CLIENT_SECRET: ${JIRA_CLIENT_SECRET:-}
      SLACK_CLIENT_ID: ${SLACK_CLIENT_ID:-}
      SLACK_CLIENT_SECRET: ${SLACK_CLIENT_SECRET:-}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    command: >
      sh -c "python manage.py migrate --noinput &&
             python manage.py createcachetable || true &&
             gunicorn --bind 0.0.0.0:8000 --workers 2 --threads 4 --timeout 120 tformance.asgi:application -k uvicorn.workers.UvicornWorker"

  celery:
    image: ${DOCKERHUB_USERNAME}/tformance:staging
    restart: unless-stopped
    environment:
      DATABASE_URL: postgres://tformance:${POSTGRES_PASSWORD}@db:5432/tformance_staging
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: "False"
      DJANGO_SETTINGS_MODULE: tformance.settings_production
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    labels:
      - "com.centurylinklabs.watchtower.enable=true"
    command: celery -A tformance worker -l INFO --beat

volumes:
  postgres_staging:
  redis_staging:
```

### 3. `.env.staging.example`

```bash
# Docker Hub
DOCKERHUB_USERNAME=yourusername

# Database
POSTGRES_PASSWORD=change-me-to-secure-password

# Django
SECRET_KEY=change-me-generate-with-python
ALLOWED_HOSTS=staging.yourdomain.com,localhost

# GitHub OAuth (create separate staging app)
GITHUB_CLIENT_ID=your_staging_github_client_id
GITHUB_CLIENT_SECRET=your_staging_github_client_secret

# Optional: Jira OAuth
JIRA_CLIENT_ID=
JIRA_CLIENT_SECRET=

# Optional: Slack OAuth
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
```

### 4. Makefile additions

```makefile
# Staging deployment commands
staging-up:
	docker compose -f docker-compose.staging.yml --env-file .env.staging up -d

staging-down:
	docker compose -f docker-compose.staging.yml --env-file .env.staging down

staging-logs:
	docker compose -f docker-compose.staging.yml --env-file .env.staging logs -f

staging-shell:
	docker compose -f docker-compose.staging.yml --env-file .env.staging exec web python manage.py shell
```

---

## Setup Steps (One-Time)

### Step 1: Docker Hub Setup (5 min)

1. Create account at [hub.docker.com](https://hub.docker.com) (if you don't have one)
2. Create access token: Account Settings → Security → New Access Token
3. Save the token (you'll need it for GitHub secrets)

### Step 2: GitHub Secrets (5 min)

Go to your repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|-------------|-------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Access token from step 1 |

### Step 3: Create Staging OAuth Apps (15 min)

**GitHub OAuth App:**
1. GitHub → Settings → Developer settings → OAuth Apps → New
2. Application name: `tformance-staging`
3. Homepage URL: `https://staging.yourdomain.com`
4. Callback URL: `https://staging.yourdomain.com/accounts/github/login/callback/`
5. Save Client ID and Client Secret

**Jira/Slack** (optional): Same process, point to staging domain

### Step 4: Unraid Setup (10 min)

1. Copy files to Unraid:
   ```bash
   # On your local machine
   scp docker-compose.staging.yml .env.staging.example user@unraid:/path/to/tformance/
   ```

2. Create `.env.staging` from example:
   ```bash
   # On Unraid
   cd /path/to/tformance
   cp .env.staging.example .env.staging
   nano .env.staging  # Fill in your values
   ```

3. Generate Django secret key:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(50))"
   ```

4. Start the stack:
   ```bash
   docker compose -f docker-compose.staging.yml --env-file .env.staging up -d
   ```

### Step 5: Cloudflare Tunnel (5 min)

Add to your existing tunnel config:

```yaml
ingress:
  - hostname: staging.yourdomain.com
    service: http://localhost:8080
```

Or via Cloudflare Zero Trust dashboard: Add public hostname pointing to `http://localhost:8080`

### Step 6: Configure Watchtower (2 min)

Make sure your Watchtower is monitoring Docker Hub. If using label-based monitoring, the `docker-compose.staging.yml` already has the correct labels.

If Watchtower monitors all containers, you're already set.

---

## Deployment Flow

```
You push to main
       ↓
GitHub Actions builds image (~3 min)
       ↓
Pushes to Docker Hub (yourusername/tformance:staging)
       ↓
Watchtower polls every 5 min (configurable)
       ↓
Detects new image, pulls it
       ↓
Restarts web + celery containers
       ↓
Migrations run automatically on startup
       ↓
Staging is updated!
```

**Total time from push to live: ~5-8 minutes**

---

## Manual Deploy (if needed)

```bash
# On Unraid - force pull latest image
docker compose -f docker-compose.staging.yml --env-file .env.staging pull
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d
```

---

## Cost Summary

| Service | Cost |
|---------|------|
| Docker Hub | Free (1 private repo, unlimited pulls) |
| GitHub Actions | Free (2,000 min/month for private repos) |
| Watchtower | Free (already running) |
| Cloudflare Tunnel | Free |
| **Total** | **$0/month** |

---

## Production Parity

| Aspect | Staging (Unraid) | Production (render.com) |
|--------|------------------|------------------------|
| Docker image | Same `Dockerfile.web` | Same `Dockerfile.web` |
| Python deps | Identical | Identical |
| Database | Postgres 17 | Postgres (managed) |
| Redis | Redis 7 | Redis (managed) |
| Workers | Celery | Celery |
| Difference | Single server | Managed services, scaling |

---

## Rollback

If a bad deploy happens:

```bash
# On Unraid - rollback to previous image
docker compose -f docker-compose.staging.yml --env-file .env.staging down
docker pull yourusername/tformance:staging-<previous-sha>
# Edit docker-compose.staging.yml to use specific tag
docker compose -f docker-compose.staging.yml --env-file .env.staging up -d
```

---

## Summary of Code Changes

| Change Type | Count | Effort |
|-------------|-------|--------|
| New files | 4 | ~30 min to create |
| Modified files | 1 (.gitignore) | 1 line |
| Application code changes | 0 | None |
| Dockerfile changes | 0 | None |

**The application code remains unchanged.** Only DevOps/infrastructure files are added.
