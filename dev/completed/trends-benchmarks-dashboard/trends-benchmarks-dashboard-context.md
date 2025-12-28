# Trends & Benchmarks Dashboard - Context

**Last Updated:** 2025-12-25

---

## Key Files

### Services (Backend)
| File | Purpose | Modifications Needed |
|------|---------|---------------------|
| `apps/metrics/services/dashboard_service.py` | Data aggregation | Add `get_monthly_aggregation()`, extend `_get_metric_trend()` |
| `apps/metrics/services/insight_service.py` | Insight generation | Extend with trend-based insights |
| `apps/metrics/view_utils.py` | Date range parsing | Support custom date ranges, YoY |

### Views (Backend)
| File | Purpose | Modifications Needed |
|------|---------|---------------------|
| `apps/metrics/views/analytics_views.py` | Analytics pages | Add trends views |
| `apps/metrics/views/chart_views.py` | Chart data endpoints | Add monthly trend endpoints |

### Templates (Frontend)
| File | Purpose | Modifications Needed |
|------|---------|---------------------|
| `templates/metrics/analytics/base_analytics.html` | Tab navigation | Add "Trends" tab |
| `templates/metrics/partials/filters.html` | Filter components | Add custom date picker |
| `templates/metrics/partials/key_metrics_cards.html` | Metric cards | Add sparklines |

### JavaScript (Frontend)
| File | Purpose | Modifications Needed |
|------|---------|---------------------|
| `assets/javascript/dashboard/dashboard-charts.js` | Chart utilities | Add wide chart, YoY comparison |
| `assets/javascript/dashboard/chart-theme.js` | Chart theming | Add comparison line colors |

### Styles
| File | Purpose | Notes |
|------|---------|-------|
| `assets/styles/app/tailwind/design-system.css` | App classes | Use existing `.app-*` classes |
| `assets/styles/site-tailwind.css` | DaisyUI themes | No changes needed |

---

## Key Decisions

### Decision 1: Chart Library
**Choice:** Continue with Chart.js (with zoom plugin)
**Alternatives Considered:**
- ApexCharts - Better out-of-box interactions, but different ecosystem
- uPlot - Very performant, but less styled
- Recharts - React-focused, not suitable

**Rationale:** Chart.js already integrated, has zoom/pan plugin, team familiarity

### Decision 2: Date Range UI
**Choice:** Custom Alpine.js date picker with presets
**Alternatives Considered:**
- Flowbite datepicker - Available but opinionated
- Native HTML date inputs - Poor UX for ranges
- Full calendar component - Overkill

**Rationale:** Lightweight, matches existing Alpine.js patterns, easy to customize

### Decision 3: Data Aggregation Strategy
**Choice:** Live aggregation with caching (no pre-computed tables)
**Alternatives Considered:**
- Pre-computed weekly/monthly tables - Better performance, more complexity
- Materialized views - PostgreSQL-specific, migration complexity

**Rationale:** Simpler to implement, cache handles performance, data freshness

### Decision 4: Benchmark Data Source
**Choice:** Combination of public research + anonymous aggregate
**Alternatives Considered:**
- Only public data (DORA) - Limited metrics coverage
- Only our data - Privacy concerns, sample size issues
- Third-party API - Cost, dependency

**Rationale:** Best of both worlds, can grow aggregate as user base grows

### Decision 5: Trend Chart Layout
**Choice:** Full-width single chart with metric selector
**Alternatives Considered:**
- Multiple small charts - Harder to compare, more loading
- Tabbed charts - Hidden context, extra clicks
- Scrollable dashboard - Information scattered

**Rationale:** Matches Yandex Metrika pattern, focus on one metric at a time

---

## Dependencies

### npm Packages (to add)
```bash
npm install chartjs-plugin-zoom  # Pan/zoom for wide charts
```

### Python Packages (existing)
- Django ORM aggregation functions (Sum, Avg, Count, TruncMonth)
- django-cache (for caching aggregated data)

### External Data Sources
| Source | Data | Format | Frequency |
|--------|------|--------|-----------|
| DORA Report 2024 | DevOps benchmarks | Manual entry | Yearly |
| Our aggregate data | AI adoption, review time | Computed | Quarterly |
| Customer opt-in | Anonymous metrics | Computed | Real-time |

---

## Database Schema Additions

### New Model: IndustryBenchmark
```python
class IndustryBenchmark(BaseModel):
    """Industry benchmark data for comparison."""

    class TeamSizeBucket(models.TextChoices):
        TINY = "5-10", "5-10 developers"
        SMALL = "11-25", "11-25 developers"
        MEDIUM = "26-50", "26-50 developers"
        LARGE = "51-100", "51-100 developers"

    metric_name = models.CharField(max_length=50)  # cycle_time, deployment_freq, etc.
    team_size_bucket = models.CharField(max_length=20, choices=TeamSizeBucket.choices)
    percentile_25 = models.DecimalField(max_digits=10, decimal_places=2)
    percentile_50 = models.DecimalField(max_digits=10, decimal_places=2)  # median
    percentile_75 = models.DecimalField(max_digits=10, decimal_places=2)
    percentile_90 = models.DecimalField(max_digits=10, decimal_places=2)
    source = models.CharField(max_length=100)  # "DORA 2024", "tformance aggregate"
    source_year = models.IntegerField()
    notes = models.TextField(blank=True)
```

### New Model: TrendInsight
```python
class TrendInsight(BaseTeamModel):
    """Generated insights from trend analysis."""

    class InsightType(models.TextChoices):
        TREND_ALERT = "trend_alert", "Trend Alert"
        CORRELATION = "correlation", "Correlation"
        ACHIEVEMENT = "achievement", "Achievement"
        RECOMMENDATION = "recommendation", "Recommendation"
        BENCHMARK = "benchmark", "Benchmark"

    insight_type = models.CharField(max_length=20, choices=InsightType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField()
    metric_name = models.CharField(max_length=50)
    metric_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    change_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    is_positive = models.BooleanField(null=True)  # True = improvement
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    dismissed_by = models.ForeignKey("users.CustomUser", null=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["-created_at"]
```

---

## URL Patterns

### New URLs (in `apps/metrics/urls.py`)
```python
# Trends section
path("trends/", views.trends_overview, name="trends_overview"),
path("trends/cycle-time/", views.trends_cycle_time, name="trends_cycle_time"),
path("trends/ai-adoption/", views.trends_ai_adoption, name="trends_ai_adoption"),
path("trends/delivery/", views.trends_delivery, name="trends_delivery"),
path("trends/benchmarks/", views.trends_benchmarks, name="trends_benchmarks"),

# Chart endpoints
path("api/chart/trend/<str:metric>/", views.chart_trend_data, name="chart_trend_data"),
path("api/chart/comparison/", views.chart_yoy_comparison, name="chart_yoy_comparison"),
path("api/benchmarks/<str:metric>/", views.benchmark_data, name="benchmark_data"),
```

---

## API Response Formats

### Trend Data Endpoint
```json
GET /a/<team>/metrics/api/chart/trend/cycle_time/?start=2024-01-01&end=2024-12-31&granularity=monthly

{
  "metric": "cycle_time",
  "granularity": "monthly",
  "unit": "hours",
  "data": [
    {"date": "2024-01-01", "value": 24.5},
    {"date": "2024-02-01", "value": 22.3},
    ...
  ],
  "summary": {
    "current_period_avg": 18.2,
    "previous_period_avg": 24.1,
    "change_pct": -24.5
  }
}
```

### YoY Comparison Endpoint
```json
GET /a/<team>/metrics/api/chart/comparison/?metric=cycle_time&year=2025&compare_year=2024

{
  "metric": "cycle_time",
  "current": {
    "year": 2025,
    "data": [{"month": 1, "value": 18.2}, ...]
  },
  "comparison": {
    "year": 2024,
    "data": [{"month": 1, "value": 24.5}, ...]
  },
  "ytd_change_pct": -24.5
}
```

### Benchmark Endpoint
```json
GET /a/<team>/metrics/api/benchmarks/cycle_time/

{
  "metric": "cycle_time",
  "team_value": 18.2,
  "team_size_bucket": "11-25",
  "benchmarks": {
    "percentile_25": 12.0,
    "percentile_50": 24.0,
    "percentile_75": 48.0,
    "percentile_90": 72.0
  },
  "team_percentile": 72,
  "interpretation": "better_than_average",
  "source": "DORA 2024"
}
```

---

## Testing Strategy

### Unit Tests
- `test_trend_service.py` - Monthly aggregation, YoY comparison
- `test_benchmark_service.py` - Percentile calculation, bucket matching
- `test_insight_engine.py` - Insight generation rules

### Integration Tests
- `test_trends_views.py` - View responses, date parsing
- `test_chart_endpoints.py` - JSON response formats

### E2E Tests
- `tests/e2e/trends.spec.ts` - Date picker, chart rendering, benchmark display

---

## Performance Considerations

### Caching Strategy
| Data | Cache TTL | Key Pattern |
|------|-----------|-------------|
| Monthly aggregations | 1 hour | `monthly_agg:{team}:{metric}:{year}` |
| Benchmark data | 24 hours | `benchmark:{metric}:{bucket}` |
| Trend insights | 15 minutes | `insights:{team}:{date}` |

### Query Optimization
- Use `TruncMonth` for monthly grouping (PostgreSQL-optimized)
- Add database index on `(team_id, merged_at)` for PR queries
- Consider materialized view for very large teams (100+ PRs/month)

---

## Related Documentation

| Document | Location |
|----------|----------|
| PRD | `prd/PRD-MVP.md` |
| Dashboard spec | `prd/DASHBOARDS.md` |
| Architecture | `prd/ARCHITECTURE.md` |
| Design system | `assets/styles/app/tailwind/design-system.css` |
