# AI Detection PR Descriptions - Tasks

**Last Updated**: 2025-12-25

## Completed

### Phase 1: Regex Pattern System
- [x] AI_SIGNATURE_PATTERNS in ai_patterns.py (v1.9.0)
- [x] Pattern versioning with PATTERNS_VERSION
- [x] Pattern changelog documentation

### Phase 2: LLM Prompt System
- [x] Jinja2 template infrastructure
- [x] System prompt with sections (ai_detection, tech_detection, health_assessment)
- [x] User prompt with full PR context (25+ variables)
- [x] Response schema with JSON validation
- [x] PROMPT_VERSION tracking (now 6.8.0)

### Phase 3: Golden Test System
- [x] GoldenTest dataclass with all PR context fields
- [x] 29 original test cases across 6 categories
- [x] to_promptfoo_test() conversion function
- [x] Category filtering helpers

### Phase 4: TDD Data Consistency (2025-12-25)
- [x] Add test_file_count_matches_file_paths TDD test
- [x] Add test_all_tests_have_repo_name TDD test
- [x] Fix health_slow_review: expand file_paths to 12
- [x] Fix health_draft_wip: expand file_paths to 5
- [x] Add repo_name to all 29 golden tests
- [x] Add realistic file_paths to edge/tech/type/health tests
- [x] Verify 29/29 promptfoo tests pass

### Phase 5: Extended Test Coverage (2025-12-25)
- [x] Add 5 new positive tests (cody, coderabbit, devin, tabnine, greptile)
- [x] Add 5 new negative tests (sdk_version_bump, ai_documentation, llm_test_suite, ai_competitor_analysis, openai_client_library)
- [x] Add 8 new edge cases (indirect_disclosure, review_comment_ai, ai_typo_false_positive, github_actions_ai, confidence_high/medium/low, multi_tool)
- [x] Verify TDD consistency tests pass with 46 tests

### Phase 6: Prompt Refinement (2025-12-25)
- [x] v6.6.0: Add logical consistency rules (is_assisted ↔ tools)
- [x] v6.6.0: Add vague mentions rule ("assistance" without context)
- [x] v6.6.0: Add Security Notice for prompt injection protection
- [x] v6.7.0: Add CI/CD configuration rule (configuring != using AI)
- [x] v6.8.0: Clarify PR type definitions (feature vs chore vs ci)
- [x] Achieve 47/47 tests passing (100%)

### Phase 7: Promptfoo Integration
- [x] export_prompts management command
- [x] Promptfoo YAML generation from golden tests
- [x] .env symlink for GROQ_API_KEY
- [x] GPT-OSS-20B config with include_reasoning: false

## In Progress

None - v6.8.0 is complete and tested

## Backlog

### Future Enhancements
- [ ] Add more edge case tests for aider, windsurf patterns
- [ ] Add tests for commit message AI detection patterns
- [ ] Add tests for review comment AI mentions
- [ ] Consider Llama 3.3 70B as primary model (higher quality)
- [ ] Add adversarial prompt injection test cases

### Known Limitations (Documented)
- [ ] Aider patterns may need refinement (only detects "aider:" prefix)
- [ ] Windsurf/Codeium detection relies on explicit mention
- [ ] No detection of VS Code Copilot via telemetry

## Test Commands

```bash
# TDD consistency tests
.venv/bin/pytest apps/metrics/prompts/tests/test_golden_tests.py::TestGoldenTestDataConsistency -v

# All golden tests
.venv/bin/pytest apps/metrics/prompts/tests/test_golden_tests.py -v

# Full prompts test suite
.venv/bin/pytest apps/metrics/prompts/tests/ -v

# Promptfoo evaluation (100% pass rate)
cd dev/active/ai-detection-pr-descriptions/experiments
/bin/bash -c 'export GROQ_API_KEY=$(grep "^GROQ_API_KEY" .env | cut -d= -f2) && npx promptfoo eval -c promptfoo.yaml'
```

## Session Notes

### 2025-12-25: Extended Testing & Prompt Refinement

**Extended Golden Tests**: Added 17 new test cases based on research findings:
- 5 new AI tools (Cody, CodeRabbit, Devin, Tabnine, Greptile)
- 5 false positive prevention scenarios (SDK bumps, docs, building AI features)
- 8 edge cases including confidence calibration and multi-tool detection

**Prompt Improvements**: Fixed 4 issues discovered during testing:
1. Logical inconsistency (tools detected but is_assisted=false)
2. False positives on vague words ("assistance" without AI context)
3. CI/CD configuration falsely detected (configuring coderabbit action != using AI)
4. PR type classification clarity (feature vs chore vs ci)

**Security**: Added prompt injection guardrails to protect against malicious PR descriptions.

**Final Result**: 47/47 tests passing (100%)
