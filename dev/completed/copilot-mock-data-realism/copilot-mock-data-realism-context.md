# Copilot Mock Data Realism - Context

**Last Updated: 2026-01-11**

## Key Files

### Primary Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `apps/integrations/services/copilot_metrics.py` | API response parsing | Phase 0: Support official nested schema |
| `apps/integrations/services/copilot_mock_data.py` | Mock data generator | Phases 1-3, 5: Realism improvements |
| `apps/metrics/management/commands/seed_copilot_demo.py` | Seeding command | Phase 4: Power user distribution |

### Test Files

| File | Purpose |
|------|---------|
| `apps/integrations/tests/test_copilot_mock_data.py` | Generator tests (40+ cases) |
| `apps/integrations/tests/test_copilot_mock_mode.py` | Mock mode integration tests |
| `apps/integrations/tests/test_copilot_metrics.py` | API parsing tests |

### Related Files (Read-Only Reference)

| File | Purpose |
|------|---------|
| `apps/metrics/models/copilot.py` | CopilotSeatSnapshot, CopilotLanguageDaily models |
| `apps/metrics/models/ai_usage.py` | AIUsageDaily model |
| `apps/metrics/seeding/deterministic.py` | DeterministicRandom helper |

---

## Key Decisions

### Decision 1: Schema Compatibility Approach
**Decision**: Fix generator AND parser to use official schema (CLEAN BREAK)

> **REVISED per plan review**: Do NOT support legacy format. Fix both ends to use official schema.

**Rationale**:
- Supporting both formats creates technical debt
- Mock data's purpose is to mimic real API
- Legacy format would mask issues until real API is used

**Implementation** (Correct Approach):
```python
# Generator produces official nested format
def _generate_editors(self, total_completions: int, acceptance_rate: float) -> list[dict]:
    """Generate editor breakdown with nested models and languages."""
    # ... each editor has models[] with languages[] inside
    return [{
        "name": "vscode",
        "total_engaged_users": 13,
        "models": [{
            "name": "default",
            "is_custom_model": False,
            "languages": [{
                "name": "python",
                "total_code_suggestions": 249,  # CORRECT field name
                "total_code_acceptances": 123,
                ...
            }]
        }]
    }]

# Parser aggregates from nested structure
def parse_metrics_response(data):
    for editor in code_completions.get("editors", []):
        for model in editor.get("models", []):
            for lang in model.get("languages", []):
                total_suggestions += lang.get("total_code_suggestions", 0)
                # ... aggregate
```

### Decision 2: Acceptance Rate Calibration
**Decision**: Align with real-world ~30% average

**Before**:
| Scenario | Range |
|----------|-------|
| high_adoption | 40-55% |
| mixed_usage | 15-65% |
| growth | 30% → 70% |
| decline | 70% → 30% |

**After**:
| Scenario | Range |
|----------|-------|
| high_adoption | 30-38% |
| mixed_usage | 20-40% |
| growth | 25% → 38% |
| decline | 38% → 25% |

### Decision 3: Weekend Modeling
**Decision**: On by default, backward compatible

**Approach**: Add `model_weekends=True` parameter to `generate()`

**Modifiers**:
- Volume: 0.60-0.70x on weekends
- Active users: 0.50-0.65x on weekends
- Acceptance rate: 1.05-1.10x on weekends (slightly higher)

### Decision 4: Lines vs Suggestions Acceptance
**Decision**: Lines acceptance = 60-70% of suggestions acceptance

**Real-world data**:
- Suggestion acceptance: ~30%
- Lines acceptance: ~20%
- Ratio: 20/30 ≈ 0.67

---

## Dependencies

### Internal Dependencies
- `DeterministicRandom` from `apps/metrics/seeding/deterministic.py`
- `ScenarioConfig` dataclass in same file
- `CopilotScenario` enum in same file

### External Dependencies
None - this is internal mock data generation

### Downstream Impact
Changes will affect:
- AI Adoption dashboard display
- Test assertions (need updates)
- Seeded demo data appearance
- Any code using `CopilotMockDataGenerator`

---

## Code Patterns to Follow

### Scenario Configuration Pattern
```python
SCENARIO_CONFIGS: dict[str, ScenarioConfig] = {
    CopilotScenario.HIGH_ADOPTION.value: ScenarioConfig(
        acceptance_rate_range=(0.30, 0.38),  # Updated range
        active_users_range=(15, 30),
        completions_range=(500, 3000),
    ),
}
```

### Deterministic Random Pattern
```python
def __init__(self, seed: int = 42):
    self.seed = seed
    self.rng = DeterministicRandom(seed)
```

### API Format Detection Pattern
```python
# Check for nested structure presence
if "models" in code_completions.get("editors", [{}])[0]:
    # Official API format
else:
    # Legacy mock format
```

---

## Test Patterns

### Scenario Test Pattern
```python
def test_high_adoption_scenario(self):
    generator = CopilotMockDataGenerator(seed=42)
    data = generator.generate(
        since="2025-01-01",
        until="2025-01-07",
        scenario="high_adoption",
    )

    for day_data in data:
        completions = day_data["copilot_ide_code_completions"]
        if completions["total_completions"] > 0:
            acceptance_rate = completions["total_acceptances"] / completions["total_completions"]
            self.assertGreaterEqual(acceptance_rate, 0.30)  # Updated
            self.assertLessEqual(acceptance_rate, 0.38)     # Updated
```

### Deterministic Output Test Pattern
```python
def test_same_seed_produces_same_data(self):
    generator1 = CopilotMockDataGenerator(seed=42)
    generator2 = CopilotMockDataGenerator(seed=42)

    data1 = generator1.generate(since="2025-01-01", until="2025-01-07")
    data2 = generator2.generate(since="2025-01-01", until="2025-01-07")

    self.assertEqual(data1, data2)
```

---

## API Schema Reference

### Official GitHub Copilot Metrics API (Current)
```json
{
  "date": "2024-06-24",
  "total_active_users": 24,
  "total_engaged_users": 20,
  "copilot_ide_code_completions": {
    "total_engaged_users": 20,
    "languages": [
      {"name": "python", "total_engaged_users": 10}
    ],
    "editors": [
      {
        "name": "vscode",
        "total_engaged_users": 13,
        "models": [
          {
            "name": "default",
            "is_custom_model": false,
            "languages": [
              {
                "name": "python",
                "total_code_suggestions": 249,
                "total_code_acceptances": 123,
                "total_code_lines_suggested": 225,
                "total_code_lines_accepted": 135
              }
            ]
          }
        ]
      }
    ]
  }
}
```

### Our Mock Data Format (Legacy)
```json
{
  "date": "2024-06-24",
  "total_active_users": 24,
  "total_engaged_users": 20,
  "copilot_ide_code_completions": {
    "total_completions": 1500,
    "total_acceptances": 600,
    "total_lines_suggested": 3000,
    "total_lines_accepted": 1200,
    "languages": [
      {
        "name": "python",
        "total_completions": 500,
        "total_acceptances": 200,
        "total_lines_suggested": 1000,
        "total_lines_accepted": 400
      }
    ],
    "editors": [
      {
        "name": "vscode",
        "total_completions": 800,
        "total_acceptances": 320,
        "total_lines_suggested": 1600,
        "total_lines_accepted": 640
      }
    ]
  }
}
```

---

## Commands Reference

```bash
# Run tests
.venv/bin/pytest apps/integrations/tests/test_copilot_mock_data.py -v

# Seed demo data
.venv/bin/python manage.py seed_copilot_demo --team=demo --scenario=mixed_usage --weeks=8 --clear-existing

# Check specific scenario
.venv/bin/python -c "
from apps.integrations.services.copilot_mock_data import CopilotMockDataGenerator
gen = CopilotMockDataGenerator(seed=42)
data = gen.generate('2025-01-01', '2025-01-07', scenario='high_adoption')
for d in data:
    c = d['copilot_ide_code_completions']
    if c['total_completions'] > 0:
        rate = c['total_acceptances'] / c['total_completions']
        print(f\"{d['date']}: {rate:.2%}\")
"
```
