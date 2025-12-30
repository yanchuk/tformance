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


class TestTechBreakdownAIFilter(TestCase):
    """Tests for AI Assisted filter on tech breakdown."""

    def setUp(self):
        """Set up test fixtures with AI and non-AI PRs."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

        # Create AI-assisted PR with LLM summary
        self.ai_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            llm_summary={
                "ai": {"is_assisted": True, "confidence": 0.9, "tools": ["copilot"]},
                "tech": {"categories": ["backend"]},
            },
        )
        PRFileFactory(
            team=self.team,
            pull_request=self.ai_pr,
            filename="apps/api/views.py",
        )

        # Create non-AI PR with LLM summary
        self.non_ai_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            llm_summary={
                "ai": {"is_assisted": False, "confidence": 0.1, "tools": []},
                "tech": {"categories": ["frontend"]},
            },
        )
        PRFileFactory(
            team=self.team,
            pull_request=self.non_ai_pr,
            filename="src/components/Button.tsx",
        )

    def test_get_tech_breakdown_accepts_ai_filter_parameter(self):
        """Test that get_tech_breakdown accepts ai_assisted filter parameter."""
        # Should not raise TypeError for unexpected keyword argument
        result = dashboard_service.get_tech_breakdown(self.team, self.start_date, self.end_date, ai_assisted="all")
        self.assertIsInstance(result, list)

    def test_get_tech_breakdown_ai_filter_all_returns_both(self):
        """Test that ai_assisted='all' returns both AI and non-AI PRs."""
        result = dashboard_service.get_tech_breakdown(self.team, self.start_date, self.end_date, ai_assisted="all")

        # Should have both backend (AI) and frontend (non-AI) categories
        categories = {item["category"] for item in result}
        self.assertIn("backend", categories)
        self.assertIn("frontend", categories)

    def test_get_tech_breakdown_ai_filter_yes_returns_only_ai(self):
        """Test that ai_assisted='yes' returns only AI-assisted PRs."""
        result = dashboard_service.get_tech_breakdown(self.team, self.start_date, self.end_date, ai_assisted="yes")

        # Should only have backend (from AI PR)
        categories = {item["category"] for item in result}
        self.assertIn("backend", categories)
        self.assertNotIn("frontend", categories)

    def test_get_tech_breakdown_ai_filter_no_returns_only_non_ai(self):
        """Test that ai_assisted='no' returns only non-AI PRs."""
        result = dashboard_service.get_tech_breakdown(self.team, self.start_date, self.end_date, ai_assisted="no")

        # Should only have frontend (from non-AI PR)
        categories = {item["category"] for item in result}
        self.assertNotIn("backend", categories)
        self.assertIn("frontend", categories)

    def test_get_tech_breakdown_ai_filter_uses_effective_property(self):
        """Test that filter uses effective_is_ai_assisted property."""
        # Create PR with is_ai_assisted=True but LLM says False
        # LLM should take priority (effective_is_ai_assisted returns LLM value)
        mixed_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            is_ai_assisted=True,  # Pattern detection says yes
            llm_summary={
                "ai": {"is_assisted": False, "confidence": 0.8, "tools": []},  # LLM says no
                "tech": {"categories": ["devops"]},
            },
        )
        PRFileFactory(team=self.team, pull_request=mixed_pr, filename=".github/workflows/ci.yml")

        # Filter for AI=yes should NOT include this PR (LLM takes priority)
        result = dashboard_service.get_tech_breakdown(self.team, self.start_date, self.end_date, ai_assisted="yes")
        categories = {item["category"] for item in result}
        self.assertNotIn("devops", categories)

        # Filter for AI=no SHOULD include this PR
        result = dashboard_service.get_tech_breakdown(self.team, self.start_date, self.end_date, ai_assisted="no")
        categories = {item["category"] for item in result}
        self.assertIn("devops", categories)


class TestMonthlyTechTrendAIFilter(TestCase):
    """Tests for AI Assisted filter on monthly tech trend."""

    def setUp(self):
        """Set up test fixtures with AI and non-AI PRs in different months."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 3, 31)

        # AI PR in January
        self.ai_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            llm_summary={
                "ai": {"is_assisted": True, "confidence": 0.9, "tools": ["copilot"]},
                "tech": {"categories": ["backend"]},
            },
        )

        # Non-AI PR in February
        self.non_ai_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
            llm_summary={
                "ai": {"is_assisted": False, "confidence": 0.1, "tools": []},
                "tech": {"categories": ["frontend"]},
            },
        )

    def test_get_monthly_tech_trend_accepts_ai_filter_parameter(self):
        """Test that get_monthly_tech_trend accepts ai_assisted filter parameter."""
        # get_monthly_tech_trend returns {category: [{month: ..., value: ...}]}
        result = dashboard_service.get_monthly_tech_trend(self.team, self.start_date, self.end_date, ai_assisted="all")
        self.assertIsInstance(result, dict)
        # Should have both categories
        self.assertIn("backend", result)
        self.assertIn("frontend", result)

    def test_get_monthly_tech_trend_ai_filter_yes_only_includes_ai_prs(self):
        """Test that ai_assisted='yes' only includes AI-assisted PRs in datasets."""
        result = dashboard_service.get_monthly_tech_trend(self.team, self.start_date, self.end_date, ai_assisted="yes")

        # Should only have backend category (from AI PR)
        self.assertIn("backend", result)
        self.assertNotIn("frontend", result)

    def test_get_monthly_tech_trend_ai_filter_no_only_includes_non_ai_prs(self):
        """Test that ai_assisted='no' only includes non-AI PRs in datasets."""
        result = dashboard_service.get_monthly_tech_trend(self.team, self.start_date, self.end_date, ai_assisted="no")

        # Should only have frontend category (from non-AI PR)
        self.assertNotIn("backend", result)
        self.assertIn("frontend", result)
