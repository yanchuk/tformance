# Type Hints & Code Refactoring - Tasks

**Last Updated:** 2026-01-10
**Status:** PLANNING

## Phase 0: Pre-Implementation Validation

### 0.1 Test Pyright on Current State (BEFORE any changes)
- [ ] Install pyright: `pip install pyright==1.1.391`
- [ ] Run on insight_llm.py: `pyright apps/metrics/services/insight_llm.py`
- [ ] Run on github_sync.py: `pyright apps/integrations/services/github_sync.py`
- [ ] Run on llm_prompts.py: `pyright apps/metrics/services/llm_prompts.py`
- [ ] Document baseline errors count: ___
- [ ] Identify PyGithub stub gaps
- [ ] Identify Groq/LiteLLM stub gaps

## Phase 1: Setup & Types Foundation

### 1.1 Environment Setup
- [ ] Add pyright==1.1.391 to dev dependencies in pyproject.toml
- [ ] Install pyright: `uv pip install pyright==1.1.391`
- [ ] Verify pyright runs: `pyright --version`

### 1.2 Configuration
- [ ] Add [tool.pyright] section to pyproject.toml (Django-specific settings)
- [ ] Set typeCheckingMode = "basic"
- [ ] Set reportUnknownMemberType = false (Django QuerySets)
- [ ] Set reportGeneralTypeIssues = "warning"
- [ ] Configure include/exclude paths
- [ ] Run baseline: `pyright apps/metrics/services/insight_llm.py`

### 1.3 Create Type Definitions
- [ ] Create `apps/metrics/types.py`
  - [ ] MetricCard TypedDict
  - [ ] InsightAction TypedDict
  - [ ] InsightResponse TypedDict
  - [ ] InsightData TypedDict
  - [ ] VelocityMetrics TypedDict
- [ ] Create `apps/integrations/types.py`
  - [ ] PRDict TypedDict
  - [ ] SyncResult TypedDict
  - [ ] ReviewDict TypedDict

### 1.4 Pre-commit Hook
- [ ] Add pyright hook to .pre-commit-config.yaml
- [ ] Set to warnings mode initially
- [ ] Test with: `pre-commit run pyright --all-files`

## Phase 2: insight_llm.py (794 lines)

### 2.1 TDD Baseline
- [ ] Run tests: `pytest apps/metrics/tests/services/test_insight_llm.py -v`
- [ ] Document passing count: ___

### 2.2 Type Imports
- [ ] Add TypedDict imports from apps.metrics.types
- [ ] Add TYPE_CHECKING block if needed
- [ ] Import Team, DailyInsight properly

### 2.3 Function: resolve_action_url
- [ ] Add InsightAction type for action param
- [ ] Verify tests pass

### 2.4 Function: build_metric_cards
- [ ] Change `data: dict` → `data: InsightData`
- [ ] Change return → `list[MetricCard]`
- [ ] Verify tests pass

### 2.5 Function: _get_top_contributors
- [ ] Type return as `list[ContributorInfo]` (create TypedDict)
- [ ] Verify tests pass

### 2.6 Function: gather_insight_data
- [ ] Type return as `InsightData`
- [ ] Verify tests pass

### 2.7 Function: generate_insight
- [ ] Type return as `InsightResponse`
- [ ] Add specific exception types
- [ ] Verify tests pass

### 2.8 Function: cache_insight
- [ ] Verify existing types correct
- [ ] No changes expected

### 2.9 Refactoring
- [ ] Move BOT_USERNAME_PATTERNS to constants module
- [ ] Move INSIGHT_JSON_SCHEMA to prompts/schemas.py
- [ ] Run pyright: zero errors
- [ ] Run tests: all pass

## Phase 3: github_sync.py (1,138 lines)

### 3.1 TDD Baseline
- [ ] Run tests: `pytest apps/integrations/tests/test_github_sync.py -v`
- [ ] Document passing count: ___

### 3.2 Type Imports
- [ ] Import github.PullRequest as GHPullRequest
- [ ] Import types from apps.integrations.types
- [ ] Add TYPE_CHECKING imports for Django models

### 3.3 Function: _convert_pr_to_dict
- [ ] Add `pr: GHPullRequest` parameter type
- [ ] Change return → `PRDict`
- [ ] Verify tests pass

### 3.4 Generator Functions
- [ ] Type get_repository_pull_requests return
- [ ] Type get_updated_pull_requests return
- [ ] Use Generator[PRDict, None, None]
- [ ] Verify tests pass

### 3.5 Sync Functions
- [ ] Type _sync_pr_reviews params and return
- [ ] Type sync_pr_commits params and return
- [ ] Type sync_pr_check_runs params and return
- [ ] Type sync_pr_files params and return
- [ ] Verify tests pass after each

### 3.6 Complex Functions
- [ ] Type _process_prs with SyncResult return
- [ ] Type sync_repository_history
- [ ] Type sync_repository_incremental
- [ ] Verify tests pass

### 3.7 Refactoring
- [ ] Extract rate limit handling to decorator
- [ ] Simplify _process_prs if possible
- [ ] Run pyright: zero errors
- [ ] Run tests: all pass

## Phase 4: llm_prompts.py (1,043 lines)

### 4.1 TDD Baseline
- [ ] Run tests: `pytest apps/metrics/tests/services/test_llm_prompts.py -v`
- [ ] Document passing count: ___

### 4.2 Type Imports
- [ ] Ensure TimelineEvent dataclass imported
- [ ] Add TYPE_CHECKING for PullRequest, TeamMember
- [ ] Import types from apps.metrics.types

### 4.3 Helper Functions
- [ ] Type _get_member_display_name param (TeamMember | None)
- [ ] Type format_review_content (nested)
- [ ] Type format_comment_content (nested)
- [ ] Verify tests pass

### 4.4 Timeline Functions
- [ ] Type _collect_timeline_events return → list[TimelineEvent]
- [ ] Verify build_timeline consistency
- [ ] Verify tests pass

### 4.5 Context Building
- [ ] Type build_llm_pr_context return
- [ ] Type get_user_prompt return
- [ ] Verify tests pass

### 4.6 Refactoring
- [ ] Consider extracting nested functions
- [ ] Simplify complex conditionals
- [ ] Run pyright: zero errors
- [ ] Run tests: all pass

## Phase 5: Verification & Enforcement

### 5.1 Final Verification
- [ ] Run pyright on all three files: zero errors
- [ ] Run full test suite: all pass
- [ ] Run pre-commit: all hooks pass

### 5.2 Enable Enforcement
- [ ] Change pyright hook from warnings to errors
- [ ] Test pre-commit enforcement works

### 5.3 Documentation
- [ ] Update CLAUDE.md with typing guidelines
- [ ] Document typing patterns in dev/guides/

### 5.4 Cleanup
- [ ] Remove any temporary `# type: ignore` comments
- [ ] Final code review

## Completion Checklist

- [ ] All three target files fully typed
- [ ] Pyright shows zero errors
- [ ] All tests pass
- [ ] Pre-commit enforces types on new code
- [ ] Documentation updated

## Notes

### Commands Reference

```bash
# Run pyright on specific file
pyright apps/metrics/services/insight_llm.py

# Run pyright on all modified files
pyright apps/metrics/services/ apps/integrations/services/

# Run specific test file
pytest apps/metrics/tests/services/test_insight_llm.py -v

# Run pre-commit manually
pre-commit run pyright --all-files

# Check type coverage
pyright --verifytypes apps.metrics.services.insight_llm
```

### Type Error Patterns to Watch

1. **Incompatible types**: Fix with proper TypedDict
2. **Missing attribute**: Check for Optional handling
3. **Argument type**: Ensure param annotations match usage
4. **Return type**: Ensure all code paths return correct type
