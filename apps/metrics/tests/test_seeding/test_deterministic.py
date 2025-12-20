"""Tests for DeterministicRandom class."""

from datetime import datetime
from decimal import Decimal

from django.test import TestCase

from apps.metrics.seeding.deterministic import DeterministicRandom


class TestDeterministicRandomReproducibility(TestCase):
    """Tests verifying that same seed produces identical results."""

    def test_same_seed_produces_identical_randint(self):
        """Same seed should produce identical randint sequences."""
        rng1 = DeterministicRandom(42)
        rng2 = DeterministicRandom(42)

        values1 = [rng1.randint(1, 100) for _ in range(10)]
        values2 = [rng2.randint(1, 100) for _ in range(10)]

        self.assertEqual(values1, values2)

    def test_same_seed_produces_identical_choice(self):
        """Same seed should produce identical choice sequences."""
        options = ["a", "b", "c", "d", "e"]
        rng1 = DeterministicRandom(42)
        rng2 = DeterministicRandom(42)

        choices1 = [rng1.choice(options) for _ in range(10)]
        choices2 = [rng2.choice(options) for _ in range(10)]

        self.assertEqual(choices1, choices2)

    def test_same_seed_produces_identical_should_happen(self):
        """Same seed should produce identical should_happen sequences."""
        rng1 = DeterministicRandom(42)
        rng2 = DeterministicRandom(42)

        results1 = [rng1.should_happen(0.5) for _ in range(20)]
        results2 = [rng2.should_happen(0.5) for _ in range(20)]

        self.assertEqual(results1, results2)

    def test_different_seeds_produce_different_results(self):
        """Different seeds should produce different results."""
        rng1 = DeterministicRandom(42)
        rng2 = DeterministicRandom(123)

        values1 = [rng1.randint(1, 100) for _ in range(10)]
        values2 = [rng2.randint(1, 100) for _ in range(10)]

        # Very unlikely to be identical with different seeds
        self.assertNotEqual(values1, values2)


class TestDeterministicRandomMethods(TestCase):
    """Tests for individual DeterministicRandom methods."""

    def setUp(self):
        """Set up test fixtures."""
        self.rng = DeterministicRandom(42)

    def test_randint_in_range(self):
        """randint should return values in specified range."""
        for _ in range(100):
            value = self.rng.randint(10, 20)
            self.assertGreaterEqual(value, 10)
            self.assertLessEqual(value, 20)

    def test_uniform_in_range(self):
        """uniform should return values in specified range."""
        for _ in range(100):
            value = self.rng.uniform(1.5, 2.5)
            self.assertGreaterEqual(value, 1.5)
            self.assertLessEqual(value, 2.5)

    def test_decimal_returns_decimal(self):
        """decimal should return Decimal with correct precision."""
        value = self.rng.decimal(1.0, 2.0, places=3)
        self.assertIsInstance(value, Decimal)
        # Check precision (should have at most 3 decimal places)
        str_value = str(value)
        if "." in str_value:
            decimal_places = len(str_value.split(".")[1])
            self.assertLessEqual(decimal_places, 3)

    def test_should_happen_probability(self):
        """should_happen should respect probability over many trials."""
        rng = DeterministicRandom(42)

        # With 70% probability, expect roughly 70% True over many trials
        true_count = sum(1 for _ in range(1000) if rng.should_happen(0.7))

        # Allow 5% tolerance
        self.assertGreater(true_count, 650)
        self.assertLess(true_count, 750)

    def test_datetime_in_range(self):
        """datetime_in_range should return datetime within bounds."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)

        for _ in range(100):
            dt = self.rng.datetime_in_range(start, end)
            self.assertGreaterEqual(dt, start)
            self.assertLessEqual(dt, end)

    def test_timedelta_in_range(self):
        """timedelta_in_range should return timedelta within bounds."""
        for _ in range(100):
            td = self.rng.timedelta_in_range(1.0, 5.0)
            hours = td.total_seconds() / 3600
            self.assertGreaterEqual(hours, 1.0)
            self.assertLessEqual(hours, 5.0)

    def test_weighted_choice_respects_weights(self):
        """weighted_choice should respect weights over many trials."""
        options = {"high": 0.7, "medium": 0.2, "low": 0.1}
        rng = DeterministicRandom(42)

        counts = {"high": 0, "medium": 0, "low": 0}
        for _ in range(1000):
            choice = rng.weighted_choice(options)
            counts[choice] += 1

        # "high" should be most common
        self.assertGreater(counts["high"], counts["medium"])
        self.assertGreater(counts["medium"], counts["low"])

    def test_shuffle_returns_same_elements(self):
        """shuffle should return all original elements."""
        original = [1, 2, 3, 4, 5]
        shuffled = self.rng.shuffle(original)

        self.assertEqual(sorted(shuffled), sorted(original))
        self.assertEqual(len(shuffled), len(original))

    def test_shuffle_does_not_modify_original(self):
        """shuffle should not modify the original list."""
        original = [1, 2, 3, 4, 5]
        original_copy = original.copy()
        self.rng.shuffle(original)

        self.assertEqual(original, original_copy)

    def test_sample_returns_unique_elements(self):
        """sample should return k unique elements."""
        seq = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        sample = self.rng.sample(seq, 5)

        self.assertEqual(len(sample), 5)
        self.assertEqual(len(set(sample)), 5)  # All unique

    def test_choices_can_repeat(self):
        """choices with replacement can repeat elements."""
        seq = [1, 2, 3]
        # With k=10 and only 3 options, we should get repeats
        choices = self.rng.choices(seq, k=10)

        self.assertEqual(len(choices), 10)
        # All choices should be from original sequence
        for choice in choices:
            self.assertIn(choice, seq)

    def test_gauss_distribution(self):
        """gauss should generate values around the mean."""
        rng = DeterministicRandom(42)

        values = [rng.gauss(100, 10) for _ in range(1000)]
        mean = sum(values) / len(values)

        # Mean should be close to 100
        self.assertGreater(mean, 95)
        self.assertLess(mean, 105)

    def test_triangular_distribution(self):
        """triangular should generate values biased toward mode."""
        rng = DeterministicRandom(42)

        # Mode at 2, range 1-3
        values = [rng.triangular(1, 3, 2) for _ in range(1000)]

        # Values should be in range
        for v in values:
            self.assertGreaterEqual(v, 1)
            self.assertLessEqual(v, 3)

        # Mean should be close to (low + mode + high) / 3 = 2
        mean = sum(values) / len(values)
        self.assertGreater(mean, 1.9)
        self.assertLess(mean, 2.1)
