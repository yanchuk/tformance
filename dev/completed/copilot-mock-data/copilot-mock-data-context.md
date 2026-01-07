# Copilot Mock Data - Context

**Last Updated**: 2026-01-06

## Key Files

### Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/services/copilot_mock_data.py` | Main mock generator with scenarios |
| `apps/integrations/tests/test_copilot_mock_data.py` | TDD tests for mock generator |
| `apps/metrics/management/commands/seed_copilot_demo.py` | CLI for seeding demo data |
| `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2` | LLM prompt section |

### Files to Modify

| File | Change |
|------|--------|
| `apps/integrations/services/copilot_metrics.py` | Add mock mode toggle |
| `apps/metrics/seeding/real_project_seeder.py` | Add Copilot overlay support |
| `apps/metrics/prompts/templates/insight/user_v2.jinja2` | Include copilot_metrics |
| `apps/metrics/prompts/render.py` | Pass copilot_metrics context |
| `tformance/settings.py` | Add COPILOT_* settings |

### Existing Infrastructure to Leverage

| File | Reuse |
|------|-------|
| `apps/metrics/seeding/deterministic.py` | `DeterministicRandom` for reproducibility |
| `apps/metrics/factories.py` | `AIUsageDailyFactory` |
| `apps/metrics/seeding/real_projects.py` | `RealProjectConfig` |
| `apps/metrics/seeding/real_project_seeder.py` | Base seeder pattern |
| `apps/metrics/seeding/scenarios/base.py` | `BaseScenario`, `MemberArchetype` |

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Base data source | Real GitHub (PostHog, Railsware) | Realistic PR patterns |
| Mock trigger | Environment variable only | Explicit opt-in |
| Scenario architecture | Standalone module | Simpler, focused |
| Randomness | `DeterministicRandom` | Reproducible for demos/tests |

---

## GitHub Copilot API Reference

**Endpoints:**
- `GET /orgs/{org}/copilot/metrics` - Org-level daily metrics
- `GET /orgs/{org}/copilot/billing/seats` - Seat utilization

**Requirements:**
- Minimum 5 active licenses for metrics
- 100-day history maximum
- Daily granularity only
- Requires `manage_billing:copilot` scope

**Response Schema Keys:**
```python
REQUIRED_FIELDS = [
    "date",
    "total_active_users",
    "total_engaged_users",
    "copilot_ide_code_completions",
    "copilot_ide_chat",
    "copilot_dotcom_chat",
    "copilot_dotcom_pull_requests",
]

CODE_COMPLETIONS_FIELDS = [
    "total_completions",
    "total_acceptances",
    "total_lines_suggested",
    "total_lines_accepted",
    "languages",  # list of {name, total_completions, total_acceptances}
    "editors",    # list of {name, total_completions, total_acceptances}
]
```

---

## Model Reference

### AIUsageDaily (existing)

```python
class AIUsageDaily(BaseTeamModel):
    member = ForeignKey(TeamMember)
    date = DateField()
    source = CharField(choices=[("copilot", "GitHub Copilot"), ("cursor", "Cursor")])
    suggestions_shown = IntegerField()
    suggestions_accepted = IntegerField()
    acceptance_rate = DecimalField(max_digits=5, decimal_places=2)
    active_hours = DecimalField(optional)

    # Unique: (team, member, date, source)
```

### PullRequest (for correlation)

```python
# Fields to update when correlating Copilot usage
pr.is_ai_assisted = True
pr.ai_tools_detected = ["copilot"]
```

---

## Scenario Parameters

### User Archetypes

```python
@dataclass
class CopilotUserArchetype:
    name: str
    acceptance_rate_range: tuple[float, float]  # (min, max) e.g., (0.40, 0.55)
    daily_suggestions_range: tuple[int, int]    # (min, max) e.g., (200, 500)
    usage_days_per_week: tuple[int, int]        # (min, max) e.g., (5, 7)
    count: int                                   # Number of users with this type
```

### Weekly Progression (for growth/decline)

```python
def get_weekly_multiplier(week: int, scenario: str) -> float:
    """
    week 0 = earliest, week N = most recent

    growth:  0.3 → 1.0 over N weeks
    decline: 1.0 → 0.3 over N weeks
    stable:  1.0 constant
    """
```

---

## Test Patterns

### TDD Red-Green-Refactor

```python
# RED: Write failing test first
def test_generates_valid_api_format(self):
    generator = CopilotMockDataGenerator(seed=42)
    data = generator.generate_daily_metrics("test-org", date(2025,1,1), date(2025,1,7))

    assert len(data) == 7
    for day in data:
        assert "date" in day
        assert "copilot_ide_code_completions" in day
        assert "total_completions" in day["copilot_ide_code_completions"]

# GREEN: Implement minimal code to pass
# REFACTOR: Clean up while keeping tests passing
```

### Factory Usage

```python
# Creating test data
AIUsageDailyFactory(
    team=team,
    member=member,
    date=date(2025, 1, 15),
    source="copilot",
    suggestions_shown=200,
    suggestions_accepted=80,
    acceptance_rate=Decimal("40.00"),
)
```

---

## Quick Commands

```bash
# Run tests for copilot mock data
.venv/bin/pytest apps/integrations/tests/test_copilot_mock_data.py -v

# Seed demo data
python manage.py seed_copilot_demo --team=demo --scenario=growth --weeks=8

# Quick scenario switch
python manage.py seed_copilot_demo --team=demo --scenario=mixed_usage --clear-existing

# Generate insights to test LLM integration
python manage.py generate_insights --team=demo
```

---

## Related Documentation

- [GitHub Copilot Metrics API](https://docs.github.com/en/rest/copilot/copilot-metrics)
- `prd/ARCHITECTURE.md` - System architecture
- `dev/guides/TESTING-GUIDE.md` - TDD workflow
- `dev/guides/CODE-GUIDELINES.md` - Python patterns
