"""Tests for scenario implementations."""

from decimal import Decimal

from django.test import TestCase

from apps.metrics.seeding.scenarios import (
    SCENARIO_REGISTRY,
    AISuccessScenario,
    BaselineScenario,
    DetectiveGameScenario,
    ReviewBottleneckScenario,
    get_scenario,
    list_scenarios,
)


class TestScenarioRegistry(TestCase):
    """Tests for the scenario registry system."""

    def test_all_scenarios_registered(self):
        """All 4 scenarios should be registered."""
        expected = {"ai-success", "review-bottleneck", "baseline", "detective-game"}
        actual = set(SCENARIO_REGISTRY.keys())
        self.assertEqual(actual, expected)

    def test_get_scenario_returns_instance(self):
        """get_scenario should return a scenario instance."""
        scenario = get_scenario("ai-success")
        self.assertIsInstance(scenario, AISuccessScenario)

    def test_get_scenario_unknown_raises(self):
        """get_scenario should raise KeyError for unknown scenario."""
        with self.assertRaises(KeyError):
            get_scenario("unknown-scenario")

    def test_list_scenarios_returns_info(self):
        """list_scenarios should return scenario info dicts."""
        scenarios = list_scenarios()
        self.assertEqual(len(scenarios), 4)

        # Check structure of returned info
        for info in scenarios:
            self.assertIn("name", info)
            self.assertIn("description", info)
            self.assertIn("member_count", info)
            self.assertIn("weeks", info)


class TestAISuccessScenario(TestCase):
    """Tests for the AI Success scenario."""

    def setUp(self):
        """Set up scenario instance."""
        self.scenario = AISuccessScenario()

    def test_config_values(self):
        """Scenario should have correct config values."""
        config = self.scenario.config
        self.assertEqual(config.name, "ai-success")
        self.assertEqual(config.member_count, 5)
        self.assertEqual(config.weeks, 8)

    def test_weekly_params_progression(self):
        """AI adoption should increase from 10% to 75% over 8 weeks."""
        params_week_0 = self.scenario.get_weekly_params(0)
        params_week_7 = self.scenario.get_weekly_params(7)

        # AI adoption increases
        self.assertLess(params_week_0["ai_adoption_rate"], Decimal("0.15"))
        self.assertGreater(params_week_7["ai_adoption_rate"], Decimal("0.70"))

        # Cycle time decreases
        self.assertGreater(params_week_0["avg_cycle_time_hours"], Decimal("60"))
        self.assertLess(params_week_7["avg_cycle_time_hours"], Decimal("30"))

        # Quality improves slightly
        self.assertLess(params_week_0["quality_rating"], params_week_7["quality_rating"])

    def test_member_archetypes_count_matches_config(self):
        """Total archetype count should match config.member_count."""
        archetypes = self.scenario.get_member_archetypes()
        total = sum(a.count for a in archetypes)
        self.assertEqual(total, self.scenario.config.member_count)

    def test_member_archetype_types(self):
        """Scenario should have early_adopter, follower, and skeptic archetypes."""
        archetypes = self.scenario.get_member_archetypes()
        names = {a.name for a in archetypes}
        self.assertEqual(names, {"early_adopter", "follower", "skeptic"})

    def test_guess_accuracy_varies_by_archetype(self):
        """Different archetypes should have different guess accuracy."""
        early_adopter = self.scenario.get_guess_accuracy_for_archetype("early_adopter")
        skeptic = self.scenario.get_guess_accuracy_for_archetype("skeptic")

        # Early adopters are easier to detect
        self.assertGreater(early_adopter[0], skeptic[0])

    def test_validation_passes(self):
        """Scenario should pass validation."""
        errors = self.scenario.validate()
        self.assertEqual(errors, [])


class TestReviewBottleneckScenario(TestCase):
    """Tests for the Review Bottleneck scenario."""

    def setUp(self):
        """Set up scenario instance."""
        self.scenario = ReviewBottleneckScenario()

    def test_config_values(self):
        """Scenario should have correct config values."""
        config = self.scenario.config
        self.assertEqual(config.name, "review-bottleneck")
        self.assertEqual(config.member_count, 5)

    def test_cycle_time_worsens(self):
        """Cycle time should increase over time (worsening)."""
        params_week_0 = self.scenario.get_weekly_params(0)
        params_week_7 = self.scenario.get_weekly_params(7)

        self.assertLess(
            params_week_0["avg_cycle_time_hours"],
            params_week_7["avg_cycle_time_hours"],
        )

    def test_quality_declines(self):
        """Quality should decrease over time."""
        params_week_0 = self.scenario.get_weekly_params(0)
        params_week_7 = self.scenario.get_weekly_params(7)

        self.assertGreater(
            params_week_0["quality_rating"],
            params_week_7["quality_rating"],
        )

    def test_ai_adoption_steady(self):
        """AI adoption should stay around 70%."""
        for week in range(8):
            params = self.scenario.get_weekly_params(week)
            self.assertAlmostEqual(
                float(params["ai_adoption_rate"]),
                0.70,
                delta=0.05,
            )

    def test_reviewer_weights_show_bottleneck(self):
        """Bottleneck reviewer should handle 60% of reviews."""
        weights = self.scenario.get_reviewer_selection_weights(0)

        self.assertIn("bottleneck_reviewer", weights)
        self.assertEqual(weights["bottleneck_reviewer"], 0.60)

    def test_open_prs_increase_over_time(self):
        """Open PRs should increase as bottleneck worsens."""
        dist_week_0 = self.scenario.get_pr_state_distribution(0)
        dist_week_7 = self.scenario.get_pr_state_distribution(7)

        self.assertLess(dist_week_0["open"], dist_week_7["open"])

    def test_validation_passes(self):
        """Scenario should pass validation."""
        errors = self.scenario.validate()
        self.assertEqual(errors, [])


class TestBaselineScenario(TestCase):
    """Tests for the Baseline scenario."""

    def setUp(self):
        """Set up scenario instance."""
        self.scenario = BaselineScenario()

    def test_config_values(self):
        """Scenario should have correct config values."""
        config = self.scenario.config
        self.assertEqual(config.name, "baseline")
        self.assertEqual(config.member_count, 5)

    def test_ai_adoption_low_and_steady(self):
        """AI adoption should stay around 15%."""
        for week in range(8):
            params = self.scenario.get_weekly_params(week)
            self.assertAlmostEqual(
                float(params["ai_adoption_rate"]),
                0.15,
                delta=0.05,
            )

    def test_metrics_relatively_stable(self):
        """Metrics should not vary significantly."""
        params_week_0 = self.scenario.get_weekly_params(0)
        params_week_7 = self.scenario.get_weekly_params(7)

        # Cycle time stays around 48h (±10)
        self.assertAlmostEqual(
            float(params_week_0["avg_cycle_time_hours"]),
            float(params_week_7["avg_cycle_time_hours"]),
            delta=10,
        )

        # Quality stays around 2.6 (±0.1)
        self.assertAlmostEqual(
            float(params_week_0["quality_rating"]),
            float(params_week_7["quality_rating"]),
            delta=0.1,
        )

    def test_homogeneous_team(self):
        """Team should be mostly homogeneous."""
        archetypes = self.scenario.get_member_archetypes()

        # Find standard_dev archetype
        standard = next((a for a in archetypes if a.name == "standard_dev"), None)
        self.assertIsNotNone(standard)
        self.assertEqual(standard.count, 4)  # Most of the team

    def test_validation_passes(self):
        """Scenario should pass validation."""
        errors = self.scenario.validate()
        self.assertEqual(errors, [])


class TestDetectiveGameScenario(TestCase):
    """Tests for the Detective Game scenario."""

    def setUp(self):
        """Set up scenario instance."""
        self.scenario = DetectiveGameScenario()

    def test_config_values(self):
        """Scenario should have correct config values."""
        config = self.scenario.config
        self.assertEqual(config.name, "detective-game")
        self.assertEqual(config.member_count, 6)

    def test_four_distinct_archetypes(self):
        """Should have all 4 detectability archetypes."""
        archetypes = self.scenario.get_member_archetypes()
        names = {a.name for a in archetypes}

        expected = {"obvious_ai", "stealth_ai", "obvious_manual", "stealth_manual"}
        self.assertEqual(names, expected)

    def test_obvious_ai_high_detectability(self):
        """obvious_ai archetype should have high detectability."""
        archetypes = self.scenario.get_member_archetypes()
        obvious_ai = next(a for a in archetypes if a.name == "obvious_ai")

        self.assertGreaterEqual(obvious_ai.detectability, 0.8)

    def test_stealth_archetypes_low_detectability(self):
        """stealth archetypes should have low detectability."""
        archetypes = self.scenario.get_member_archetypes()

        stealth_ai = next(a for a in archetypes if a.name == "stealth_ai")
        stealth_manual = next(a for a in archetypes if a.name == "stealth_manual")

        self.assertLessEqual(stealth_ai.detectability, 0.4)
        self.assertLessEqual(stealth_manual.detectability, 0.3)

    def test_guess_accuracy_ranges(self):
        """Guess accuracy should vary appropriately by archetype."""
        # Easy to detect when AI is obvious
        obvious_ai_acc = self.scenario.get_guess_accuracy_for_archetype("obvious_ai")
        self.assertGreater(obvious_ai_acc[0], 0.6)

        # Hard to detect stealth AI (looks human)
        stealth_ai_acc = self.scenario.get_guess_accuracy_for_archetype("stealth_ai")
        self.assertLess(stealth_ai_acc[1], 0.5)

        # Hard to detect obvious_manual (looks AI but isn't)
        obvious_manual_acc = self.scenario.get_guess_accuracy_for_archetype("obvious_manual")
        self.assertLess(obvious_manual_acc[1], 0.55)

    def test_higher_approval_rate_for_surveys(self):
        """Should have higher approval rate for more survey opportunities."""
        dist = self.scenario.get_review_state_distribution(0)

        # Higher approval rate than default (0.6)
        self.assertEqual(dist["approved"], 0.70)

    def test_validation_passes(self):
        """Scenario should pass validation."""
        errors = self.scenario.validate()
        self.assertEqual(errors, [])


class TestScenarioValidation(TestCase):
    """Tests for scenario validation logic."""

    def test_all_scenarios_validate(self):
        """All registered scenarios should pass validation."""
        for name, scenario_cls in SCENARIO_REGISTRY.items():
            scenario = scenario_cls()
            errors = scenario.validate()
            self.assertEqual(
                errors,
                [],
                f"Scenario '{name}' has validation errors: {errors}",
            )

    def test_all_scenarios_have_matching_member_counts(self):
        """All scenarios should have archetype counts matching config."""
        for name, scenario_cls in SCENARIO_REGISTRY.items():
            scenario = scenario_cls()
            archetypes = scenario.get_member_archetypes()
            total = sum(a.count for a in archetypes)

            self.assertEqual(
                total,
                scenario.config.member_count,
                f"Scenario '{name}' archetype count mismatch",
            )
