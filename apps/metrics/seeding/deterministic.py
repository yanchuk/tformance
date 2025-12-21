"""
Deterministic random utilities for reproducible demo data generation.

This module provides a seedable random generator that produces identical
sequences when initialized with the same seed, enabling reproducible
demo data generation across runs.

Usage:
    rng = DeterministicRandom(seed=42)
    value = rng.randint(1, 100)  # Always same value for seed=42
    should_do = rng.should_happen(0.7)  # 70% probability
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal


class DeterministicRandom:
    """Seedable random generator for reproducible data generation.

    All methods use the same internal random.Random instance, ensuring
    that the sequence of random values is deterministic given the same seed.

    Example:
        rng1 = DeterministicRandom(42)
        rng2 = DeterministicRandom(42)
        assert rng1.randint(1, 100) == rng2.randint(1, 100)  # Always True
    """

    def __init__(self, seed: int):
        """Initialize with a seed for reproducibility.

        Args:
            seed: Integer seed value. Same seed produces identical sequences.
        """
        self.seed = seed
        self.rng = random.Random(seed)

    def choice(self, seq):
        """Return a random element from a non-empty sequence.

        Args:
            seq: A non-empty sequence (list, tuple, etc.)

        Returns:
            A random element from the sequence.
        """
        return self.rng.choice(seq)

    def choices(self, seq, k: int = 1):
        """Return k random elements from a sequence with replacement.

        Args:
            seq: A sequence to choose from.
            k: Number of elements to choose.

        Returns:
            A list of k randomly chosen elements.
        """
        return self.rng.choices(seq, k=k)

    def sample(self, seq, k: int):
        """Return k unique random elements from a sequence without replacement.

        Args:
            seq: A sequence to sample from.
            k: Number of unique elements to sample.

        Returns:
            A list of k unique randomly chosen elements.
        """
        return self.rng.sample(list(seq), k)

    def random(self) -> float:
        """Return a random float in the range [0.0, 1.0).

        Returns:
            A random float from 0.0 (inclusive) to 1.0 (exclusive).
        """
        return self.rng.random()

    def randint(self, a: int, b: int) -> int:
        """Return a random integer N such that a <= N <= b.

        Args:
            a: Lower bound (inclusive).
            b: Upper bound (inclusive).

        Returns:
            A random integer in the range [a, b].
        """
        return self.rng.randint(a, b)

    def uniform(self, a: float, b: float) -> float:
        """Return a random floating point number N such that a <= N <= b.

        Args:
            a: Lower bound (inclusive).
            b: Upper bound (inclusive).

        Returns:
            A random float in the range [a, b].
        """
        return self.rng.uniform(a, b)

    def decimal(self, a: float, b: float, places: int = 2) -> Decimal:
        """Return a random Decimal value between a and b.

        Args:
            a: Lower bound (inclusive).
            b: Upper bound (inclusive).
            places: Number of decimal places to round to.

        Returns:
            A random Decimal in the range [a, b] with specified precision.
        """
        value = self.uniform(a, b)
        return Decimal(str(round(value, places)))

    def should_happen(self, probability: float) -> bool:
        """Return True with the given probability.

        Args:
            probability: A float between 0.0 and 1.0 representing
                the probability of returning True.

        Returns:
            True with the specified probability, False otherwise.

        Example:
            if rng.should_happen(0.7):  # 70% chance
                do_something()
        """
        return self.uniform(0, 1) < probability

    def datetime_in_range(self, start: datetime, end: datetime) -> datetime:
        """Return a random datetime between start and end.

        Args:
            start: The earliest possible datetime.
            end: The latest possible datetime.

        Returns:
            A random datetime in the range [start, end].
        """
        delta = (end - start).total_seconds()
        random_seconds = self.uniform(0, delta)
        return start + timedelta(seconds=random_seconds)

    def timedelta_in_range(
        self,
        min_hours: float,
        max_hours: float,
    ) -> timedelta:
        """Return a random timedelta between min and max hours.

        Args:
            min_hours: Minimum hours.
            max_hours: Maximum hours.

        Returns:
            A random timedelta in the specified range.
        """
        hours = self.uniform(min_hours, max_hours)
        return timedelta(hours=hours)

    def weighted_choice(self, options: dict) -> str:
        """Choose an option based on weights.

        Args:
            options: A dict mapping options to their weights.
                Example: {"approved": 0.6, "changes_requested": 0.3, "commented": 0.1}

        Returns:
            One of the options, chosen according to their weights.
        """
        items = list(options.keys())
        weights = list(options.values())
        return self.rng.choices(items, weights=weights, k=1)[0]

    def shuffle(self, seq: list) -> list:
        """Return a shuffled copy of the sequence.

        Args:
            seq: A sequence to shuffle.

        Returns:
            A new list with elements in random order.
        """
        result = list(seq)
        self.rng.shuffle(result)
        return result

    def gauss(self, mu: float, sigma: float) -> float:
        """Return a random float from a Gaussian distribution.

        Args:
            mu: Mean of the distribution.
            sigma: Standard deviation.

        Returns:
            A random float from the Gaussian distribution.
        """
        return self.rng.gauss(mu, sigma)

    def triangular(self, low: float, high: float, mode: float) -> float:
        """Return a random float from a triangular distribution.

        Useful for generating values that cluster around a mode.

        Args:
            low: Lower limit.
            high: Upper limit.
            mode: Most likely value.

        Returns:
            A random float from the triangular distribution.
        """
        return self.rng.triangular(low, high, mode)
