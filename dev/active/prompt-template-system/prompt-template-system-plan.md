# Prompt Template System - Implementation Plan

**Last Updated:** 2025-12-25

## Executive Summary

Implement a robust prompt template management system for LLM-based PR analysis. This addresses critical issues with the current implementation: manual sync between code and test files, monolithic prompt structure, embedded schemas, and fragmented test cases.

The system will provide:
- **Auto-generated promptfoo configs** eliminating version drift
- **JSON Schema validation** for LLM responses
- **Jinja2 template composition** for modular prompts
- **Unified golden tests** shared between Python and promptfoo

## Current State Analysis

### Existing Architecture

```
apps/metrics/services/llm_prompts.py
├── PROMPT_VERSION = "6.2.0" (string constant)
├── PR_ANALYSIS_SYSTEM_PROMPT (126-line monolithic string)
├── get_user_prompt() (dynamic context builder)
└── build_llm_pr_context() (unified PR data extraction)

dev/active/ai-detection-pr-descriptions/experiments/
├── promptfoo.yaml (references v5-system.txt - STALE!)
├── prompts/v5-system.txt, v6-system.txt (manual copies)
└── test-cases-*.json (curated test data)
```

### Pain Points

| Problem | Current State | Impact |
|---------|---------------|--------|
| Version drift | promptfoo.yaml uses v5, code is v6.2 | Tests don't match production |
| Manual sync | Copy prompt to .txt file manually | Error-prone, forgotten |
| No schema validation | Schema in prose, not code | Can't validate responses |
| Monolithic prompt | One 126-line string | Can't iterate on sections |
| Scattered tests | promptfoo.yaml separate from unit tests | Duplicate maintenance |

## Proposed Future State

### Target Architecture

```
apps/metrics/prompts/
├── __init__.py
├── registry.py              # PromptVersion dataclass, CHANGELOG
├── schemas.py               # JSON Schema for response validation
├── render.py                # render_system_prompt(), render_user_prompt()
├── export.py                # export_promptfoo_config()
├── golden_tests.py          # GOLDEN_TESTS list, GoldenTest dataclass
│
├── templates/
│   ├── system.jinja2        # Main prompt (includes sections)
│   ├── user.jinja2          # User prompt template
│   └── sections/
│       ├── ai_detection.jinja2
│       ├── tech_detection.jinja2
│       ├── health_assessment.jinja2
│       ├── response_schema.jinja2
│       └── enums.jinja2
│
└── tests/
    └── test_prompts.py      # Moved from apps/metrics/tests/

apps/metrics/management/commands/
└── export_prompts.py        # Generate promptfoo config
```

### Key Benefits

1. **Single source of truth** - Templates in code, auto-exported
2. **Version metadata** - Changelog, author, breaking changes tracked
3. **Response validation** - JSON Schema validates LLM output
4. **Modular iteration** - Edit sections independently
5. **Unified testing** - Golden tests shared across frameworks

---

## Implementation Phases

### Phase 1: Eliminate Manual Sync (Quick Win)

**Goal:** Auto-generate promptfoo configuration from Python code

**Scope:**
- Create `export_prompts` management command
- Generate promptfoo.yaml with correct version reference
- Export current prompt to versioned .txt file
- Update CI to regenerate before testing

**Acceptance Criteria:**
- Running `python manage.py export_prompts` generates valid promptfoo config
- Generated config references correct prompt version
- `npx promptfoo eval` passes with generated config

---

### Phase 2: Extract Response Schema

**Goal:** Move JSON response schema from prose to actual JSON Schema

**Scope:**
- Create `schemas.py` with PR_ANALYSIS_RESPONSE_SCHEMA
- Add jsonschema validation to tests
- Use schema in promptfoo assertions
- Generate schema docs for prompts

**Acceptance Criteria:**
- JSON Schema validates all expected response fields
- Unit tests validate LLM responses against schema
- Promptfoo uses schema-based assertions

---

### Phase 3: Template Composition (Jinja2)

**Goal:** Split monolithic prompt into composable Jinja2 templates

**Scope:**
- Create `templates/` directory structure
- Split PR_ANALYSIS_SYSTEM_PROMPT into sections
- Create `render_system_prompt()` function
- Maintain backward compatibility (identical output)

**Acceptance Criteria:**
- Rendered prompt identical to current hardcoded version
- Each section editable independently
- Templates loadable without Django running

---

### Phase 4: Golden Test Unification

**Goal:** Single source of truth for prompt test cases

**Scope:**
- Create `golden_tests.py` with GoldenTest dataclass
- Define GOLDEN_TESTS covering all edge cases
- Export to promptfoo test format
- Use same cases in unit tests

**Acceptance Criteria:**
- All promptfoo test cases generated from Python
- Unit tests and promptfoo use identical test data
- Adding a test case auto-appears in both frameworks

---

## Detailed Task Breakdown

### Phase 1 Tasks

#### 1.1 Create export_prompts management command
**Effort:** M
**Dependencies:** None

```python
# apps/metrics/management/commands/export_prompts.py
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--output", default="dev/active/ai-detection-pr-descriptions/experiments/")

    def handle(self, *args, **options):
        # 1. Write current system prompt to v{VERSION}-system.txt
        # 2. Generate promptfoo.yaml with correct references
        # 3. Report what was generated
```

**Acceptance:**
- Command runs without errors
- Creates versioned prompt file
- Creates valid promptfoo.yaml

#### 1.2 Generate promptfoo.yaml dynamically
**Effort:** M
**Dependencies:** 1.1

Create YAML config with:
- Correct prompt version reference
- Provider config (groq:llama-3.3-70b-versatile)
- Default test variables
- Placeholder for test cases

#### 1.3 Add to Makefile
**Effort:** S
**Dependencies:** 1.1

```makefile
export-prompts:
	python manage.py export_prompts
```

#### 1.4 Update documentation
**Effort:** S
**Dependencies:** 1.1, 1.2

Update `prd/AI-DETECTION-TESTING.md` with new workflow.

---

### Phase 2 Tasks

#### 2.1 Create schemas.py with JSON Schema
**Effort:** M
**Dependencies:** None

```python
# apps/metrics/prompts/schemas.py
PR_ANALYSIS_RESPONSE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "required": ["ai", "tech", "summary", "health"],
    "properties": {
        "ai": {...},
        "tech": {...},
        "summary": {...},
        "health": {...}
    }
}
```

#### 2.2 Add jsonschema to dependencies
**Effort:** S
**Dependencies:** None

```bash
uv add jsonschema
```

#### 2.3 Create schema validation helper
**Effort:** S
**Dependencies:** 2.1, 2.2

```python
def validate_llm_response(response: dict) -> tuple[bool, list[str]]:
    """Validate LLM response against schema, return (valid, errors)."""
```

#### 2.4 Add schema validation to tests
**Effort:** M
**Dependencies:** 2.3

Update `test_llm_prompts.py` to validate responses.

#### 2.5 Generate schema for promptfoo
**Effort:** S
**Dependencies:** 2.1

Export schema as YAML for promptfoo JavaScript assertions.

---

### Phase 3 Tasks

#### 3.1 Create prompts package structure
**Effort:** S
**Dependencies:** None

```bash
mkdir -p apps/metrics/prompts/templates/sections
touch apps/metrics/prompts/__init__.py
touch apps/metrics/prompts/templates/system.jinja2
```

#### 3.2 Add Jinja2 dependency
**Effort:** S
**Dependencies:** None

```bash
uv add Jinja2
```

#### 3.3 Split system prompt into sections
**Effort:** L
**Dependencies:** 3.1

Create template files:
- `sections/ai_detection.jinja2` - AI detection rules
- `sections/tech_detection.jinja2` - Technology detection
- `sections/health_assessment.jinja2` - Health metrics
- `sections/response_schema.jinja2` - JSON format spec
- `sections/enums.jinja2` - Tool/language/framework lists

#### 3.4 Create render_system_prompt() function
**Effort:** M
**Dependencies:** 3.2, 3.3

```python
def render_system_prompt(
    include_health: bool = True,
    include_tech: bool = True,
) -> str:
    """Render system prompt from Jinja2 templates."""
```

#### 3.5 Create render_user_prompt() function
**Effort:** M
**Dependencies:** 3.2

Refactor `get_user_prompt()` to use Jinja2 template.

#### 3.6 Verify output equivalence
**Effort:** M
**Dependencies:** 3.4, 3.5

Add test that compares rendered output to original hardcoded prompt.

#### 3.7 Update llm_prompts.py to use new render functions
**Effort:** S
**Dependencies:** 3.6

Replace hardcoded strings with render function calls.

---

### Phase 4 Tasks

#### 4.1 Create GoldenTest dataclass
**Effort:** S
**Dependencies:** None

```python
@dataclass
class GoldenTest:
    id: str
    description: str
    pr_title: str = ""
    pr_body: str = ""
    additions: int = 0
    deletions: int = 0
    expected_ai_assisted: bool | None = None
    expected_tools: list[str] = field(default_factory=list)
    min_confidence: float = 0.0
    expected_tech_categories: list[str] = field(default_factory=list)
    expected_pr_type: str | None = None
```

#### 4.2 Define GOLDEN_TESTS from existing promptfoo cases
**Effort:** M
**Dependencies:** 4.1

Migrate all test cases from promptfoo.yaml to Python.

#### 4.3 Create export_to_promptfoo_tests()
**Effort:** M
**Dependencies:** 4.1, 4.2

```python
def export_to_promptfoo_tests() -> list[dict]:
    """Convert GOLDEN_TESTS to promptfoo test format."""
```

#### 4.4 Update export_prompts command to include tests
**Effort:** S
**Dependencies:** 4.3

Generate complete promptfoo.yaml with test cases.

#### 4.5 Create unit tests using golden tests
**Effort:** M
**Dependencies:** 4.2

```python
class TestGoldenCases(TestCase):
    def test_golden_tests_cover_key_scenarios(self):
        """Ensure golden tests cover positive, negative, edge cases."""
```

#### 4.6 Add production failure import workflow
**Effort:** M
**Dependencies:** 4.1

```python
# Management command to add failed cases
python manage.py add_golden_test --pr-id 12345 --expected-ai-assisted true
```

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Jinja2 template errors at runtime | Medium | High | Comprehensive tests, pre-render validation |
| Schema too strict, rejects valid responses | Medium | Medium | Start permissive, tighten gradually |
| Performance impact from template rendering | Low | Low | Cache rendered templates |
| Breaking existing tests | Medium | High | Run full test suite at each phase |

### Process Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Scope creep to advanced features | High | Medium | Strict phase boundaries |
| Incomplete migration leaves dual systems | Medium | High | Phase 3 must update llm_prompts.py |

---

## Success Metrics

### Phase 1
- [ ] `export_prompts` command runs in < 1 second
- [ ] Generated promptfoo.yaml passes validation
- [ ] Zero manual steps required to sync prompts

### Phase 2
- [ ] 100% of response fields covered by schema
- [ ] Schema validation catches malformed responses
- [ ] Promptfoo uses schema-based assertions

### Phase 3
- [ ] Rendered prompt byte-identical to original
- [ ] Each section < 50 lines
- [ ] Template render time < 10ms

### Phase 4
- [ ] All 25+ promptfoo test cases in Python
- [ ] Single source generates both test frameworks
- [ ] Adding test case takes < 5 minutes

---

## Required Resources

### Dependencies

```toml
# pyproject.toml additions
jsonschema = "^4.23"
Jinja2 = "^3.1"  # May already be installed via Django
```

### Files to Create

| File | Purpose |
|------|---------|
| `apps/metrics/prompts/__init__.py` | Package init |
| `apps/metrics/prompts/registry.py` | Version tracking |
| `apps/metrics/prompts/schemas.py` | JSON Schema |
| `apps/metrics/prompts/render.py` | Template rendering |
| `apps/metrics/prompts/export.py` | Promptfoo generation |
| `apps/metrics/prompts/golden_tests.py` | Test cases |
| `apps/metrics/prompts/templates/*.jinja2` | Templates |
| `apps/metrics/management/commands/export_prompts.py` | CLI command |

### Files to Modify

| File | Changes |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | Use render functions |
| `apps/metrics/tests/test_llm_prompts.py` | Add schema validation |
| `prd/AI-DETECTION-TESTING.md` | Updated workflow |
| `Makefile` | Add export-prompts target |

---

## Timeline Estimate

| Phase | Effort | Estimated Duration |
|-------|--------|-------------------|
| Phase 1 | Medium | 2-3 hours |
| Phase 2 | Medium | 2-3 hours |
| Phase 3 | Large | 4-6 hours |
| Phase 4 | Medium | 3-4 hours |
| **Total** | | **11-16 hours** |

Phases can be implemented incrementally with production value at each step.
