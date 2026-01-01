# LLM Prompt Optimization - Context

**Last Updated**: 2026-01-01
**Status**: ✅ COMPLETED

---

## Key Files

### Prompt Source Files

| File | Purpose | Lines |
|------|---------|-------|
| `apps/metrics/services/llm_prompts.py` | PR analysis system prompt + user prompt builder | 839 |
| `apps/metrics/services/insight_llm.py` | Dashboard insight generation (reference) | 601 |
| `apps/metrics/prompts/templates/system.jinja2` | Modular system prompt template | 16 |
| `apps/metrics/prompts/templates/sections/intro.jinja2` | Identity + security notice | 50 |
| `apps/metrics/prompts/templates/sections/ai_detection.jinja2` | AI detection rules (STRONG) | 46 |
| `apps/metrics/prompts/templates/sections/tech_detection.jinja2` | Tech detection (ENHANCED v8.0.0) | 105 |
| `apps/metrics/prompts/templates/sections/summary_guidelines.jinja2` | PR type + summary rules (NEW v8.0.0) | 60 |
| `apps/metrics/prompts/templates/sections/health_assessment.jinja2` | Health assessment rules | ~30 |
| `apps/metrics/prompts/templates/sections/response_schema.jinja2` | JSON output schema | ~40 |
| `apps/metrics/prompts/templates/sections/definitions.jinja2` | Category/type definitions | ~20 |
| `apps/metrics/prompts/templates/sections/enums.jinja2` | Tool/language/framework lists | ~10 |

### Testing Files

| File | Purpose | Test Count |
|------|---------|------------|
| `apps/metrics/prompts/golden_tests.py` | Golden test cases dataclass + tests | 57 tests |
| `apps/metrics/prompts/insight_promptfoo.yaml` | Promptfoo evaluation config | - |

### Documentation

| File | Purpose |
|------|---------|
| `prd/PROMPT-ENGINEERING.md` | Project prompt engineering guide |
| `prd/AI-DETECTION-TESTING.md` | AI detection testing workflow |
| `.claude/skills/prompt-engineer/` | Claude Code prompt engineering skill |

---

## Current Prompt Versions

| Prompt | Version | Last Updated |
|--------|---------|--------------|
| PR Analysis System | **8.0.0** | **2026-01-01** |
| Dashboard Insight | Version K | 2025-12-31 |

---

## Results Summary

### Baseline (v7.0.0)

**Evaluated**: 2026-01-01
**Results**: `results/baseline-v7.0.0/`

| Metric | Value |
|--------|-------|
| **Total Tests** | 47 |
| **Passed** | 45 (95.7%) |
| **Failed** | 2 (4.3%) |

**Failed Tests**:
1. `pos_coderabbit_review` - Failed to detect CodeRabbit as AI tool
2. `pos_greptile_codebase` - Failed to detect Greptile as AI tool

### Final (v8.0.0)

**Evaluated**: 2026-01-01
**Results**: `results/v8.0.0-final/`

| Metric | v7.0.0 Baseline | v8.0.0 Final | Improvement |
|--------|-----------------|--------------|-------------|
| **Total Tests** | 47 | 57 | +10 new |
| **Passed** | 45 (95.7%) | 57 (100%) | +12 tests |
| **Failed** | 2 | 0 | Fixed all |

---

## What Changed in v8.0.0

### 1. Enhanced Tech Detection (`tech_detection.jinja2`)

- File extension → language mapping table (22 extensions)
- Framework detection signal table (16 frameworks)
- Category assignment rules with disambiguation
- SQL category disambiguation (data vs backend)
- 5 few-shot examples with reasoning

### 2. New Summary Guidelines (`summary_guidelines.jinja2`)

- PR type decision tree (7-step priority order)
- Common classification mistakes (infra, DB migrations)
- Title/description rules with good/bad examples
- 5 type examples with reasoning

### 3. Enhanced Identity Section (`intro.jinja2`)

- Clearer role definition
- "Senior engineering analyst" framing
- Business impact focus

### 4. New Test Coverage

| Category | New Tests |
|----------|-----------|
| Rust backend | tech_rust_backend |
| Next.js fullstack | tech_nextjs_fullstack |
| Terraform | tech_terraform_infra |
| iOS Swift | tech_mobile_swift |
| Data pipeline | tech_data_pipeline |
| Go microservice | tech_go_microservice |
| Vue frontend | tech_vue_frontend |
| Android Kotlin | tech_kotlin_android |
| GitHub Actions | tech_github_actions_ci |
| SQL analytics | tech_sql_only |

---

## Golden Test Categories (57 total)

| Category | Count | Description |
|----------|-------|-------------|
| POSITIVE | 12 | Should detect AI usage |
| NEGATIVE | 12 | Should NOT detect AI usage |
| EDGE_CASE | 10 | Ambiguous or boundary conditions |
| TECH_DETECTION | 14 | Technology detection focus |
| SUMMARY | 5 | Summary generation focus |
| HEALTH | 4 | Health assessment focus |

---

## Key Decisions

### Decision 1: Keep AI Detection Unchanged

**Status**: Approved
**Rationale**: AI detection is already well-structured with 46 lines of detailed rules. Risk of regression is not worth potential gain.

### Decision 2: Use Jinja2 Templates for Modularity

**Status**: Current practice
**Rationale**: Templates in `templates/sections/` allow independent iteration on each section while maintaining a unified system prompt.

### Decision 3: Apply OpenAI Prompt Structure

**Status**: Implemented
**Reference**: prd/PROMPT-ENGINEERING.md

Structure order:
1. Identity (who is the model)
2. Instructions (rules, constraints)
3. Examples (few-shot learning)
4. Context (dynamic data at end for caching)

### Decision 4: Use XML Tags for Examples

**Status**: Implemented
**Rationale**: Per Anthropic best practices, XML tags with attributes provide clear boundaries.

### Decision 5: Defer Langfuse Integration

**Status**: Deferred
**Rationale**: User decided to focus on prompt improvements first, defer infrastructure changes.

---

## Prompt Token Estimates

| Section | v7.0.0 Tokens | v8.0.0 Tokens | Delta |
|---------|---------------|---------------|-------|
| Identity | ~30 | ~50 | +20 |
| Security Notice | ~100 | ~100 | - |
| AI Detection Rules | ~400 | ~400 | - |
| Tech Detection | ~80 | ~350 | +270 |
| Summary Guidelines | 0 | ~400 | +400 |
| Health Assessment | ~150 | ~150 | - |
| Response Format | ~200 | ~200 | - |
| Examples | ~0 | ~200 | +200 |
| Enums | ~100 | ~100 | - |
| **Total** | **~1,500** | **~2,100** | **+600** |

**Cost Impact**: ~40% token increase (~$0.0002/request). Justified by 100% vs 95.7% accuracy.

---

## Model Configuration

### PR Analysis (Batch Processing)

| Setting | Value | Rationale |
|---------|-------|-----------|
| Model | llama-3.3-70b-versatile | Good JSON output, cost-effective |
| Temperature | 0.1 | Low variance for structured output |
| Max tokens | 1000 | JSON response ~300-500 tokens |
| Response format | json_object | Enforce JSON output |

### Dashboard Insights

| Setting | Value | Rationale |
|---------|-------|-----------|
| Primary Model | openai/gpt-oss-120b | Best prose quality |
| Fallback Model | llama-3.3-70b-versatile | Reliable backup |
| Temperature | 0.2 | Slight creativity for prose |
| Max tokens | 600 | Short insight text |
| Response format | json_schema (strict) | 100% JSON reliability |

---

## Dependencies

### External Services

| Service | Usage | Credentials |
|---------|-------|-------------|
| Groq API | LLM inference | GROQ_API_KEY env var |

### Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| groq | latest | Groq API client |
| jinja2 | 3.x | Template rendering |

### NPM Packages

| Package | Version | Purpose |
|---------|---------|---------|
| promptfoo | latest | Prompt evaluation |

---

## Verification Commands

```bash
# Run golden tests
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/pytest apps/metrics/prompts/tests/ -v

# Export and run promptfoo evaluation
python manage.py export_prompts --output results/verify
cd results/verify && npx promptfoo eval -c promptfoo.yaml

# Check prompt version
grep PROMPT_VERSION apps/metrics/services/llm_prompts.py
```

---

## Reference: Prompt Engineering Best Practices

From `.claude/skills/prompt-engineer/`:

### Structure Order (for Caching)
```
1. IDENTITY      → Static role definition
2. INSTRUCTIONS  → Static rules and constraints
3. EXAMPLES      → Semi-static few-shot pairs
4. CONTEXT       → Dynamic data (at end)
```

### GPT Model Guidance
- Treat as "junior coworker" - needs explicit instructions
- Provide step-by-step processes
- Be very specific about output format
- Use detailed examples

### Few-Shot Examples
- Show 2-5 diverse examples
- Include edge cases
- Add `<reasoning>` tags to explain decisions
- Use consistent XML formatting
