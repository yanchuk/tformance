# Demo Data Seeding - Context

**Last Updated:** 2025-12-20

## Overview

Enhanced demo data seeding system with scenario-based presets, hybrid GitHub/factory data sourcing, and deterministic reproducibility. Inspired by PostHog's `generate_demo_data` approach.

## Current Implementation State

**Phase 1: COMPLETE** - Foundation infrastructure created and tested.
**Phase 2: COMPLETE** - All 4 scenario implementations with 48 tests passing.

### Files Created

| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/seeding/__init__.py` | Package exports | Done |
| `apps/metrics/seeding/deterministic.py` | DeterministicRandom class | Done, 17 tests passing |
| `apps/metrics/seeding/scenarios/__init__.py` | Scenario exports + imports | Done |
| `apps/metrics/seeding/scenarios/base.py` | BaseScenario, ScenarioConfig, WeeklyParams, MemberArchetype | Done |
| `apps/metrics/seeding/scenarios/registry.py` | Scenario registry with decorator | Done |
| `apps/metrics/seeding/scenarios/ai_success.py` | AI adoption success scenario | Done |
| `apps/metrics/seeding/scenarios/review_bottleneck.py` | Review bottleneck scenario | Done |
| `apps/metrics/seeding/scenarios/baseline.py` | Steady-state baseline scenario | Done |
| `apps/metrics/seeding/scenarios/detective_game.py` | AI Detective game scenario | Done |
| `apps/metrics/tests/test_seeding/` | Test package | Done |
| `apps/metrics/tests/test_seeding/test_deterministic.py` | DeterministicRandom tests | Done, 17 tests |
| `apps/metrics/tests/test_seeding/test_scenarios.py` | Scenario tests | Done, 31 tests |

### Files To Create (Phase 3+)

| File | Purpose | Phase |
|------|---------|-------|
| `apps/metrics/seeding/github_fetcher.py` | Public repo PR fetcher | 3 |
| `apps/metrics/seeding/data_generator.py` | Main orchestrator | 4 |
| `apps/metrics/seeding/weekly_metrics_calculator.py` | Coherent aggregation | 4 |

### Files To Modify

| File | Changes | Phase |
|------|---------|-------|
| `apps/metrics/management/commands/seed_demo_data.py` | Add --scenario, --seed, --source-repo flags | 5 |

## Key Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | Hybrid (25% GitHub + 75% factory) | Realistic data without rate limits |
| Reproducibility | `--seed` flag with deterministic random | Consistent demos and testing |
| Scenario system | Class-based with `@register_scenario` decorator | Extensible, testable patterns |
| Backward compat | Legacy flags still work | No breaking changes |
| GitHub client | Unauthenticated PyGithub | 60 req/hour sufficient for seeding |
| Member behavior | MemberArchetype dataclass | Clean abstraction for team patterns |

## Dependencies

### Already Installed
- `PyGithub>=2.8.1` - GitHub API client
- `factory-boy>=3.3.0` - Test data factories

### No New Packages Required

## Models Affected

### Core Models (Always Seeded)
- `TeamMember` - Developer identities
- `PullRequest` - PRs with cycle_time_hours, review_time_hours
- `PRReview` - Review states (approved, changes_requested)
- `Commit` - Git commits

### Extended Models (Seeded if Exist)
- `PRCheckRun` - CI/CD status
- `PRFile` - Files changed in PRs
- `PRComment` - Issue and review comments (may not exist yet)

### Integration Models
- `JiraIssue` - Jira issues with story points
- `AIUsageDaily` - Copilot/Cursor usage

### Survey Models
- `PRSurvey` - Author AI disclosure
- `PRSurveyReview` - Reviewer guesses and quality ratings

### Aggregate Models
- `WeeklyMetrics` - Pre-computed weekly aggregates

## Scenario Definitions

### ai-success
- **Pattern**: Progressive AI adoption success story
- **AI Adoption**: 10% → 75% over 8 weeks
- **Cycle Time**: 72h → 24h (improving)
- **Quality**: 2.5 → 2.8 (maintained/improving)
- **Revert Rate**: 5% → 3% (improving)

### review-bottleneck
- **Pattern**: High AI output, bottlenecked reviews
- **AI Adoption**: Steady 70%
- **Cycle Time**: 36h → 60h (worsening)
- **Quality**: 2.8 → 2.2 (declining)
- **Key**: One reviewer handles 60% of all reviews

### baseline
- **Pattern**: Steady state, low AI adoption
- **AI Adoption**: Steady 15%
- **Cycle Time**: Steady 48h
- **Quality**: Steady 2.6
- **Use Case**: Reference for comparison dashboards

### detective-game
- **Pattern**: Survey engagement focus
- **Guess Accuracy**: 30-70% varied by archetype
- **Member Types**: obvious_ai, stealth_ai, obvious_manual, stealth_manual
- **Use Case**: Demonstrate AI Detective leaderboard

## Data Relationships

### Must Maintain Coherence
1. **WeeklyMetrics ↔ PRs**: `prs_merged` matches actual merged PR count
2. **PRSurvey ↔ AIUsageDaily**: AI disclosure correlates with usage records
3. **PRReview distribution**: Follows scenario's reviewer weights
4. **Temporal**: `merged_at > first_review_at > pr_created_at`

## GitHub Repos for Real Data

### Default Repos
- `yanchuk/github-issues-rag` - User's own project
- `tiangolo/fastapi` - Popular, well-structured PRs
- `pallets/flask` - Classic Python project

## Verification Commands

```bash
# Run seeding tests
.venv/bin/python manage.py test apps.metrics.tests.test_seeding --keepdb

# Verify imports work
.venv/bin/python -c "from apps.metrics.seeding import DeterministicRandom; print('OK')"

# Check lint
.venv/bin/ruff check apps/metrics/seeding/
```

## Next Session Handoff

**Continue with Phase 3**: Implement GitHub Fetcher

1. Create `apps/metrics/seeding/github_fetcher.py`
2. Use `PyGithub` (already installed) with unauthenticated client
3. Implement `FetchedPR` dataclass and `GitHubPublicFetcher` class
4. Add in-memory caching to avoid repeated API calls
5. Handle rate limiting gracefully (return empty list, log warning)

**All scenarios are implemented and tested:**
- `ai-success`: 10%→75% AI adoption, improving metrics
- `review-bottleneck`: 70% AI, worsening cycle times, one bottleneck reviewer
- `baseline`: 15% AI, steady metrics for comparison
- `detective-game`: 4 detectability archetypes for AI Detective feature

**Total test count: 48** (17 DeterministicRandom + 31 scenarios)

**Test command:**
```bash
.venv/bin/python manage.py test apps.metrics.tests.test_seeding --keepdb
```

**No uncommitted changes** - all Phase 1 & 2 work is saved to files.
**No migrations needed** - pure Python utility code.
