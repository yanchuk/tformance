# Render Deployment Guide

## Quick Start

### 1. Push deployment files to GitHub

```bash
git add render.yaml build.sh build_celery.sh
git commit -m "Add Render deployment configuration"
git push
```

### 2. Create Blueprint in Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **Blueprint**
3. Connect your GitHub repository
4. Select the branch (usually `main`)
5. Click **Apply**

Render will automatically create:
- Web service (Django)
- Worker service (Celery)
- PostgreSQL database
- Redis instance

### 3. Set Environment Variables

After the blueprint creates your services, go to each service and set these variables:

#### Required (Web Service)

| Variable | Where to Get It |
|----------|-----------------|
| `ALLOWED_HOSTS` | Your Render URL, e.g., `tformance-web.onrender.com` |

#### Required for OAuth (Both Web & Worker)

| Variable | Where to Get It |
|----------|-----------------|
| `GITHUB_CLIENT_ID` | [GitHub OAuth App](https://github.com/settings/developers) |
| `GITHUB_CLIENT_SECRET` | Same GitHub OAuth App |

#### Optional

| Variable | Purpose |
|----------|---------|
| `SENTRY_DSN` | Error tracking |
| `STRIPE_*` | Payment processing |
| `MAILGUN_API_KEY` | Email sending |

### 4. Create Superuser

After first deployment, open a **Shell** in Render Dashboard:

```bash
python manage.py createsuperuser
```

### 5. Verify Deployment

1. Visit your URL: `https://tformance-web.onrender.com`
2. Check health: `https://tformance-web.onrender.com/health/`
3. Access admin: `https://tformance-web.onrender.com/admin/`

---

## Pricing Summary

| Service | Plan | Cost |
|---------|------|------|
| Web | Starter | $9/mo |
| Worker | Starter | $9/mo |
| PostgreSQL | Basic-256mb | $6/mo |
| Redis | Free | $0 |
| **Total** | | **$24/mo** |

### Free Tier Testing

To test with free tier (30-day DB limit, web sleeps):

1. Edit `render.yaml`:
   - Change web `plan: starter` → `plan: free`
   - Change database `plan: basic-256mb` → `plan: free`
   - Comment out the worker service (no free tier for workers)

---

## GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in:
   - **Application name**: `tformance`
   - **Homepage URL**: `https://tformance-web.onrender.com`
   - **Authorization callback URL**: `https://tformance-web.onrender.com/accounts/github/login/callback/`
4. Copy Client ID and Client Secret to Render environment variables

---

## Troubleshooting

### Build Fails

Check build logs in Render Dashboard. Common issues:
- Missing environment variables
- Database connection issues (check `DATABASE_URL`)

### Migrations Fail

Run manually via Render Shell:
```bash
python manage.py migrate
```

### Celery Not Running

1. Ensure worker service is deployed and running
2. Check `REDIS_URL` is set correctly
3. View worker logs in Dashboard

### Static Files Missing

Static files are built in Dockerfile. If issues:
```bash
python manage.py collectstatic --noinput
```

---

## Updating

Push to your deployment branch to trigger auto-deploy:
```bash
git push origin main
```

Or manually deploy from Render Dashboard.

---

## Scaling

When ready to scale:

1. **Web**: Increase plan (Standard = $25/mo, Pro = $85/mo)
2. **Database**: Upgrade to Pro for HA and PITR ($55+/mo)
3. **Redis**: Upgrade to Starter ($10/mo) for persistence
4. **Workers**: Add more instances or scale horizontally
