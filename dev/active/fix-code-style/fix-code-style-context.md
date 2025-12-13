# Fix code-style Context

**Last Updated:** 2025-12-13

## Key Files

### Workflow Configuration
- `.github/workflows/tests.yml` - GitHub Actions workflow with `code-style` job
- `.pre-commit-config.yaml` - Pre-commit hooks configuration

### Files to Fix
| File | Line(s) | Error | Fix |
|------|---------|-------|-----|
| `apps/integrations/tests/test_github_comments.py` | 155 | F841 | Remove `result =` |
| `apps/metrics/tests/test_security_isolation.py` | 288 | F841 | Remove `all_avg =` |
| `apps/metrics/services/survey_tokens.py` | 91 | B904 | Add `from None` |
| `apps/integrations/webhooks/slack_interactions.py` | 22-32 | E402 | Move imports to top |
| `apps/metrics/tests/test_pr_processor.py` | 349, 371, 394 | SIM117 | Combine `with` |

### Already Fixed (in working directory)
| File | Line(s) | Error | Status |
|------|---------|-------|--------|
| `apps/metrics/tests/test_survey_tokens.py` | 403 | F841 | Fixed |
| `apps/utils/middleware.py` | 53, 54, 57 | E501 | Fixed |
| `apps/web/decorators.py` | 45, 53 | B904 | Fixed |
| `apps/web/decorators.py` | 79-81 | SIM103 | Fixed |

## Technical Decisions

### Import Reordering Strategy
The `slack_interactions.py` file has imports after a constant definition. The constant `MAX_SLACK_PAYLOAD_SIZE` is defined before imports. Strategy: Move constant after all imports.

### Exception Chaining
Use `from None` when the original exception should be suppressed (we're replacing it with a cleaner error), use `from e` when we want to preserve the traceback.

## Dependencies

- ruff v0.13.1 (specified in `.pre-commit-config.yaml`)
- Python 3.12

## Commands

```bash
# Check specific files
.venv/bin/ruff check apps/path/to/file.py

# Fix auto-fixable issues
make ruff

# Run all pre-commit hooks
pre-commit run --all-files

# Run tests to verify changes
make test ARGS='--keepdb'
```

## GitHub Actions Job Details

```yaml
# From .github/workflows/tests.yml
code-style:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python 3.12
      uses: actions/setup-python@v5
      with:
        python-version: 3.12
    - name: Run pre-commit hooks
      uses: pre-commit/action@v3.0.0
```
