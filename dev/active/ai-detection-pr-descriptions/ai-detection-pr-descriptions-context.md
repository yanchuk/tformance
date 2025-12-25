# AI Detection PR Descriptions - Context

**Last Updated**: 2025-12-25

## Current State

### Prompt Version: 6.8.0

The LLM prompt system for AI detection is production-ready with:
- Jinja2 template-based prompt rendering
- 46 golden test cases (29 original + 17 new) covering all categories
- TDD data consistency validation
- Promptfoo evaluation passing **47/47 tests (100%)**

### Recent Session Work (2025-12-25)

**Extended Golden Tests (17 new cases):**

| Category | New Tests |
|----------|-----------|
| POSITIVE | pos_cody_sourcegraph, pos_coderabbit_review, pos_devin_bot_author, pos_tabnine_autocomplete, pos_greptile_codebase |
| NEGATIVE | neg_sdk_version_bump, neg_ai_documentation, neg_llm_test_suite, neg_ai_competitor_analysis, neg_openai_client_library |
| EDGE_CASE | edge_indirect_disclosure, edge_review_comment_ai, edge_ai_typo_false_positive, edge_github_actions_ai, confidence_high_signature, confidence_medium_mention, confidence_low_ambiguous, multi_tool_cursor_claude_copilot |

**Prompt Improvements (v6.5.0 → v6.8.0):**

1. **v6.6.0 - Logical consistency + vague words + security**
   - Added: `LOGICAL CONSISTENCY: If is_assisted=false, tools array MUST be empty`
   - Added: Vague mentions rule ("assistance", "help" without AI context)
   - Added: Security Notice for prompt injection protection

2. **v6.7.0 - CI/CD configuration rule**
   - Added: CI/CD configuration with AI tools is NOT AI-assisted
   - Configuring GitHub Actions (coderabbit-ai/action) != using AI to code

3. **v6.8.0 - PR type definitions**
   - Clarified: "feature" = product functionality visible to users
   - Clarified: "chore" = Docker, deps, local dev config
   - Clarified: "ci" = .github/workflows/, Jenkins, CircleCI

## Architecture

### Prompt Template System

```
apps/metrics/prompts/
├── templates/
│   ├── system.jinja2          # Main system prompt
│   ├── user.jinja2            # User prompt with PR context
│   └── sections/              # Composable sections
│       ├── intro.jinja2       # Intro + Security Notice
│       ├── ai_detection.jinja2
│       ├── tech_detection.jinja2
│       ├── health_assessment.jinja2
│       ├── response_schema.jinja2
│       ├── definitions.jinja2
│       └── enums.jinja2
├── golden_tests.py            # 46 test cases (single source of truth)
├── render.py                  # Template rendering
├── export.py                  # Promptfoo YAML generation
└── tests/                     # TDD tests
```

### Golden Test Categories

| Category | Count | Purpose |
|----------|-------|---------|
| POSITIVE | 11 | Should detect AI |
| NEGATIVE | 12 | Should NOT detect AI |
| EDGE_CASE | 10 | Boundary cases, confidence calibration |
| TECH_DETECTION | 4 | Technology categorization |
| SUMMARY | 5 | PR type classification |
| HEALTH | 4 | Health assessment |

## Key Decisions

1. **repo_name is required** - All golden tests must have repo_name for consistent LLM context
2. **file_count must match file_paths** - TDD tests enforce this constraint
3. **Realistic test data** - Tests use believable file paths, author names, timelines
4. **AI company repos** - vercel/ai, anthropics/cookbook used to test skeptical detection
5. **Logical consistency** - is_assisted and tools must be consistent (both or neither)
6. **Prompt injection protection** - Security notice prevents malicious PR descriptions

## Commands

```bash
# Run golden tests
.venv/bin/pytest apps/metrics/prompts/tests/ -v

# Regenerate promptfoo config
.venv/bin/python manage.py export_prompts

# Run LLM evaluation
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=$(grep "^GROQ_API_KEY" .env | cut -d= -f2) npx promptfoo eval -c promptfoo.yaml

# View results
npx promptfoo view
```

## Integration Points

- `apps/integrations/services/groq_batch.py` - LLM batch processing
- `apps/integrations/services/github_graphql_sync.py` - PR sync with AI detection
- `apps/metrics/services/ai_patterns.py` - Regex patterns (v1.9.0)
- `apps/metrics/services/llm_prompts.py` - PROMPT_VERSION + user prompt builder

## No Migrations Needed

This session only modified test data and prompt templates - no model changes.
