# Experiment Results

This directory stores experiment results. Files are gitignored as they can be large and may contain sensitive PR data.

## File Structure

```
results/
├── <experiment-name>/
│   ├── results.json      # Full detection results
│   ├── summary.json      # Aggregated metrics
│   ├── disagreements.csv # Regex vs LLM disagreements
│   └── config.yaml       # Config used for this run
```

## Accessing Results

```python
from apps.metrics.experiments.analysis import ExperimentAnalysis

analysis = ExperimentAnalysis("experiments/results/my-experiment")
print(analysis.summary())
```

## PostHog Dashboard

For real-time analytics, use PostHog:
https://app.posthog.com/project/<id>/llm-analytics
