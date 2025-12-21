"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    DeploymentFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetDeploymentMetrics(TestCase):
    """Tests for get_deployment_metrics function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_deployment_metrics_returns_dict(self):
        """Test that get_deployment_metrics returns a dict with required keys."""
        result = dashboard_service.get_deployment_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("total_deployments", result)
        self.assertIn("production_deployments", result)
        self.assertIn("success_rate", result)
        self.assertIn("deployments_per_week", result)
        self.assertIn("by_environment", result)

    def test_get_deployment_metrics_counts_correctly(self):
        """Test that get_deployment_metrics counts deployments correctly."""
        creator = TeamMemberFactory(team=self.team)

        # Create 3 production deployments and 2 staging
        for _ in range(3):
            DeploymentFactory(
                team=self.team,
                environment="production",
                status="success",
                creator=creator,
                deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
        for _ in range(2):
            DeploymentFactory(
                team=self.team,
                environment="staging",
                status="success",
                creator=creator,
                deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            )

        result = dashboard_service.get_deployment_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_deployments"], 5)
        self.assertEqual(result["production_deployments"], 3)

    def test_get_deployment_metrics_calculates_success_rate(self):
        """Test that get_deployment_metrics calculates success rate correctly."""
        creator = TeamMemberFactory(team=self.team)

        # Create 4 successful and 1 failed deployment
        for _ in range(4):
            DeploymentFactory(
                team=self.team,
                environment="production",
                status="success",
                creator=creator,
                deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
        DeploymentFactory(
            team=self.team,
            environment="production",
            status="failure",
            creator=creator,
            deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
        )

        result = dashboard_service.get_deployment_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["success_rate"], Decimal("80.00"))

    def test_get_deployment_metrics_returns_zero_when_no_data(self):
        """Test that get_deployment_metrics returns zero values when no data exists."""
        result = dashboard_service.get_deployment_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_deployments"], 0)
        self.assertEqual(result["success_rate"], Decimal("0.00"))
        self.assertEqual(result["deployments_per_week"], Decimal("0.00"))

    def test_get_deployment_metrics_breaks_down_by_environment(self):
        """Test that get_deployment_metrics breaks down by environment."""
        creator = TeamMemberFactory(team=self.team)

        DeploymentFactory(
            team=self.team,
            environment="production",
            status="success",
            creator=creator,
            deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        DeploymentFactory(
            team=self.team,
            environment="staging",
            status="success",
            creator=creator,
            deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
        )
        DeploymentFactory(
            team=self.team,
            environment="staging",
            status="success",
            creator=creator,
            deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 14, 12, 0)),
        )

        result = dashboard_service.get_deployment_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result["by_environment"]), 2)
        env_counts = {e["environment"]: e["total"] for e in result["by_environment"]}
        self.assertEqual(env_counts["production"], 1)
        self.assertEqual(env_counts["staging"], 2)

    def test_get_deployment_metrics_filters_by_team(self):
        """Test that get_deployment_metrics only includes data from the specified team."""
        creator = TeamMemberFactory(team=self.team)
        DeploymentFactory(
            team=self.team,
            environment="production",
            status="success",
            creator=creator,
            deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        # Create deployment for other team
        other_team = TeamFactory()
        other_creator = TeamMemberFactory(team=other_team)
        DeploymentFactory(
            team=other_team,
            environment="production",
            status="success",
            creator=other_creator,
            deployed_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_deployment_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_deployments"], 1)
