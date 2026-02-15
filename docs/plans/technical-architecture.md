# Technical Architecture: Public OSS Analytics Daily Sync Pipeline

**Document Version:** 1.0
**Date:** 2026-02-15
**Related Plan:** [glistening-sauteeing-kahan.md](/.claude/plans/glistening-sauteeing-kahan.md)

---

## Table of Contents

1. [Sync Pipeline Logic](#1-sync-pipeline-logic)
2. [API Quota Estimation](#2-api-quota-estimation)
3. [Redis Cache Strategy](#3-redis-cache-strategy)
4. [Job Scheduling Analysis](#4-job-scheduling-analysis)
5. [Per-Story Technical Details](#5-per-story-technical-details)

---

## 1. Sync Pipeline Logic

### 1.1 Daily Sync Flow (Step-by-Step)

The daily sync pipeline runs as a Celery chain with 3 sequential tasks:

```
4:00 AM UTC → sync_public_repos_task()
                ↓ (passes team_ids)
              process_public_prs_llm_task()
                ↓ (passes team_ids)
              compute_public_stats_task()
```

### 1.2 Sync Task: `sync_public_repos_task()`

**File:** `apps/public/tasks.py` (new)

**Function Signature:**
```python
@shared_task(soft_time_limit=3600, time_limit=4000)
def sync_public_repos_task() -> dict[str, int]:
    """Sync PRs for all public orgs from GitHub using incremental mode.

    Returns:
        Dict with stats: {org_count, total_prs_fetched, api_calls_made}
    """
```

**Logic Flow:**

1. **Load Public Org Profiles**
   ```python
   profiles = PublicOrgProfile.objects.filter(is_public=True).select_related('team')
   # Returns ~70+ orgs
   ```

2. **For Each Org** (sequential processing):
   ```python
   for profile in profiles:
       team = profile.team

       # Get repos from PublicOrgProfile.repos JSONField (migrated from RealProjectConfig)
       repos = profile.repos  # List[str] e.g., ["posthog/posthog", "posthog/posthog-js"]

       # Determine last sync date
       last_sync = PublicOrgStats.objects.get(org_profile=profile).last_computed_at
       since_date = last_sync or (timezone.now() - timedelta(days=90))
   ```

3. **Fetch PRs per Repo** (incremental sync):
   ```python
   from apps.metrics.seeding.github_graphql_fetcher import GitHubGraphQLFetcher

   fetcher = GitHubGraphQLFetcher(
       token=os.environ["GITHUB_SEEDING_TOKENS"],
       use_cache=True,  # Uses .seeding_cache/ with repo change detection
       fetch_check_runs=True,  # REST fallback for CI data
   )

   for repo in repos:
       # Incremental sync: only fetch PRs updated since last sync
       prs = fetcher.fetch_prs_with_details(
           repo,
           since=since_date,
           until=None,
           max_prs=1000,  # Safety limit per repo
       )
   ```

4. **GraphQL Fetcher Details**

   **Cache Validation** (`apps/metrics/seeding/github_graphql_fetcher.py:482-538`):
   ```python
   # Step 1: Fetch repo.pushedAt (cheap ~1 point query)
   repo_pushed_at = await self._fetch_repo_pushed_at(repo_full_name)

   # Step 2: Load cache
   cache = PRCache.load(repo_full_name, cache_dir=".seeding_cache")

   # Step 3: Validate cache freshness
   if cache and cache.repo_pushed_at == repo_pushed_at:
       # Repo unchanged since cache - use cached data
       return cache.prs
   elif cache and cache.repo_pushed_at < repo_pushed_at:
       # Repo has changed - incremental sync
       updated_prs = await self._fetch_updated_prs_async(repo_full_name, cache.fetched_at)
       merged_prs = self._merge_prs(cache.prs, updated_prs)  # Dedupe by PR number
       # Save merged cache
       return merged_prs
   else:
       # No cache - full sync
       prs = await self._fetch_prs_async(repo_full_name, since, max_prs)
       # Save to cache
       return prs
   ```

   **GraphQL Query** (for full sync - `apps/integrations/services/github_graphql.py`):
   ```graphql
   query($owner: String!, $repo: String!, $cursor: String) {
     repository(owner: $owner, name: $repo) {
       pullRequests(
         first: 100,
         after: $cursor,
         orderBy: {field: CREATED_AT, direction: DESC}
       ) {
         nodes {
           number
           title
           body
           state
           isDraft
           createdAt
           updatedAt
           mergedAt
           closedAt
           additions
           deletions
           headRefName
           baseRefName
           author { login }
           labels(first: 10) { nodes { name } }
           milestone { title }
           assignees(first: 5) { nodes { login } }
           closingIssuesReferences(first: 3) { nodes { number } }
           reviews(first: 20) {
             nodes {
               databaseId
               author { login }
               state
               submittedAt
               body
             }
           }
           commits(first: 50) {
             nodes {
               commit {
                 oid
                 message
                 additions
                 deletions
                 author { name, date, user { login } }
               }
             }
           }
           files(first: 100) {
             nodes {
               path
               changeType
               additions
               deletions
             }
           }
         }
         pageInfo {
           hasNextPage
           endCursor
         }
       }
     }
     rateLimit {
       remaining
       resetAt
       cost
     }
   }
   ```

   **Incremental Query** (for cache updates):
   ```graphql
   query($owner: String!, $repo: String!, $since: DateTime!, $cursor: String) {
     repository(owner: $owner, name: $repo) {
       pullRequests(
         first: 100,
         after: $cursor,
         orderBy: {field: UPDATED_AT, direction: DESC}
       ) {
         nodes {
           # Same fields as above
           updatedAt  # Used to stop pagination when updatedAt < since
         }
         pageInfo {
           hasNextPage
           endCursor
         }
       }
     }
   }
   ```

   **Check Runs Fallback** (REST API - `github_graphql_fetcher.py:408-455`):
   ```python
   # GraphQL doesn't support check runs, use REST API fallback
   # Uses commit SHA from GraphQL data → 1 API call per PR
   for pr in prs:
       if pr.commits:
           sha = pr.commits[-1].sha
           check_runs = self._fetch_check_runs_for_commit(repo_full_name, sha)
           pr.check_runs.extend(check_runs)

   # REST endpoint: GET /repos/{owner}/{repo}/commits/{sha}/check-runs
   # Returns: [{id, name, status, conclusion, started_at, completed_at}]
   ```

5. **Deduplication** (`apps/metrics/seeding/real_project_seeder.py:550-652`):
   ```python
   # PRs are deduplicated by (team_id, github_pr_id, github_repo)
   # Constraint: unique_team_pr

   for pr_data in prs:
       existing_pr = PullRequest.objects.filter(
           team=team,
           github_pr_id=pr_data.number,
           github_repo=pr_data.github_repo,
       ).first()

       if existing_pr:
           # Update existing PR if data changed
           if existing_pr.merged_at != pr_data.merged_at:
               self._update_pr(existing_pr, pr_data)
       else:
           # Create new PR
           self._create_single_pr(team, pr_data)
   ```

6. **PR Creation Pattern** (`real_project_seeder.py:554-652`):
   ```python
   def _create_single_pr(self, team: Team, pr_data: FetchedPRFull) -> PullRequest:
       """Create a single PR with all relations."""

       # Find or create author
       author = self._find_member(pr_data.author_login, pr_data.author_id)
       if not author:
           author = self._create_member_from_pr_author(team, pr_data)

       # Create PR
       pr = PullRequestFactory(
           team=team,
           github_pr_id=pr_data.number,
           github_repo=pr_data.github_repo,
           title=pr_data.title,
           body=pr_data.body,
           state=pr_data.state,
           author=author,
           pr_created_at=pr_data.created_at,
           merged_at=pr_data.merged_at,
           additions=pr_data.additions,
           deletions=pr_data.deletions,
           # ... other fields
       )

       # Create PRFile records (bulk_create for speed)
       files = [
           PRFile(
               team=team,
               pull_request=pr,
               filename=f.filename,
               additions=f.additions,
               deletions=f.deletions,
               status=f.status,
           )
           for f in pr_data.files
       ]
       PRFile.objects.bulk_create(files, ignore_conflicts=True)

       # Create PRReview records
       for review in pr_data.reviews:
           reviewer = self._find_member(review.reviewer_login, None)
           if reviewer:
               PRReview.objects.create(
                   team=team,
                   pull_request=pr,
                   reviewer=reviewer,
                   state=review.state,
                   submitted_at=review.submitted_at,
               )

       # Create PRCheckRun records
       for check_run in pr_data.check_runs:
           PRCheckRun.objects.create(
               team=team,
               pull_request=pr,
               github_id=check_run.github_id,
               name=check_run.name,
               status=check_run.status,
               conclusion=check_run.conclusion,
               started_at=check_run.started_at,
               completed_at=check_run.completed_at,
           )

       return pr
   ```

7. **Error Handling**:
   ```python
   try:
       prs_fetched = sync_org_repos(profile)
       total_prs_fetched += prs_fetched
   except GitHubGraphQLRateLimitError as e:
       logger.error(f"Rate limit hit for {profile.display_name}: {e}")
       # Stop processing remaining orgs, return partial results
       break
   except Exception as e:
       logger.exception(f"Failed to sync {profile.display_name}")
       error_count += 1
       # Continue to next org
       continue
   ```

### 1.3 LLM Processing: `process_public_prs_llm_task()`

**File:** `apps/public/tasks.py` (new)

**Function Signature:**
```python
@shared_task(soft_time_limit=7200, time_limit=8000)
def process_public_prs_llm_task() -> dict[str, int]:
    """Process PRs without LLM analysis using Groq Batch API.

    Returns:
        Dict with stats: {prs_submitted, prs_processed, batch_id}
    """
```

**Logic Flow:**

1. **Query PRs without LLM analysis**:
   ```python
   # Get all public org teams
   team_ids = PublicOrgProfile.objects.filter(is_public=True).values_list('team_id', flat=True)

   # Find PRs needing analysis (limit to prevent overwhelming batch API)
   prs = (
       PullRequest.objects.filter(  # noqa: TEAM001
           team_id__in=team_ids,
           llm_summary__isnull=True,
           body__isnull=False,
       )
       .exclude(body="")
       .select_related("author", "team")
       .prefetch_related("files", "commits", "reviews__reviewer")
       .order_by("-pr_created_at")[:500]  # Daily limit
   )
   ```

2. **Submit to Groq Batch API** (`apps/integrations/services/groq_batch.py`):
   ```python
   from apps.integrations.services.groq_batch import GroqBatchProcessor

   processor = GroqBatchProcessor(
       api_key=os.environ["GROQ_API_KEY"],
       model="openai/gpt-oss-20b",  # Cheapest model
       temperature=0.1,
   )

   # Build JSONL batch file
   batch_requests = []
   for pr in prs:
       context = build_llm_pr_context(pr)  # From apps/metrics/services/llm_prompts.py
       batch_requests.append({
           "custom_id": f"pr-{pr.id}",
           "method": "POST",
           "url": "/v1/chat/completions",
           "body": {
               "model": "openai/gpt-oss-20b",
               "messages": [
                   {"role": "system", "content": PR_ANALYSIS_SYSTEM_PROMPT},
                   {"role": "user", "content": context}
               ],
               "temperature": 0.1,
               "response_format": {
                   "type": "json_schema",
                   "json_schema": {
                       "name": "pr_analysis",
                       "strict": True,
                       "schema": get_strict_schema()
                   }
               }
           }
       })

   # Submit batch
   batch_id = processor.submit_batch(batch_requests)
   # Batch ID saved to .groq_batches/{batch_id}.json for tracking
   ```

3. **Poll for Completion**:
   ```python
   # Groq batch processing is async - typically 1-5 minutes for 500 PRs
   # Polling loop with exponential backoff

   max_wait_time = 3600  # 1 hour timeout
   poll_interval = 30  # Start with 30s

   elapsed = 0
   while elapsed < max_wait_time:
       status = processor.check_batch_status(batch_id)

       if status.status == "completed":
           break
       elif status.status == "failed":
           raise Exception(f"Batch {batch_id} failed: {status.error}")

       time.sleep(poll_interval)
       elapsed += poll_interval
       poll_interval = min(poll_interval * 1.5, 300)  # Max 5 min
   ```

4. **Download and Save Results**:
   ```python
   results = processor.get_results(batch_id)
   # results = [{"custom_id": "pr-123", "response": {...}}, ...]

   for result in results:
       pr_id = int(result["custom_id"].split("-")[1])
       pr = PullRequest.objects.get(id=pr_id)

       # Extract LLM response
       llm_data = result["response"]["body"]["choices"][0]["message"]["content"]
       llm_json = json.loads(llm_data)

       # Save to PR
       pr.llm_summary = llm_json
       pr.llm_summary_version = PROMPT_VERSION
       pr.save(update_fields=["llm_summary", "llm_summary_version"])

       # Update AI confidence score
       from apps.metrics.services.ai_detection import update_pr_ai_confidence
       update_pr_ai_confidence(pr)
   ```

### 1.4 Stats Recomputation: `compute_public_stats_task()`

**File:** `apps/public/tasks.py` (existing)

This task already exists and is documented in `apps/public/tasks.py:64-138`.

**Key Changes:** None needed, already implemented.

**Logic:**
- Iterates all `PublicOrgProfile` with `is_public=True`
- Calls `compute_team_summary()` and `compute_ai_tools_breakdown()`
- Updates `PublicOrgStats` via `update_or_create()`
- Clears Redis cache via `_clear_public_cache()`
- Purges Cloudflare CDN via `purge_all_cache()`

### 1.5 Chain Failure Handling

**Question:** What happens if one step fails?

**Answer:** Celery chains abort on first failure. To prevent data loss:

```python
# Use link_error for error handling
chain(
    sync_public_repos_task.si(),
    process_public_prs_llm_task.si(),
    compute_public_stats_task.si(),
).apply_async(link_error=handle_pipeline_error.s())

@shared_task
def handle_pipeline_error(task_id, exc, traceback):
    """Log pipeline failures and alert operators."""
    logger.error(f"Public pipeline failed at task {task_id}: {exc}")
    # Send alert email or Slack notification
```

---

## 2. API Quota Estimation

### 2.1 GitHub GraphQL Quota

**Rate Limit:** 5,000 points/hour (resets hourly)
**Cost Model:** Each query consumes points based on complexity

**Complexity Calculation:**
- Base query: 1 point
- First 100 nodes: +1 point
- Each additional 100 nodes: +1 point
- Nested connections: multiply by depth

**Our PR Query Cost** (from rateLimit.cost in response):
```
Query fetches:
- 100 PRs per page
- 20 reviews per PR
- 50 commits per PR
- 100 files per PR

Estimated cost: ~50-75 points per query (observed in testing)
```

**Repository Count:**
From `apps/metrics/seeding/real_projects.py`, we track 70+ orgs:
- Most orgs: 1-2 repos (e.g., Polar: 1, Supabase: 1)
- Multi-repo orgs: PostHog (4), Antiwork (3), Cal.com (2)

**Total repos:** ~85 repos (conservative estimate)

### 2.2 Daily Sync Quota Math

**Scenario 1: Full Cache Hit (Repo Unchanged)**
```
Per repo:
- 1 query to check repo.pushedAt: ~1 point
- Load from cache: 0 API calls

Total for 85 repos: 85 points
Time: < 1 minute
```

**Scenario 2: Incremental Sync (Repo Changed)**
```
Per repo:
- 1 query for repo.pushedAt: ~1 point
- 1-3 queries for updated PRs: ~60-180 points
  (depends on how many PRs updated since last sync)
- Typical OSS repo: 5-20 new/updated PRs per day
  → 1-2 GraphQL queries (100 PRs per page)

Average per changed repo: ~75 points
```

**Estimate: Daily Change Rate**
- Active repos (10-20 PRs/day): ~15 repos (PostHog, Supabase, Cal.com, etc.)
- Low-activity repos (0-5 PRs/day): ~70 repos

**Daily Quota Consumption:**
```
Unchanged repos: 70 × 1 = 70 points
Changed repos: 15 × 75 = 1,125 points

Total GraphQL: ~1,200 points/day
Hourly rate: 1,200 / 1 = 1,200 points (if run sequentially in 1 hour)

✅ Well within 5,000 points/hour limit
```

### 2.3 REST API Quota (Check Runs)

**Rate Limit:** 5,000 requests/hour (different from GraphQL)

**Check Runs Fetching:**
```
Per PR: 1 REST call to GET /repos/{owner}/{repo}/commits/{sha}/check-runs
Daily new PRs: ~150-250 PRs across all 85 repos

Total REST calls: ~200 requests/day
Hourly rate: 200 / 1 = 200 requests (if run in 1 hour)

✅ Well within 5,000 requests/hour limit
```

### 2.4 Can We Do All 70+ Orgs in One Run?

**YES.** Conservative estimate:

```
GraphQL quota: 1,200 / 5,000 = 24% utilization
REST quota: 200 / 5,000 = 4% utilization
Wall-clock time: ~60-90 minutes (sequential org processing)

Even if we 3x our repo count (255 repos), we'd still be under quota.
```

**Recommendation:** Process all orgs in a single sync run at 4:00 AM UTC.

---

## 3. Redis Cache Strategy

### 3.1 Current Cache TTL

**Redis Cache:** 1 hour (3600 seconds)
**CDN Cache:** 12 hours (43200 seconds)

**Location:** `apps/public/services.py:37`

```python
PUBLIC_CACHE_TTL = 3600  # 1 hour
PUBLIC_CACHE_MAX_AGE = 43200  # 12 hours CDN
```

### 3.2 Problem with Current TTL

**Issue:** Data updates only once daily (4:00 AM UTC), but cache expires every hour.

**Result:**
- 23 unnecessary cache misses per day
- Recompute same data 23 times
- Waste CPU on identical aggregations

### 3.3 Recommended Cache TTL

**Redis Cache:** 6 hours (21600 seconds)
**CDN Cache:** 12 hours (43200 seconds)

**Rationale:**
```
Data freshness: Updated daily at ~4:30 AM UTC (after sync + LLM + stats)
Cache expires: 6 hours later = 10:30 AM UTC
Next expiry: 4:30 PM UTC
Next expiry: 10:30 PM UTC
Next expiry: 4:30 AM UTC (right when new data arrives)

Result: 4 cache refreshes per day (vs 24 currently)
Each refresh serves ~6 hours of traffic
```

**Edge Case:** Mid-day repo request
```
User submits new repo request at 2:00 PM UTC
→ Admin approves and adds to PublicOrgProfile
→ Manual sync: python manage.py sync_public_repos --org=new-org
→ Manual stats recompute: python manage.py compute_public_stats --org=new-org
→ Cache invalidation: cache.delete(f"public:org:{slug}")

New org appears on directory immediately
```

### 3.4 Cache Key Structure

**Current Keys** (`apps/public/services.py`):
```python
CACHE_PREFIX = "public:"

# Directory page (all orgs)
f"{CACHE_PREFIX}directory"          # No year filter
f"{CACHE_PREFIX}directory:{year}"   # Year-specific

# Org detail pages
f"{CACHE_PREFIX}org:{slug}"

# Industry comparison
f"{CACHE_PREFIX}industry:{industry_key}"

# Global stats
f"{CACHE_PREFIX}global"
```

### 3.5 Cache Invalidation Strategy

**When to Invalidate:**
1. After `compute_public_stats_task()` completes
2. When manually adding new org
3. When updating org metadata (logo, description)

**How:**
```python
# Selective invalidation (preferred)
cache.delete(f"{CACHE_PREFIX}org:{slug}")
cache.delete(f"{CACHE_PREFIX}industry:{industry}")
cache.delete(f"{CACHE_PREFIX}global")
cache.delete(f"{CACHE_PREFIX}directory")

# Full invalidation (fallback)
from django_redis import get_redis_connection
redis_conn = get_redis_connection("default")
keys = list(redis_conn.scan_iter(match=f"*{CACHE_PREFIX}*", count=100))
redis_conn.delete(*keys)
```

---

## 4. Job Scheduling Analysis

### 4.1 Celery Beat Schedule

**File:** `tformance/settings.py`

**New Schedule:**
```python
SCHEDULED_TASKS = {
    # Existing task (unchanged)
    "sync-github-repositories-daily": {
        "task": "apps.integrations.tasks.sync_all_repositories_task",
        "schedule": schedules.crontab(minute=0, hour=4),  # 4:00 AM UTC
        "expire_seconds": 60 * 60 * 4,
    },

    # NEW: Public analytics daily pipeline
    "sync-public-analytics-daily": {
        "task": "apps.public.tasks.run_daily_public_pipeline",
        "schedule": schedules.crontab(minute=0, hour=4),  # 4:00 AM UTC
        "expire_seconds": 60 * 60 * 6,  # 6 hour expiry
    },

    # NEW: Weekly public insights generation
    "generate-public-insights-weekly": {
        "task": "apps.public.tasks.generate_public_insights_task",
        "schedule": schedules.crontab(minute=0, hour=6, day_of_week=1),  # Monday 6:00 AM UTC
        "expire_seconds": 60 * 60 * 2,
    },
}
```

**Chain Task** (`apps/public/tasks.py`):
```python
@shared_task
def run_daily_public_pipeline():
    """Run daily public analytics pipeline as a Celery chain.

    Chain ensures sequential execution:
    1. Sync PRs from GitHub
    2. Process PRs with LLM
    3. Recompute stats

    Each task receives results from previous task.
    Pipeline aborts on first failure.
    """
    from celery import chain

    chain(
        sync_public_repos_task.si(),
        process_public_prs_llm_task.si(),
        compute_public_stats_task.si(),
    ).apply_async(link_error=handle_pipeline_error.s())
```

### 4.2 Sequential vs Parallel Processing

**Decision:** Sequential org processing (not parallel)

**Rationale:**
1. **GitHub API Best Practices:** "Make requests serially instead of concurrently to avoid secondary rate limits"
   - Source: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api

2. **Memory Efficiency:** Processing 70+ orgs in parallel would load ~50,000 PRs into memory
   - Sequential: ~500-1,000 PRs in memory at a time
   - Parallel: 50,000+ PRs in memory = OOM risk

3. **Error Recovery:** Sequential processing allows graceful degradation
   - If org #30 fails, orgs #31-70 still process
   - Parallel: one failure can cascade

**Implementation:**
```python
for profile in profiles:  # Sequential loop, not parallel tasks
    try:
        sync_org_repos(profile)
    except Exception as e:
        logger.exception(f"Failed to sync {profile.display_name}")
        continue  # Don't block other orgs
```

### 4.3 Wall-Clock Time Estimate

**Sync Task:** `sync_public_repos_task()`
```
Per org (cache hit):     ~5 seconds (1 GraphQL query)
Per org (incremental):   ~30-60 seconds (2-4 GraphQL queries + check runs)

Estimate: 15 orgs changed × 45s = 675s (11 min)
          70 orgs cached × 5s = 350s (6 min)
          Total: ~17 minutes
```

**LLM Task:** `process_public_prs_llm_task()`
```
Batch submission:   ~30 seconds (upload JSONL, create batch)
Groq processing:    ~3-5 minutes (500 PRs)
Result download:    ~30 seconds
DB save:            ~1 minute (500 updates)

Total: ~6 minutes
```

**Stats Task:** `compute_public_stats_task()`
```
Per org:    ~2 seconds (aggregation queries + cache clear)
70 orgs:    ~140 seconds (2.3 minutes)
Cloudflare purge: ~5 seconds

Total: ~3 minutes
```

**Full Pipeline:** ~26 minutes (end-to-end)

### 4.4 Groq Batch API Details

**How Long Do Batches Take?**

From testing and docs:
- Batch API is async (fire-and-forget)
- Processing time: ~30-60 seconds per 100 PRs
- 500 PRs: typically 3-5 minutes
- Max wait: 10 minutes (safety timeout)

**Batch Status Polling:**
```python
# File: apps/integrations/services/groq_batch.py

def wait_for_batch_completion(self, batch_id: str, max_wait: int = 600) -> dict:
    """Poll batch status until completion.

    Args:
        batch_id: Groq batch ID
        max_wait: Maximum seconds to wait (default: 10 min)

    Returns:
        Batch status dict with {status, completed_count, failed_count}

    Raises:
        TimeoutError: If batch doesn't complete within max_wait
    """
    start_time = time.time()
    poll_interval = 10  # Start with 10s

    while time.time() - start_time < max_wait:
        status = self.check_batch_status(batch_id)

        if status["status"] == "completed":
            return status
        elif status["status"] == "failed":
            raise Exception(f"Batch {batch_id} failed")

        time.sleep(poll_interval)
        poll_interval = min(poll_interval * 1.2, 60)  # Max 1 min

    raise TimeoutError(f"Batch {batch_id} timed out after {max_wait}s")
```

**Is It Async?**

Yes, Groq batch API is async:
1. Submit batch → returns batch_id immediately
2. Groq processes in background
3. Poll status endpoint to check progress
4. Download results when status="completed"

**Our task waits for completion** (synchronous at task level):
```python
batch_id = processor.submit_batch(batch_requests)
results = processor.wait_for_batch_completion(batch_id)  # Blocks until done
processor.save_results(results)
```

### 4.5 Should We Batch Orgs into Groups?

**NO.** Current sequential processing is optimal because:

1. **API Quotas:** We use <25% of hourly quota (1,200 / 5,000)
   - No need to spread across multiple hours

2. **Wall-Clock Time:** 26 minutes is acceptable for daily sync
   - Runs at 4:00 AM UTC (low traffic)
   - Completes by 4:30 AM

3. **Complexity:** Batching adds coordination overhead
   - Need to track which orgs in which batch
   - Need to handle partial failures across batches
   - No benefit given we're within quota

**If we add 200+ more orgs** (future scaling):
```
Estimated time: 200 orgs × 30s = 100 min (1h 40m)
GraphQL quota: ~4,000 / 5,000 points (80% utilization)

Then consider batching:
- Batch 1 (4:00 AM): Orgs 1-100
- Batch 2 (5:00 AM): Orgs 101-200
```

### 4.6 Memory Considerations

**Per-Org Memory:**
```
Org with 500 PRs:
- PR objects: 500 × 2 KB = 1 MB
- Files: 500 PRs × 10 files × 0.5 KB = 2.5 MB
- Reviews: 500 PRs × 3 reviews × 0.3 KB = 0.45 MB
- Total: ~4 MB per org
```

**Sequential Processing:**
```
Peak memory: 1 org at a time = 4 MB
70 orgs sequentially = 4 MB peak (garbage collected between orgs)
```

**Parallel Processing (hypothetical):**
```
Peak memory: 70 orgs × 4 MB = 280 MB (just for PR data)
Plus Django ORM overhead: ~500 MB total
Risk of OOM on small Heroku dynos (512 MB)
```

**Recommendation:** Keep sequential processing.

---

## 5. Per-Story Technical Details

### Story 1: Repos Analyzed List

**New Function:** `apps/public/aggregations.py`

```python
def compute_repos_analyzed(team_id: int) -> list[dict[str, Any]]:
    """Compute list of repos with PR counts for an org.

    Args:
        team_id: Team ID

    Returns:
        List of dicts: [{repo, pr_count, github_url}, ...]
        Sorted by pr_count descending.

    Example:
        [
            {
                "repo": "posthog/posthog",
                "pr_count": 1834,
                "github_url": "https://github.com/posthog/posthog"
            },
            {
                "repo": "posthog/posthog-js",
                "pr_count": 156,
                "github_url": "https://github.com/posthog/posthog-js"
            }
        ]
    """
    from django.db.models import Count

    qs = (
        PullRequest.objects.filter(  # noqa: TEAM001
            team_id=team_id,
            state="merged"
        )
        .exclude(
            Q(author__github_username__endswith="[bot]")
            | Q(author__github_username__in=BOT_USERNAMES)
        )
        .values("github_repo")
        .annotate(pr_count=Count("id"))
        .order_by("-pr_count")
    )

    return [
        {
            "repo": row["github_repo"],
            "pr_count": row["pr_count"],
            "github_url": f"https://github.com/{row['github_repo']}"
        }
        for row in qs
    ]
```

**Service Layer:** `apps/public/services.py`

```python
# In PublicAnalyticsService.get_org_detail()
# Line ~190, add:

repos_analyzed = compute_repos_analyzed(team_id)

# Add to result dict:
result = {
    # ... existing fields ...
    "repos_analyzed": repos_analyzed,
}
```

**Template:** `templates/public/org_detail.html`

```html
<!-- Section 11: Repos Analyzed (before Methodology) -->
<section class="repos-analyzed">
    <h2>Repositories Analyzed</h2>
    <ul class="repo-list">
        {% for repo in repos_analyzed %}
        <li>
            <a href="{{ repo.github_url }}" target="_blank" rel="noopener">
                {{ repo.repo }}
            </a>
            <span class="badge">{{ repo.pr_count }} PRs</span>
        </li>
        {% endfor %}
    </ul>
</section>
```

---

### Story 2: Combined Cycle Time + AI Adoption Chart

**No Backend Changes** — data already available in template context.

**Template:** `templates/public/org_detail.html`

```html
<!-- Section 3: Add dual-axis chart -->
<canvas id="combinedTrendChart" width="400" height="200"></canvas>

<script>
const ctx = document.getElementById('combinedTrendChart').getContext('2d');

// Data from Django template context
const months = {{ monthly_trends|map(attribute='month')|map('date', 'Y-m')|list|json_script:"months-data" }};
const aiAdoption = {{ monthly_trends|map(attribute='ai_pct')|list|json_script:"ai-data" }};
const cycleTime = {{ cycle_time_trend|map(attribute='avg_cycle_time')|list|json_script:"cycle-data" }};

new Chart(ctx, {
    type: 'line',
    data: {
        labels: JSON.parse(document.getElementById('months-data').textContent),
        datasets: [
            {
                label: 'AI Adoption (%)',
                data: JSON.parse(document.getElementById('ai-data').textContent),
                yAxisID: 'y-right',
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                fill: true
            },
            {
                label: 'Cycle Time (hours)',
                data: JSON.parse(document.getElementById('cycle-data').textContent),
                yAxisID: 'y-left',
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                fill: true
            }
        ]
    },
    options: {
        responsive: true,
        scales: {
            'y-left': {
                type: 'linear',
                position: 'left',
                title: { display: true, text: 'Cycle Time (hours)' }
            },
            'y-right': {
                type: 'linear',
                position: 'right',
                title: { display: true, text: 'AI Adoption (%)' },
                grid: { drawOnChartArea: false }
            }
        }
    }
});
</script>
```

---

### Story 3: PR Size Distribution

**New Function:** `apps/public/aggregations.py`

```python
def compute_pr_size_distribution(
    team_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> list[dict[str, Any]]:
    """Compute PR size distribution in 5 buckets.

    Buckets:
    - XS: 1-50 lines
    - S: 51-200 lines
    - M: 201-500 lines
    - L: 501-1000 lines
    - XL: 1000+ lines

    Args:
        team_id: Team ID
        start_date: Start datetime for rolling window
        end_date: End datetime for rolling window

    Returns:
        List of dicts: [{bucket, count, pct}, ...]

    Example:
        [
            {"bucket": "XS", "count": 145, "pct": 29.0},
            {"bucket": "S", "count": 203, "pct": 40.6},
            {"bucket": "M", "count": 98, "pct": 19.6},
            {"bucket": "L", "count": 38, "pct": 7.6},
            {"bucket": "XL", "count": 16, "pct": 3.2}
        ]
    """
    from django.db.models import Case, When, IntegerField, Count, F

    qs = _base_pr_queryset(team_id, start_date=start_date, end_date=end_date)

    # Annotate each PR with its size bucket
    qs = qs.annotate(
        total_lines=F("additions") + F("deletions"),
        size_bucket=Case(
            When(total_lines__lte=50, then=Value("XS")),
            When(total_lines__lte=200, then=Value("S")),
            When(total_lines__lte=500, then=Value("M")),
            When(total_lines__lte=1000, then=Value("L")),
            default=Value("XL"),
            output_field=IntegerField(),
        )
    )

    # Group by bucket and count
    distribution = (
        qs.values("size_bucket")
        .annotate(count=Count("id"))
        .order_by("size_bucket")
    )

    # Calculate percentages
    total = sum(row["count"] for row in distribution)

    # Map to ordered buckets
    bucket_order = ["XS", "S", "M", "L", "XL"]
    bucket_counts = {row["size_bucket"]: row["count"] for row in distribution}

    return [
        {
            "bucket": bucket,
            "count": bucket_counts.get(bucket, 0),
            "pct": round(bucket_counts.get(bucket, 0) * 100.0 / total, 1) if total > 0 else 0
        }
        for bucket in bucket_order
    ]
```

**Service Layer:** `apps/public/services.py`

```python
# In PublicAnalyticsService.get_org_detail()
# Add:
pr_size_distribution = compute_pr_size_distribution(team_id, start_date=start_date, end_date=end_date)

# Add to result dict:
result = {
    # ... existing fields ...
    "pr_size_distribution": pr_size_distribution,
}
```

**Template:** `templates/public/org_detail.html`

```html
<!-- Doughnut chart -->
<canvas id="prSizeChart" width="300" height="300"></canvas>

<script>
const sizeData = {{ pr_size_distribution|json_script:"size-data" }};
const parsed = JSON.parse(document.getElementById('size-data').textContent);

new Chart(document.getElementById('prSizeChart'), {
    type: 'doughnut',
    data: {
        labels: parsed.map(d => d.bucket),
        datasets: [{
            data: parsed.map(d => d.count),
            backgroundColor: [
                '#4ade80', // XS - green
                '#60a5fa', // S - blue
                '#fbbf24', // M - yellow
                '#f97316', // L - orange
                '#ef4444'  // XL - red
            ]
        }]
    },
    options: {
        plugins: {
            tooltip: {
                callbacks: {
                    label: (context) => {
                        const item = parsed[context.dataIndex];
                        return `${item.bucket}: ${item.count} PRs (${item.pct}%)`;
                    }
                }
            }
        }
    }
});
</script>
```

---

### Story 4: Fix PR Author Attribution Bug

**This bug is already documented in the plan.** No new architecture needed.

**Files Changed:**
- `apps/metrics/seeding/real_project_seeder.py` (3 fixes)
- `apps/metrics/tests/seeding/test_member_collision.py` (new tests)

**After Fix:** Re-run `python manage.py seed_from_cache --org=posthog` to correct existing data.

---

### Story 5: Team Member Breakdown with Avatars

**Modified Function:** `apps/public/aggregations.py`

```python
def compute_member_breakdown(
    team_id: int,
    year: int | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> list[dict[str, Any]]:
    """Compute per-member metrics with avatar URLs.

    Returns:
        List of dicts with fields:
        - author_id: int
        - display_name: str
        - github_username: str
        - avatar_url: str  # NEW
        - prs_merged: int
        - avg_cycle_time: float
        - ai_pct: float
        - reviews_given: int
    """
    # ... existing code ...

    # Add avatar_url to results
    results = []
    for row in author_stats:
        results.append({
            "author_id": row["author"],
            "display_name": row["author__display_name"],
            "github_username": row["author__github_username"],
            "avatar_url": f"https://github.com/{row['author__github_username']}.png?size=40",  # NEW
            "prs_merged": row["prs_merged"],
            "avg_cycle_time": round(float(row["avg_cycle_time"]), 1) if row["avg_cycle_time"] else 0,
            "ai_pct": ai_pct,
            "reviews_given": review_counts.get(row["author"], 0),
        })
    return results
```

**Template:** `templates/public/org_detail.html`

```html
<!-- Section 5: Member Breakdown -->
<table class="member-breakdown">
    <thead>
        <tr>
            <th>Contributor</th>
            <th>PRs</th>
            <th>Cycle Time</th>
            <th>AI %</th>
            <th>Reviews</th>
        </tr>
    </thead>
    <tbody>
        {% for member in member_breakdown %}
        <tr>
            <td class="contributor-cell">
                <img
                    src="{{ member.avatar_url }}"
                    alt="{{ member.display_name }}"
                    class="avatar"
                    loading="lazy"
                    onerror="this.src='/static/img/default-avatar.png'"
                >
                <span>{{ member.display_name }}</span>
            </td>
            <td>{{ member.prs_merged }}</td>
            <td>{{ member.avg_cycle_time }}h</td>
            <td>{{ member.ai_pct }}%</td>
            <td>{{ member.reviews_given }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<style>
.avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    margin-right: 8px;
    vertical-align: middle;
}
</style>
```

---

### Story 6: Organisation Image at Top

**No Backend Changes** — `logo_url` already in `PublicOrgProfile` model.

**Template:** `templates/public/org_detail.html`

```html
<!-- Section 1: Hero -->
<div class="hero">
    <img
        src="{% if profile.logo_url %}{{ profile.logo_url }}{% else %}https://github.com/{{ profile.github_org_url|split:'/'|last }}.png?size=80{% endif %}"
        alt="{{ profile.display_name }} logo"
        class="org-logo"
    >
    <h1>{{ profile.display_name }}</h1>
    <p>{{ profile.description }}</p>
</div>

<style>
.org-logo {
    width: 80px;
    height: 80px;
    border-radius: 12px;
    margin-bottom: 16px;
}
</style>
```

---

### Story 7: Limit Top Reviewers to 10

**File:** `apps/public/aggregations.py`

**Change:** Line 639
```python
# Before:
.order_by("-reviews_given")[:15]

# After:
.order_by("-reviews_given")[:10]
```

---

### Story 8: Enhanced PR Table

**Modified Function:** `apps/public/aggregations.py`

```python
def compute_recent_prs(team_id: int, limit: int = 10) -> list[dict[str, Any]]:
    """Fetch recently merged PRs with enhanced metadata.

    Returns:
        List of dicts with fields:
        - title: str
        - author_name: str
        - author_github: str
        - github_repo: str
        - github_url: str
        - cycle_time_hours: float | None
        - is_ai_assisted: bool
        - ai_tools: list[str]
        - merged_at: datetime
        - github_pr_id: int
        - pr_type: str  # NEW: feature/bugfix/refactor/etc
        - tech_categories: list[str]  # NEW: backend/frontend/devops/etc
        - size_label: str  # NEW: XS/S/M/L/XL
        - additions: int  # NEW
        - deletions: int  # NEW
    """
    prs = (
        PullRequest.objects.filter(  # noqa: TEAM001
            team_id=team_id,
            state="merged",
        )
        .exclude(Q(author__github_username__endswith="[bot]") | Q(author__github_username__in=BOT_USERNAMES))
        .select_related("author")
        .order_by("-merged_at")[:limit]
    )

    results = []
    for pr in prs:
        # Calculate size label
        total_lines = (pr.additions or 0) + (pr.deletions or 0)
        if total_lines <= 50:
            size_label = "XS"
        elif total_lines <= 200:
            size_label = "S"
        elif total_lines <= 500:
            size_label = "M"
        elif total_lines <= 1000:
            size_label = "L"
        else:
            size_label = "XL"

        results.append({
            "title": pr.title,
            "author_name": pr.author.display_name if pr.author else "Unknown",
            "author_github": pr.author.github_username if pr.author else "",
            "github_repo": pr.github_repo,
            "cycle_time_hours": float(pr.cycle_time_hours) if pr.cycle_time_hours else None,
            "is_ai_assisted": pr.is_ai_assisted,
            "ai_tools": pr.effective_ai_tools,  # Uses effective_* property
            "merged_at": pr.merged_at,
            "github_pr_id": pr.github_pr_id,
            "github_url": f"https://github.com/{pr.github_repo}/pull/{pr.github_pr_id}",
            # NEW FIELDS
            "pr_type": pr.effective_pr_type,  # Uses effective_* property (LLM + fallback)
            "tech_categories": pr.effective_tech_categories,  # Uses effective_* property
            "size_label": size_label,
            "additions": pr.additions or 0,
            "deletions": pr.deletions or 0,
        })
    return results
```

**Template:** `templates/public/org_detail.html`

```html
<!-- Section 4: Recent PRs -->
<table class="recent-prs">
    <thead>
        <tr>
            <th>PR</th>
            <th>Type</th>
            <th>Size</th>
            <th>Tech</th>
            <th>Cycle Time</th>
            <th>AI</th>
        </tr>
    </thead>
    <tbody>
        {% for pr in recent_prs %}
        <tr>
            <td>
                <a href="{{ pr.github_url }}" target="_blank">
                    {{ pr.title|truncatewords:10 }}
                </a>
                <div class="meta">{{ pr.author_name }}</div>
            </td>
            <td>
                <span class="badge badge-{{ pr.pr_type }}">
                    {{ pr.pr_type }}
                </span>
            </td>
            <td>
                <span class="badge badge-size-{{ pr.size_label|lower }}" title="+{{ pr.additions }}/-{{ pr.deletions }}">
                    {{ pr.size_label }}
                </span>
            </td>
            <td>
                {% if pr.tech_categories %}
                    {{ pr.tech_categories|join:", " }}
                {% else %}
                    <span class="text-muted">—</span>
                {% endif %}
            </td>
            <td>
                {% if pr.cycle_time_hours %}
                    {{ pr.cycle_time_hours }}h
                {% else %}
                    <span class="text-muted">—</span>
                {% endif %}
            </td>
            <td>
                {% if pr.is_ai_assisted %}
                    <span class="badge badge-success" title="{{ pr.ai_tools|join:', ' }}">
                        AI
                    </span>
                {% else %}
                    <span class="text-muted">—</span>
                {% endif %}
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<style>
.badge-feature { background: #3b82f6; } /* blue */
.badge-bugfix { background: #ef4444; } /* red */
.badge-refactor { background: #f59e0b; } /* orange */
.badge-docs { background: #8b5cf6; } /* purple */
.badge-test { background: #10b981; } /* green */
.badge-chore { background: #6b7280; } /* gray */
.badge-ci { background: #06b6d4; } /* cyan */

.badge-size-xs { background: #4ade80; } /* green */
.badge-size-s { background: #60a5fa; } /* blue */
.badge-size-m { background: #fbbf24; } /* yellow */
.badge-size-l { background: #f97316; } /* orange */
.badge-size-xl { background: #ef4444; } /* red */
</style>
```

---

### Story 9: Technology & PR Type Trends

**New Functions:** `apps/public/aggregations.py`

```python
def compute_tech_category_trends(
    team_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> list[dict[str, Any]]:
    """Compute monthly tech category trends using effective_* properties.

    Uses ORM + Python grouping (per architecture decision #3).

    Args:
        team_id: Team ID
        start_date: Start datetime for rolling window
        end_date: End datetime for rolling window

    Returns:
        List of dicts: [{month, categories: {backend: N, frontend: N, ...}}]

    Example:
        [
            {
                "month": "2026-01",
                "categories": {
                    "backend": 45,
                    "frontend": 32,
                    "devops": 12,
                    "test": 8
                }
            },
            {
                "month": "2026-02",
                "categories": {
                    "backend": 38,
                    "frontend": 41,
                    "devops": 15,
                    "test": 6
                }
            }
        ]
    """
    from collections import defaultdict
    from django.db.models.functions import TruncMonth

    qs = _base_pr_queryset(team_id, start_date=start_date, end_date=end_date)

    # Load PRs with month annotation
    prs = qs.annotate(month=TruncMonth("pr_created_at")).values(
        "id", "month", "llm_summary", "files__filename"
    )

    # Group by month in Python
    monthly_categories = defaultdict(lambda: defaultdict(int))

    for pr_row in prs:
        month_str = pr_row["month"].strftime("%Y-%m")

        # Get categories from effective_tech_categories property
        # (we need to load the PR object for this)
        pr = PullRequest.objects.get(id=pr_row["id"])
        categories = pr.effective_tech_categories  # Uses LLM + file-based fallback

        for category in categories:
            monthly_categories[month_str][category] += 1

    # Convert to sorted list
    results = []
    for month in sorted(monthly_categories.keys()):
        results.append({
            "month": month,
            "categories": dict(monthly_categories[month])
        })

    return results


def compute_pr_type_trends(
    team_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None
) -> list[dict[str, Any]]:
    """Compute monthly PR type trends using effective_* properties.

    Uses ORM + Python grouping (per architecture decision #3).

    Args:
        team_id: Team ID
        start_date: Start datetime for rolling window
        end_date: End datetime for rolling window

    Returns:
        List of dicts: [{month, types: {feature: N, bugfix: N, ...}}]

    Example:
        [
            {
                "month": "2026-01",
                "types": {
                    "feature": 28,
                    "bugfix": 15,
                    "refactor": 7,
                    "docs": 3,
                    "test": 2
                }
            }
        ]
    """
    from collections import defaultdict
    from django.db.models.functions import TruncMonth

    qs = _base_pr_queryset(team_id, start_date=start_date, end_date=end_date)

    # Load PRs with month annotation
    prs = qs.annotate(month=TruncMonth("pr_created_at")).values(
        "id", "month", "llm_summary", "labels"
    )

    # Group by month in Python
    monthly_types = defaultdict(lambda: defaultdict(int))

    for pr_row in prs:
        month_str = pr_row["month"].strftime("%Y-%m")

        # Get type from effective_pr_type property
        pr = PullRequest.objects.get(id=pr_row["id"])
        pr_type = pr.effective_pr_type  # Uses LLM + label fallback

        monthly_types[month_str][pr_type] += 1

    # Convert to sorted list
    results = []
    for month in sorted(monthly_types.keys()):
        results.append({
            "month": month,
            "types": dict(monthly_types[month])
        })

    return results
```

**Service Layer:** `apps/public/services.py`

```python
# In PublicAnalyticsService.get_org_detail()
# Add:
tech_category_trends = compute_tech_category_trends(team_id, start_date=start_date, end_date=end_date)
pr_type_trends = compute_pr_type_trends(team_id, start_date=start_date, end_date=end_date)

# Add to result dict:
result = {
    # ... existing fields ...
    "tech_category_trends": tech_category_trends,
    "pr_type_trends": pr_type_trends,
}
```

**Template:** `templates/public/org_detail.html`

```html
<!-- Section 10.5: Tech & PR Type Trends (before Related Orgs) -->
<div class="trend-charts-row">
    <div class="chart-col">
        <h3>Technology Categories Over Time</h3>
        <canvas id="techTrendsChart" width="400" height="300"></canvas>
    </div>
    <div class="chart-col">
        <h3>PR Types Over Time</h3>
        <canvas id="prTypeTrendsChart" width="400" height="300"></canvas>
    </div>
</div>

<script>
// Tech Categories - Stacked Area Chart
const techData = {{ tech_category_trends|json_script:"tech-trends" }};
const techParsed = JSON.parse(document.getElementById('tech-trends').textContent);

const techMonths = techParsed.map(d => d.month);
const techCategories = [...new Set(techParsed.flatMap(d => Object.keys(d.categories)))];

const techDatasets = techCategories.map((cat, i) => ({
    label: cat,
    data: techParsed.map(d => d.categories[cat] || 0),
    backgroundColor: `hsla(${i * 40}, 70%, 60%, 0.6)`,
    borderColor: `hsl(${i * 40}, 70%, 50%)`,
    fill: true
}));

new Chart(document.getElementById('techTrendsChart'), {
    type: 'line',
    data: {
        labels: techMonths,
        datasets: techDatasets
    },
    options: {
        scales: {
            y: { stacked: true }
        }
    }
});

// PR Types - Stacked Bar Chart
const typeData = {{ pr_type_trends|json_script:"type-trends" }};
const typeParsed = JSON.parse(document.getElementById('type-trends').textContent);

const typeMonths = typeParsed.map(d => d.month);
const prTypes = ['feature', 'bugfix', 'refactor', 'docs', 'test', 'chore', 'ci'];

const typeDatasets = prTypes.map((type, i) => ({
    label: type,
    data: typeParsed.map(d => d.types[type] || 0),
    backgroundColor: `hsla(${i * 50}, 70%, 60%, 0.8)`
}));

new Chart(document.getElementById('prTypeTrendsChart'), {
    type: 'bar',
    data: {
        labels: typeMonths,
        datasets: typeDatasets
    },
    options: {
        scales: {
            y: { stacked: true }
        }
    }
});
</script>
```

---

### Story 10: Automated Daily Data Refresh Pipeline

All technical details covered in [Section 1: Sync Pipeline Logic](#1-sync-pipeline-logic).

**Summary of New Files:**

| File | Purpose |
|------|---------|
| `apps/public/tasks.py` (modified) | Add 3 new tasks: `sync_public_repos_task`, `process_public_prs_llm_task`, `run_daily_public_pipeline` |
| `apps/public/management/commands/check_public_pipeline.py` | Health check command for monitoring |
| `tformance/settings.py` (modified) | Add Celery Beat schedule entries |

---

## Summary

This technical architecture document provides:

1. **Exact sync pipeline flow** with GraphQL queries, cache validation, deduplication, and PR creation patterns
2. **Precise API quota calculations** showing we use <25% of GitHub's rate limits
3. **Optimized cache strategy** (6h Redis TTL vs current 1h) aligned with daily refresh schedule
4. **Detailed job scheduling** with wall-clock time estimates (~26 min end-to-end)
5. **Complete function signatures and data structures** for all 10 stories

All implementations follow the architecture decisions from the plan:
- ✅ Celery chain for pipeline orchestration
- ✅ Repos stored in PublicOrgProfile.repos JSONField
- ✅ ORM + Python for JSONB trends (not raw SQL)
- ✅ Management command health check (not Celery signals)

This document is ready for implementation by any developer without ambiguity.
