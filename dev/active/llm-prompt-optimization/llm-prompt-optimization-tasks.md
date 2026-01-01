# LLM Prompt Optimization - Tasks

**Last Updated**: 2026-01-01
**Status**: ✅ COMPLETED

---

## Phase 1: Baseline Measurement ✅

**Objective**: Establish current performance metrics before any changes.

- [x] **1.1** Run `make export-prompts` to generate promptfoo config
- [x] **1.2** Execute full promptfoo evaluation with v7.0.0 prompts
- [x] **1.3** Document baseline pass/fail rates:
  - AI detection positive tests: 12/12 ✅
  - AI detection negative tests: 10/12 (2 failed: coderabbit, greptile)
  - AI detection edge cases: 7/7 ✅
  - Tech detection tests: 4/4 ✅
  - Summary tests: 5/5 ✅
  - Health tests: 4/4 ✅
- [x] **1.4** Create `results/baseline-v7.0.0/` directory with all outputs

**Result**: 47 tests, 45 passed (95.7%), 2 failed

---

## Phase 2: Tech Detection Enhancement ✅

**Objective**: Improve technology and framework detection accuracy.

### 2.1 Analyze Current Gaps ✅

- [x] **2.1.1** Review existing tech detection tests in golden_tests.py
- [x] **2.1.2** Identify file extensions not currently mapped
- [x] **2.1.3** Identify frameworks without detection signals
- [x] **2.1.4** Document category assignment edge cases

### 2.2 Create Enhanced Tech Detection Template ✅

- [x] **2.2.1** Create file extension → language mapping table (22 extensions)
- [x] **2.2.2** Create framework detection signal table (16 frameworks)
- [x] **2.2.3** Create category assignment rules with disambiguation
- [x] **2.2.4** Write enhanced `tech_detection.jinja2` template

### 2.3 Add Few-Shot Examples ✅

- [x] **2.3.1** Create example: Backend Python/Django PR
- [x] **2.3.2** Create example: Frontend React/TypeScript PR
- [x] **2.3.3** Create example: DevOps Docker/CI PR
- [x] **2.3.4** Create example: Full-stack multi-category PR
- [x] **2.3.5** Create example: Data SQL analytics PR

### 2.4 Add Golden Tests ✅

- [x] **2.4.1** `tech_rust_backend` - Rust backend with Cargo
- [x] **2.4.2** `tech_nextjs_fullstack` - Next.js with API routes
- [x] **2.4.3** `tech_terraform_infra` - Terraform infrastructure
- [x] **2.4.4** `tech_mobile_swift` - iOS Swift app
- [x] **2.4.5** `tech_data_pipeline` - Python data pipeline
- [x] **2.4.6** `tech_go_microservice` - Go microservice
- [x] **2.4.7** `tech_vue_frontend` - Vue.js frontend
- [x] **2.4.8** `tech_kotlin_android` - Android Kotlin app
- [x] **2.4.9** `tech_github_actions_ci` - GitHub Actions only
- [x] **2.4.10** `tech_sql_only` - SQL analytics tables

### 2.5 Evaluate Changes ✅

- [x] **2.5.1** Export updated prompts
- [x] **2.5.2** Run promptfoo evaluation
- [x] **2.5.3** Document improvements

**Result**: All 10 new tests pass

---

## Phase 3: Summary Quality Enhancement ✅

**Objective**: Improve title/description quality for CTO audience.

### 3.1 Create Summary Guidelines Section ✅

- [x] **3.1.1** Define title constraints (5-10 words)
- [x] **3.1.2** Define action verb requirements
- [x] **3.1.3** Define business language guidelines
- [x] **3.1.4** Create PR type decision tree (7-step priority)
- [x] **3.1.5** Write `summary_guidelines.jinja2` template

### 3.2 Add Good/Bad Example Pairs ✅

- [x] **3.2.1** Chore: Docker local dev example
- [x] **3.2.2** Feature: Terraform production infra example
- [x] **3.2.3** CI: GitHub Actions example
- [x] **3.2.4** Common classification mistakes section

### 3.3 Evaluate Changes ✅

- [x] **3.3.1** Export updated prompts
- [x] **3.3.2** Run promptfoo evaluation
- [x] **3.3.3** Verify all tests pass

**Result**: All 57 tests pass (100%)

---

## Phase 4: Prompt Structure Optimization ✅

**Objective**: Apply best practices from prompt engineering guide.

### 4.1 Restructure System Prompt ✅

- [x] **4.1.1** Enhance Identity section with clearer role definition
- [x] **4.1.2** Add summary_guidelines include to system.jinja2
- [x] **4.1.3** Use XML tags consistently for examples

### 4.2 Version Update ✅

- [x] **4.2.1** Update PROMPT_VERSION to "8.0.0" in llm_prompts.py
- [x] **4.2.2** Run full regression test
- [x] **4.2.3** Verify 100% pass rate

**Result**: PROMPT_VERSION = "8.0.0", all tests pass

---

## Phase 5: Langfuse Integration ⏸️ DEFERRED

**Status**: User decided not to introduce Langfuse at this time.

**Reason**: Focus on prompt improvements first, defer infrastructure changes.

**Future Consideration**: Can revisit for:
- Version control without code deploys
- A/B testing via labels
- Non-dev prompt editing
- Cost/latency tracking per version

---

## Summary Metrics Tracking

| Phase | Status | Tests Passing | Notes |
|-------|--------|---------------|-------|
| Baseline | ✅ | 45/47 | 2 AI detection failures |
| Tech Detection | ✅ | 55/57 | Added 10 new tests |
| Summary Quality | ✅ | 57/57 | Added guidelines |
| Structure | ✅ | 57/57 | v8.0.0 released |
| Langfuse | ⏸️ | N/A | Deferred |

---

## Rollback Checklist (Not Needed)

- [ ] Revert PROMPT_VERSION to "7.0.0"
- [ ] Remove summary_guidelines include
- [ ] Disable Langfuse feature flag (if enabled)
- [ ] Notify team of rollback
- [ ] Document issues for post-mortem
