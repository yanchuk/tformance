"""
Demo data seeding package for tformance.

This package provides scenario-based demo data generation with:
- Hybrid data sourcing (GitHub + factories)
- Deterministic reproducibility via --seed flag
- 4 scenario presets: ai-success, review-bottleneck, baseline, detective-game

Usage:
    python manage.py seed_demo_data --scenario ai-success --seed 42
"""

from .deterministic import DeterministicRandom
from .github_fetcher import FetchedPR, GitHubPublicFetcher
from .scenarios.registry import SCENARIO_REGISTRY

__all__ = [
    "DeterministicRandom",
    "FetchedPR",
    "GitHubPublicFetcher",
    "SCENARIO_REGISTRY",
]
