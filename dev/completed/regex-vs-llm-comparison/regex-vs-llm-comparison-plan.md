# Regex vs LLM Detection Comparison in Promptfoo

**Last Updated: 2025-12-25**

## Executive Summary

Add a custom Python provider for promptfoo that runs regex pattern detection alongside LLM detection, enabling side-by-side comparison in the promptfoo UI. This allows evaluating where regex and LLM agree/disagree, identifying pattern improvement opportunities, and catching LLM false positives.

## Current State Analysis

### Existing Infrastructure
- **AI Detection (Regex)**: `apps/metrics/services/ai_detector.py` with `detect_ai_in_text()` function
- **Pattern Versioning**: `PATTERNS_VERSION` in `ai_patterns.py` (currently v1.7.0)
- **LLM Detection**: Groq-based analysis via `run_llm_analysis` command
- **Promptfoo Export**: `apps/metrics/prompts/export.py` generates promptfoo.yaml from golden tests
- **Golden Tests**: 29 test cases in `apps/metrics/prompts/golden_tests.py`
- **Real PR Export**: `export_prs_to_promptfoo` command exports real PRs for testing

### Current Gaps
1. No side-by-side comparison of regex vs LLM in promptfoo
2. Real PR export doesn't include LLM results for comparison
3. No unified test case format that includes both expected regex and LLM results

## Proposed Future State

### Architecture
```
promptfoo evaluation
    ├── Provider 1: Groq LLM (gpt-oss-20b)
    │   └── Returns: {ai: {is_assisted, tools, ...}, tech: {...}, ...}
    │
    ├── Provider 2: Python Regex Provider
    │   └── Returns: {ai: {is_assisted, tools, ...}, _regex_details: {...}}
    │
    └── Test Cases (from export_comparison_tests command)
        ├── Real PRs with pre-computed regex results
        ├── Assertions comparing both outputs
        └── Metadata for analysis
```

### New Components
1. **Regex Provider** (`regex_provider.py`): Custom promptfoo provider that runs regex detection
2. **Comparison Config** (`compare-detection.yaml`): Promptfoo config with both providers
3. **Export Command** (`export_comparison_tests.py`): Django command to generate test cases
4. **Test Case Format**: JSON with both regex baseline and LLM expectations

## Implementation Phases

### Phase 1: Python Provider for Regex Detection (S)
Create a promptfoo-compatible Python provider that runs regex detection.

**Files:**
- `dev/active/ai-detection-pr-descriptions/experiments/regex_provider.py`

**Acceptance Criteria:**
- Provider implements `call_api(prompt, options, context)` interface
- Returns JSON matching LLM response schema
- Includes `_regex_details` section with pattern version
- Can be run standalone for testing

### Phase 2: Export Comparison Tests Command (M)
Create Django management command to export real PRs with pre-computed regex results.

**Files:**
- `apps/metrics/management/commands/export_comparison_tests.py`

**Acceptance Criteria:**
- Exports real PRs from database with full context
- Pre-computes regex detection for each PR
- Includes both regex results and PR metadata
- Generates comparison-test-cases.json
- Supports `--limit`, `--team`, `--output` arguments

### Phase 3: Comparison Promptfoo Config (S)
Create promptfoo configuration that uses both providers.

**Files:**
- `dev/active/ai-detection-pr-descriptions/experiments/compare-detection.yaml`

**Acceptance Criteria:**
- Uses both Groq LLM and Python regex providers
- Loads test cases from external JSON file
- Shows side-by-side results in promptfoo UI
- Includes assertions for comparison

### Phase 4: Comparison Assertions (M)
Add specialized assertions to compare regex vs LLM results.

**Acceptance Criteria:**
- Assert when both agree on detection
- Flag discrepancies (LLM-only, regex-only)
- Include confidence thresholds
- Generate comparison summary

## Detailed Tasks

### Phase 1 Tasks

1.1. **Create regex_provider.py** (S)
- Implement `call_api()` function
- Setup Django environment
- Parse user_prompt to extract PR body
- Run `detect_ai_in_text()`
- Format response as LLM-compatible JSON

1.2. **Add standalone test mode** (S)
- Add `if __name__ == "__main__"` block
- Test with sample prompts
- Verify output format

### Phase 2 Tasks

2.1. **Create export_comparison_tests command** (M)
- Query PRs with body content
- Pre-compute regex results for each
- Build user prompts using `build_llm_pr_context()`
- Generate JSON test cases

2.2. **Add comparison metadata** (S)
- Include regex detection result
- Include pattern version
- Include existing is_ai_assisted flag from DB

2.3. **Generate assertions** (S)
- Create assertions based on regex baseline
- Flag expected agreements/disagreements

### Phase 3 Tasks

3.1. **Create compare-detection.yaml** (S)
- Define both providers
- Reference external test cases file
- Configure output path

3.2. **Document usage** (S)
- Add usage comments in YAML
- Document workflow in README

### Phase 4 Tasks

4.1. **Add agreement assertions** (S)
- Assert both detect or both miss
- Track agreement rate

4.2. **Add discrepancy handling** (M)
- Custom assertion for LLM-only detections
- Custom assertion for regex-only detections
- Include in comparison report

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Promptfoo Python provider compatibility | Low | Medium | Test with promptfoo versions, provide JS fallback |
| Django setup in provider | Low | Low | Well-documented pattern, already used in other scripts |
| Large test case files | Medium | Low | Use `--limit` to control size, stream JSON |
| Rate limiting on large comparisons | Medium | Medium | Use `maxConcurrency: 3` in config |

## Success Metrics

1. **Functional**: Both providers return valid JSON responses
2. **Comparison**: Side-by-side results visible in promptfoo UI
3. **Accuracy**: Identify specific PRs where regex/LLM disagree
4. **Actionable**: Generate list of pattern improvement opportunities

## Required Resources

### Dependencies
- promptfoo >= 0.70.0 (Python provider support)
- Existing Django app infrastructure
- Groq API key for LLM provider

### Files Modified
- None (all new files)

### Files Created
- `dev/active/ai-detection-pr-descriptions/experiments/regex_provider.py`
- `dev/active/ai-detection-pr-descriptions/experiments/compare-detection.yaml`
- `apps/metrics/management/commands/export_comparison_tests.py`
- `apps/metrics/tests/test_export_comparison_tests.py`

## Test Commands

```bash
# Test regex provider standalone
cd dev/active/ai-detection-pr-descriptions/experiments
python regex_provider.py

# Export comparison test cases
python manage.py export_comparison_tests --limit 50 --output experiments/comparison-test-cases.json

# Run comparison evaluation
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=... npx promptfoo eval -c compare-detection.yaml

# View results
npx promptfoo view
```
