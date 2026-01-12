# Copilot Development Guide

This guide covers the Copilot mock data system for development and testing without real Copilot API access.

## Why Mock Data?

GitHub requires **5+ Copilot licenses** to access the metrics API. For development and testing without real Copilot access, use the mock data system.

## Quick Start

```bash
# Seed demo Copilot data for a team
.venv/bin/python manage.py seed_copilot_demo --team=my-team --scenario=growth --weeks=8

# With PR correlation (marks PRs as AI-assisted based on Copilot usage)
.venv/bin/python manage.py seed_copilot_demo --team=my-team --scenario=mixed_usage --correlate-prs

# Clear existing and reseed
.venv/bin/python manage.py seed_copilot_demo --team=my-team --scenario=high_adoption --clear-existing
```

## Enable Mock Mode for API Calls

Add to `.env` or Django settings to make `fetch_copilot_metrics()` return mock data instead of real API calls:

```bash
COPILOT_USE_MOCK_DATA=True
COPILOT_MOCK_SEED=42           # For reproducible data
COPILOT_MOCK_SCENARIO=mixed_usage
```

## Available Scenarios

| Scenario | Acceptance Rate | Description |
|----------|-----------------|-------------|
| `high_adoption` | 40-55% | Power users, high acceptance |
| `low_adoption` | 15-30% | Struggling team, low acceptance |
| `growth` | 20% → 50% | Improving adoption over time |
| `decline` | 50% → 20% | Declining usage over time |
| `mixed_usage` | Variable | Realistic mix of user types (default) |
| `inactive_licenses` | Some 0% | Users with licenses but no usage |

## Key Files

| File | Purpose |
|------|---------|
| `apps/integrations/services/copilot_mock_data.py` | `CopilotMockDataGenerator` class |
| `apps/integrations/services/copilot_metrics.py` | API client with mock mode toggle |
| `apps/integrations/services/copilot_pr_correlation.py` | Correlate PRs with Copilot usage |
| `apps/integrations/services/copilot_metrics_prompt.py` | Aggregate metrics for LLM prompts |
| `apps/metrics/management/commands/seed_copilot_demo.py` | Management command |
| `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2` | LLM prompt template |

## Using in Code

```python
# Generate mock data directly
from apps.integrations.services.copilot_mock_data import CopilotMockDataGenerator

generator = CopilotMockDataGenerator(seed=42)
data = generator.generate(since="2025-01-01", until="2025-01-31", scenario="growth")

# Fetch metrics (respects COPILOT_USE_MOCK_DATA setting)
from apps.integrations.services.copilot_metrics import fetch_copilot_metrics

metrics = fetch_copilot_metrics(access_token, org_slug, since="2025-01-01")

# Correlate PRs with Copilot usage
from apps.integrations.services.copilot_pr_correlation import correlate_prs_with_copilot_usage

count = correlate_prs_with_copilot_usage(team, min_suggestions=1)

# Get metrics for LLM prompts
from apps.integrations.services.copilot_metrics_prompt import get_copilot_metrics_for_prompt

prompt_data = get_copilot_metrics_for_prompt(team, start_date, end_date)
```

## Generated Data Format

Mock data matches the exact GitHub Copilot Metrics API schema:

```json
{
  "date": "2025-01-06",
  "total_active_users": 15,
  "total_engaged_users": 12,
  "copilot_ide_code_completions": {
    "total_completions": 2500,
    "total_acceptances": 875,
    "total_lines_suggested": 4200,
    "total_lines_accepted": 1470,
    "languages": [...],
    "editors": [...]
  },
  "copilot_ide_chat": { "total_chats": 45 },
  "copilot_dotcom_chat": { "total_chats": 12 },
  "copilot_dotcom_pull_requests": { "total_prs": 5 }
}
```
