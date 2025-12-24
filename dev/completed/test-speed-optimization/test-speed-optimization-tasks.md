# Test Speed Optimization Tasks

**Last Updated: 2025-12-22**
**Status: Phase 2 Complete**

## Phase 1: Quick Wins ✅

### 1.1 Make --keepdb the default ✅
- [x] Edit `Makefile` test target to include `--keepdb`
- [x] Added `test-fresh` command for when fresh DB needed
- [x] Verified test run uses existing database

### 1.2 Install tblib ✅
- [x] Added `tblib>=3.0.0` to dev dependencies in pyproject.toml
- [x] Ran `uv sync`
- [x] Verified import works

### 1.3 Fix TeamMemberFactory unique constraint ✅
- [x] Changed `display_name` to use `factory.Sequence`
- [x] Changed `email` to use `factory.Sequence`
- [x] Changed `github_username` to use `factory.Sequence`
- [x] Tests pass without flaky IntegrityError

### 1.4 Verify Phase 1 complete ✅
- [x] All 2018 tests pass with `--keepdb`
- [x] Baseline: ~75 seconds sequential

---

## Phase 2: Enable Parallel Execution ✅

### 2.1 Fix test_fields.py for parallel safety ✅
- [x] Refactored to use `IntegrationCredential` model instead of creating/dropping tables
- [x] Removed `setUpClass`/`tearDownClass` that created/dropped `utils_testmodel` table
- [x] All 10 EncryptedTextField tests pass

### 2.2 Fix migration issue for fresh DB creation ✅
- [x] Fixed `_backfill_utils.py` to use raw SQL instead of ORM
- [x] Migrations now work when creating fresh test database
- [x] All 2018 tests pass

### 2.3 Full parallel test run ✅
- [x] Ran `make test-parallel`
- [x] All 2018 tests pass in **29.97 seconds**
- [x] **60% faster** than sequential (~75s)

### 2.4 Update documentation ✅
- [x] Updated CLAUDE.md testing section
- [x] Added speed tips for test commands
- [x] Added factory Sequence best practice

---

## Phase 3: Test Data Optimization [Deferred]

These optimizations are optional and can be done incrementally:

### 3.1 Convert to setUpTestData (not started)
- [ ] `apps/integrations/tests/test_views.py` (111 factory calls)
- [ ] `apps/metrics/tests/test_quick_stats.py` (110 factory calls)
- [ ] `apps/metrics/tests/test_insight_rules.py` (77 factory calls)
- [ ] `apps/metrics/tests/test_chart_views.py` (36 factory calls)

**Note**: This provides ~10-20% additional speedup but requires careful analysis of test mutation patterns.

---

## Phase 4: pytest Migration [Deferred]

Migrating to pytest offers additional benefits but is lower priority now that parallel works:

- pytest-xdist for more flexible parallelization
- Better test discovery and fixtures
- pytest-randomly for test order randomization

---

## Results Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Sequential time | ~125s | ~75s | 40% faster (--keepdb) |
| Parallel time | N/A (broken) | ~30s | 60% faster than sequential |
| Parallel vs original | ~125s | ~30s | **76% faster** |
| Flaky tests | 1+ | 0 | Fixed |
| Tests passing | 1942 | 2018 | +76 tests added |

## Files Modified

1. `Makefile` - Added `--keepdb` default, `test-fresh`, `test-parallel`
2. `pyproject.toml` - Added `tblib>=3.0.0`
3. `apps/metrics/factories.py` - Fixed `TeamMemberFactory` with Sequence
4. `apps/utils/tests/test_fields.py` - Refactored for parallel safety
5. `apps/metrics/migrations/_backfill_utils.py` - Fixed for fresh DB creation
6. `apps/integrations/tests/test_views.py` - Fixed pre-existing test bugs
7. `CLAUDE.md` - Updated testing section with speed tips
