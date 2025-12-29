# Heroku Deployment Guide (Docker)

> Tformance uses Docker-based deployment on Heroku for full portability across platforms.

## Why Docker (Not Buildpacks)

| Aspect | Docker | Buildpacks |
|--------|--------|------------|
| **Portability** | Same image runs anywhere | Heroku-specific |
| **Migration** | Copy Dockerfile to any platform | Rewrite for each platform |
| **Reproducibility** | Deterministic builds | Depends on buildpack versions |
| **Customization** | Full control | Limited to buildpack options |

The same `Dockerfile.web` works on Heroku, Render, Fly.io, Railway, AWS ECS, and Kubernetes.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         HEROKU                               │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Web Dyno    │  │ Worker Dyno  │  │  Beat Dyno   │       │
│  │  (gunicorn)  │  │  (celery)    │  │  (scheduler) │       │
│  │  Basic $7/mo │  │  Basic $7/mo │  │  Basic $7/mo │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│          │                 │                 │               │
│          └────────────────┴────────────────┘               │
│                           │                                  │
│  ┌──────────────────────────────────────────────────┐       │
│  │              Heroku Add-ons                       │       │
│  │  ┌─────────────────┐  ┌─────────────────┐        │       │
│  │  │   PostgreSQL    │  │     Redis       │        │       │
│  │  │  Essential-0    │  │     Mini        │        │       │
│  │  │    $5/mo        │  │     $3/mo       │        │       │
│  │  └─────────────────┘  └─────────────────┘        │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Files

| File | Purpose |
|------|---------|
| `Dockerfile.web` | Multi-stage Docker build (Python deps → Node build → runtime) |
| `heroku.yml` | Heroku Docker configuration (dynos, addons, commands) |
| `tformance/settings_production.py` | Production Django settings |

---

## Environments

| Environment | App Name | Branch | Purpose |
|-------------|----------|--------|---------|
| **Staging** | `tformance-staging` | `main` | Testing before production |
| **Production** | `tformance` | `main` | Live application |

---

## Initial Setup (One-Time)

### 1. Install Heroku CLI

```bash
# macOS
brew tap heroku/brew && brew install heroku

# Verify
heroku --version
```

### 2. Login

```bash
heroku login
```

### 3. Create Staging App

```bash
# Create app
heroku create tformance-staging --region us

# Set container stack (required for Docker)
heroku stack:set container -a tformance-staging

# Add git remote
heroku git:remote -a tformance-staging -r staging
```

### 4. Create Production App

```bash
heroku create tformance --region us
heroku stack:set container -a tformance
heroku git:remote -a tformance -r production
```

---

## Add-ons Setup

The `heroku.yml` auto-provisions these, but you can also add manually:

### PostgreSQL

```bash
# Staging (Essential-0: $5/mo)
heroku addons:create heroku-postgresql:essential-0 -a tformance-staging

# Production (Essential-0 or higher)
heroku addons:create heroku-postgresql:essential-0 -a tformance
```

### Redis

```bash
# Staging (Mini: $3/mo, 25MB)
heroku addons:create heroku-redis:mini -a tformance-staging

# Production (Premium-0: $15/mo, 512MB - recommended)
heroku addons:create heroku-redis:premium-0 -a tformance
```

---

## Environment Variables

### Required Variables

```bash
# Set for staging (replace values)
APP=tformance-staging

# Django core
heroku config:set DJANGO_SETTINGS_MODULE=tformance.settings_production -a $APP
heroku config:set DEBUG=False -a $APP
heroku config:set ALLOWED_HOSTS=tformance-staging.herokuapp.com -a $APP

# Security keys (generate unique per environment)
heroku config:set SECRET_KEY="$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" -a $APP

heroku config:set INTEGRATION_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')" -a $APP
```

### OAuth Apps (Per Environment)

Each environment needs **separate OAuth apps** with environment-specific callback URLs.

#### GitHub OAuth

1. Go to: https://github.com/settings/developers
2. Create new OAuth App:
   - **Name:** `Tformance Staging` (or `Tformance` for prod)
   - **Homepage URL:** `https://tformance-staging.herokuapp.com`
   - **Callback URL:** `https://tformance-staging.herokuapp.com/accounts/github/login/callback/`

```bash
heroku config:set GITHUB_CLIENT_ID=xxx -a $APP
heroku config:set GITHUB_CLIENT_SECRET=xxx -a $APP
```

#### Jira OAuth

1. Go to: https://developer.atlassian.com/console/myapps/
2. Create new OAuth 2.0 app:
   - **Callback URL:** `https://tformance-staging.herokuapp.com/integrations/jira/callback/`

```bash
heroku config:set JIRA_CLIENT_ID=xxx -a $APP
heroku config:set JIRA_CLIENT_SECRET=xxx -a $APP
```

#### Slack App

1. Go to: https://api.slack.com/apps
2. Create new app:
   - **Redirect URL:** `https://tformance-staging.herokuapp.com/integrations/slack/oauth/callback/`

```bash
heroku config:set SLACK_CLIENT_ID=xxx -a $APP
heroku config:set SLACK_CLIENT_SECRET=xxx -a $APP
heroku config:set SLACK_SIGNING_SECRET=xxx -a $APP
```

### LLM (Groq)

```bash
heroku config:set GROQ_API_KEY=xxx -a $APP
```

### Verify All Variables

```bash
heroku config -a tformance-staging
```

---

## Deployment

### Deploy to Staging

```bash
git push staging main
```

### Deploy to Production

```bash
git push production main
```

### What Happens on Deploy

1. Heroku receives code + `Dockerfile.web`
2. Heroku builds Docker image (multi-stage)
3. Heroku runs release command: `python manage.py migrate --noinput`
4. Heroku starts dynos from the image

---

## Scaling Dynos

### Staging (Minimal)

```bash
heroku ps:scale web=1:basic worker=1:basic -a tformance-staging

# Optional: beat scheduler (adds $7/mo)
# heroku ps:scale beat=1:basic -a tformance-staging
```

### Production (Recommended)

```bash
heroku ps:scale web=1:basic worker=1:basic beat=1:basic -a tformance
```

### Check Dyno Status

```bash
heroku ps -a tformance-staging
```

---

## Common Operations

### View Logs

```bash
# Tail logs
heroku logs --tail -a tformance-staging

# Filter by dyno
heroku logs --tail --dyno web -a tformance-staging
heroku logs --tail --dyno worker -a tformance-staging
```

### Run One-Off Commands

```bash
# Django shell
heroku run python manage.py shell -a tformance-staging

# Database shell
heroku run python manage.py dbshell -a tformance-staging

# Run migrations manually
heroku run python manage.py migrate -a tformance-staging

# Create superuser
heroku run python manage.py createsuperuser -a tformance-staging
```

### Restart Dynos

```bash
heroku restart -a tformance-staging
```

### Database Operations

```bash
# Connect to database
heroku pg:psql -a tformance-staging

# Database info
heroku pg:info -a tformance-staging

# Create backup
heroku pg:backups:capture -a tformance-staging

# Download backup
heroku pg:backups:download -a tformance-staging

# Copy production DB to staging
heroku pg:copy tformance::DATABASE_URL DATABASE_URL -a tformance-staging
```

### Redis Operations

```bash
# Redis info
heroku redis:info -a tformance-staging

# Redis CLI
heroku redis:cli -a tformance-staging
```

---

## Cost Summary

### Staging Environment

| Component | Plan | Cost |
|-----------|------|------|
| Web Dyno | Basic | $7/mo |
| Worker Dyno | Basic | $7/mo |
| PostgreSQL | Essential-0 | $5/mo |
| Redis | Mini | $3/mo |
| **Total** | | **$22/mo** |

### Production Environment

| Component | Plan | Cost |
|-----------|------|------|
| Web Dyno | Basic | $7/mo |
| Worker Dyno | Basic | $7/mo |
| Beat Dyno | Basic | $7/mo |
| PostgreSQL | Essential-0 | $5/mo |
| Redis | Premium-0 | $15/mo |
| **Total** | | **$41/mo** |

---

## Troubleshooting

### Build Fails

```bash
# Check build logs
heroku builds -a tformance-staging
heroku builds:info <build-id> -a tformance-staging
```

### App Crashes on Start

```bash
# Check logs for errors
heroku logs --tail -a tformance-staging

# Common issues:
# - Missing environment variables
# - Database not ready
# - Redis connection failed
```

### Database Connection Issues

```bash
# Verify DATABASE_URL is set
heroku config:get DATABASE_URL -a tformance-staging

# Test connection
heroku pg:psql -a tformance-staging -c "SELECT 1;"
```

### Memory Issues

```bash
# Check memory usage
heroku logs --tail -a tformance-staging | grep "Memory"

# Upgrade dyno if needed
heroku ps:scale web=1:standard-1x -a tformance-staging
```

---

## Migration to Other Platforms

Since we use Docker, migration is straightforward:

| Platform | Steps |
|----------|-------|
| **Render** | Use existing `render.yaml` (already configured) |
| **Fly.io** | Run `fly launch`, it detects `Dockerfile.web` |
| **Railway** | Connect repo, Railway detects Dockerfile |
| **AWS ECS** | Use same `Dockerfile.web` + task definitions |

The `Dockerfile.web` is the portable artifact that works everywhere.

---

## Files Reference

### heroku.yml

```yaml
setup:
  addons:
    - plan: heroku-postgresql
      as: DATABASE
    - plan: heroku-redis
      as: REDIS
  config:
    DJANGO_SETTINGS_MODULE: tformance.settings_production
    DEBUG: false
build:
  docker:
    django: Dockerfile.web
release:
  image: django
  command:
    - python manage.py migrate --noinput
run:
  web:
    command:
      - gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 tformance.asgi:application -k uvicorn.workers.UvicornWorker
    image: django
  worker:
    command:
      - celery -A tformance worker -l INFO --pool threads --concurrency 20
    image: django
  beat:
    command:
      - celery -A tformance beat -l INFO
    image: django
```

### Quick Commands Cheatsheet

```bash
# Deploy
git push staging main
git push production main

# Logs
heroku logs -t -a tformance-staging

# Shell
heroku run python manage.py shell -a tformance-staging

# Scale
heroku ps:scale web=1:basic worker=1:basic -a tformance-staging

# Config
heroku config -a tformance-staging
heroku config:set KEY=value -a tformance-staging

# DB
heroku pg:psql -a tformance-staging
heroku pg:backups:capture -a tformance-staging

# Restart
heroku restart -a tformance-staging
```
