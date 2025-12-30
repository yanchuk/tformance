"""Tests for get_needs_attention_prs function.

Tests for the dashboard service function that identifies PRs needing attention
based on issue severity: reverts, hotfixes, long cycle time, large PRs, and
missing Jira links (when Jira is connected).
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import JiraIntegrationFactory
from apps.metrics.factories import (
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetNeedsAttentionPrs(TestCase):
    """Tests for get_needs_attention_prs function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team, display_name="Alice Developer")
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_returns_dict_with_required_keys(self):
        """Test that get_needs_attention_prs returns dict with items, total, page, per_page, has_next, has_prev."""
        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("items", result)
        self.assertIn("total", result)
        self.assertIn("page", result)
        self.assertIn("per_page", result)
        self.assertIn("has_next", result)
        self.assertIn("has_prev", result)

    def test_returns_empty_items_when_no_issues(self):
        """Test that PRs without issues don't appear in results."""
        # Create a normal PR with no issues: not revert, not hotfix, reasonable size, has cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
            additions=50,
            deletions=30,  # Total 80 lines - not large
            cycle_time_hours=Decimal("24.0"),  # Reasonable cycle time
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["items"], [])
        self.assertEqual(result["total"], 0)

    def test_identifies_revert_prs(self):
        """Test that PRs with is_revert=True are flagged."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Revert: Bad commit",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
            additions=10,
            deletions=10,
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["id"], pr.id)
        self.assertEqual(result["items"][0]["issue_type"], "revert")
        self.assertEqual(result["items"][0]["issue_priority"], 1)

    def test_identifies_hotfix_prs(self):
        """Test that PRs with is_hotfix=True are flagged."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="hotfix: Fix critical bug",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=True,
            additions=20,
            deletions=5,
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["id"], pr.id)
        self.assertEqual(result["items"][0]["issue_type"], "hotfix")
        self.assertEqual(result["items"][0]["issue_priority"], 2)

    def test_identifies_long_cycle_time_prs(self):
        """Test that PRs with cycle_time > 2x team average are flagged."""
        # Create PRs to establish a baseline average cycle time
        # Average will be around 24 hours
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_revert=False,
                is_hotfix=False,
                additions=30,
                deletions=20,
                cycle_time_hours=Decimal("24.0"),
            )

        # Create a PR with cycle time > 2x average (> 48 hours)
        slow_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Very slow PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20, 12, 0)),
            is_revert=False,
            is_hotfix=False,
            additions=30,
            deletions=20,
            cycle_time_hours=Decimal("100.0"),  # > 2x average of 24
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], slow_pr.id)
        self.assertEqual(result["items"][0]["issue_type"], "long_cycle")
        self.assertEqual(result["items"][0]["issue_priority"], 3)

    def test_identifies_large_prs(self):
        """Test that PRs with lines_changed > 500 are flagged."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Large refactoring PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
            additions=400,
            deletions=150,  # Total 550 lines > 500
            cycle_time_hours=Decimal("24.0"),
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], pr.id)
        self.assertEqual(result["items"][0]["issue_type"], "large_pr")
        self.assertEqual(result["items"][0]["issue_priority"], 4)

    def test_identifies_missing_jira_when_jira_connected(self):
        """Test that PRs without jira_issue are flagged only if team has Jira connected."""
        # Connect Jira for this team
        JiraIntegrationFactory(team=self.team)

        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="No Jira link PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
            additions=50,
            deletions=30,
            jira_key="",  # No Jira link
            cycle_time_hours=Decimal("24.0"),
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], pr.id)
        self.assertEqual(result["items"][0]["issue_type"], "missing_jira")
        self.assertEqual(result["items"][0]["issue_priority"], 5)

    def test_does_not_flag_missing_jira_when_jira_not_connected(self):
        """Test that missing Jira link is not flagged if team has no Jira integration."""
        # No Jira integration for this team
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="No Jira link but thats OK",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
            additions=50,
            deletions=30,
            jira_key="",  # No Jira link, but that's fine
            cycle_time_hours=Decimal("24.0"),
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        # Should not flag missing jira since team has no Jira connected
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["items"], [])

    def test_prioritizes_reverts_first(self):
        """Test that reverts appear before other issue types."""
        # Create a large PR (priority 4)
        large_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Large PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
            additions=400,
            deletions=150,  # > 500 lines
            cycle_time_hours=Decimal("24.0"),
        )

        # Create a revert PR (priority 1) - created later but should appear first
        revert_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Revert: Something bad",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_revert=True,
            is_hotfix=False,
            additions=10,
            deletions=10,
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 2)
        # Revert (priority 1) should be first
        self.assertEqual(result["items"][0]["id"], revert_pr.id)
        self.assertEqual(result["items"][0]["issue_priority"], 1)
        # Large PR (priority 4) should be second
        self.assertEqual(result["items"][1]["id"], large_pr.id)
        self.assertEqual(result["items"][1]["issue_priority"], 4)

    def test_prioritizes_hotfixes_second(self):
        """Test that hotfixes appear after reverts but before other issue types."""
        # Create a large PR (priority 4)
        large_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Large PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=False,
            is_hotfix=False,
            additions=400,
            deletions=150,  # > 500 lines
            cycle_time_hours=Decimal("24.0"),
        )

        # Create a hotfix PR (priority 2)
        hotfix_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="hotfix: Critical fix",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
            is_revert=False,
            is_hotfix=True,
            additions=20,
            deletions=5,
        )

        # Create a revert PR (priority 1)
        revert_pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Revert: Bad change",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
            is_revert=True,
            is_hotfix=False,
            additions=10,
            deletions=10,
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 3)
        # Order should be: revert (1), hotfix (2), large_pr (4)
        self.assertEqual(result["items"][0]["id"], revert_pr.id)
        self.assertEqual(result["items"][0]["issue_priority"], 1)
        self.assertEqual(result["items"][1]["id"], hotfix_pr.id)
        self.assertEqual(result["items"][1]["issue_priority"], 2)
        self.assertEqual(result["items"][2]["id"], large_pr.id)
        self.assertEqual(result["items"][2]["issue_priority"], 4)

    def test_pagination_returns_correct_page(self):
        """Test that page=2 returns second set of items."""
        # Create 15 revert PRs
        prs = []
        for i in range(15):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                title=f"Revert PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i % 20, 12, 0)),
                is_revert=True,
                is_hotfix=False,
                additions=10,
                deletions=10,
            )
            prs.append(pr)

        # Get page 1
        result_page1 = dashboard_service.get_needs_attention_prs(
            self.team, self.start_date, self.end_date, page=1, per_page=10
        )
        # Get page 2
        result_page2 = dashboard_service.get_needs_attention_prs(
            self.team, self.start_date, self.end_date, page=2, per_page=10
        )

        self.assertEqual(result_page1["total"], 15)
        self.assertEqual(len(result_page1["items"]), 10)
        self.assertEqual(result_page1["page"], 1)

        self.assertEqual(result_page2["total"], 15)
        self.assertEqual(len(result_page2["items"]), 5)
        self.assertEqual(result_page2["page"], 2)

        # Ensure page 1 and page 2 have different items
        page1_ids = {item["id"] for item in result_page1["items"]}
        page2_ids = {item["id"] for item in result_page2["items"]}
        self.assertEqual(len(page1_ids & page2_ids), 0)  # No overlap

    def test_pagination_has_next_true_when_more_items(self):
        """Test that has_next=True when more pages exist."""
        # Create 15 revert PRs
        for i in range(15):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                title=f"Revert PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i % 20, 12, 0)),
                is_revert=True,
                is_hotfix=False,
                additions=10,
                deletions=10,
            )

        result = dashboard_service.get_needs_attention_prs(
            self.team, self.start_date, self.end_date, page=1, per_page=10
        )

        self.assertTrue(result["has_next"])

    def test_pagination_has_prev_true_on_page_2(self):
        """Test that has_prev=True on page > 1."""
        # Create 15 revert PRs
        for i in range(15):
            PullRequestFactory(
                team=self.team,
                author=self.member,
                state="merged",
                title=f"Revert PR {i}",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i % 20, 12, 0)),
                is_revert=True,
                is_hotfix=False,
                additions=10,
                deletions=10,
            )

        result_page1 = dashboard_service.get_needs_attention_prs(
            self.team, self.start_date, self.end_date, page=1, per_page=10
        )
        result_page2 = dashboard_service.get_needs_attention_prs(
            self.team, self.start_date, self.end_date, page=2, per_page=10
        )

        self.assertFalse(result_page1["has_prev"])
        self.assertTrue(result_page2["has_prev"])

    def test_pr_can_have_multiple_issues_uses_highest_priority(self):
        """Test that if PR is both revert and large, it uses the highest priority (revert)."""
        # Create a PR that is both a revert AND large
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Revert: Large bad change",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,  # Priority 1
            is_hotfix=False,
            additions=400,
            deletions=150,  # > 500 lines - would be priority 4 on its own
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["id"], pr.id)
        # Should use revert priority (1), not large_pr priority (4)
        self.assertEqual(result["items"][0]["issue_type"], "revert")
        self.assertEqual(result["items"][0]["issue_priority"], 1)

    def test_pr_dict_contains_required_fields(self):
        """Test that each PR dict contains all required fields."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Revert: Test PR",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
            github_repo="org/repo",
            github_pr_id=123,
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result["items"]), 1)
        pr_data = result["items"][0]

        # Check all required fields exist
        self.assertIn("id", pr_data)
        self.assertIn("title", pr_data)
        self.assertIn("url", pr_data)
        self.assertIn("author", pr_data)
        self.assertIn("author_avatar_url", pr_data)
        self.assertIn("issue_type", pr_data)
        self.assertIn("issue_priority", pr_data)
        self.assertIn("merged_at", pr_data)

        # Verify values
        self.assertEqual(pr_data["id"], pr.id)
        self.assertEqual(pr_data["title"], "Revert: Test PR")
        self.assertEqual(pr_data["url"], "https://github.com/org/repo/pull/123")
        self.assertEqual(pr_data["author"], "Alice Developer")
        self.assertIsNotNone(pr_data["merged_at"])

    def test_filters_by_date_range(self):
        """Test that only PRs merged within date range are included."""
        # In range
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="In Range Revert",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # Before start date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Before Start",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 31, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # After end date (should be excluded)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="After End",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 1, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["title"], "In Range Revert")

    def test_filters_by_team(self):
        """Test that only PRs from specified team are included."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)

        # Target team PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            title="Target Team Revert",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        # Other team PR (should be excluded)
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            title="Other Team Revert",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            is_revert=True,
            is_hotfix=False,
        )

        result = dashboard_service.get_needs_attention_prs(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["title"], "Target Team Revert")
