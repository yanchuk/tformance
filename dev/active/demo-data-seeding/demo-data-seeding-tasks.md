# Demo Data Seeding - Tasks

**Last Updated:** 2025-12-20

## Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | **COMPLETE** | 5/5 |
| Phase 2: Scenarios | **COMPLETE** | 6/6 |
| Phase 3: GitHub Fetcher | Not Started | 0/4 |
| Phase 4: Data Generator | Not Started | 0/6 |
| Phase 5: Command | Not Started | 0/7 |
| Phase 6: Documentation | Not Started | 0/4 |

---

## Phase 1: Foundation Infrastructure [Effort: M] - COMPLETE

- [x] 1.1 Create `apps/metrics/seeding/` package structure
  - Created `__init__.py`
  - Created `scenarios/__init__.py`

- [x] 1.2 Implement `deterministic.py` with `DeterministicRandom` class
  - `__init__(self, seed: int)`
  - `choice(self, seq)`, `choices(self, seq, k)`, `sample(self, seq, k)`
  - `randint(self, a, b)`, `uniform(self, a, b)`
  - `decimal(self, a, b, places)`
  - `should_happen(self, probability: float) -> bool`
  - `datetime_in_range(self, start, end)`, `timedelta_in_range(min_hours, max_hours)`
  - `weighted_choice(self, options: dict)`
  - `shuffle(self, seq)`, `gauss(mu, sigma)`, `triangular(low, high, mode)`

- [x] 1.3 Create `scenarios/base.py`
  - `WeeklyParams` TypedDict
  - `MemberArchetype` dataclass
  - `ScenarioConfig` dataclass
  - `BaseScenario` abstract class with methods:
    - `get_weekly_params(week)` - abstract
    - `get_member_archetypes()` - abstract
    - `get_reviewer_selection_weights(week)`
    - `get_pr_state_distribution(week)`
    - `get_review_state_distribution(week)`
    - `get_guess_accuracy_for_archetype(archetype)`
    - `validate()`

- [x] 1.4 Create `scenarios/registry.py`
  - `SCENARIO_REGISTRY: dict[str, type[BaseScenario]]`
  - `@register_scenario(name)` decorator
  - `get_scenario(name)` function
  - `list_scenarios()` function
  - `_load_scenarios()` lazy loader

- [x] 1.5 Write unit tests for `DeterministicRandom`
  - 17 tests in `apps/metrics/tests/test_seeding/test_deterministic.py`
  - All tests pass

---

## Phase 2: Scenario Implementations [Effort: L] - COMPLETE

- [x] 2.1 Implement `ai_success.py`
  - Progressive AI adoption: 10% → 75%
  - Improving cycle times: 72h → 24h
  - Maintained quality: 2.5 → 2.8
  - Member archetypes: early_adopter, follower, skeptic

- [x] 2.2 Implement `review_bottleneck.py`
  - Steady 70% AI adoption
  - Worsening cycle times: 36h → 60h
  - Declining quality: 2.8 → 2.2
  - Key: `get_reviewer_selection_weights()` returns 60% for bottleneck
  - Overrides `get_pr_state_distribution()` to show increasing open PRs

- [x] 2.3 Implement `baseline.py`
  - Steady 15% AI adoption
  - Steady 48h cycle times (with minor variations)
  - Steady 2.6 quality
  - Used as comparison baseline

- [x] 2.4 Implement `detective_game.py`
  - Focus on guess accuracy variation
  - Archetypes: obvious_ai, stealth_ai, obvious_manual, stealth_manual
  - Guess accuracy ranges per archetype (30-85%)
  - Higher approval rate for more survey opportunities

- [x] 2.5 Register all scenarios in registry
  - Auto-registration via `@register_scenario` decorator
  - Imported in `scenarios/__init__.py` for loading

- [x] 2.6 Write tests for weekly param progression
  - 31 tests in `apps/metrics/tests/test_seeding/test_scenarios.py`
  - Tests for all 4 scenarios' weekly progression
  - Validation tests for archetype counts matching config

---

## Phase 3: GitHub Fetcher [Effort: M] - NEXT

- [ ] 3.1 Implement `github_fetcher.py`
  - `FetchedPR` dataclass (title, additions, deletions, files_changed, commits_count)
  - `GitHubPublicFetcher` class
  - Unauthenticated `Github()` client

- [ ] 3.2 Add caching to avoid repeated API calls
  - `cache: dict[str, list[FetchedPR]]`
  - Check cache before fetching

- [ ] 3.3 Add graceful fallback when rate limited
  - Catch `GithubException` and return empty list
  - Log warning message

- [ ] 3.4 Test with mock PyGithub responses
  - Mock `Github.get_repo()` and `repo.get_pulls()`
  - Test cache prevents duplicate calls

---

## Phase 4: Data Generator [Effort: L]

- [ ] 4.1 Implement `data_generator.py` orchestrator
  - `ScenarioDataGenerator` class
  - `__init__(scenario, seed, fetch_github)`
  - `generate(team) -> dict` returns stats

- [ ] 4.2 Add hybrid data creation (GitHub + factory)
  - `pre_fetch_github_data()` - load GitHub PRs into pool
  - Use GitHub PR metadata for ~25% of PRs
  - Fall back to factory for rest

- [ ] 4.3 Add weekly progression logic
  - Loop through 8 weeks
  - Apply `get_weekly_params(week)` to each week's data
  - Respect member archetypes for variations

- [ ] 4.4 Implement `weekly_metrics_calculator.py`
  - Calculate actual aggregates from generated data
  - Ensure `prs_merged` matches real PR count
  - Ensure `avg_cycle_time_hours` matches real average

- [ ] 4.5 Add model existence checks
  - Check if PRComment, PRFile, etc. models exist before creating
  - Skip gracefully if model not yet implemented

- [ ] 4.6 Validate data relationships are coherent
  - WeeklyMetrics matches PR data
  - Review distribution matches scenario weights
  - Temporal order is correct

---

## Phase 5: Command Enhancement [Effort: M]

- [ ] 5.1 Add `--scenario` argument
  - `choices=["ai-success", "review-bottleneck", "baseline", "detective-game"]`

- [ ] 5.2 Add `--seed` argument
  - `type=int, default=42`

- [ ] 5.3 Add `--source-repo` argument (repeatable)
  - `action="append", dest="source_repos"`

- [ ] 5.4 Add `--no-github` flag
  - `action="store_true"`

- [ ] 5.5 Add `--list-scenarios` action
  - Print scenario names and descriptions
  - Exit after listing

- [ ] 5.6 Preserve backward compatibility
  - Legacy args still work: `--teams, --members, --prs, --clear, --team-slug`
  - When no `--scenario`, use legacy behavior

- [ ] 5.7 Write integration tests
  - Test legacy mode unchanged
  - Test scenario mode creates expected data
  - Test `--seed` reproducibility

---

## Phase 6: Documentation & Finalization [Effort: S]

- [ ] 6.1 Update `dev/DEV-ENVIRONMENT.md`
  - Add scenario documentation
  - Add usage examples

- [ ] 6.2 Add usage examples to command docstring
  - Update module docstring in `seed_demo_data.py`

- [ ] 6.3 Update CLAUDE.md if needed
  - Add note about scenario-based seeding

- [ ] 6.4 Run full test suite
  - `make test`
  - Ensure no regressions

---

## Demo Data Updates Checklist (for new features)

When implementing new models, include in your feature plan:

- [ ] Factory created: `apps/<app>/factories.py`
- [ ] Seed logic added: `apps/metrics/seeding/data_generator.py`
- [ ] Add model to `SEEDED_MODELS` registry
- [ ] Scenario-specific behavior defined (if needed)
- [ ] Tests verify seeded data

---

## Session Notes

### Session 2025-12-20

**Completed Phase 1: Foundation Infrastructure**

Files created:
- `apps/metrics/seeding/__init__.py`
- `apps/metrics/seeding/deterministic.py` - DeterministicRandom class
- `apps/metrics/seeding/scenarios/__init__.py`
- `apps/metrics/seeding/scenarios/base.py` - BaseScenario, ScenarioConfig, MemberArchetype, WeeklyParams
- `apps/metrics/seeding/scenarios/registry.py` - Scenario registry with decorator pattern
- `apps/metrics/tests/test_seeding/__init__.py`
- `apps/metrics/tests/test_seeding/test_deterministic.py` - 17 tests, all passing

**Key decisions:**
- Used `@register_scenario` decorator pattern for clean scenario registration
- Added `MemberArchetype` dataclass for defining team member behavior patterns
- Included extra methods in BaseScenario: review weights, PR state distribution, guess accuracy
- DeterministicRandom includes extra utility methods: gauss, triangular, shuffle, sample

**Completed Phase 2: Scenario Implementations**

Files created:
- `apps/metrics/seeding/scenarios/ai_success.py` - Progressive AI adoption scenario
- `apps/metrics/seeding/scenarios/review_bottleneck.py` - Review bottleneck scenario
- `apps/metrics/seeding/scenarios/baseline.py` - Steady-state baseline scenario
- `apps/metrics/seeding/scenarios/detective_game.py` - AI Detective game scenario
- `apps/metrics/tests/test_seeding/test_scenarios.py` - 31 tests for scenarios

**Key implementations:**
- Each scenario implements `get_weekly_params(week)` with distinct progression patterns
- `ai_success`: AI adoption 10%→75%, cycle time 72h→24h, quality 2.5→2.8
- `review_bottleneck`: Steady 70% AI, worsening cycle times 36h→60h, one reviewer handles 60%
- `baseline`: Steady 15% AI, stable metrics for comparison
- `detective_game`: 4 archetypes (obvious_ai, stealth_ai, obvious_manual, stealth_manual)

**Simplified registry:**
- Removed `_load_scenarios()` lazy loader (redundant since `__init__.py` imports scenarios)
- Scenarios auto-register via `@register_scenario` decorator

**Total tests: 48** (17 DeterministicRandom + 31 scenarios)

**Next steps:**
- Implement Phase 3: GitHub Fetcher - fetch real PR metadata from public repos
- Create `github_fetcher.py` with caching and rate limit handling

**No migrations needed** - this is pure Python utility code, no model changes.

**Test command:**
```bash
.venv/bin/python manage.py test apps.metrics.tests.test_seeding --keepdb
```
