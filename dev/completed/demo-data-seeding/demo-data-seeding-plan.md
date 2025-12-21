# Enhanced Demo Data Seeding System - Plan

**Last Updated:** 2025-12-20

## Executive Summary

Create a comprehensive demo data seeding system inspired by PostHog's approach, featuring:
- **Hybrid data sourcing**: 20-30% real PR metadata from public GitHub repos + factory-generated data
- **4 scenario presets**: ai-success, review-bottleneck, baseline, detective-game
- **Deterministic seeding**: `--seed` flag for reproducible data generation
- **Backward compatible**: Existing `seed_demo_data` command behavior preserved

## Current State

The existing `seed_demo_data` command:
- Creates basic randomized data (teams, members, PRs, reviews, etc.)
- Uses hash-based pseudo-determinism (not truly reproducible)
- No scenario-based patterns
- No GitHub integration for realistic data
- All data is random with no coherent narratives

## Proposed Future State

### File Structure

```
apps/metrics/
  seeding/
    __init__.py
    deterministic.py              # Seedable random utilities
    github_fetcher.py             # Public repo PR fetcher
    data_generator.py             # Main generation orchestrator
    weekly_metrics_calculator.py  # Coherent weekly aggregation
    scenarios/
      __init__.py
      base.py                     # BaseScenario abstract class
      ai_success.py               # AI adoption success story
      review_bottleneck.py        # Review bottleneck scenario
      baseline.py                 # Steady-state comparison
      detective_game.py           # Survey/leaderboard focus
      registry.py                 # Scenario lookup
  management/commands/
    seed_demo_data.py             # Enhanced (backward compatible)
```

### Scenarios

| Scenario | Key Pattern | AI Adoption | Quality Trend |
|----------|-------------|-------------|---------------|
| ai-success | 10%→75% adoption, improving metrics | Progressive | 2.5→2.8 |
| review-bottleneck | 1 reviewer handles 60% of reviews | Steady 70% | 2.8→2.2 |
| baseline | Steady state for comparison | Steady 15% | Steady 2.6 |
| detective-game | Varied guess accuracy 30-70% | Mixed | N/A |

### Command Interface

```bash
# New arguments
--scenario {ai-success,review-bottleneck,baseline,detective-game}
--seed INT          # Default: 42
--source-repo URL   # Can specify multiple
--no-github         # Skip GitHub fetching
--list-scenarios    # Print scenarios and exit

# Legacy (unchanged)
--teams, --members, --prs, --clear, --team-slug
```

## Implementation Phases

### Phase 1: Foundation Infrastructure [Effort: M]
Create seeding package structure with core utilities:
- `DeterministicRandom` class with seedable random methods
- `BaseScenario`, `ScenarioConfig`, `WeeklyParams` dataclasses
- Scenario registry for lookup

### Phase 2: Scenario Implementations [Effort: L]
Implement 4 concrete scenarios:
- Each defines weekly parameter progression
- Each defines member distribution/archetypes
- Each provides coherent data patterns

### Phase 3: GitHub Fetcher Service [Effort: M]
Unauthenticated public repo PR fetcher:
- PyGithub unauthenticated client (60 req/hour limit)
- Caching to avoid repeated API calls
- Graceful fallback when rate limited

### Phase 4: Data Generator [Effort: L]
Main orchestrator combining scenarios + GitHub + factories:
- Create members based on scenario distribution
- Generate 8 weeks of data with progression
- Validate data relationships are coherent

### Phase 5: Command Enhancement [Effort: M]
Add new flags while preserving backward compatibility.

### Phase 6: Documentation & Tests [Effort: S]
Update docs and add comprehensive tests.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub rate limits | Medium | Low | Caching, `--no-github` flag |
| Model changes during development | High | Medium | Model existence checks |
| Breaking legacy behavior | Low | High | Extensive backward compat tests |

## Success Metrics

- [ ] All 4 scenarios produce distinct, recognizable data patterns
- [ ] Same seed produces identical data across runs
- [ ] GitHub fetcher works with default repos
- [ ] Legacy command usage unchanged
- [ ] Tests cover all new code paths

## Usage Examples

```bash
# List available scenarios
python manage.py seed_demo_data --list-scenarios

# Seed AI success story (reproducible)
python manage.py seed_demo_data --scenario ai-success --seed 12345

# Seed with custom GitHub repos
python manage.py seed_demo_data --scenario baseline \
    --source-repo yanchuk/github-issues-rag

# Offline mode (no GitHub API)
python manage.py seed_demo_data --scenario detective-game --no-github

# Clear and reseed
python manage.py seed_demo_data --clear --scenario review-bottleneck

# Legacy mode (unchanged)
python manage.py seed_demo_data --teams 2 --members 10 --prs 100
```
