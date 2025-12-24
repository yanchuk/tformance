"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetTeamBreakdown(TestCase):
    """Tests for get_team_breakdown function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_team_breakdown_returns_list_of_dicts(self):
        """Test that get_team_breakdown returns a list of member dicts."""
        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, list)

    def test_get_team_breakdown_includes_member_name(self):
        """Test that get_team_breakdown includes member display name."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreater(len(result), 0)
        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertIsNotNone(member_data)

    def test_get_team_breakdown_counts_prs_merged_per_member(self):
        """Test that get_team_breakdown counts PRs merged per member."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")

        # Create 3 merged PRs for this member
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertEqual(member_data["prs_merged"], 3)

    def test_get_team_breakdown_calculates_avg_cycle_time_per_member(self):
        """Test that get_team_breakdown calculates average cycle time per member."""
        member = TeamMemberFactory(team=self.team, display_name="Bob Jones")

        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("24.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("48.00"),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Bob Jones"), None)
        # Average should be (24 + 48) / 2 = 36
        self.assertEqual(member_data["avg_cycle_time"], Decimal("36.00"))

    def test_get_team_breakdown_calculates_ai_percentage_per_member(self):
        """Test that get_team_breakdown calculates AI-assisted percentage per member."""
        member = TeamMemberFactory(team=self.team, display_name="Charlie Brown")

        # Create 4 PRs: 3 AI-assisted, 1 not
        ai_flags = [True, True, True, False]
        for i, ai_flag in enumerate(ai_flags):
            pr = PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=ai_flag)

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Charlie Brown"), None)
        # 3 out of 4 = 75%
        self.assertAlmostEqual(float(member_data["ai_pct"]), 75.0, places=1)

    def test_get_team_breakdown_includes_multiple_members(self):
        """Test that get_team_breakdown includes all members with activity."""
        member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        member2 = TeamMemberFactory(team=self.team, display_name="Bob")

        PullRequestFactory(
            team=self.team,
            author=member1,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PullRequestFactory(
            team=self.team,
            author=member2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreaterEqual(len(result), 2)
        names = [m["member_name"] for m in result]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

    def test_get_team_breakdown_excludes_members_with_no_activity(self):
        """Test that get_team_breakdown excludes members with no merged PRs."""
        active_member = TeamMemberFactory(team=self.team, display_name="Active")
        TeamMemberFactory(team=self.team, display_name="Inactive")  # Intentionally unused

        PullRequestFactory(
            team=self.team,
            author=active_member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        names = [m["member_name"] for m in result]
        self.assertIn("Active", names)
        self.assertNotIn("Inactive", names)

    def test_get_team_breakdown_query_count_is_constant(self):
        """Test that query count is constant regardless of team size (no N+1)."""
        # Create 10 members with PRs
        for i in range(10):
            member = TeamMemberFactory(team=self.team, display_name=f"Member{i}")
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )

        # Should use constant number of queries (not N+1)
        # Expected: 2 queries (PR aggregates with JOIN, surveys aggregate)
        with self.assertNumQueries(2):
            result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertEqual(len(result), 10)

    def test_get_team_breakdown_includes_member_id(self):
        """Test that get_team_breakdown includes member_id in each row."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreater(len(result), 0)
        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertIsNotNone(member_data)
        self.assertIn("member_id", member_data)
        self.assertEqual(member_data["member_id"], member.id)

    def test_get_team_breakdown_default_sort_is_prs_merged_desc(self):
        """Test that default sorting is by prs_merged descending (most active first)."""
        # Create members with different PR counts
        member_low = TeamMemberFactory(team=self.team, display_name="Low Activity")
        member_high = TeamMemberFactory(team=self.team, display_name="High Activity")
        member_mid = TeamMemberFactory(team=self.team, display_name="Mid Activity")

        # Low: 2 PRs
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                author=member_low,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
            )

        # High: 10 PRs
        for i in range(10):
            PullRequestFactory(
                team=self.team,
                author=member_high,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )

        # Mid: 5 PRs
        for i in range(5):
            PullRequestFactory(
                team=self.team,
                author=member_mid,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
            )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        # Should be sorted by prs_merged descending: High (10), Mid (5), Low (2)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["member_name"], "High Activity")
        self.assertEqual(result[0]["prs_merged"], 10)
        self.assertEqual(result[1]["member_name"], "Mid Activity")
        self.assertEqual(result[1]["prs_merged"], 5)
        self.assertEqual(result[2]["member_name"], "Low Activity")
        self.assertEqual(result[2]["prs_merged"], 2)

    def test_get_team_breakdown_sort_by_cycle_time_asc(self):
        """Test that sorting by cycle_time ascending works correctly."""
        # Create members with different cycle times
        member_slow = TeamMemberFactory(team=self.team, display_name="Slow Developer")
        member_fast = TeamMemberFactory(team=self.team, display_name="Fast Developer")
        member_medium = TeamMemberFactory(team=self.team, display_name="Medium Developer")

        # Slow: avg 72 hours
        PullRequestFactory(
            team=self.team,
            author=member_slow,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            cycle_time_hours=Decimal("72.00"),
        )

        # Fast: avg 12 hours
        PullRequestFactory(
            team=self.team,
            author=member_fast,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
            cycle_time_hours=Decimal("12.00"),
        )

        # Medium: avg 36 hours
        PullRequestFactory(
            team=self.team,
            author=member_medium,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            cycle_time_hours=Decimal("36.00"),
        )

        result = dashboard_service.get_team_breakdown(
            self.team, self.start_date, self.end_date, sort_by="cycle_time", order="asc"
        )

        # Should be sorted by cycle_time ascending: Fast (12), Medium (36), Slow (72)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["member_name"], "Fast Developer")
        self.assertEqual(result[0]["avg_cycle_time"], Decimal("12.00"))
        self.assertEqual(result[1]["member_name"], "Medium Developer")
        self.assertEqual(result[1]["avg_cycle_time"], Decimal("36.00"))
        self.assertEqual(result[2]["member_name"], "Slow Developer")
        self.assertEqual(result[2]["avg_cycle_time"], Decimal("72.00"))

    def test_get_team_breakdown_sort_by_name_asc(self):
        """Test that sorting by name ascending works correctly (alphabetical)."""
        # Create members with names that will sort differently
        member_z = TeamMemberFactory(team=self.team, display_name="Zara Wilson")
        member_a = TeamMemberFactory(team=self.team, display_name="Alice Anderson")
        member_m = TeamMemberFactory(team=self.team, display_name="Mike Martinez")

        # Give them all PRs
        for member in [member_z, member_a, member_m]:
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )

        result = dashboard_service.get_team_breakdown(
            self.team, self.start_date, self.end_date, sort_by="name", order="asc"
        )

        # Should be sorted alphabetically: Alice, Mike, Zara
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["member_name"], "Alice Anderson")
        self.assertEqual(result[1]["member_name"], "Mike Martinez")
        self.assertEqual(result[2]["member_name"], "Zara Wilson")

    def test_get_team_breakdown_sort_by_ai_pct_desc(self):
        """Test that sorting by ai_pct descending works correctly."""
        # Create members with different AI percentages
        member_low_ai = TeamMemberFactory(team=self.team, display_name="Low AI User")
        member_high_ai = TeamMemberFactory(team=self.team, display_name="High AI User")
        member_mid_ai = TeamMemberFactory(team=self.team, display_name="Mid AI User")

        # Low AI: 1 out of 4 PRs = 25%
        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                author=member_low_ai,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=(i == 0))

        # High AI: 4 out of 4 PRs = 100%
        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                author=member_high_ai,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=True)

        # Mid AI: 2 out of 4 PRs = 50%
        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                author=member_mid_ai,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
            )
            PRSurveyFactory(team=self.team, pull_request=pr, author_ai_assisted=(i < 2))

        result = dashboard_service.get_team_breakdown(
            self.team, self.start_date, self.end_date, sort_by="ai_pct", order="desc"
        )

        # Should be sorted by ai_pct descending: High (100%), Mid (50%), Low (25%)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["member_name"], "High AI User")
        self.assertAlmostEqual(float(result[0]["ai_pct"]), 100.0, places=1)
        self.assertEqual(result[1]["member_name"], "Mid AI User")
        self.assertAlmostEqual(float(result[1]["ai_pct"]), 50.0, places=1)
        self.assertEqual(result[2]["member_name"], "Low AI User")
        self.assertAlmostEqual(float(result[2]["ai_pct"]), 25.0, places=1)


class TestAvatarUrlFromGithubId(TestCase):
    """Tests for _avatar_url_from_github_id helper function."""

    def test_avatar_url_with_numeric_id(self):
        """Test that numeric GitHub ID produces /u/<id> format URL."""
        from apps.metrics.services.dashboard_service import _avatar_url_from_github_id

        result = _avatar_url_from_github_id("281715")

        self.assertEqual(result, "https://avatars.githubusercontent.com/u/281715?s=80")

    def test_avatar_url_with_username(self):
        """Test that username produces /<username> format URL (no /u/)."""
        from apps.metrics.services.dashboard_service import _avatar_url_from_github_id

        result = _avatar_url_from_github_id("birkjernstrom")

        # Username should not have /u/ prefix
        self.assertEqual(result, "https://avatars.githubusercontent.com/birkjernstrom?s=80")

    def test_avatar_url_with_none(self):
        """Test that None returns empty string."""
        from apps.metrics.services.dashboard_service import _avatar_url_from_github_id

        result = _avatar_url_from_github_id(None)

        self.assertEqual(result, "")

    def test_avatar_url_with_empty_string(self):
        """Test that empty string returns empty string."""
        from apps.metrics.services.dashboard_service import _avatar_url_from_github_id

        result = _avatar_url_from_github_id("")

        self.assertEqual(result, "")
