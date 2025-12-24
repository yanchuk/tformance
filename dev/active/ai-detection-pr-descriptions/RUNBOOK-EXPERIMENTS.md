# AI Detection Experiments Runbook

**Purpose**: This runbook enables running AI detection experiments without prior context. Follow these steps to iterate on prompts, test new repos, and analyze results.

## Quick Start

```bash
# 1. Set environment variables
export GROQ_API_KEY="your-key"
export POSTHOG_API_KEY="your-key"

# 2. Run experiment on sample PRs
python manage.py run_ai_detection_experiment \
  --config experiments/default.yaml \
  --limit 50 \
  --dry-run

# 3. View results in PostHog dashboard
# https://app.posthog.com/project/<id>/llm-analytics
```

---

## Directory Structure

```
dev/active/ai-detection-pr-descriptions/
├── RUNBOOK-EXPERIMENTS.md      # This file - how to run experiments
├── RUNBOOK-PROMPTS.md          # How to modify detection prompts
├── RUNBOOK-REPOS.md            # How to add/modify target repos
├── llm-detection-architecture.md  # Technical architecture
├── experiments/
│   ├── default.yaml            # Default experiment config
│   ├── results/                # Experiment results (gitignored)
│   └── prompts/                # Prompt versions
│       ├── v1.md               # Initial prompt
│       ├── v2.md               # Improved prompt
│       └── current.md          # Symlink to active prompt
```

---

## Running Experiments

### 1. Using Management Command

```bash
# Full experiment with LLM
python manage.py run_ai_detection_experiment \
  --config experiments/default.yaml \
  --experiment-name "cursor-patterns-v2" \
  --limit 100

# Compare regex vs LLM
python manage.py run_ai_detection_experiment \
  --config experiments/default.yaml \
  --compare-regex \
  --limit 50

# Test specific repo
python manage.py run_ai_detection_experiment \
  --repo antiwork/gumroad \
  --limit 20
```

### 2. Using Python Script

```python
from apps.metrics.experiments.runner import ExperimentRunner

runner = ExperimentRunner(
    config_path="dev/active/ai-detection-pr-descriptions/experiments/default.yaml",
    experiment_name="my-experiment"
)

# Run on specific PRs
results = runner.run(pr_ids=[1, 2, 3])

# Run on team
results = runner.run(team="Antiwork", limit=50)

# Compare approaches
comparison = runner.compare_regex_vs_llm(limit=100)
```

### 3. Batch Processing (Groq Batch API)

```bash
# Create batch file
python manage.py create_detection_batch \
  --team "Antiwork" \
  --output /tmp/batch.jsonl

# Submit to Groq
python manage.py submit_detection_batch \
  --file /tmp/batch.jsonl \
  --window 24h

# Poll for results
python manage.py poll_detection_batch \
  --batch-id "batch_xxx"
```

---

## Experiment Configuration

### Config File Format (YAML)

```yaml
# experiments/default.yaml
experiment:
  name: "ai-detection-v1"
  description: "Test detection accuracy on Gumroad PRs"

model:
  provider: "groq"
  name: "llama-3.3-70b-versatile"
  temperature: 0
  max_tokens: 500

prompt:
  file: "prompts/current.md"
  # OR inline:
  # system: "You are an AI detection system..."
  # user_template: "Analyze this PR:\n\n{body}"

repos:
  - owner: antiwork
    repo: gumroad
    limit: 100
  - owner: anthropic
    repo: anthropic-cookbook
    limit: 50

logging:
  posthog:
    enabled: true
    project_key: "${POSTHOG_API_KEY}"
  local:
    enabled: true
    output_dir: "experiments/results"

evaluation:
  ground_truth_file: "experiments/ground_truth.json"  # optional
  metrics:
    - precision
    - recall
    - f1
    - agreement_rate
```

---

## Viewing Results

### PostHog Dashboard

1. Go to PostHog → LLM Analytics
2. Filter by:
   - `$ai_model = "llama-3.3-70b-versatile"`
   - `experiment_name = "your-experiment"`
3. View:
   - Cost per experiment
   - Latency distribution
   - Token usage
   - Error rates

### Local Results

```bash
# Results are saved to experiments/results/<experiment-name>/
ls experiments/results/my-experiment/
# results.json      - Full results
# summary.json      - Aggregated metrics
# disagreements.csv - Regex vs LLM disagreements
```

### Analysis Script

```python
from apps.metrics.experiments.analysis import ExperimentAnalysis

analysis = ExperimentAnalysis("experiments/results/my-experiment")

# Get summary
print(analysis.summary())

# Compare with baseline
print(analysis.compare_with("experiments/results/baseline"))

# Export for manual review
analysis.export_for_review("review.csv", sample=50)
```

---

## Common Tasks

### Task 1: Test a New Prompt

```bash
# 1. Create new prompt version
cp experiments/prompts/current.md experiments/prompts/v3.md
# Edit v3.md

# 2. Update config to use new prompt
# Edit experiments/default.yaml: prompt.file: "prompts/v3.md"

# 3. Run experiment
python manage.py run_ai_detection_experiment \
  --config experiments/default.yaml \
  --experiment-name "prompt-v3-test" \
  --limit 100

# 4. Compare with baseline
python manage.py compare_experiments \
  --baseline "prompt-v2" \
  --current "prompt-v3-test"
```

### Task 2: Add a New Repository

```bash
# 1. Add to config
# Edit experiments/default.yaml repos section

# 2. Fetch PRs from new repo
python apps/metrics/scripts/fetch_oss_prs.py \
  --repo owner/repo \
  --limit 100

# 3. Run experiment on new repo
python manage.py run_ai_detection_experiment \
  --repo owner/repo \
  --limit 50
```

### Task 3: Create Ground Truth Labels

```bash
# 1. Export sample for labeling
python manage.py export_for_labeling \
  --team "Antiwork" \
  --sample 100 \
  --output experiments/to_label.csv

# 2. Label in spreadsheet (add 'ground_truth' column)
# 3. Import labeled data
python manage.py import_ground_truth \
  --file experiments/labeled.csv \
  --output experiments/ground_truth.json
```

### Task 4: Backfill Production Data

```bash
# 1. Dry run
python manage.py backfill_ai_detection \
  --team "Antiwork" \
  --use-llm \
  --dry-run \
  --limit 50

# 2. Review changes
# 3. Run actual backfill
python manage.py backfill_ai_detection \
  --team "Antiwork" \
  --use-llm
```

---

## Troubleshooting

### Groq Rate Limits

```bash
# Check current rate limit status
python manage.py check_groq_rate_limit

# Use batch API for large experiments (no rate limit impact)
python manage.py create_detection_batch --team "Antiwork"
```

### PostHog Not Logging

```python
# Verify PostHog is configured
import posthog
posthog.debug = True
posthog.capture("test", "test_event")
```

### JSON Parse Errors

LLM sometimes returns invalid JSON. The runner automatically:
1. Retries with `temperature=0`
2. Extracts JSON from markdown blocks
3. Falls back to regex detection

---

## Metrics Definitions

| Metric | Formula | Description |
|--------|---------|-------------|
| **Detection Rate** | Detected / Total | % of PRs flagged as AI-assisted |
| **Precision** | TP / (TP + FP) | Of detected, how many correct |
| **Recall** | TP / (TP + FN) | Of actual AI PRs, how many detected |
| **Agreement** | Same / Total | Regex vs LLM same answer |
| **LLM Lift** | LLM Recall - Regex Recall | Value added by LLM |

---

## PostHog Event Schema

Events captured for each LLM call:

```json
{
  "event": "$ai_generation",
  "properties": {
    "$ai_model": "llama-3.3-70b-versatile",
    "$ai_provider": "groq",
    "$ai_input_tokens": 1100,
    "$ai_output_tokens": 150,
    "$ai_latency_ms": 450,
    "$ai_trace_id": "exp-12345",

    "experiment_name": "prompt-v3-test",
    "experiment_config": "default.yaml",
    "pr_id": 123,
    "pr_repo": "antiwork/gumroad",

    "result_is_ai_assisted": true,
    "result_tools": ["cursor", "claude"],
    "result_confidence": 0.95,

    "regex_detected": false,
    "regex_tools": [],
    "is_disagreement": true
  }
}
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-24 | Initial runbook |
