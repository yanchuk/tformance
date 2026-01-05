"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRReviewFactory,
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

        # Create 4 PRs: 3 AI-assisted, 1 not (using is_ai_assisted field, not surveys)
        ai_flags = [True, True, True, False]
        for i, ai_flag in enumerate(ai_flags):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_ai_assisted=ai_flag,
            )

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
        # Expected: 3 queries:
        #   1. PR aggregates with JOIN (prs_merged, cycle_time, pr_size, ai_pct)
        #   2. Reviews given aggregate
        #   3. Review response time aggregate
        with self.assertNumQueries(3):
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

        # Low AI: 1 out of 4 PRs = 25% (using is_ai_assisted field, not surveys)
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=member_low_ai,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
                is_ai_assisted=(i == 0),
            )

        # High AI: 4 out of 4 PRs = 100%
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=member_high_ai,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_ai_assisted=True,
            )

        # Mid AI: 2 out of 4 PRs = 50%
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=member_mid_ai,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
                is_ai_assisted=(i < 2),
            )

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

    # ========================================================================
    # NEW METRICS TESTS - Individual Performance Analytics Feature
    # ========================================================================

    def test_get_team_breakdown_calculates_avg_pr_size(self):
        """Test that get_team_breakdown calculates avg PR size (additions + deletions)."""
        member = TeamMemberFactory(team=self.team, display_name="Alice Smith")

        # Create 3 PRs with different sizes
        # PR 1: 100 additions + 50 deletions = 150 lines
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=100,
            deletions=50,
        )
        # PR 2: 200 additions + 100 deletions = 300 lines
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
            additions=200,
            deletions=100,
        )
        # PR 3: 50 additions + 100 deletions = 150 lines
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
            additions=50,
            deletions=100,
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Alice Smith"), None)
        self.assertIsNotNone(member_data)
        self.assertIn("avg_pr_size", member_data)
        # Average should be (150 + 300 + 150) / 3 = 200 lines
        self.assertEqual(member_data["avg_pr_size"], 200)

    def test_get_team_breakdown_handles_zero_additions_deletions(self):
        """Test that avg_pr_size handles zero additions/deletions correctly."""
        member = TeamMemberFactory(team=self.team, display_name="Bob Jones")

        # Create PR with zero additions/deletions (empty PR)
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            additions=0,
            deletions=0,
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Bob Jones"), None)
        self.assertIsNotNone(member_data)
        self.assertIn("avg_pr_size", member_data)
        # Should return 0 for empty PRs
        self.assertEqual(member_data["avg_pr_size"], 0)

    def test_get_team_breakdown_counts_reviews_given(self):
        """Test that get_team_breakdown counts reviews given by member as reviewer."""
        author = TeamMemberFactory(team=self.team, display_name="Author")
        reviewer = TeamMemberFactory(team=self.team, display_name="Reviewer")

        # Create PRs authored by 'author' but reviewed by 'reviewer'
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            # Reviewer gives 5 reviews total across PRs
            if i < 2:
                PRReviewFactory(
                    team=self.team,
                    pull_request=pr,
                    reviewer=reviewer,
                    submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 14, 0)),
                )

        # Reviewer also needs a PR to appear in breakdown (reviewer must have authored at least 1 PR)
        PullRequestFactory(
            team=self.team,
            author=reviewer,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        reviewer_data = next((m for m in result if m["member_name"] == "Reviewer"), None)
        self.assertIsNotNone(reviewer_data)
        self.assertIn("reviews_given", reviewer_data)
        self.assertEqual(reviewer_data["reviews_given"], 2)

    def test_get_team_breakdown_excludes_ai_bot_reviews(self):
        """Test that reviews_given excludes AI/bot reviews (is_ai_review=True)."""
        author = TeamMemberFactory(team=self.team, display_name="Author")
        reviewer = TeamMemberFactory(team=self.team, display_name="Human Reviewer")

        # Create PRs
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            # 2 human reviews, 1 bot review
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=reviewer,
                submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 14, 0)),
                is_ai_review=i == 2,  # Third review is AI
            )

        # Reviewer needs a PR to appear in breakdown
        PullRequestFactory(
            team=self.team,
            author=reviewer,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        reviewer_data = next((m for m in result if m["member_name"] == "Human Reviewer"), None)
        self.assertIsNotNone(reviewer_data)
        self.assertIn("reviews_given", reviewer_data)
        # Should only count 2 human reviews, not the AI review
        self.assertEqual(reviewer_data["reviews_given"], 2)

    def test_get_team_breakdown_calculates_avg_review_response_hours(self):
        """Test that avg_review_response_hours is avg time from PR creation to first review."""
        author = TeamMemberFactory(team=self.team, display_name="Author")
        reviewer = TeamMemberFactory(team=self.team, display_name="Fast Reviewer")

        # PR 1: Created Jan 10 at 10:00, first review at 12:00 = 2 hours
        pr1 = PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 18, 0)),
            pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 10, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr1,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),  # 2 hours later
        )

        # PR 2: Created Jan 11 at 10:00, first review at 14:00 = 4 hours
        pr2 = PullRequestFactory(
            team=self.team,
            author=author,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 18, 0)),
            pr_created_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 10, 0)),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr2,
            reviewer=reviewer,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 14, 0)),  # 4 hours later
        )

        # Reviewer needs a PR to appear in breakdown
        PullRequestFactory(
            team=self.team,
            author=reviewer,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        reviewer_data = next((m for m in result if m["member_name"] == "Fast Reviewer"), None)
        self.assertIsNotNone(reviewer_data)
        self.assertIn("avg_review_response_hours", reviewer_data)
        # Average should be (2 + 4) / 2 = 3 hours
        self.assertAlmostEqual(float(reviewer_data["avg_review_response_hours"]), 3.0, places=1)

    def test_get_team_breakdown_ai_pct_uses_effective_is_ai_assisted(self):
        """Test that ai_pct uses effective_is_ai_assisted (LLM-based) not surveys."""
        member = TeamMemberFactory(team=self.team, display_name="AI Developer")

        # Create 4 PRs with LLM-detected AI assistance (NOT surveys)
        # 3 AI-assisted, 1 not (using is_ai_assisted and llm_summary)
        ai_flags = [True, True, True, False]
        for i, is_ai in enumerate(ai_flags):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                is_ai_assisted=is_ai,  # Pattern-based detection
                llm_summary={"ai": {"is_assisted": is_ai, "confidence": 0.9}} if is_ai else None,
            )

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "AI Developer"), None)
        self.assertIsNotNone(member_data)
        # 3 out of 4 = 75% AI-assisted
        self.assertAlmostEqual(float(member_data["ai_pct"]), 75.0, places=1)

    def test_get_team_breakdown_ai_pct_without_surveys(self):
        """Test that ai_pct works when there are no surveys (common case)."""
        member = TeamMemberFactory(team=self.team, display_name="Developer No Survey")

        # Create PRs with is_ai_assisted flag but NO surveys
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            is_ai_assisted=True,
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
            is_ai_assisted=False,
        )
        # No PRSurvey created!

        result = dashboard_service.get_team_breakdown(self.team, self.start_date, self.end_date)

        member_data = next((m for m in result if m["member_name"] == "Developer No Survey"), None)
        self.assertIsNotNone(member_data)
        # Should still calculate 50% from is_ai_assisted field (not 0%)
        self.assertAlmostEqual(float(member_data["ai_pct"]), 50.0, places=1)


class TestGetTeamAverages(TestCase):
    """Tests for get_team_averages function - team-wide averages for comparison."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_team_averages_returns_dict(self):
        """Test that get_team_averages returns a dict with avg metrics."""
        # Create some data
        member = TeamMemberFactory(team=self.team, display_name="Alice")
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )

        result = dashboard_service.get_team_averages(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("avg_prs", result)
        self.assertIn("avg_cycle_time", result)
        self.assertIn("avg_pr_size", result)
        self.assertIn("avg_reviews", result)
        self.assertIn("avg_response_time", result)
        self.assertIn("avg_ai_pct", result)

    def test_get_team_averages_calculates_all_metrics(self):
        """Test that get_team_averages calculates correct averages."""
        member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        member2 = TeamMemberFactory(team=self.team, display_name="Bob")

        # Alice: 3 PRs, 24h cycle time, 100 lines avg
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=member1,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
                cycle_time_hours=Decimal("24.00"),
                additions=50,
                deletions=50,
            )

        # Bob: 1 PR, 48h cycle time, 200 lines
        bob_pr = PullRequestFactory(
            team=self.team,
            author=member2,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
            cycle_time_hours=Decimal("48.00"),
            additions=100,
            deletions=100,
        )

        # Alice reviews Bob's PR
        PRReviewFactory(
            team=self.team,
            pull_request=bob_pr,
            reviewer=member1,
            submitted_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 0)),
        )

        result = dashboard_service.get_team_averages(self.team, self.start_date, self.end_date)

        # avg_prs = (3 + 1) / 2 = 2
        self.assertEqual(result["avg_prs"], 2)
        # avg_cycle_time = avg of member averages = (24 + 48) / 2 = 36 hours
        # (not weighted by PR count - we want equal weight per member for comparison)
        self.assertAlmostEqual(float(result["avg_cycle_time"]), 36.0, places=1)
        # avg_pr_size = avg of member averages = (100 + 200) / 2 = 150 lines
        self.assertAlmostEqual(float(result["avg_pr_size"]), 150.0, places=1)

    def test_get_team_averages_empty_team(self):
        """Test that get_team_averages handles empty team gracefully."""
        result = dashboard_service.get_team_averages(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        # Should return zeros or None for empty data
        self.assertEqual(result["avg_prs"], 0)


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
