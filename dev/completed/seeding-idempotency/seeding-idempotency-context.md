# Seeding Idempotency Context

**Last Updated: 2025-12-25**

## Key Files

### Primary Seeder
- `apps/metrics/seeding/real_project_seeder.py` - Main orchestrator for seeding

### Simulators (Already Fixed)
- `apps/metrics/seeding/jira_simulator.py` - Jira issue simulation
- `apps/metrics/seeding/survey_ai_simulator.py` - Surveys and AI usage simulation

### Models with Unique Constraints
- `PRReview` - Constraint: `unique_team_pr_review` on `(team, pull_request, github_review_id)`
- `PRFile` - Constraint: `unique_pr_file` on `(pull_request, filename)`

### Factory Files
- `apps/metrics/factories.py` - Factory definitions

## Key Decisions

### Pattern Selection

| Model | Pattern | Reason |
|-------|---------|--------|
| GitHub-sourced (PR, Review, Commit, File) | Skip if exists | Data from GitHub shouldn't change |
| Simulated (Jira, Survey, AI Usage) | update_or_create | Simulation parameters may evolve |

### Unique Constraint Fields

| Model | Lookup Fields |
|-------|---------------|
| PRReview | `team`, `pull_request`, `github_review_id` |
| PRFile | `pull_request`, `filename` |

## Dependencies

- No external dependencies
- Uses existing Django ORM patterns
- Factory Boy for test fixtures only

## Error Examples (Before Fix)

```
IntegrityError: duplicate key value violates unique constraint "unique_team_pr_review"
DETAIL: Key (team_id, pull_request_id, github_review_id)=(1, 100, 12345) already exists.

IntegrityError: duplicate key value violates unique constraint "unique_pr_file"
DETAIL: Key (pull_request_id, filename)=(100, "src/app.py") already exists.
```

## Test Files

- `apps/metrics/tests/test_real_project_seeder.py` - If exists
- `apps/metrics/seeding/tests/` - Seeding-specific tests
