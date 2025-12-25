# Historical Data Sync for User Onboarding

## Executive Summary

When users connect their GitHub repositories during onboarding, we need to fetch and process historical PR data to populate their dashboards immediately. This creates the "aha moment" - users see real insights about their team within minutes of signing up.

**Key Goals:**
- Parse 12 months of history + beginning of earliest month in range
- Batch process PRs through Groq LLM for AI detection and summarization
- Show real-time progress with Celery progress bars (Pegasus pattern)
- Process all data before showing dashboard (onboarding gate)
- Multi-repo priority: start with most active repos first

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Onboarding Flow                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  1. User selects repos    2. Queue sync task     3. Background sync     │
│  ┌─────────────────┐      ┌─────────────────┐    ┌─────────────────┐    │
│  │ TrackedRepository│ ──▶ │ Celery Task     │ ──▶│ GraphQL Fetcher │    │
│  │ (sync_status:   │      │ sync_historical │    │ (10x faster)    │    │
│  │  pending)       │      │ _data_task      │    └────────┬────────┘    │
│  └─────────────────┘      └─────────────────┘             │              │
│                                                           ▼              │
│  4. Real-time progress    5. LLM batch processing  6. Dashboard ready  │
│  ┌─────────────────┐      ┌─────────────────┐    ┌─────────────────┐    │
│  │ celery_progress │ ◀─── │ GroqBatchProc   │ ◀──│ PRs saved to DB │    │
│  │ (JS polling)    │      │ (100 PR batches)│    │ with LLM summary│    │
│  └─────────────────┘      └─────────────────┘    └─────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Core Sync Infrastructure

### 1.1 Date Range Calculation

```python
def calculate_sync_date_range(months: int = 12) -> tuple[date, date]:
    """
    Calculate sync date range: 12 months + beginning of earliest month.

    Example: If today is Dec 25, 2025 and months=12:
    - End date: Dec 25, 2025
    - Start date: Jan 1, 2024 (12 months back, then to start of month)
    """
    end_date = date.today()
    # Go back N months
    start_date = end_date - relativedelta(months=months)
    # Extend to beginning of that month
    start_date = start_date.replace(day=1)
    return start_date, end_date
```

### 1.2 Repository Priority Ordering

Sort repos by PR activity in last 6 months to start with most valuable data:

```python
def prioritize_repositories(repos: list[TrackedRepository]) -> list[TrackedRepository]:
    """
    Order repos by PR count in last 6 months (descending).
    Most active repos first = faster time-to-value for user.
    """
    six_months_ago = timezone.now() - timedelta(days=180)

    # Annotate with recent PR count
    repos_with_counts = repos.annotate(
        recent_pr_count=Count(
            'pullrequest',
            filter=Q(pullrequest__pr_created_at__gte=six_months_ago)
        )
    ).order_by('-recent_pr_count')

    return list(repos_with_counts)
```

### 1.3 Sync Status Tracking

Leverage existing `TrackedRepository` fields:

| Field | Purpose |
|-------|---------|
| `sync_status` | pending → syncing → completed/failed |
| `sync_progress` | 0-100 percentage |
| `sync_prs_total` | Total PRs to process |
| `sync_prs_completed` | PRs processed so far |
| `sync_started_at` | When sync began |
| `last_synced_at` | When sync completed |

---

## Phase 2: Celery Task with Progress

### 2.1 Main Sync Task

```python
from celery import shared_task
from celery_progress.backend import ProgressRecorder

@shared_task(bind=True)
def sync_historical_data_task(self, team_id: int, repo_ids: list[int]):
    """
    Sync historical PR data for selected repositories.
    Reports progress in real-time via celery_progress.
    """
    progress_recorder = ProgressRecorder(self)

    repos = TrackedRepository.objects.filter(id__in=repo_ids)
    repos = prioritize_repositories(repos)

    total_repos = len(repos)

    for i, repo in enumerate(repos):
        # Update repo status
        repo.sync_status = 'syncing'
        repo.sync_started_at = timezone.now()
        repo.save()

        try:
            # Sync this repo
            sync_single_repository(
                repo=repo,
                progress_recorder=progress_recorder,
                repo_index=i,
                total_repos=total_repos,
            )

            repo.sync_status = 'completed'
            repo.last_synced_at = timezone.now()

        except Exception as e:
            repo.sync_status = 'failed'
            repo.sync_error = str(e)

        repo.save()

        # Emit signal
        historical_sync_repo_complete.send(
            sender=self.__class__,
            repo=repo,
            success=repo.sync_status == 'completed',
        )

    # Final signal
    historical_sync_complete.send(
        sender=self.__class__,
        team_id=team_id,
        repos=repos,
    )

    return {'status': 'complete', 'repos_synced': total_repos}
```

### 2.2 Progress Calculation

Multi-level progress: repos → PRs → LLM batches

```python
def calculate_overall_progress(
    repo_index: int,
    total_repos: int,
    prs_completed: int,
    prs_total: int,
) -> tuple[int, int, str]:
    """
    Calculate overall progress across all repos.
    Returns: (current, total, message)
    """
    # Each repo gets equal weight
    repo_weight = 100 / total_repos

    # Progress within current repo
    if prs_total > 0:
        repo_progress = (prs_completed / prs_total) * repo_weight
    else:
        repo_progress = 0

    # Completed repos + current progress
    overall = (repo_index * repo_weight) + repo_progress

    message = f"Processing {repo.name}: {prs_completed}/{prs_total} PRs"

    return int(overall), 100, message
```

---

## Phase 3: GraphQL Fetching with Batching

### 3.1 Adapt GitHubGraphQLFetcher

Reuse existing `GitHubGraphQLFetcher` with onboarding-specific settings:

```python
class OnboardingSyncService:
    """
    Orchestrates historical sync for onboarding.
    Uses existing GraphQL fetcher with batched LLM processing.
    """

    # Configurable settings
    HISTORY_MONTHS = 12
    LLM_BATCH_SIZE = 100
    GRAPHQL_PAGE_SIZE = 25  # Same as real_project_seeder

    def __init__(self, team: Team, github_token: str):
        self.team = team
        self.fetcher = GitHubGraphQLFetcher(github_token)
        self.groq_processor = GroqBatchProcessor()

    def sync_repository(
        self,
        repo: TrackedRepository,
        progress_callback: Callable[[int, int, str], None],
    ):
        """
        Sync a single repository with progress reporting.
        """
        start_date, end_date = calculate_sync_date_range(self.HISTORY_MONTHS)

        # Fetch PRs via GraphQL
        prs_data = self.fetcher.fetch_prs(
            org=repo.organization,
            repo=repo.name,
            since=start_date,
            page_size=self.GRAPHQL_PAGE_SIZE,
        )

        total_prs = len(prs_data)
        repo.sync_prs_total = total_prs
        repo.save()

        # Process in batches
        for batch_start in range(0, total_prs, self.LLM_BATCH_SIZE):
            batch_end = min(batch_start + self.LLM_BATCH_SIZE, total_prs)
            batch = prs_data[batch_start:batch_end]

            # Create PR records
            pr_objects = self._create_pr_records(batch, repo)

            # Send to Groq for LLM analysis
            self._process_llm_batch(pr_objects)

            # Update progress
            repo.sync_prs_completed = batch_end
            repo.sync_progress = int((batch_end / total_prs) * 100)
            repo.save()

            progress_callback(batch_end, total_prs, f"Processed {batch_end}/{total_prs} PRs")
```

### 3.2 LLM Batch Processing

```python
def _process_llm_batch(self, prs: list[PullRequest]):
    """
    Send batch to Groq for AI detection and summarization.
    Uses existing GroqBatchProcessor.
    """
    # Filter PRs with body text (needed for LLM)
    prs_with_body = [pr for pr in prs if pr.body]

    if not prs_with_body:
        return

    # Submit batch
    batch_id = self.groq_processor.submit_batch(prs_with_body)

    # Poll for completion (sync for onboarding, async for regular)
    while True:
        status = self.groq_processor.get_status(batch_id)
        if status.is_complete:
            break
        time.sleep(5)  # Poll every 5 seconds

    # Apply results
    results = self.groq_processor.get_results(batch_id)
    for result in results:
        pr = next((p for p in prs if p.id == result.pr_id), None)
        if pr:
            pr.is_ai_assisted = result.is_ai_assisted
            pr.ai_tools_detected = result.tools
            pr.llm_summary = result.llm_summary
            pr.llm_summary_version = result.prompt_version
            pr.save()
```

---

## Phase 4: Django Signals for Extensibility

### 4.1 Signal Definitions

```python
# apps/integrations/signals.py

from django.dispatch import Signal

# Fired when a single repo sync completes
historical_sync_repo_complete = Signal()
# Provides: repo, success

# Fired when all repos for a team are synced
historical_sync_complete = Signal()
# Provides: team_id, repos

# Fired when sync progress updates (every batch)
historical_sync_progress = Signal()
# Provides: team_id, repo, prs_completed, prs_total
```

### 4.2 Signal Handlers (Future)

```python
# apps/integrations/receivers.py

@receiver(historical_sync_complete)
def send_sync_complete_email(sender, team_id, repos, **kwargs):
    """Send email when historical sync finishes."""
    team = Team.objects.get(id=team_id)
    # TODO: Implement email sending
    pass

@receiver(historical_sync_complete)
def trigger_weekly_aggregation(sender, team_id, repos, **kwargs):
    """Trigger weekly metrics aggregation after sync."""
    from apps.metrics.tasks import aggregate_team_weekly_metrics
    aggregate_team_weekly_metrics.delay(team_id)
```

---

## Phase 5: Frontend Progress UI

### 5.1 Onboarding Sync Page Template

```html
{% extends "onboarding/base.html" %}
{% load static %}

{% block content %}
<div class="app-card max-w-2xl mx-auto">
  <h2 class="text-2xl font-bold text-base-content mb-4">
    Setting Up Your Dashboard
  </h2>

  <p class="text-base-content/80 mb-6">
    We're importing your team's PR history. This usually takes 2-5 minutes
    depending on your repository size.
  </p>

  <!-- Overall progress -->
  <div class="mb-8">
    <div class="flex justify-between text-sm mb-2">
      <span class="text-base-content/70">Overall Progress</span>
      <span id="progress-percent" class="font-mono text-primary">0%</span>
    </div>
    <div class="w-full bg-base-300 rounded-full h-3">
      <div id="progress-bar" class="bg-primary h-3 rounded-full transition-all duration-300"
           style="width: 0%"></div>
    </div>
    <p id="progress-message" class="text-sm text-base-content/70 mt-2">
      Preparing to sync...
    </p>
  </div>

  <!-- Repository status list -->
  <div class="space-y-3">
    {% for repo in repositories %}
    <div class="flex items-center justify-between p-3 bg-base-200 rounded-lg"
         id="repo-{{ repo.id }}">
      <div class="flex items-center gap-3">
        <span class="repo-status-icon">
          <span class="loading loading-spinner loading-sm text-base-content/50"></span>
        </span>
        <span class="text-base-content">{{ repo.name }}</span>
      </div>
      <span class="repo-status text-sm text-base-content/70">Waiting...</span>
    </div>
    {% endfor %}
  </div>

  <!-- CTA appears when complete -->
  <div id="complete-section" class="hidden mt-8 text-center">
    <div class="text-success text-5xl mb-4">✓</div>
    <h3 class="text-xl font-bold text-base-content mb-2">You're All Set!</h3>
    <p class="text-base-content/70 mb-6">
      We've imported <span id="pr-count" class="font-mono text-primary">0</span> PRs
      from your repositories.
    </p>
    <a href="{% url 'metrics:analytics_overview' team.slug %}"
       class="btn btn-primary">
      View Your Dashboard
    </a>
  </div>
</div>
{% endblock %}

{% block page_js %}
<script src="{% static 'celery_progress/celery_progress.js' %}"></script>
<script>
  const progressUrl = "{% url 'celery_progress:task_status' task_id %}";

  document.addEventListener("DOMContentLoaded", function() {
    CeleryProgressBar.initProgressBar(progressUrl, {
      onProgress: function(progressBarEl, messageEl, progress) {
        // Update progress bar
        document.getElementById('progress-bar').style.width = progress.percent + '%';
        document.getElementById('progress-percent').textContent = progress.percent + '%';
        document.getElementById('progress-message').textContent = progress.description;

        // Update repo statuses from progress.info if available
        if (progress.info && progress.info.repos) {
          updateRepoStatuses(progress.info.repos);
        }
      },
      onSuccess: function(progressBarEl, messageEl, result) {
        // Show completion UI
        document.getElementById('complete-section').classList.remove('hidden');
        document.getElementById('pr-count').textContent = result.total_prs || 0;
      },
      onError: function(progressBarEl, messageEl, error) {
        const msgEl = document.getElementById('progress-message');
        msgEl.textContent = 'An error occurred. Please try again or contact support.';
        msgEl.classList.add('text-error');
      }
    });
  });

  function updateRepoStatuses(repos) {
    repos.forEach(function(repo) {
      const el = document.getElementById('repo-' + repo.id);
      if (!el) return;

      const statusEl = el.querySelector('.repo-status');
      const iconEl = el.querySelector('.repo-status-icon');

      // Clear existing content safely
      while (iconEl.firstChild) {
        iconEl.removeChild(iconEl.firstChild);
      }

      if (repo.status === 'completed') {
        const checkmark = document.createElement('span');
        checkmark.className = 'text-success';
        checkmark.textContent = '✓';
        iconEl.appendChild(checkmark);
        statusEl.textContent = repo.pr_count + ' PRs';
        statusEl.classList.add('text-success');
      } else if (repo.status === 'syncing') {
        const spinner = document.createElement('span');
        spinner.className = 'loading loading-spinner loading-sm text-primary';
        iconEl.appendChild(spinner);
        statusEl.textContent = repo.progress + '%';
      } else if (repo.status === 'failed') {
        const errorMark = document.createElement('span');
        errorMark.className = 'text-error';
        errorMark.textContent = '✗';
        iconEl.appendChild(errorMark);
        statusEl.textContent = 'Failed';
        statusEl.classList.add('text-error');
      }
    });
  }
</script>
{% endblock %}
```

---

## Time Estimates

Based on analysis of recent parsing logs and existing infrastructure:

| Phase | Tasks | Estimate |
|-------|-------|----------|
| **Phase 1** | Date range, repo priority, status tracking | 2-3 hours |
| **Phase 2** | Celery task with progress recording | 3-4 hours |
| **Phase 3** | OnboardingSyncService, adapt fetcher | 4-5 hours |
| **Phase 4** | Django signals | 1-2 hours |
| **Phase 5** | Frontend progress UI | 3-4 hours |
| **Testing** | Unit tests, integration tests | 4-5 hours |
| **Edge cases** | Error handling, retries, rate limits | 2-3 hours |
| **Total** | **~20-26 hours** (~3-4 days focused work) |

### Parsing Time Estimates (from logs)

Based on `real_project_seeder.py` logs:
- GraphQL fetch: ~25 PRs/page, ~1-2 seconds per page
- Groq batch processing: ~100 PRs in 30-60 seconds
- DB writes: ~100 PRs in 1-2 seconds

**For a typical team (500 PRs, 3 repos):**
- GraphQL fetching: ~40 seconds
- LLM processing: ~5 minutes (5 batches x 60s)
- DB writes: ~10 seconds
- **Total: ~6 minutes**

**For a large team (2000 PRs, 10 repos):**
- GraphQL fetching: ~3 minutes
- LLM processing: ~20 minutes (20 batches x 60s)
- DB writes: ~40 seconds
- **Total: ~25 minutes**

---

## Configuration

### Settings (configurable via env/settings)

```python
# tformance/settings.py

HISTORICAL_SYNC_CONFIG = {
    'HISTORY_MONTHS': int(os.getenv('SYNC_HISTORY_MONTHS', 12)),
    'LLM_BATCH_SIZE': int(os.getenv('SYNC_LLM_BATCH_SIZE', 100)),
    'GRAPHQL_PAGE_SIZE': 25,  # Optimal for GitHub API
    'MAX_RETRIES': 3,
    'RETRY_DELAY_SECONDS': 30,
    'GROQ_POLL_INTERVAL': 5,  # seconds
}
```

---

## Success Criteria

1. **User sees dashboard within 10 minutes** of completing onboarding (for typical team)
2. **Real-time progress** updates every 5 seconds
3. **All 12 months** of history available on first dashboard load
4. **AI detection** works for all PRs with body text
5. **Graceful degradation** if Groq API is unavailable (PRs still saved, LLM processing queued)
6. **Signals enable** future extensibility (emails, Slack notifications)

---

## Dependencies

| Component | Status | Notes |
|-----------|--------|-------|
| `GitHubGraphQLFetcher` | ✅ Ready | Proven in seeding |
| `GroqBatchProcessor` | ✅ Ready | v5/v6 prompts working |
| `celery_progress` | ✅ Installed | Pegasus example works |
| `TrackedRepository` fields | ✅ Ready | Sync tracking fields exist |
| Onboarding views | 🔄 Needs update | Add sync step after repo selection |
