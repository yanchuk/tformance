# Phase 1: Rule-Based Insights System

**Last Updated:** 2025-12-21

## Executive Summary

Implement a rule-based insights engine that automatically detects patterns and anomalies in team metrics data. This foundation provides immediate value with zero external API costs and serves as the data layer for future LLM-powered features.

## Goals

1. **Automated Pattern Detection** - Identify trends, anomalies, and actionable insights
2. **Daily Computation** - Generate insights via Celery task during sync
3. **Dashboard Integration** - Display insights prominently on CTO dashboard
4. **Foundation for LLM** - Pre-computed data ready for natural language summarization

## Proposed Architecture

```
Daily Sync (Celery) → Insight Engine → DailyInsight Model → Dashboard Display
                           ↓
                    Insight Rules
                    ├── TrendDetector
                    ├── AnomalyDetector
                    ├── ComparisonAnalyzer
                    └── ThresholdChecker
```

## Data Model

```python
class DailyInsight(BaseTeamModel):
    CATEGORY_CHOICES = [
        ("trend", "Trend"),
        ("anomaly", "Anomaly"),
        ("comparison", "Comparison"),
        ("action", "Action"),
    ]
    PRIORITY_CHOICES = [("high", "High"), ("medium", "Medium"), ("low", "Low")]

    date = models.DateField(db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    metric_type = models.CharField(max_length=50)
    metric_value = models.JSONField(null=True)
    is_dismissed = models.BooleanField(default=False)
```

## Insight Categories

| Category | Example |
|----------|---------|
| Trend | "AI adoption increased 15% over 4 weeks" |
| Anomaly | "Unusual spike in hotfixes (5 vs avg 1)" |
| Comparison | "AI PRs have 0.3 higher quality rating" |
| Action | "Redundant reviewers: Alice & Bob agree 98%" |

## Files to Create

```
apps/metrics/
├── models.py                    # Add DailyInsight
├── services/insight_engine.py   # Core engine
├── services/insight_rules.py    # Rule implementations
├── tasks.py                     # Celery task
templates/metrics/partials/
└── insights_panel.html          # Dashboard component
```
