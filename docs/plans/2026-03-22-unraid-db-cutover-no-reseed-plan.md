# Unraid DB Cutover Without Reseeding Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the existing Tformance stack and current local database to Unraid without reseeding or reprocessing the full public dataset.

**Architecture:** Use the local Postgres DB as the migration source, restore it into Unraid Postgres, bootstrap sync state from restored data, rebuild derived artifacts locally on Unraid, and let the first scheduled sync run in delta mode only.

**Tech Stack:** Docker Compose on Unraid, PostgreSQL, Redis, Django, Celery, Cloudflare Tunnel, existing public snapshot/OG commands, GitHub PAT token pool.

---

## Summary

This plan is intentionally **not** a reseed plan.

The external team must not:
- run a full GitHub reseed after restore
- force all repos into backfill
- rerun broad Groq processing
- rebuild public history from scratch

The correct sequence is:
1. Build and publish the Unraid image.
2. Provision the Unraid runtime with its own compose and env file.
3. Restore the current local DB into Unraid Postgres.
4. Run migrations.
5. Bootstrap sync state from the restored data.
6. Rebuild repo/org snapshots and OG images from restored rows.
7. Start workers and beat.
8. Let the first scheduled sync fetch deltas only.

Security prerequisite:
- Rotate any credentials that were shared outside your secret store before the rollout starts.
- `IMAGE_TAG=latest` is forbidden for the production cutover.
- `GITHUB_APP_ENABLED=True` with an empty `GITHUB_APP_PRIVATE_KEY` is forbidden.

---

## Target Runtime Topology

```text
                         +----------------------+
Public DNS / Tunnel ---->|  cloudflared / proxy |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         |        web           |
                         | Django + Gunicorn    |
                         +----+----------+------+
                              |          |
                              v          v
                     +-------------+   +-------------+
                     |   redis     |   |  postgres   |
                     +-------------+   +-------------+
                              ^
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
   +-------------+     +-------------+     +-------------+
   | worker-sync |     |worker-compute|    |  worker-llm |
   +-------------+     +-------------+     +-------------+
                              ^
                              |
                         +-------------+
                         |    beat     |
                         +-------------+
```

---

## Runtime Contract

**Repo-tracked files**
- `docker-compose.unraid.yml`
- `.env.unraid.example`
- `dev/guides/UNRAID-DEPLOYMENT.md`

**Runtime files on Unraid**
- `/mnt/user/appdata/tformance/docker-compose.yml`
- `/mnt/user/appdata/tformance/.env`

**Runtime directories on Unraid**
- `/mnt/user/appdata/tformance/postgres`
- `/mnt/user/appdata/tformance/redis`
- `/mnt/user/appdata/tformance/media`
- `/mnt/user/appdata/tformance/backups`

**Required runtime services**
- `db`
- `redis`
- `web`
- `worker-sync`
- `worker-compute`
- `worker-llm`
- `beat`

**Queue/concurrency decisions**
- `worker-sync`: concurrency `3`
- `worker-compute`: concurrency `4`
- `worker-llm`: concurrency `2`

**Image/update rules**
- Build from `Dockerfile.web`
- Publish immutable tags `sha-<gitsha>`
- Production Unraid must use `IMAGE_TAG=sha-<gitsha>`
- Do not use `latest` for production deploys
- Do not rely on Watchtower for the initial rollout

---

## Environment Contract

**Required env vars**
- `IMAGE_TAG`
- `SECRET_KEY`
- `ALLOWED_HOSTS`
- `CSRF_TRUSTED_ORIGINS`
- `SECURE_SSL_REDIRECT`
- `USE_HTTPS_IN_ABSOLUTE_URLS`
- `SITE_DOMAIN`
- `SITE_NAME`
- `INTEGRATION_ENCRYPTION_KEY`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `GITHUB_CLIENT_ID`
- `GITHUB_SECRET_ID`
- `GITHUB_APP_ENABLED`
- `GITHUB_APP_ID`
- `GITHUB_APP_NAME`
- `GITHUB_APP_PRIVATE_KEY`
- `GITHUB_APP_WEBHOOK_SECRET`
- `GROQ_API_KEY`
- `POSTHOG_API_KEY`
- `POSTHOG_HOST`
- `GOOGLE_ANALYTICS_ID`
- `RESEND_API_KEY`
- `DEFAULT_FROM_EMAIL`
- `SERVER_EMAIL`
- `AUTH_MODE`
- `SENTRY_DSN`
- `TURNSTILE_KEY`
- `TURNSTILE_SECRET`
- `GITHUB_SEEDING_TOKENS`
- `PUBLIC_MIN_PRS_THRESHOLD`
- `HEALTHCHECK_TOKEN`
- `HEALTH_CHECK_TOKENS`

**Required values and rules**
- `SITE_DOMAIN=tformance.com`
- `SITE_NAME=Tformance`
- `PUBLIC_MIN_PRS_THRESHOLD=100`
- `SECURE_SSL_REDIRECT=True` for production
- `USE_HTTPS_IN_ABSOLUTE_URLS=True`
- `GITHUB_SEEDING_TOKENS` must be one single comma-separated line
- `SENTRY_DSN` must be one single line
- `HEALTH_CHECK_TOKENS` must include `HEALTHCHECK_TOKEN`
- `GITHUB_APP_PRIVATE_KEY` must be a valid single-line env string with escaped `\\n` if App auth is enabled
- If the private key is not ready, set `GITHUB_APP_ENABLED=False` for cutover; do not leave it enabled with an empty key

**Host rules**
- Production hostnames only:
  - `tformance.com`
  - `www.tformance.com`
- Do not mix temporary or development hosts into the production `.env`
- If a separate admin/verification hostname is used on Unraid, it must be added to both `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`

---

## Task 1: Update the Repo-Tracked Unraid Deployment Artifacts

**User story:** As an operator, I have one clear Unraid runtime contract and the checked-in files match the real deployment.

**Files**
- Modify: `docker-compose.unraid.yml`
- Modify: `.env.unraid.example`
- Modify: `dev/guides/UNRAID-DEPLOYMENT.md`

**Implementation**
- `docker-compose.unraid.yml` must:
  - mount bind volumes for Postgres, Redis, and media under `/mnt/user/appdata/tformance/*`
  - define `web`, `worker-sync`, `worker-compute`, `worker-llm`, and `beat`
  - pass `GITHUB_SEEDING_TOKENS` to `web` and `worker-sync`
  - pass `GITHUB_APP_WEBHOOK_SECRET`, `TURNSTILE_*`, `GOOGLE_ANALYTICS_ID`, and `SERVER_EMAIL` to `web`
  - include a healthcheck for `web` against `/health/?token=$HEALTHCHECK_TOKEN`
- `.env.unraid.example` must exactly match the compose/runtime contract
- `UNRAID-DEPLOYMENT.md` must match the compose and env files; no stale variable lists are allowed

**Acceptance criteria**
- Given the repo-tracked compose file, when `docker compose config` runs, then it validates successfully.
- Given `.env.unraid.example`, when compared to compose, then no required env var is missing.
- Given the deployment guide, when followed literally, then it results in the same runtime contract as compose.

**TDD**
- For management commands or settings-related code touched by this task, write targeted failing tests first.
- For compose/env/docs, use verification-first rather than code-level TDD.

**Verification**
- `docker compose -f docker-compose.unraid.yml config`
- Manual env-to-compose diff against `.env.unraid.example`

---

## Task 2: Add or Finalize the Restore-Safe Bootstrap Commands

**User story:** As an operator, I can restore an existing DB and mark warm repos as ready instead of forcing a reseed.

**Files**
- Modify: `apps/public/management/commands/init_public_repo_sync_state.py`
- Modify: `apps/public/management/commands/rebuild_public_catalog_snapshots.py`
- Extend: `apps/public/tests/test_management_commands.py`
- Extend: `apps/public/tests/test_public_repo_sync_orchestration.py`

**Implementation**
- `init_public_repo_sync_state` must inspect restored repo data and set:
  - `ready` for repos with usable recent history
  - `pending_backfill` only for repos that are truly missing or stale
- It must seed:
  - `last_successful_sync_at`
  - `last_synced_updated_at`
  - `last_backfill_completed_at` where appropriate
- It must not mark every repo as `pending_backfill`
- `rebuild_public_catalog_snapshots` must:
  - rebuild repo snapshots from restored DB data
  - rebuild org snapshots from restored DB data
  - regenerate org and repo OG images
  - not call GitHub
  - not call Groq

**Acceptance criteria**
- Given a restored repo with recent PR history, when `init_public_repo_sync_state` runs, then the repo becomes `ready`.
- Given a restored repo with missing history, when `init_public_repo_sync_state` runs, then the repo becomes `pending_backfill`.
- Given restored data, when `rebuild_public_catalog_snapshots` runs, then pages become warm without any GitHub calls.
- Given the bootstrap commands run, when the first scheduled sync executes, then warm repos use delta sync instead of full backfill.

**TDD**
- Add failing command tests for `ready` vs `pending_backfill` classification.
- Add a failing command test asserting snapshot rebuild does not call GitHub clients.
- Add a failing test that OG images are generated during snapshot rebuild.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_management_commands.py apps/public/tests/test_public_repo_sync_orchestration.py -n 0`

---

## Task 3: Cut Over the Existing Local DB to Unraid Without Reseeding

**User story:** As the operator, I move the current local DB to Unraid and reuse the parsed history already present.

**Implementation**
- Source DB is the current local Postgres database.
- Use `pg_dump -Fc` and `pg_restore`.
- Do not run a full GitHub reseed after restore.
- Do not run broad Groq enrichment after restore.
- Keep the local stack intact until Unraid smoke tests pass.

**Cutover sequence**
1. Stop or pause local workers that write to the DB.
2. Create a final backup from the local DB.
3. Copy the dump to `/mnt/user/appdata/tformance/backups/`.
4. Bring up only `db` and `redis` on Unraid.
5. Restore the dump into Unraid Postgres.
6. Bring up `web`.
7. Run:
   - `.venv/bin/python manage.py migrate --noinput`
   - `.venv/bin/python manage.py bootstrap_site_domain --domain tformance.com --name "Tformance"`
   - `.venv/bin/python manage.py init_public_repo_sync_state`
   - `.venv/bin/python manage.py rebuild_public_catalog_snapshots`
8. Smoke-test public routes.
9. Bring up `worker-sync`, `worker-compute`, `worker-llm`, and `beat`.
10. Run one controlled public sync pass.
11. Verify that the sync behaves like delta-only refresh for warm repos.

**Acceptance criteria**
- Given the restored Unraid DB, when `web` starts, then `/open-source/`, org pages, and repo pages render before the first scheduled sync finishes.
- Given a restored repo with valid recent data, when the first sync runs, then it uses the delta overlap window instead of 180-day backfill.
- Given the migrated DB, when smoke-tested, then row counts for key models match the source DB closely enough for a warm cutover.
- Given the cutover is complete, when local workers remain off, then Unraid is the only writer.

**TDD**
- No fake reseed tests. The critical guardrail is command behavior and sync-state classification.
- Add one orchestration test proving that restored `ready` repos do not go through full backfill.

**Verification**
- Source vs target counts for:
  - `PublicOrgProfile`
  - `PublicRepoProfile`
  - `PublicOrgStats`
  - `PublicRepoStats`
  - `PullRequest`
- Smoke routes:
  - `/open-source/`
  - `/open-source/polar/`
  - `/open-source/polar/repos/polar/`
- OG routes:
  - `/og/open-source/polar.png`
  - `/og/open-source/polar/polar.png`

---

## Task 4: Ensure Ongoing Daily Sync on Unraid Fills Only Gaps and Updates

**User story:** As an operator, I trust Unraid to keep public data fresh without reprocessing all history.

**Files**
- Modify if needed: `apps/public/tasks.py`
- Modify if needed: `apps/public/public_sync.py`
- Modify if needed: `apps/public/services/sync_orchestrator.py`
- Extend: `apps/public/tests/test_public_sync_tasks.py`
- Extend: `apps/public/tests/test_public_repo_sync_orchestration.py`

**Implementation**
- Daily public sync on Unraid must:
  - read the repo catalog from the DB
  - fetch only deltas using overlap windows for `ready` repos
  - use bounded backfill only for repos that are stale or `pending_backfill`
- Public parsing must keep using `GITHUB_SEEDING_TOKENS`
- PAT exhaustion must:
  - defer the repo
  - preserve checkpoint state
  - not corrupt sync state
- Weekly Groq insights remain snapshot-level and flagship-only
- Public parsing must not switch to GitHub App auth in this phase

**Acceptance criteria**
- Given a warm repo on Unraid, when the daily sync runs, then it fetches only incremental changes.
- Given a stale repo, when the daily sync runs, then it enters bounded recovery instead of blind full-history reseed.
- Given PAT exhaustion, when the sync stops, then the repo remains retryable and checkpointed.
- Given weekly insight generation, when it runs, then it touches flagship repos only and does not reprocess all PRs.

**TDD**
- Add failing orchestration tests for delta-only sync, stale recovery, and rate-limit retry behavior.
- Add one test proving weekly insight selection remains scoped.

**Verification**
- `.venv/bin/pytest apps/public/tests/test_public_sync_tasks.py apps/public/tests/test_public_repo_sync_orchestration.py -n 0`
- `docker logs tformance-worker-sync --tail 200`
- `docker logs tformance-beat --tail 200`

---

## Task 5: Final Unraid Smoke, Rollback, and Operations Runbook

**User story:** As the operator, I can verify the cutover quickly and roll back cleanly if the Unraid stack is not ready.

**Implementation**
- Add one final runbook section to `UNRAID-DEPLOYMENT.md` covering:
  - pre-cutover checklist
  - cutover commands
  - smoke tests
  - rollback steps
  - daily operator checks
- Rollback decision:
  - do not destroy the local runtime until Unraid passes smoke checks
  - if Unraid smoke fails, stop Unraid writers, keep local runtime authoritative, fix forward, and repeat restore if needed
- Daily operator checks must include:
  - health endpoint
  - beat logs
  - sync worker logs
  - one public route
  - one OG route

**Acceptance criteria**
- Given the runbook, when followed by a mid-level developer, then they can perform the cutover without inventing missing steps.
- Given Unraid smoke fails, when rollback is triggered, then local remains the authoritative writer.
- Given the cutover is successful, when daily checks are run, then health, sync, and public routes all pass.

**Verification**
- `docker compose -f /mnt/user/appdata/tformance/docker-compose.yml config`
- `docker compose -f /mnt/user/appdata/tformance/docker-compose.yml up -d`
- `curl -I https://tformance.com/health/?token=<HEALTHCHECK_TOKEN>`
- `docker exec -it tformance-web .venv/bin/python manage.py check --deploy`

---

## Final Cutover Checklist

- Secrets rotated and stored outside chat history
- Immutable image built and pushed
- Unraid compose and env validated
- Local final DB dump created
- DB restored on Unraid
- Migrations applied
- Site domain bootstrapped
- Sync state initialized from restored data
- Repo/org snapshots rebuilt
- OG images rebuilt
- Public routes smoke-tested
- Workers and beat started
- Controlled delta sync executed
- Local writers left off after successful cutover

---

## Assumptions

- The current local Postgres DB is the correct source of truth for the first Unraid rollout.
- Public OSS parsing continues to use `GITHUB_SEEDING_TOKENS`.
- A full reseed after migration is explicitly out of scope.
- Weekly Groq work remains limited to flagship snapshot insights only.
- `PUBLIC_MIN_PRS_THRESHOLD=100` is the approved threshold for public inclusion.
- The external team are implementers, not product deciders; they must follow this plan literally where it specifies behavior.
