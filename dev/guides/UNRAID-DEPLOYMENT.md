# Unraid Docker Deployment Guide

> Deploy Tformance to Unraid with Cloudflare Tunnel for public access at `dev2.ianchuk.com`

## Overview

This guide deploys a **staging instance** on Unraid using:
- **Docker Compose** via Unraid's Docker Compose Manager plugin
- **Cloudflare Tunnel** for secure public access (no port forwarding)
- **Watchtower** for automatic container updates
- **Docker Hub** for Docker images

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            UNRAID SERVER                                 │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    CLOUDFLARE TUNNEL                                │ │
│  │                    (cloudflared)                                    │ │
│  │                         ↓                                           │ │
│  │            dev2.ianchuk.com → localhost:8000                        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                              ↓                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    TFORMANCE STACK                                  │ │
│  │                                                                      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                          │ │
│  │  │   web    │  │  worker  │  │   beat   │                          │ │
│  │  │ :8000    │  │ (celery) │  │ (sched)  │                          │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘                          │ │
│  │       │             │             │                                  │ │
│  │       └─────────────┼─────────────┘                                  │ │
│  │                     ↓                                                │ │
│  │  ┌─────────────────────────────────────────────────────────┐        │ │
│  │  │  ┌─────────────────┐    ┌─────────────────┐             │        │ │
│  │  │  │   PostgreSQL    │    │     Redis       │             │        │ │
│  │  │  │   (db)          │    │                 │             │        │ │
│  │  │  └─────────────────┘    └─────────────────┘             │        │ │
│  │  └─────────────────────────────────────────────────────────┘        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    WATCHTOWER                                       │ │
│  │            (auto-updates tformance containers)                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- [x] Unraid server with Docker installed
- [x] Docker Compose Manager plugin installed
- [x] Existing Cloudflare Tunnel (cloudflared) container
- [x] Existing Watchtower container
- [x] Domain `dev2.ianchuk.com` managed by Cloudflare

---

## Step 1: Docker Hub Setup (Private Image)

### 1.1 Create Docker Hub Access Token

1. Go to: https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Name: `tformance-unraid`
4. Permissions: **Read & Write**
5. Save the token securely

### 1.2 GitHub Secrets (For CI/CD Push)

Add these secrets to your GitHub repo:
1. Go to: https://github.com/ayanch/tformance/settings/secrets/actions
2. Add:
   - `DOCKERHUB_USERNAME`: `ayanchuk`
   - `DOCKERHUB_TOKEN`: Access token from step 1.1

### 1.3 Authenticate Docker on Unraid

SSH into Unraid and login to Docker Hub:

```bash
docker login -u ayanchuk
# Enter your access token when prompted
```

This creates `~/.docker/config.json` with credentials.

### 1.4 Verify Image Access

```bash
docker pull ayanchuk/tformance:latest
```

If the image doesn't exist yet, trigger the first build:
1. Go to: https://github.com/ayanch/tformance/actions/workflows/docker-build.yml
2. Click "Run workflow"

### 1.5 Make Repository Private

1. Go to: https://hub.docker.com/repository/docker/ayanchuk/tformance/settings
2. Set visibility to **Private**

---

## Step 2: Create Directory Structure

```bash
# Create appdata directory for tformance
mkdir -p /mnt/user/appdata/tformance

# Copy the compose file
cd /mnt/user/appdata/tformance
```

---

## Step 3: Create Environment File

Create `/mnt/user/appdata/tformance/.env`:

```bash
# Generate required keys first
python3 -c "from django.core.management.utils import get_random_secret_key; print('SECRET_KEY=' + get_random_secret_key())"
python3 -c "from cryptography.fernet import Fernet; print('INTEGRATION_ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Then create the `.env` file with all required values:

```env
# =============================================================================
# DOCKER
# =============================================================================
IMAGE_TAG=latest
WEB_PORT=8000

# =============================================================================
# REQUIRED: Django Core
# =============================================================================
SECRET_KEY=<generated-secret-key>
ALLOWED_HOSTS=dev2.ianchuk.com,localhost
INTEGRATION_ENCRYPTION_KEY=<generated-fernet-key>

# =============================================================================
# REQUIRED: Database
# =============================================================================
POSTGRES_DB=tformance
POSTGRES_USER=tformance
POSTGRES_PASSWORD=<strong-password-here>

# =============================================================================
# OAUTH: GitHub (create app at github.com/settings/developers)
# Homepage: https://dev2.ianchuk.com
# Callback: https://dev2.ianchuk.com/accounts/github/login/callback/
# =============================================================================
GITHUB_CLIENT_ID=<your-client-id>
GITHUB_SECRET_ID=<your-client-secret>

# =============================================================================
# Optional integrations (add as needed)
# =============================================================================
# JIRA_CLIENT_ID=
# JIRA_CLIENT_SECRET=
# SLACK_CLIENT_ID=
# SLACK_CLIENT_SECRET=
# SLACK_SIGNING_SECRET=
# GROQ_API_KEY=
# RESEND_API_KEY=
# POSTHOG_API_KEY=
```

---

## Step 4: Download Docker Compose File

```bash
cd /mnt/user/appdata/tformance

# Download from repository
curl -O https://raw.githubusercontent.com/ayanch/tformance/main/docker-compose.unraid.yml

# Or copy manually from the repo
```

---

## Step 5: Configure Cloudflare Tunnel

### Option A: Add to Existing Tunnel Config

If you have an existing `cloudflared` container, add a new ingress rule.

Edit your tunnel config (usually at `/mnt/user/appdata/cloudflared/config.yml`):

```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/<your-tunnel-id>.json

ingress:
  # Existing rules...

  # ADD THIS: Tformance staging
  - hostname: dev2.ianchuk.com
    service: http://tformance-web:8000
    originRequest:
      noTLSVerify: true

  # Catch-all (must be last)
  - service: http_status:404
```

**Important:** The `tformance-web` hostname works if cloudflared is on the same Docker network.

### Option B: Point to Host IP

If your tunnel isn't on the same Docker network:

```yaml
ingress:
  - hostname: dev2.ianchuk.com
    service: http://192.168.1.X:8000  # Your Unraid IP
    originRequest:
      noTLSVerify: true
```

### Option C: Configure via Cloudflare Dashboard

1. Go to: https://one.dash.cloudflare.com/ → Access → Tunnels
2. Select your tunnel → Configure
3. Add a Public Hostname:
   - **Subdomain:** `dev2`
   - **Domain:** `ianchuk.com`
   - **Type:** HTTP
   - **URL:** `192.168.1.X:8000` (or `tformance-web:8000` if same network)

### Restart Tunnel

```bash
docker restart cloudflared
```

---

## Step 6: Deploy with Docker Compose Manager

### Via Unraid UI

1. Go to **Docker** tab
2. Click **Compose** (requires Docker Compose Manager plugin)
3. Click **Add New Stack**
4. Name: `tformance`
5. Compose File: `/mnt/user/appdata/tformance/docker-compose.unraid.yml`
6. Click **Apply**

### Via Terminal

```bash
cd /mnt/user/appdata/tformance
docker compose -f docker-compose.unraid.yml up -d
```

---

## Step 7: Verify Deployment

### Check Container Status

```bash
docker ps | grep tformance
```

Expected output:
```
tformance-web      ... Up (healthy)
tformance-worker   ... Up
tformance-beat     ... Up
tformance-db       ... Up (healthy)
tformance-redis    ... Up (healthy)
```

### Check Logs

```bash
# Web server logs
docker logs -f tformance-web

# All logs
docker compose -f docker-compose.unraid.yml logs -f
```

### Verify Migration Ran

```bash
docker logs tformance-web 2>&1 | grep -i migrat
```

### Test Public Access

```bash
curl -I https://dev2.ianchuk.com
# Should return HTTP 200
```

---

## Step 8: Configure Watchtower (Auto-Updates)

Your existing Watchtower container will automatically update tformance containers because they have the label:

```yaml
labels:
  - "com.centurylinklabs.watchtower.enable=true"
```

### Verify Watchtower Config

Ensure your Watchtower is configured to:
- Monitor labeled containers: `--label-enable` flag
- Access Docker Hub credentials: mount `config.json`

Example Watchtower compose/command:

```yaml
watchtower:
  image: containrrr/watchtower
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
    - /root/.docker/config.json:/config.json:ro  # Docker Hub auth for private images
  environment:
    - WATCHTOWER_CLEANUP=true
    - WATCHTOWER_LABEL_ENABLE=true
    - WATCHTOWER_POLL_INTERVAL=300  # 5 minutes
  command: --label-enable
```

> **Important:** The `config.json` mount is required for Watchtower to pull private images from Docker Hub.

### How Auto-Updates Work

1. You push code to `main` branch
2. GitHub Actions builds new Docker image → pushes to Docker Hub as `latest`
3. Watchtower polls Docker Hub every 5 minutes
4. Watchtower pulls new image and recreates containers
5. Migrations run automatically on container start

---

## Step 9: Create Initial Admin User

```bash
docker exec -it tformance-web python manage.py createsuperuser
```

---

## Common Operations

### View Logs

```bash
# All services
docker compose -f docker-compose.unraid.yml logs -f

# Specific service
docker logs -f tformance-web
docker logs -f tformance-worker
docker logs -f tformance-beat
```

### Run Django Commands

```bash
# Django shell
docker exec -it tformance-web python manage.py shell

# Run specific command
docker exec -it tformance-web python manage.py <command>
```

### Database Access

```bash
# Django dbshell
docker exec -it tformance-web python manage.py dbshell

# Direct PostgreSQL access
docker exec -it tformance-db psql -U tformance -d tformance
```

### Manual Update

```bash
cd /mnt/user/appdata/tformance
docker compose -f docker-compose.unraid.yml pull
docker compose -f docker-compose.unraid.yml up -d
```

### Stop Stack

```bash
docker compose -f docker-compose.unraid.yml down
```

### Full Reset (including data)

```bash
docker compose -f docker-compose.unraid.yml down -v
docker compose -f docker-compose.unraid.yml up -d
```

---

## Backup

### Database Backup

```bash
# Create backup
docker exec tformance-db pg_dump -U tformance tformance > backup_$(date +%Y%m%d).sql

# Or directly to a file
docker exec tformance-db pg_dump -U tformance tformance | gzip > /mnt/user/backups/tformance_$(date +%Y%m%d).sql.gz
```

### Restore Database

```bash
# Stop web/worker first
docker compose -f docker-compose.unraid.yml stop web worker beat

# Restore
cat backup.sql | docker exec -i tformance-db psql -U tformance -d tformance

# Start services
docker compose -f docker-compose.unraid.yml start web worker beat
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs for errors
docker logs tformance-web

# Common issues:
# - Missing environment variables
# - Database not ready (check healthcheck)
# - Port already in use
```

### Database Connection Errors

```bash
# Verify database is healthy
docker exec tformance-db pg_isready -U tformance

# Check DATABASE_URL format
docker exec tformance-web printenv DATABASE_URL
```

### Cloudflare Tunnel Not Working

```bash
# Check tunnel logs
docker logs cloudflared

# Verify tunnel config
docker exec cloudflared cat /etc/cloudflared/config.yml

# Test internal connectivity
docker exec cloudflared wget -q -O- http://tformance-web:8000/health/
```

### Migrations Failed

```bash
# Run migrations manually
docker exec tformance-web python manage.py migrate --noinput

# Check for migration errors
docker exec tformance-web python manage.py showmigrations
```

### Image Pull Failed

```bash
# Verify Docker Hub login
docker login -u ayanchuk

# Try pulling again
docker pull ayanchuk/tformance:latest

# Check credentials file exists
cat ~/.docker/config.json | grep "index.docker.io"

# Check Docker Hub for available tags (requires login):
# https://hub.docker.com/r/ayanchuk/tformance/tags
```

---

## Cost Summary

| Component | Cost |
|-----------|------|
| Unraid Server | (existing hardware) |
| Cloudflare Tunnel | **Free** |
| Docker Hub | **Free** (1 private repo) |
| Domain | (existing) |
| **Total** | **$0/mo** |

---

## Comparison: Unraid Staging vs Heroku Staging

| Aspect | Unraid (this setup) | Heroku |
|--------|---------------------|--------|
| **Cost** | $0/mo | $22/mo |
| **Purpose** | Always-on staging for quick testing | Official staging before production |
| **Auto-deploy** | Yes (Watchtower) | Yes (git push) |
| **Reliability** | Depends on home network | Enterprise-grade |
| **SSL** | Cloudflare Tunnel | Heroku managed |
| **Database backups** | Manual | Automatic |
| **Scaling** | Limited to server resources | Easy dyno scaling |

**Use Unraid for:** Quick testing, demos, personal use
**Use Heroku for:** Official staging, client demos, pre-production validation

---

## Files Reference

| File | Location |
|------|----------|
| Docker Compose | `docker-compose.unraid.yml` (repo root) |
| Environment Template | `.env.unraid.example` (repo root) |
| GitHub Action | `.github/workflows/docker-build.yml` |
| Production Dockerfile | `Dockerfile.web` |
| This Guide | `dev/guides/UNRAID-DEPLOYMENT.md` |
