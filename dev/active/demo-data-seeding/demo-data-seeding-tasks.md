# Demo Data Seeding - Tasks

**Last Updated:** 2025-12-21

## Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Foundation | **COMPLETE** | 5/5 |
| Phase 2: Scenarios | **COMPLETE** | 6/6 |
| Phase 3: GitHub Fetcher | **COMPLETE** | 4/4 |
| Phase 4: Data Generator | **COMPLETE** | 6/6 |
| Phase 5: Command | **COMPLETE** | 7/7 |
| Phase 6: Documentation | **COMPLETE** | 4/4 |

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

## Phase 3: GitHub Fetcher [Effort: M] - COMPLETE

- [x] 3.1 Implement `github_fetcher.py`
  - `FetchedPR` dataclass with all PR metadata
  - `GitHubPublicFetcher` class with unauthenticated client
  - Default repos: tiangolo/fastapi, pallets/flask, psf/requests

- [x] 3.2 Add caching to avoid repeated API calls
  - Cache by `(repo_name, state)` key
  - Cache cleared with `clear_cache()` method

- [x] 3.3 Add graceful fallback when rate limited
  - Catches `RateLimitExceededException` and `GithubException`
  - Returns empty list with warning log

- [x] 3.4 Test with mock PyGithub responses
  - 13 tests in `test_github_fetcher.py`
  - Tests cache, rate limits, error handling

---

## Phase 4: Data Generator [Effort: L] - COMPLETE

- [x] 4.1 Implement `data_generator.py` orchestrator
  - `ScenarioDataGenerator` dataclass with generate() method
  - `GeneratorStats` for tracking created objects
  - `MemberWithArchetype` for pairing members with behaviors

- [x] 4.2 Add hybrid data creation (GitHub + factory)
  - Pre-fetches from scenario's GitHub repos
  - `github_percentage` controls mix (default 25%)
  - Falls back to factory when no GitHub data

- [x] 4.3 Add weekly progression logic
  - Loops through 8 weeks with dated data
  - Applies weekly params to each week's generation
  - Member archetypes modify AI adoption, PR volume, review load

- [x] 4.4 Implement weekly metrics calculation (inline)
  - Calculates real aggregates from generated PRs
  - WeeklyMetrics accurately reflects actual data
  - Queries PullRequest to compute avg_cycle_time_hours

- [x] 4.5 Add model existence checks
  - Creates all available models (PR, Review, Commit, Survey, etc.)
  - Skips gracefully if constraints violated

- [x] 4.6 Validate data relationships are coherent
  - 12 tests in `test_data_generator.py`
  - Tests reproducibility, reviewer weights, temporal ordering

---

## Phase 5: Command Enhancement [Effort: M] - COMPLETE

- [x] 5.1 Add `--scenario` argument
  - Choices: ai-success, review-bottleneck, baseline, detective-game
  - Routes to `handle_scenario_mode()`

- [x] 5.2 Add `--seed` argument
  - `type=int, default=42`
  - Passed to ScenarioDataGenerator for reproducibility

- [x] 5.3 Add `--source-repo` argument (repeatable)
  - `action="append", dest="source_repos"`
  - Overrides scenario's default GitHub repos

- [x] 5.4 Add `--no-github` flag
  - Sets `fetch_github=False` in generator
  - Uses factory data only

- [x] 5.5 Add `--list-scenarios` action
  - `print_scenarios()` displays all available scenarios
  - Shows name, description, member count, weeks

- [x] 5.6 Preserve backward compatibility
  - Legacy mode via `handle_legacy_mode()`
  - All legacy args work: --teams, --members, --prs, --clear, --team-slug
  - No --scenario = legacy factory behavior

- [x] 5.7 Command tested manually
  - `--list-scenarios` shows all 4 scenarios
  - Scenario mode creates team with scenario's slug/name
  - 73 seeding tests pass

---

## Phase 6: Documentation & Finalization [Effort: S] - COMPLETE

- [x] 6.1 Update `dev/DEV-ENVIRONMENT.md`
  - Added scenario-based seeding section (recommended)
  - Added all 4 scenarios with descriptions
  - Added legacy mode section
  - Added scenario features list

- [x] 6.2 Add usage examples to command docstring
  - Module docstring already has comprehensive examples
  - Shows all flags and both modes

- [x] 6.3 Update CLAUDE.md if needed
  - Added scenario-based seeding examples
  - Added --list-scenarios hint
  - Referenced DEV-ENVIRONMENT.md for full docs

- [x] 6.4 Run full test suite
  - All 1584 tests pass
  - No regressions

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

### Session 2025-12-20 (Earlier - Phases 1-2)

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

### Session 2025-12-20 (Later - Phases 3-5)

**Completed Phase 3: GitHub Fetcher**

Files created:
- `apps/metrics/seeding/github_fetcher.py` - FetchedPR dataclass, GitHubPublicFetcher class
- `apps/metrics/tests/test_seeding/test_github_fetcher.py` - 13 tests

**Key implementations:**
- `FetchedPR` dataclass with PR metadata fields
- In-memory caching by `(repo_name, state)` key
- Graceful rate limit handling (catches exceptions, returns empty list)
- Default repos: tiangolo/fastapi, pallets/flask, psf/requests

**Completed Phase 4: Data Generator**

Files created:
- `apps/metrics/seeding/data_generator.py` - ScenarioDataGenerator orchestrator
- `apps/metrics/tests/test_seeding/test_data_generator.py` - 12 tests

**Key implementations:**
- `ScenarioDataGenerator` dataclass with `generate()` method
- `GeneratorStats` tracking created objects
- `MemberWithArchetype` pairing members with behavior definitions
- Hybrid data sourcing (25% GitHub + 75% factory by default)
- Weekly progression through 8 weeks with scenario params
- WeeklyMetrics calculated from actual PR data

**Bug fixes:**
- Fixed unhashable `MemberWithArchetype` by using index as dict key for weighted_choice
- Fixed test threshold for bottleneck reviewer (35% → 25%)

**Completed Phase 5: Command Enhancement**

Files modified:
- `apps/metrics/management/commands/seed_demo_data.py` - Added all new arguments

**New arguments:**
- `--scenario {ai-success,review-bottleneck,baseline,detective-game}`
- `--seed INT` (default: 42)
- `--source-repo URL` (repeatable with `action="append"`)
- `--no-github` flag
- `--list-scenarios` action

**Backward compatibility preserved:**
- Legacy mode via `handle_legacy_mode()`
- All legacy args work: --teams, --members, --prs, --clear, --team-slug

**Commits made:**
- `991dae8` - Phases 1-3: Foundation, scenarios, GitHub fetcher
- `4f799db` - Phase 4: Data generator
- `9cecf39` - Phase 5: Enhanced command

**Total tests: 73** (17 + 31 + 13 + 12)

**No migrations needed** - pure Python utility code.

**Test command:**
```bash
.venv/bin/python manage.py test apps.metrics.tests.test_seeding --keepdb
```

### Session 2025-12-21 (PR Iteration Metrics Support)

**Added seeding for new dashboard models:**

Files modified:
- `apps/metrics/factories.py` - Fixed PRFileFactory
- `apps/metrics/seeding/data_generator.py` - Added new methods
- `apps/metrics/tests/test_dashboard_service.py` - Added 18 unit tests

**New seeding methods:**
- `_create_pr_files()` - 2-8 files per PR with category distribution
- `_create_check_runs()` - 2-6 CI checks per PR with 80% pass rate
- `_create_deployments()` - 1-3 deployments per week

**GeneratorStats updated:**
- `pr_files_created`, `check_runs_created`, `deployments_created`

**Bug fixes:**
- PRFileFactory class-level constants removed (caused model errors)
- PRCheckRun field names corrected (started_at, completed_at)
- PRFile unique constraint handled with index-based filenames

**Commits:**
- `472ac7a` - Add seed data generation for PRFile, PRCheckRun, and Deployment
- `9874e96` - Complete security-audit and ui-review tasks

**Total tests: 1620** (all passing)
