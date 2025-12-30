"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRFileFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetFileCategoryBreakdown(TestCase):
    """Tests for get_file_category_breakdown function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_file_category_breakdown_returns_dict(self):
        """Test that get_file_category_breakdown returns a dict with required keys."""
        result = dashboard_service.get_file_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("total_files", result)
        self.assertIn("total_changes", result)
        self.assertIn("by_category", result)

    def test_get_file_category_breakdown_counts_files_correctly(self):
        """Test that get_file_category_breakdown counts files correctly."""
        member = TeamMemberFactory(team=self.team)
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        # Create 3 backend files
        for i in range(3):
            PRFileFactory(
                team=self.team,
                pull_request=pr,
                filename=f"apps/module/views{i}.py",
                additions=10,
                deletions=5,
            )

        result = dashboard_service.get_file_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_files"], 3)
        self.assertEqual(result["total_changes"], 45)  # 3 * (10 + 5)

    def test_get_file_category_breakdown_groups_by_category(self):
        """Test that get_file_category_breakdown groups files by category."""
        member = TeamMemberFactory(team=self.team)
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        # Backend files
        PRFileFactory(team=self.team, pull_request=pr, filename="apps/users/views.py", additions=50, deletions=10)
        # Frontend files
        PRFileFactory(team=self.team, pull_request=pr, filename="src/components/Button.tsx", additions=30, deletions=5)
        PRFileFactory(team=self.team, pull_request=pr, filename="src/pages/Home.tsx", additions=40, deletions=15)

        result = dashboard_service.get_file_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_files"], 3)
        # Find categories
        categories = {c["category"]: c for c in result["by_category"]}
        self.assertIn("backend", categories)
        self.assertIn("frontend", categories)
        self.assertEqual(categories["backend"]["file_count"], 1)
        self.assertEqual(categories["frontend"]["file_count"], 2)

    def test_get_file_category_breakdown_returns_zero_when_no_data(self):
        """Test that get_file_category_breakdown returns zero values when no data exists."""
        result = dashboard_service.get_file_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_files"], 0)
        self.assertEqual(result["total_changes"], 0)
        self.assertEqual(result["by_category"], [])

    def test_get_file_category_breakdown_filters_by_team(self):
        """Test that get_file_category_breakdown only includes data from the specified team."""
        member = TeamMemberFactory(team=self.team)
        pr = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRFileFactory(team=self.team, pull_request=pr, filename="apps/views.py", additions=10, deletions=5)

        # Create file for other team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        other_pr = PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRFileFactory(team=other_team, pull_request=other_pr, filename="apps/models.py", additions=20, deletions=10)

        result = dashboard_service.get_file_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_files"], 1)
        self.assertEqual(result["total_changes"], 15)

    def test_get_file_category_breakdown_filters_by_date_range(self):
        """Test that get_file_category_breakdown filters by date range."""
        member = TeamMemberFactory(team=self.team)

        # PR within range
        pr_in_range = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRFileFactory(team=self.team, pull_request=pr_in_range, filename="apps/views.py", additions=10, deletions=5)

        # PR outside range
        pr_outside_range = PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
        )
        PRFileFactory(
            team=self.team, pull_request=pr_outside_range, filename="apps/models.py", additions=20, deletions=10
        )

        result = dashboard_service.get_file_category_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_files"], 1)
        self.assertEqual(result["total_changes"], 15)


class TestIsValidCategory(TestCase):
    """Tests for _is_valid_category helper function."""

    def test_is_valid_category_accepts_valid_strings(self):
        """Test that valid category strings return True."""
        from apps.metrics.services.dashboard_service import _is_valid_category

        valid_categories = ["frontend", "backend", "devops", "test", "other"]
        for cat in valid_categories:
            self.assertTrue(_is_valid_category(cat), f"Should accept: {cat}")

    def test_is_valid_category_rejects_empty_string(self):
        """Test that empty string returns False."""
        from apps.metrics.services.dashboard_service import _is_valid_category

        self.assertFalse(_is_valid_category(""))
        self.assertFalse(_is_valid_category("   "))

    def test_is_valid_category_rejects_none(self):
        """Test that None returns False."""
        from apps.metrics.services.dashboard_service import _is_valid_category

        self.assertFalse(_is_valid_category(None))

    def test_is_valid_category_rejects_empty_dict(self):
        """Test that empty dict returns False."""
        from apps.metrics.services.dashboard_service import _is_valid_category

        self.assertFalse(_is_valid_category({}))

    def test_is_valid_category_rejects_dict_string_representation(self):
        """Test that '{}' string returns False."""
        from apps.metrics.services.dashboard_service import _is_valid_category

        self.assertFalse(_is_valid_category("{}"))
        self.assertFalse(_is_valid_category("[]"))

    def test_is_valid_category_rejects_none_string(self):
        """Test that 'None' and 'null' strings return False."""
        from apps.metrics.services.dashboard_service import _is_valid_category

        self.assertFalse(_is_valid_category("None"))
        self.assertFalse(_is_valid_category("null"))
