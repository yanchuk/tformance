# PR Iteration Metrics & GitHub Analytics - Implementation Plan

**Last Updated:** 2025-12-20

## Executive Summary

Implement comprehensive PR iteration tracking and GitHub analytics to enable analysis of code review cycles, CI/CD performance, deployment patterns, and review correlations. This extends the existing GitHub integration to provide deep insights into team productivity and AI impact.

### Business Value

- **CTOs can see:** Review efficiency, CI pass rates, deploy frequency, reviewer correlations
- **Leads can identify:** Bottlenecks, redundant reviews, slow CI pipelines
- **Teams can optimize:** Review turnaround, iteration efficiency, deployment practices
- **AI Correlation:** "AI-assisted PRs have X% higher CI pass rate"

---

## Current State Analysis

### What We Have

| Component | Status | Notes |
|-----------|--------|-------|
| `PullRequest` model | Complete | `cycle_time_hours`, `review_time_hours`, `first_review_at` |
| `PRReview` model | Complete | `state`, `submitted_at`, `reviewer` FK |
| `Commit` model | Exists | Schema ready, **not synced** |
| OAuth scopes | Sufficient | `repo` scope covers all needed APIs |
| Webhook events | Active | `pull_request`, `pull_request_review` |

### What's Missing

| Component | Status | Needed For |
|-----------|--------|------------|
| `PRComment` model | Missing | Comment tracking, response time |
| `PRCheckRun` model | Missing | CI/CD status tracking |
| `PRFile` model | Missing | File-type analysis, review correlations |
| `Deployment` model | Missing | Deploy frequency, DORA metrics |
| Commit sync | Not implemented | Iteration detection |
| CI/CD sync | Not implemented | Build success correlation |

---

## Implementation Phases Overview

| Phase | Focus | Effort | Priority |
|-------|-------|--------|----------|
| 1 | Commit Sync | M | High |
| 2 | Comment Model & Sync | M | High |
| 3 | Iteration Metrics | M | High |
| 4 | CI/CD Check Runs | M | Very High |
| 5 | PR Files & Categories | S | Medium |
| 6 | Deployments | S | High |
| 7 | Review Correlations | M | Medium |
| 8 | Dashboard Integration | M | High |

---

## Phase 1: Commit Sync (Foundation)

**Goal:** Populate the existing `Commit` model with PR commit data

### Tasks

#### 1.1 Add Commit Sync Function
- Implement `sync_pr_commits()` in `github_sync.py`
- Fetch via `pr.get_commits()`
- Create/update `Commit` records
- Link to PullRequest FK
- **Effort:** M

#### 1.2 Integrate into Sync Pipeline
- Call in `_process_prs()`
- Update sync stats with `commits_synced`
- **Effort:** S

#### 1.3 Tests
- TDD tests for commit sync
- **Effort:** M

---

## Phase 2: Comment Model & Sync

**Goal:** Track PR comments for discussion analysis

### Tasks

#### 2.1 Create PRComment Model
```python
class PRComment(BaseTeamModel):
    github_comment_id = BigIntegerField()
    pull_request = ForeignKey(PullRequest)
    author = ForeignKey(TeamMember, null=True)
    body = TextField()
    comment_type = CharField()  # "issue" or "review"
    # Review comment specific
    path = CharField(null=True)  # File path
    line = IntegerField(null=True)
    in_reply_to_id = BigIntegerField(null=True)
    # Timestamps
    comment_created_at = DateTimeField()
    comment_updated_at = DateTimeField(null=True)
```
- **Effort:** S

#### 2.2 Comment Sync Functions
- `sync_pr_issue_comments()`
- `sync_pr_review_comments()`
- **Effort:** M

#### 2.3 Tests
- **Effort:** M

---

## Phase 3: Iteration Metrics Calculation

**Goal:** Derive review rounds, fix response times

### Tasks

#### 3.1 Add Fields to PullRequest
```python
# New fields
review_rounds = IntegerField(null=True)
avg_fix_response_hours = DecimalField(null=True)
commits_after_first_review = IntegerField(null=True)
total_comments = IntegerField(null=True)
```
- **Effort:** S

#### 3.2 Review Round Detection
- Count changes_requested → commits → re-review cycles
- **Effort:** M

#### 3.3 Fix Response Time
- Time from review to next commit
- **Effort:** M

#### 3.4 Tests
- **Effort:** M

---

## Phase 4: CI/CD Check Runs (High Value)

**Goal:** Track CI pass/fail rates, correlate with AI usage

### Tasks

#### 4.1 Create PRCheckRun Model
```python
class PRCheckRun(BaseTeamModel):
    """CI/CD check run for a pull request."""
    github_check_run_id = BigIntegerField()
    pull_request = ForeignKey(PullRequest)
    name = CharField(max_length=255)  # "pytest", "eslint", "build"
    status = CharField()  # "queued", "in_progress", "completed"
    conclusion = CharField(null=True)  # "success", "failure", "skipped", "cancelled"
    started_at = DateTimeField(null=True)
    completed_at = DateTimeField(null=True)
    # Calculated
    duration_seconds = IntegerField(null=True)
```
- **Effort:** S

#### 4.2 Create Migration
- **Effort:** S

#### 4.3 Add Check Run Sync Function
```python
def sync_pr_check_runs(pr, github_pr, team):
    """Sync CI/CD check runs for a PR."""
    # Get the head commit
    head_sha = github_pr.head.sha
    commit = repo.get_commit(head_sha)
    check_runs = commit.get_check_runs()

    for check in check_runs:
        PRCheckRun.objects.update_or_create(
            team=team,
            github_check_run_id=check.id,
            defaults={
                'pull_request': pr,
                'name': check.name,
                'status': check.status,
                'conclusion': check.conclusion,
                'started_at': check.started_at,
                'completed_at': check.completed_at,
                'duration_seconds': calculate_duration(check),
            }
        )
```
- **Effort:** M

#### 4.4 Add CI Metrics to PullRequest
```python
# New fields on PullRequest
ci_status = CharField(null=True)  # "success", "failure", "pending"
ci_duration_seconds = IntegerField(null=True)
ci_passed_count = IntegerField(default=0)
ci_failed_count = IntegerField(default=0)
```
- **Effort:** S

#### 4.5 Integrate into Sync Pipeline
- **Effort:** S

#### 4.6 Tests
- **Effort:** M

---

## Phase 5: PR Files & Categories

**Goal:** Track files changed, enable file-type analysis

### Tasks

#### 5.1 Create PRFile Model
```python
class PRFile(BaseTeamModel):
    """File changed in a pull request."""
    pull_request = ForeignKey(PullRequest)
    filename = CharField(max_length=500)
    status = CharField()  # "added", "modified", "removed", "renamed"
    additions = IntegerField(default=0)
    deletions = IntegerField(default=0)
    changes = IntegerField(default=0)
    # Derived category
    file_category = CharField(max_length=50)  # "frontend", "backend", "test", "config", "docs"

    @staticmethod
    def categorize_file(filename):
        if filename.endswith(('.tsx', '.jsx', '.vue', '.css', '.scss', '.html')):
            return 'frontend'
        elif filename.endswith(('.py', '.go', '.java', '.rb', '.rs')):
            return 'backend'
        elif 'test' in filename.lower() or 'spec' in filename.lower():
            return 'test'
        elif filename.endswith(('.md', '.rst', '.txt')):
            return 'docs'
        elif filename.endswith(('.json', '.yaml', '.yml', '.toml', '.ini', '.env')):
            return 'config'
        return 'other'
```
- **Effort:** S

#### 5.2 File Sync Function
```python
def sync_pr_files(pr, github_pr, team):
    files = github_pr.get_files()
    for file in files:
        PRFile.objects.update_or_create(
            team=team,
            pull_request=pr,
            filename=file.filename,
            defaults={
                'status': file.status,
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'file_category': PRFile.categorize_file(file.filename),
            }
        )
```
- **Effort:** S

#### 5.3 Add Category Summary to PullRequest
```python
# New fields
primary_category = CharField(null=True)  # Most changed category
files_changed_count = IntegerField(default=0)
```
- **Effort:** S

#### 5.4 Tests
- **Effort:** S

---

## Phase 6: Deployments

**Goal:** Track deploy frequency, DORA metrics

### Tasks

#### 6.1 Create Deployment Model
```python
class Deployment(BaseTeamModel):
    """Deployment from GitHub."""
    github_deployment_id = BigIntegerField()
    github_repo = CharField(max_length=255)
    environment = CharField(max_length=100)  # "production", "staging"
    status = CharField()  # "success", "failure", "pending", "error"
    creator = ForeignKey(TeamMember, null=True)
    deployed_at = DateTimeField()
    # Link to PR if available
    pull_request = ForeignKey(PullRequest, null=True)
    sha = CharField(max_length=40)
```
- **Effort:** S

#### 6.2 Deployment Sync Function
```python
def sync_repository_deployments(tracked_repo):
    deployments = repo.get_deployments()
    for deploy in deployments:
        # Get latest status
        statuses = list(deploy.get_statuses())
        latest_status = statuses[0] if statuses else None

        Deployment.objects.update_or_create(
            team=team,
            github_deployment_id=deploy.id,
            defaults={
                'github_repo': tracked_repo.full_name,
                'environment': deploy.environment,
                'status': latest_status.state if latest_status else 'pending',
                'creator': get_team_member(deploy.creator),
                'deployed_at': deploy.created_at,
                'sha': deploy.sha,
            }
        )
```
- **Effort:** M

#### 6.3 Calculate DORA Metrics
```python
def calculate_dora_metrics(team, days=30):
    """Calculate DORA deployment metrics."""
    deployments = Deployment.for_team.filter(
        environment='production',
        status='success',
        deployed_at__gte=timezone.now() - timedelta(days=days)
    )
    return {
        'deploy_frequency': deployments.count() / days,  # Deploys per day
        'total_deployments': deployments.count(),
        'failure_rate': calculate_failure_rate(team, days),
    }
```
- **Effort:** S

#### 6.4 Tests
- **Effort:** M

---

## Phase 7: Review Correlations

**Goal:** Analyze reviewer agreement patterns

### Tasks

#### 7.1 Create ReviewerCorrelation Model
```python
class ReviewerCorrelation(BaseTeamModel):
    """Cached reviewer agreement statistics."""
    reviewer_a = ForeignKey(TeamMember, related_name='correlations_as_a')
    reviewer_b = ForeignKey(TeamMember, related_name='correlations_as_b')
    # Stats
    prs_reviewed_together = IntegerField(default=0)
    both_approved = IntegerField(default=0)
    both_rejected = IntegerField(default=0)
    disagreed = IntegerField(default=0)
    agreement_rate = DecimalField(null=True)
    # Time patterns
    avg_time_between_reviews_hours = DecimalField(null=True)
    # Period
    period_start = DateField()
    period_end = DateField()
```
- **Effort:** S

#### 7.2 Correlation Calculation Service
```python
def calculate_reviewer_correlations(team, period_days=90):
    """Calculate reviewer agreement rates."""
    # Find all PRs with 2+ reviews
    prs_with_multiple_reviews = PullRequest.for_team.annotate(
        review_count=Count('reviews')
    ).filter(review_count__gte=2)

    # Build correlation matrix
    correlations = defaultdict(lambda: {
        'together': 0, 'agreed': 0, 'disagreed': 0
    })

    for pr in prs_with_multiple_reviews:
        reviews = list(pr.reviews.all())
        for i, r1 in enumerate(reviews):
            for r2 in reviews[i+1:]:
                pair = tuple(sorted([r1.reviewer_id, r2.reviewer_id]))
                correlations[pair]['together'] += 1
                if r1.state == r2.state:
                    correlations[pair]['agreed'] += 1
                else:
                    correlations[pair]['disagreed'] += 1

    return correlations
```
- **Effort:** M

#### 7.3 Redundancy Detection
```python
def find_potentially_redundant_reviewers(team):
    """Find reviewer pairs that almost always agree."""
    correlations = ReviewerCorrelation.for_team.filter(
        agreement_rate__gte=0.95,
        prs_reviewed_together__gte=10
    )
    return correlations
```
- **Effort:** S

#### 7.4 Tests
- **Effort:** M

---

## Phase 8: Dashboard Integration

**Goal:** Surface all metrics in the UI

### Tasks

#### 8.1 CI/CD Dashboard Section
- CI pass rate card
- CI pass rate by AI-assisted vs not
- Failed checks breakdown
- CI duration trends
- **Effort:** M

#### 8.2 Deployment Dashboard Section
- Deploy frequency card (DORA)
- Deployments per week chart
- Environment breakdown
- **Effort:** S

#### 8.3 Review Correlation Dashboard
- Reviewer agreement matrix
- Redundancy alerts
- Time between reviews chart
- **Effort:** M

#### 8.4 Iteration Metrics Dashboard
- Review rounds card
- Fix response time card
- Trends over time
- **Effort:** S

#### 8.5 File Category Analysis
- PRs by category
- Metrics breakdown by frontend/backend/test
- **Effort:** S

---

## Data Model Summary

### New Models

| Model | Purpose |
|-------|---------|
| `PRComment` | PR comments (issue + review) |
| `PRCheckRun` | CI/CD check run results |
| `PRFile` | Files changed in PRs |
| `Deployment` | GitHub deployments |
| `ReviewerCorrelation` | Cached reviewer stats |

### PullRequest Extensions

```python
# Iteration metrics
review_rounds = IntegerField(null=True)
avg_fix_response_hours = DecimalField(null=True)
commits_after_first_review = IntegerField(null=True)
total_comments = IntegerField(null=True)

# CI/CD metrics
ci_status = CharField(null=True)
ci_duration_seconds = IntegerField(null=True)
ci_passed_count = IntegerField(default=0)
ci_failed_count = IntegerField(default=0)

# File metrics
primary_category = CharField(null=True)
files_changed_count = IntegerField(default=0)
```

---

## API Coverage (No New Scopes Needed)

All data accessible with existing `repo` scope:

| API | PyGithub Method |
|-----|-----------------|
| Commits | `pr.get_commits()` |
| Issue comments | `pr.get_issue_comments()` |
| Review comments | `pr.get_review_comments()` |
| Check runs | `commit.get_check_runs()` |
| Files | `pr.get_files()` |
| Deployments | `repo.get_deployments()` |

---

## Implementation Order

```
Phase 1 (Commits) ──────────────────────┐
                                        │
Phase 2 (Comments) ─────────────────────┼──→ Phase 3 (Iteration Metrics)
                                        │
Phase 4 (CI/CD) ────────────────────────┤
                                        │
Phase 5 (Files) ────────────────────────┼──→ Phase 7 (Review Correlations)
                                        │
Phase 6 (Deployments) ──────────────────┘
                                        │
                                        ▼
                              Phase 8 (Dashboard)
```

---

## Phase 9: Update Real-Life Testing Guide

**Goal:** Update `dev/guides/REAL-WORLD-TESTING.md` with new sync features

### Tasks

#### 9.1 Add Sync Testing Section
- Document how to verify commit sync is working
- Document how to verify check runs sync
- Document how to verify file sync
- Document how to verify deployments sync
- Document how to verify comments sync

#### 9.2 Add Database Verification Steps
```sql
-- Verify commits synced
SELECT COUNT(*) FROM metrics_commit WHERE team_id = :team_id;

-- Verify check runs synced
SELECT COUNT(*) FROM metrics_prcheckrun WHERE team_id = :team_id;

-- Verify files synced (when implemented)
SELECT COUNT(*) FROM metrics_prfile WHERE team_id = :team_id;
```

#### 9.3 Update Testing Progress Table
- Add rows for each new sync feature
- Document verification dates

**Effort:** S

---

## Effort Summary

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1: Commits | M | High |
| Phase 2: Comments | M | High |
| Phase 3: Iteration Metrics | M | High |
| Phase 4: CI/CD | M | Very High |
| Phase 5: Files | S | Medium |
| Phase 6: Deployments | S | High |
| Phase 7: Correlations | M | Medium |
| Phase 8: Dashboard | M | High |
| Phase 9: Testing Guide | S | Medium |
| **Total** | **L** | - |

---

## Key Insights This Enables

1. **"AI-assisted PRs have 15% higher CI pass rate"**
2. **"Alice and Bob agree 97% of time - consider single reviewer for routine PRs"**
3. **"Frontend PRs take 2x longer to get first review than backend"**
4. **"Deploy frequency increased 40% since adopting AI tools"**
5. **"Average fix response time is 4 hours after changes requested"**
