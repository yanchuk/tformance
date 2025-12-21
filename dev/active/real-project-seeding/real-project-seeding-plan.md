# Real Open Source Project Demo Data Seeding

**Last Updated:** 2025-12-21

## Executive Summary

Create a system to seed realistic demo data from real open source GitHub projects (PostHog, Polar.sh, FastAPI) into separate teams. Real GitHub data (PRs, commits, reviews, files) will be fetched via authenticated GitHub API, while Jira issues, Slack surveys, and AI usage will be simulated using probabilistic heuristics.

This enables realistic product demos using real-world data patterns from well-known projects.

---

## Current State Analysis

### Existing Seeding Infrastructure
- **`seed_demo_data` command**: Scenario-based seeding with 4 predefined scenarios
- **`GitHubPublicFetcher`**: Unauthenticated fetcher (60 req/hour) for basic PR metadata
- **`ScenarioDataGenerator`**: Orchestrates coherent data generation across all models
- **Factories**: Complete set for all metrics models (PullRequest, PRReview, Commit, etc.)
- **`DeterministicRandom`**: Reproducible random generation with seeds

### Limitations
- Current fetcher only gets basic PR metadata (title, additions, deletions)
- No commits, reviews, files, or check runs fetched
- 60 req/hour rate limit insufficient for large repos
- No real contributor mapping to TeamMembers

---

## Proposed Future State

### New Capabilities
1. **Authenticated GitHub Fetcher** (5000 req/hour) with full PR details
2. **Project Configuration Registry** for PostHog, Polar, FastAPI
3. **Jira Simulator** - extract keys from PR titles or generate synthetic
4. **Survey/AI Simulator** - probabilistic AI detection based on PR characteristics
5. **Real Project Seeder** - orchestrates complete team creation from GitHub data
6. **Management Command** - `seed_real_projects` with project selection

### Architecture

```
seed_real_projects command
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                    RealProjectSeeder                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ GitHub       │  │ Jira         │  │ Survey/AI        │  │
│  │ Fetcher      │  │ Simulator    │  │ Simulator        │  │
│  │ (PAT auth)   │  │ (from PRs)   │  │ (heuristics)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
   Database Models (TeamMember, PR, Review, Commit, JiraIssue, etc.)
```

---

## Implementation Phases

### Phase 1: Authenticated GitHub Fetcher (Effort: L)
**File:** `apps/metrics/seeding/github_authenticated_fetcher.py`

Create enhanced fetcher with authenticated access:
- Uses `GITHUB_SEEDING_TOKEN` environment variable
- 5000 requests/hour rate limit
- Fetches complete PR data including commits, reviews, files, check runs
- Rate limit tracking and logging
- `get_top_contributors()` for team member creation

**Dataclasses:**
- `FetchedPRFull`: Complete PR with all related data
- `FetchedCommit`, `FetchedReview`, `FetchedFile`, `FetchedCheckRun`
- `ContributorInfo`: GitHub user data for TeamMember creation

### Phase 2: Project Configuration (Effort: S)
**File:** `apps/metrics/seeding/real_projects.py`

Define target projects with configuration:
```python
@dataclass
class RealProjectConfig:
    repo_full_name: str       # "posthog/posthog"
    team_name: str            # "PostHog Analytics"
    team_slug: str            # "posthog-demo"
    max_prs: int = 500
    max_members: int = 15
    days_back: int = 90
    jira_project_key: str     # "POST"
    ai_base_adoption_rate: float = 0.35
```

**Configured Projects:**
| Project | Repo | Team Slug | Max PRs | Max Members |
|---------|------|-----------|---------|-------------|
| PostHog | posthog/posthog | posthog-demo | 500 | 15 |
| Polar.sh | polarsource/polar | polar-demo | 300 | 10 |
| FastAPI | tiangolo/fastapi | fastapi-demo | 300 | 12 |

### Phase 3: Jira Simulator (Effort: M)
**File:** `apps/metrics/seeding/jira_simulator.py`

Simulate Jira issues from PR data:
1. **Extract existing keys** from PR titles/branches (regex: `[A-Z]+-\d+`)
2. **Generate synthetic keys** for PRs without references
3. **Estimate story points** from PR size (lines changed)
4. **Simulate sprints** based on PR dates (2-week sprints)
5. **Set issue status** based on PR state (Done if merged)

**Story Point Estimation:**
| Lines Changed | Story Points |
|---------------|--------------|
| < 50 | 1 |
| 50-150 | 2 |
| 150-400 | 3 |
| 400-800 | 5 |
| > 800 | 8 |

### Phase 4: Survey/AI Simulator (Effort: M)
**File:** `apps/metrics/seeding/survey_ai_simulator.py`

Simulate AI usage and survey responses:

**AI-Assisted Probability Calculation:**
```python
probability = base_rate  # e.g., 0.35
if total_lines > 300:
    probability += 0.15
if code_files > 5:
    probability += 0.10
probability = min(0.85, probability)
```

**Survey Response Generation:**
- Author disclosure: Based on AI-assisted flag
- Reviewer guesses: 60-75% accuracy
- Quality ratings: Skewed positive (1-3 scale)

**AIUsageDaily Records:**
- 3-5 days per week per member
- Copilot (80%) vs Cursor (20%) split
- Suggestions shown/accepted based on base adoption rate

### Phase 5: Seeder Orchestrator (Effort: L)
**File:** `apps/metrics/seeding/real_project_seeder.py`

Main orchestration class:

```python
class RealProjectSeeder:
    def seed(self) -> RealProjectStats:
        # 1. Create/get team
        team = self._get_or_create_team()

        # 2. Fetch top contributors → TeamMembers
        contributors = self._fetcher.get_top_contributors(...)
        members_map = self._create_team_members(team, contributors)

        # 3. Fetch PRs with details (last 90 days)
        prs_data = self._fetcher.fetch_prs_with_details(...)

        # 4. Create PRs with all related entities
        for pr_data in prs_data:
            self._create_pr_with_related(team, pr_data, members_map)

        # 5. Generate simulated data
        self._simulate_jira_issues(team)
        self._simulate_surveys(team)
        self._generate_ai_usage(team)

        # 6. Calculate WeeklyMetrics
        self._calculate_weekly_metrics(team)

        return self._stats
```

### Phase 6: Management Command (Effort: S)
**File:** `apps/metrics/management/commands/seed_real_projects.py`

```bash
# Seed all projects
python manage.py seed_real_projects

# Seed specific project
python manage.py seed_real_projects --project posthog

# List available projects
python manage.py seed_real_projects --list-projects

# Clear and reseed
python manage.py seed_real_projects --project polar --clear

# Custom options
python manage.py seed_real_projects --max-prs 200 --days-back 60 --seed 42
```

### Phase 7: Testing & Documentation (Effort: M)
- Unit tests for each simulator class
- Integration test for full seeding flow
- Update `dev/DEV-ENVIRONMENT.md` with usage docs
- Add `GITHUB_SEEDING_TOKEN` to `.env.example`

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| GitHub rate limit exceeded | High | Track remaining requests, pause when low, cache results |
| Large repos slow to fetch | Medium | Limit to 90 days, max 500 PRs, progress logging |
| Missing contributor data | Low | Fall back to username-only TeamMember creation |
| API schema changes | Low | Use stable PyGithub library, handle exceptions gracefully |

---

## Success Metrics

- [ ] Successfully seed 3 real projects (PostHog, Polar, FastAPI)
- [ ] Each team has 10-15 members from real contributors
- [ ] 300-500 PRs per project with full details
- [ ] Simulated Jira issues match PR count
- [ ] Survey response rate ~60%
- [ ] AI usage records for 80% of members
- [ ] WeeklyMetrics calculated correctly
- [ ] Command completes in < 10 minutes per project

---

## Dependencies

- **PyGithub**: Already installed, used for GitHub API
- **GitHub PAT**: User must create with `public_repo` scope
- **Existing factories**: All model factories already exist
- **DeterministicRandom**: Existing utility for reproducible seeding
