"""Tests for PR list service - filtering and querying PRs for data explorer page."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRFileFactory,
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.pr_list_service import (
    PR_SIZE_BUCKETS,
    get_filter_options,
    get_pr_stats,
    get_prs_queryset,
)


class TestGetPrsQueryset(TestCase):
    """Tests for get_prs_queryset function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")

    def test_returns_prs_for_team(self):
        """Test that only PRs for the specified team are returned."""
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        other_team = TeamFactory()
        PullRequestFactory(team=other_team)  # Should not be returned

        result = get_prs_queryset(self.team, {})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_repo(self):
        """Test filtering by repository."""
        pr1 = PullRequestFactory(team=self.team, github_repo="org/repo-a")
        PullRequestFactory(team=self.team, github_repo="org/repo-b")

        result = get_prs_queryset(self.team, {"repo": "org/repo-a"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_author(self):
        """Test filtering by author (team member ID)."""
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        PullRequestFactory(team=self.team, author=self.member2)

        result = get_prs_queryset(self.team, {"author": str(self.member1.id)})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_github_name(self):
        """Test filtering by GitHub username (e.g., @alice)."""
        # Create member with known github_username
        member = TeamMemberFactory(team=self.team, github_username="alice-dev")
        pr1 = PullRequestFactory(team=self.team, author=member)
        PullRequestFactory(team=self.team, author=self.member1)

        # Test with @ prefix
        result = get_prs_queryset(self.team, {"github_name": "@alice-dev"})
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

        # Test without @ prefix
        result = get_prs_queryset(self.team, {"github_name": "alice-dev"})
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_github_name_case_insensitive(self):
        """Test that github_name filter is case-insensitive."""
        member = TeamMemberFactory(team=self.team, github_username="Alice-Dev")
        pr1 = PullRequestFactory(team=self.team, author=member)

        result = get_prs_queryset(self.team, {"github_name": "@alice-dev"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_github_name_not_found_returns_empty(self):
        """Test that non-existent github_name returns empty queryset."""
        PullRequestFactory(team=self.team, author=self.member1)

        result = get_prs_queryset(self.team, {"github_name": "@nonexistent"})

        self.assertEqual(result.count(), 0)

    def test_filter_by_github_name_team_scoped(self):
        """Test that github_name filter is scoped to the current team only (security)."""
        # Create same username in different team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team, github_username="shared-user")
        PullRequestFactory(team=other_team, author=other_member)

        # Create in our team
        our_member = TeamMemberFactory(team=self.team, github_username="shared-user")
        pr1 = PullRequestFactory(team=self.team, author=our_member)

        result = get_prs_queryset(self.team, {"github_name": "@shared-user"})

        # Should only find PR from our team
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    # =========================================================================
    # reviewer_name filter tests (filter PRs by reviewer's GitHub username)
    # =========================================================================

    def test_filter_by_reviewer_name(self):
        """Test filtering by reviewer GitHub username (e.g., @alice)."""
        # Create member with known github_username who will be a reviewer
        reviewer = TeamMemberFactory(team=self.team, github_username="alice-reviewer")
        # Create PR authored by someone else, reviewed by alice-reviewer
        # Note: state="commented" used since reviewer_name filter excludes approved reviews
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        PRReviewFactory(team=self.team, pull_request=pr1, reviewer=reviewer, state="commented")
        # Create another PR without review from alice-reviewer
        PullRequestFactory(team=self.team, author=self.member1)

        # Test with @ prefix
        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

        # Test without @ prefix
        result = get_prs_queryset(self.team, {"reviewer_name": "alice-reviewer"})
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_reviewer_name_case_insensitive(self):
        """Test that reviewer_name filter is case-insensitive."""
        reviewer = TeamMemberFactory(team=self.team, github_username="Alice-Reviewer")
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        PRReviewFactory(team=self.team, pull_request=pr1, reviewer=reviewer, state="commented")

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_reviewer_name_not_found_returns_empty(self):
        """Test that non-existent reviewer_name returns empty queryset."""
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        PRReviewFactory(team=self.team, pull_request=pr1, reviewer=self.member2)

        result = get_prs_queryset(self.team, {"reviewer_name": "@nonexistent"})

        self.assertEqual(result.count(), 0)

    def test_filter_by_reviewer_name_team_scoped(self):
        """Test that reviewer_name filter is scoped to the current team only (security)."""
        # Create same username in different team
        other_team = TeamFactory()
        other_reviewer = TeamMemberFactory(team=other_team, github_username="shared-reviewer")
        other_pr = PullRequestFactory(team=other_team)
        PRReviewFactory(team=other_team, pull_request=other_pr, reviewer=other_reviewer, state="commented")

        # Create in our team with same github_username
        our_reviewer = TeamMemberFactory(team=self.team, github_username="shared-reviewer")
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        PRReviewFactory(team=self.team, pull_request=pr1, reviewer=our_reviewer, state="commented")

        result = get_prs_queryset(self.team, {"reviewer_name": "@shared-reviewer"})

        # Should only find PR from our team
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_reviewer_name_multiple_reviews(self):
        """Test that reviewer_name returns PR only once even with multiple reviews."""
        from datetime import timedelta

        from django.utils import timezone

        reviewer = TeamMemberFactory(team=self.team, github_username="multi-reviewer")
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        now = timezone.now()
        # Same reviewer submits multiple reviews on same PR
        # First review approved (older), latest review commented (newer) - should show
        # because latest review is not approved
        PRReviewFactory(
            team=self.team,
            pull_request=pr1,
            reviewer=reviewer,
            state="approved",
            submitted_at=now - timedelta(hours=2),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=pr1,
            reviewer=reviewer,
            state="commented",
            submitted_at=now - timedelta(hours=1),
        )

        result = get_prs_queryset(self.team, {"reviewer_name": "@multi-reviewer"})

        # Should return PR only once (distinct)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_reviewer(self):
        """Test filtering by reviewer (team member ID)."""
        pr1 = PullRequestFactory(team=self.team, author=self.member1)
        PullRequestFactory(team=self.team, author=self.member1)  # PR without review
        PRReviewFactory(team=self.team, pull_request=pr1, reviewer=self.member2)

        result = get_prs_queryset(self.team, {"reviewer": str(self.member2.id)})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_ai_yes(self):
        """Test filtering for AI-assisted PRs."""
        pr1 = PullRequestFactory(team=self.team, is_ai_assisted=True)
        PullRequestFactory(team=self.team, is_ai_assisted=False)

        result = get_prs_queryset(self.team, {"ai": "yes"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_ai_no(self):
        """Test filtering for non-AI-assisted PRs."""
        PullRequestFactory(team=self.team, is_ai_assisted=True)
        pr2 = PullRequestFactory(team=self.team, is_ai_assisted=False)

        result = get_prs_queryset(self.team, {"ai": "no"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr2)

    def test_filter_by_ai_all(self):
        """Test that ai=all returns all PRs."""
        PullRequestFactory(team=self.team, is_ai_assisted=True)
        PullRequestFactory(team=self.team, is_ai_assisted=False)

        result = get_prs_queryset(self.team, {"ai": "all"})

        self.assertEqual(result.count(), 2)

    def test_filter_by_ai_tool(self):
        """Test filtering by specific AI tool."""
        pr1 = PullRequestFactory(team=self.team, is_ai_assisted=True, ai_tools_detected=["claude_code"])
        PullRequestFactory(team=self.team, is_ai_assisted=True, ai_tools_detected=["copilot"])

        result = get_prs_queryset(self.team, {"ai_tool": "claude_code"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_size_xs(self):
        """Test filtering by PR size XS (0-10 lines)."""
        pr1 = PullRequestFactory(team=self.team, additions=5, deletions=3)  # 8 total
        PullRequestFactory(team=self.team, additions=50, deletions=20)  # 70 total

        result = get_prs_queryset(self.team, {"size": "XS"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_size_s(self):
        """Test filtering by PR size S (11-50 lines)."""
        PullRequestFactory(team=self.team, additions=5, deletions=3)  # 8 total - XS
        pr2 = PullRequestFactory(team=self.team, additions=20, deletions=15)  # 35 total - S
        PullRequestFactory(team=self.team, additions=100, deletions=80)  # 180 total - M

        result = get_prs_queryset(self.team, {"size": "S"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr2)

    def test_filter_by_size_m(self):
        """Test filtering by PR size M (51-200 lines)."""
        PullRequestFactory(team=self.team, additions=20, deletions=15)  # 35 total - S
        pr2 = PullRequestFactory(team=self.team, additions=100, deletions=80)  # 180 total - M
        PullRequestFactory(team=self.team, additions=300, deletions=150)  # 450 total - L

        result = get_prs_queryset(self.team, {"size": "M"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr2)

    def test_filter_by_size_l(self):
        """Test filtering by PR size L (201-500 lines)."""
        PullRequestFactory(team=self.team, additions=100, deletions=80)  # 180 total - M
        pr2 = PullRequestFactory(team=self.team, additions=300, deletions=150)  # 450 total - L
        PullRequestFactory(team=self.team, additions=600, deletions=200)  # 800 total - XL

        result = get_prs_queryset(self.team, {"size": "L"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr2)

    def test_filter_by_size_xl(self):
        """Test filtering by PR size XL (501+ lines)."""
        PullRequestFactory(team=self.team, additions=300, deletions=150)  # 450 total - L
        pr2 = PullRequestFactory(team=self.team, additions=600, deletions=200)  # 800 total - XL

        result = get_prs_queryset(self.team, {"size": "XL"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr2)

    def test_filter_by_state(self):
        """Test filtering by PR state."""
        pr1 = PullRequestFactory(team=self.team, state="merged")
        PullRequestFactory(team=self.team, state="open")
        PullRequestFactory(team=self.team, state="closed")

        result = get_prs_queryset(self.team, {"state": "merged"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_is_draft_true(self):
        """Test filtering for draft PRs."""
        pr_draft = PullRequestFactory(team=self.team, state="open", is_draft=True)
        PullRequestFactory(team=self.team, state="open", is_draft=False)

        result = get_prs_queryset(self.team, {"is_draft": "true"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr_draft)

    def test_filter_by_is_draft_false(self):
        """Test filtering for non-draft PRs."""
        PullRequestFactory(team=self.team, state="open", is_draft=True)
        pr_not_draft = PullRequestFactory(team=self.team, state="open", is_draft=False)

        result = get_prs_queryset(self.team, {"is_draft": "false"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr_not_draft)

    def test_filter_by_state_and_is_draft_combined(self):
        """Test filtering open non-draft PRs (reviewer pending reviews use case)."""
        # Draft open PR - should NOT be found
        PullRequestFactory(team=self.team, state="open", is_draft=True)
        # Non-draft open PR - should be found
        pr_ready = PullRequestFactory(team=self.team, state="open", is_draft=False)
        # Merged PR - should NOT be found
        PullRequestFactory(team=self.team, state="merged", is_draft=False)

        result = get_prs_queryset(self.team, {"state": "open", "is_draft": "false"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr_ready)

    def test_filter_by_has_jira_yes(self):
        """Test filtering for PRs with Jira links."""
        pr1 = PullRequestFactory(team=self.team, jira_key="PROJ-123")
        PullRequestFactory(team=self.team, jira_key="")

        result = get_prs_queryset(self.team, {"has_jira": "yes"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_has_jira_no(self):
        """Test filtering for PRs without Jira links."""
        PullRequestFactory(team=self.team, jira_key="PROJ-123")
        pr2 = PullRequestFactory(team=self.team, jira_key="")

        result = get_prs_queryset(self.team, {"has_jira": "no"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr2)

    def test_filter_by_date_range(self):
        """Test filtering by date range (merged_at)."""
        today = timezone.now()
        week_ago = today - timedelta(days=7)

        pr1 = PullRequestFactory(team=self.team, merged_at=today - timedelta(days=3), state="merged")
        PullRequestFactory(team=self.team, merged_at=today - timedelta(days=20), state="merged")

        result = get_prs_queryset(
            self.team,
            {"date_from": week_ago.date().isoformat(), "date_to": today.date().isoformat()},
        )

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_filter_by_date_range_for_open_prs_uses_created_at(self):
        """Test that open PRs are filtered by pr_created_at, not merged_at.

        Open PRs don't have merged_at (it's null), so filtering by merged_at
        would exclude all open PRs. This test ensures state=open uses pr_created_at.
        """
        today = timezone.now()
        week_ago = today - timedelta(days=7)

        # Open PR created 3 days ago (should be found)
        pr_open_recent = PullRequestFactory(
            team=self.team,
            state="open",
            pr_created_at=today - timedelta(days=3),
            merged_at=None,  # Open PRs have no merged_at
        )
        # Open PR created 20 days ago (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="open",
            pr_created_at=today - timedelta(days=20),
            merged_at=None,
        )
        # Merged PR from same period (should be excluded by state filter)
        PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=today - timedelta(days=3),
            merged_at=today - timedelta(days=1),
        )

        result = get_prs_queryset(
            self.team,
            {
                "state": "open",
                "date_from": week_ago.date().isoformat(),
                "date_to": today.date().isoformat(),
            },
        )

        # Should find only the recent open PR
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr_open_recent)

    def test_filter_by_date_range_for_merged_prs_uses_merged_at(self):
        """Test that merged PRs are filtered by merged_at for consistency."""
        today = timezone.now()
        week_ago = today - timedelta(days=7)

        # Merged PR merged 3 days ago (should be found)
        pr_merged_recent = PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=today - timedelta(days=30),  # Created long ago
            merged_at=today - timedelta(days=3),  # But merged recently
        )
        # Merged PR merged 20 days ago (should be excluded)
        PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=today - timedelta(days=25),
            merged_at=today - timedelta(days=20),
        )

        result = get_prs_queryset(
            self.team,
            {
                "state": "merged",
                "date_from": week_ago.date().isoformat(),
                "date_to": today.date().isoformat(),
            },
        )

        # Should find only the recently merged PR
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr_merged_recent)

    def test_multiple_filters_combined(self):
        """Test that multiple filters can be combined."""
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            github_repo="org/repo-a",
            is_ai_assisted=True,
            state="merged",
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            github_repo="org/repo-b",
            is_ai_assisted=True,
            state="merged",
        )
        PullRequestFactory(
            team=self.team,
            author=self.member2,
            github_repo="org/repo-a",
            is_ai_assisted=True,
            state="merged",
        )

        result = get_prs_queryset(
            self.team,
            {
                "author": str(self.member1.id),
                "repo": "org/repo-a",
                "ai": "yes",
                "state": "merged",
            },
        )

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr1)

    def test_empty_filters_returns_all_prs(self):
        """Test that empty filters dict returns all PRs for team."""
        PullRequestFactory(team=self.team)
        PullRequestFactory(team=self.team)
        PullRequestFactory(team=self.team)

        result = get_prs_queryset(self.team, {})

        self.assertEqual(result.count(), 3)

    def test_returns_queryset_with_select_related(self):
        """Test that returned queryset has proper select_related for performance."""
        PullRequestFactory(team=self.team, author=self.member1)

        result = get_prs_queryset(self.team, {})

        # Access related fields - should not cause additional queries
        pr = result.first()
        # This should be in select_related
        _ = pr.author.display_name


class TestGetPrStats(TestCase):
    """Tests for get_pr_stats function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_returns_total_count(self):
        """Test that stats include total PR count."""
        PullRequestFactory(team=self.team)
        PullRequestFactory(team=self.team)

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["total_count"], 2)

    def test_returns_avg_cycle_time(self):
        """Test that stats include average cycle time."""
        PullRequestFactory(team=self.team, cycle_time_hours=Decimal("10.0"))
        PullRequestFactory(team=self.team, cycle_time_hours=Decimal("20.0"))

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["avg_cycle_time"], Decimal("15.0"))

    def test_returns_avg_review_time(self):
        """Test that stats include average review time."""
        PullRequestFactory(team=self.team, review_time_hours=Decimal("5.0"))
        PullRequestFactory(team=self.team, review_time_hours=Decimal("10.0"))

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["avg_review_time"], Decimal("7.5"))

    def test_returns_total_additions_deletions(self):
        """Test that stats include total lines changed."""
        PullRequestFactory(team=self.team, additions=100, deletions=50)
        PullRequestFactory(team=self.team, additions=200, deletions=75)

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["total_additions"], 300)
        self.assertEqual(stats["total_deletions"], 125)

    def test_returns_ai_assisted_count(self):
        """Test that stats include AI-assisted PR count."""
        PullRequestFactory(team=self.team, is_ai_assisted=True)
        PullRequestFactory(team=self.team, is_ai_assisted=True)
        PullRequestFactory(team=self.team, is_ai_assisted=False)

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["ai_assisted_count"], 2)

    def test_handles_empty_queryset(self):
        """Test that stats handle empty queryset gracefully."""
        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["total_count"], 0)
        self.assertIsNone(stats["avg_cycle_time"])
        self.assertIsNone(stats["avg_review_time"])

    def test_handles_null_cycle_times(self):
        """Test that avg cycle time ignores null values."""
        PullRequestFactory(team=self.team, cycle_time_hours=Decimal("10.0"))
        PullRequestFactory(team=self.team, cycle_time_hours=None)

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["avg_cycle_time"], Decimal("10.0"))


class TestGetFilterOptions(TestCase):
    """Tests for get_filter_options function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")

    def test_returns_repos_list(self):
        """Test that filter options include list of repositories."""
        PullRequestFactory(team=self.team, github_repo="org/repo-a")
        PullRequestFactory(team=self.team, github_repo="org/repo-b")
        PullRequestFactory(team=self.team, github_repo="org/repo-a")  # Duplicate

        options = get_filter_options(self.team)

        self.assertIn("repos", options)
        self.assertEqual(set(options["repos"]), {"org/repo-a", "org/repo-b"})

    def test_returns_authors_list(self):
        """Test that filter options include list of authors."""
        PullRequestFactory(team=self.team, author=self.member1)
        PullRequestFactory(team=self.team, author=self.member2)

        options = get_filter_options(self.team)

        self.assertIn("authors", options)
        author_ids = [a["id"] for a in options["authors"]]
        self.assertIn(str(self.member1.id), author_ids)
        self.assertIn(str(self.member2.id), author_ids)

    def test_returns_reviewers_list(self):
        """Test that filter options include list of reviewers."""
        pr = PullRequestFactory(team=self.team, author=self.member1)
        PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.member2)

        options = get_filter_options(self.team)

        self.assertIn("reviewers", options)
        reviewer_ids = [r["id"] for r in options["reviewers"]]
        self.assertIn(str(self.member2.id), reviewer_ids)

    def test_returns_ai_tools_list(self):
        """Test that filter options include list of AI tools detected."""
        PullRequestFactory(team=self.team, is_ai_assisted=True, ai_tools_detected=["claude_code"])
        PullRequestFactory(team=self.team, is_ai_assisted=True, ai_tools_detected=["copilot"])
        PullRequestFactory(team=self.team, is_ai_assisted=True, ai_tools_detected=["claude_code"])

        options = get_filter_options(self.team)

        self.assertIn("ai_tools", options)
        self.assertEqual(set(options["ai_tools"]), {"claude_code", "copilot"})

    def test_returns_size_buckets(self):
        """Test that filter options include PR size bucket definitions."""
        options = get_filter_options(self.team)

        self.assertIn("size_buckets", options)
        self.assertEqual(options["size_buckets"], PR_SIZE_BUCKETS)

    def test_returns_state_choices(self):
        """Test that filter options include PR state choices."""
        options = get_filter_options(self.team)

        self.assertIn("states", options)
        self.assertEqual(set(options["states"]), {"open", "merged", "closed"})

    def test_only_returns_options_from_team_prs(self):
        """Test that options only include data from the specified team."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        PullRequestFactory(team=other_team, author=other_member, github_repo="other/repo")

        PullRequestFactory(team=self.team, author=self.member1, github_repo="our/repo")

        options = get_filter_options(self.team)

        self.assertEqual(options["repos"], ["our/repo"])
        author_ids = [a["id"] for a in options["authors"]]
        self.assertNotIn(str(other_member.id), author_ids)


class TestPrSizeBuckets(TestCase):
    """Tests for PR_SIZE_BUCKETS constant."""

    def test_buckets_are_defined(self):
        """Test that size buckets are properly defined."""
        self.assertIn("XS", PR_SIZE_BUCKETS)
        self.assertIn("S", PR_SIZE_BUCKETS)
        self.assertIn("M", PR_SIZE_BUCKETS)
        self.assertIn("L", PR_SIZE_BUCKETS)
        self.assertIn("XL", PR_SIZE_BUCKETS)

    def test_buckets_have_correct_ranges(self):
        """Test that size buckets have the expected ranges."""
        self.assertEqual(PR_SIZE_BUCKETS["XS"], (0, 10))
        self.assertEqual(PR_SIZE_BUCKETS["S"], (11, 50))
        self.assertEqual(PR_SIZE_BUCKETS["M"], (51, 200))
        self.assertEqual(PR_SIZE_BUCKETS["L"], (201, 500))
        self.assertEqual(PR_SIZE_BUCKETS["XL"], (501, None))


class TestTechCategoriesFilter(TestCase):
    """Tests for technology category filter."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_filter_by_single_tech_category(self):
        """Test filtering by a single technology category."""
        pr1 = PullRequestFactory(team=self.team, author=self.member)
        pr2 = PullRequestFactory(team=self.team, author=self.member)

        # Add frontend file to pr1
        PRFileFactory(pull_request=pr1, team=self.team, file_category="frontend")
        # Add backend file to pr2
        PRFileFactory(pull_request=pr2, team=self.team, file_category="backend")

        result = get_prs_queryset(self.team, {"tech": ["frontend"]})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr1.id)

    def test_filter_by_multiple_tech_categories(self):
        """Test filtering by multiple technology categories (OR logic)."""
        pr1 = PullRequestFactory(team=self.team, author=self.member)
        pr2 = PullRequestFactory(team=self.team, author=self.member)
        pr3 = PullRequestFactory(team=self.team, author=self.member)

        PRFileFactory(pull_request=pr1, team=self.team, file_category="frontend")
        PRFileFactory(pull_request=pr2, team=self.team, file_category="backend")
        PRFileFactory(pull_request=pr3, team=self.team, file_category="config")

        result = get_prs_queryset(self.team, {"tech": ["frontend", "backend"]})

        self.assertEqual(result.count(), 2)
        result_ids = set(result.values_list("id", flat=True))
        self.assertEqual(result_ids, {pr1.id, pr2.id})

    def test_empty_tech_filter_returns_all_prs(self):
        """Test that empty tech filter returns all PRs."""
        pr1 = PullRequestFactory(team=self.team, author=self.member)
        pr2 = PullRequestFactory(team=self.team, author=self.member)

        PRFileFactory(pull_request=pr1, team=self.team, file_category="frontend")
        PRFileFactory(pull_request=pr2, team=self.team, file_category="backend")

        result = get_prs_queryset(self.team, {})

        self.assertEqual(result.count(), 2)

    def test_pr_with_multiple_categories_appears_once(self):
        """Test that PR with files in multiple categories appears only once."""
        pr = PullRequestFactory(team=self.team, author=self.member)

        PRFileFactory(pull_request=pr, team=self.team, file_category="frontend", filename="app.tsx")
        PRFileFactory(pull_request=pr, team=self.team, file_category="backend", filename="views.py")
        PRFileFactory(pull_request=pr, team=self.team, file_category="test", filename="test_views.py")

        result = get_prs_queryset(self.team, {"tech": ["frontend", "backend"]})

        # Should appear only once despite matching both filters
        self.assertEqual(result.count(), 1)

    def test_tech_categories_annotation_returns_categories(self):
        """Test that tech_categories annotation returns list of categories."""
        pr = PullRequestFactory(team=self.team, author=self.member)

        PRFileFactory(pull_request=pr, team=self.team, file_category="frontend", filename="app.tsx")
        PRFileFactory(pull_request=pr, team=self.team, file_category="backend", filename="views.py")
        PRFileFactory(pull_request=pr, team=self.team, file_category="frontend", filename="utils.tsx")

        result = get_prs_queryset(self.team, {}).first()

        # Should have distinct categories
        self.assertIsNotNone(result.tech_categories)
        self.assertEqual(set(result.tech_categories), {"frontend", "backend"})

    def test_pr_without_files_has_empty_tech_categories(self):
        """Test that PR without files has empty tech_categories."""
        PullRequestFactory(team=self.team, author=self.member)

        result = get_prs_queryset(self.team, {}).first()

        # Should have empty list for tech_categories
        self.assertEqual(result.tech_categories, [])

    def test_filter_options_includes_tech_categories(self):
        """Test that get_filter_options returns tech_categories."""
        PullRequestFactory(team=self.team, author=self.member)

        options = get_filter_options(self.team)

        self.assertIn("tech_categories", options)
        # Should include all available categories from CATEGORY_CHOICES
        tech_values = [cat["value"] for cat in options["tech_categories"]]
        self.assertIn("frontend", tech_values)
        self.assertIn("backend", tech_values)
        self.assertIn("javascript", tech_values)

    def test_filter_options_includes_llm_categories(self):
        """Test that get_filter_options includes LLM-specific categories."""
        PullRequestFactory(team=self.team, author=self.member)

        options = get_filter_options(self.team)

        tech_values = [cat["value"] for cat in options["tech_categories"]]
        # LLM-only categories should be included
        self.assertIn("devops", tech_values)
        self.assertIn("mobile", tech_values)
        self.assertIn("data", tech_values)

    def test_filter_by_llm_category_devops(self):
        """Test filtering by LLM-only category 'devops'."""
        pr_devops = PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": ["devops"], "languages": [], "frameworks": []}},
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": ["backend"], "languages": [], "frameworks": []}},
        )

        result = get_prs_queryset(self.team, {"tech": ["devops"]})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr_devops.id)

    def test_filter_by_llm_category_mobile(self):
        """Test filtering by LLM-only category 'mobile'."""
        pr_mobile = PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": ["mobile", "frontend"], "languages": [], "frameworks": []}},
        )
        PullRequestFactory(team=self.team, author=self.member)

        result = get_prs_queryset(self.team, {"tech": ["mobile"]})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr_mobile.id)

    def test_filter_by_llm_category_data(self):
        """Test filtering by LLM-only category 'data'."""
        pr_data = PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": ["data"], "languages": ["python"], "frameworks": ["pandas"]}},
        )
        PullRequestFactory(team=self.team, author=self.member)

        result = get_prs_queryset(self.team, {"tech": ["data"]})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr_data.id)

    def test_filter_by_shared_category_matches_both_llm_and_pattern(self):
        """Test filtering by 'frontend' matches both LLM and pattern sources."""
        # PR with LLM frontend category
        pr_llm = PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": ["frontend"], "languages": [], "frameworks": []}},
        )
        # PR with pattern frontend category (no LLM)
        pr_pattern = PullRequestFactory(team=self.team, author=self.member)
        PRFileFactory(pull_request=pr_pattern, team=self.team, file_category="frontend", filename="app.tsx")
        # PR with neither
        PullRequestFactory(team=self.team, author=self.member)

        result = get_prs_queryset(self.team, {"tech": ["frontend"]})

        self.assertEqual(result.count(), 2)
        result_ids = set(result.values_list("id", flat=True))
        self.assertIn(pr_llm.id, result_ids)
        self.assertIn(pr_pattern.id, result_ids)


class TestEffectiveTechCategories(TestCase):
    """Tests for PullRequest.effective_tech_categories model property."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_returns_llm_categories_when_available(self):
        """Test that LLM categories are prioritized over pattern categories."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": ["backend", "devops"], "languages": [], "frameworks": []}},
        )
        # Add pattern-based file (should be ignored due to LLM priority)
        PRFileFactory(pull_request=pr, team=self.team, file_category="frontend", filename="app.tsx")

        result = pr.effective_tech_categories

        self.assertEqual(result, ["backend", "devops"])
        self.assertNotIn("frontend", result)

    def test_returns_pattern_categories_when_no_llm(self):
        """Test fallback to pattern-based categories when no LLM summary."""
        pr = PullRequestFactory(team=self.team, author=self.member, llm_summary=None)
        PRFileFactory(pull_request=pr, team=self.team, file_category="frontend", filename="app.tsx")
        PRFileFactory(pull_request=pr, team=self.team, file_category="backend", filename="views.py")

        result = pr.effective_tech_categories

        self.assertEqual(set(result), {"frontend", "backend"})

    def test_returns_pattern_categories_when_llm_tech_empty(self):
        """Test fallback when LLM summary exists but tech.categories is empty."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": [], "languages": ["python"], "frameworks": []}},
        )
        PRFileFactory(pull_request=pr, team=self.team, file_category="backend", filename="views.py")

        result = pr.effective_tech_categories

        self.assertEqual(result, ["backend"])

    def test_returns_empty_list_when_no_data(self):
        """Test returns empty list when no LLM or pattern categories."""
        pr = PullRequestFactory(team=self.team, author=self.member, llm_summary=None)

        result = pr.effective_tech_categories

        self.assertEqual(result, [])

    def test_uses_annotated_tech_categories_when_available(self):
        """Test uses annotated tech_categories if present (from service layer)."""
        pr = PullRequestFactory(team=self.team, author=self.member, llm_summary=None)
        PRFileFactory(pull_request=pr, team=self.team, file_category="frontend", filename="app.tsx")

        # Simulate annotation from get_prs_queryset
        pr.tech_categories = ["frontend", "test"]

        result = pr.effective_tech_categories

        # Should use annotated value
        self.assertEqual(result, ["frontend", "test"])

    def test_llm_only_categories_returned(self):
        """Test LLM-only categories (devops, mobile, data) are returned correctly."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            llm_summary={"tech": {"categories": ["devops", "mobile", "data"], "languages": [], "frameworks": []}},
        )

        result = pr.effective_tech_categories

        self.assertEqual(result, ["devops", "mobile", "data"])


class TestEffectiveAIDetection(TestCase):
    """Tests for PullRequest.effective_is_ai_assisted and effective_ai_tools properties."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_effective_is_ai_assisted_prioritizes_llm(self):
        """Test that LLM AI detection is prioritized over regex."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,  # Regex says no
            llm_summary={"ai": {"is_assisted": True, "tools": ["cursor"], "confidence": 0.9}},
        )

        self.assertTrue(pr.effective_is_ai_assisted)

    def test_effective_is_ai_assisted_llm_false_overrides_regex(self):
        """Test that LLM can override regex false positive."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Regex false positive
            llm_summary={"ai": {"is_assisted": False, "tools": [], "confidence": 0.8}},
        )

        self.assertFalse(pr.effective_is_ai_assisted)

    def test_effective_is_ai_assisted_falls_back_to_regex(self):
        """Test fallback to regex when no LLM summary."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
            llm_summary=None,
        )

        self.assertTrue(pr.effective_is_ai_assisted)

    def test_effective_is_ai_assisted_low_confidence_uses_regex(self):
        """Test that low LLM confidence falls back to regex."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Regex says yes
            llm_summary={"ai": {"is_assisted": False, "tools": [], "confidence": 0.3}},  # Low confidence
        )

        # Should use regex since LLM confidence is too low
        self.assertTrue(pr.effective_is_ai_assisted)

    def test_effective_ai_tools_prioritizes_llm(self):
        """Test that LLM tools are prioritized over regex detected tools."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            ai_tools_detected=["copilot"],  # Regex detected
            llm_summary={"ai": {"is_assisted": True, "tools": ["cursor", "claude"], "confidence": 0.9}},
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, ["cursor", "claude"])
        self.assertNotIn("copilot", result)

    def test_effective_ai_tools_falls_back_to_regex(self):
        """Test fallback to regex detected tools when no LLM."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["copilot", "claude_code"],
            llm_summary=None,
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, ["copilot", "claude_code"])

    def test_effective_ai_tools_empty_llm_falls_back(self):
        """Test fallback when LLM tools list is empty."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            ai_tools_detected=["copilot"],
            llm_summary={"ai": {"is_assisted": True, "tools": [], "confidence": 0.9}},
        )

        result = pr.effective_ai_tools

        # Falls back to regex since LLM tools is empty
        self.assertEqual(result, ["copilot"])

    def test_effective_ai_tools_returns_empty_when_no_data(self):
        """Test returns empty list when no AI tools detected anywhere."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,
            ai_tools_detected=[],
            llm_summary=None,
        )

        result = pr.effective_ai_tools

        self.assertEqual(result, [])


class TestAICategoryFilter(TestCase):
    """Tests for AI category filter in PR list."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_filter_by_ai_category_code(self):
        """Test filtering for PRs with code AI tools only."""
        # PR with code tool
        pr_code = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["cursor", "copilot"],
        )
        # PR with review tool
        PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit"],
        )
        # PR with no AI
        PullRequestFactory(team=self.team, author=self.member, is_ai_assisted=False)

        result = get_prs_queryset(self.team, {"ai_category": "code"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr_code.id)

    def test_filter_by_ai_category_review(self):
        """Test filtering for PRs with review AI tools only."""
        # PR with code tool
        PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )
        # PR with review tool
        pr_review = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit", "greptile"],
        )
        # PR with no AI
        PullRequestFactory(team=self.team, author=self.member, is_ai_assisted=False)

        result = get_prs_queryset(self.team, {"ai_category": "review"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr_review.id)

    def test_filter_by_ai_category_both(self):
        """Test filtering for PRs with both code and review AI tools."""
        # PR with code only
        PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )
        # PR with review only
        PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit"],
        )
        # PR with both
        pr_both = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["cursor", "coderabbit"],
        )

        result = get_prs_queryset(self.team, {"ai_category": "both"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr_both.id)

    def test_filter_ai_category_excludes_excluded_tools(self):
        """Test that excluded tools (snyk, mintlify) don't count as AI."""
        # PR with only excluded tools
        PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["snyk", "mintlify"],
        )
        # PR with code tool
        pr_code = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )

        result = get_prs_queryset(self.team, {"ai_category": "code"})

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr_code.id)

    def test_filter_ai_category_with_llm_priority(self):
        """Test that ai_category filter uses effective_ai_tools (LLM priority)."""
        # PR with regex=coderabbit but LLM=cursor (LLM should win)
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit"],  # Review tool from regex
            llm_summary={"ai": {"is_assisted": True, "tools": ["cursor"], "confidence": 0.9}},
        )

        result = get_prs_queryset(self.team, {"ai_category": "code"})

        # Should find PR because LLM says "cursor" (code tool)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr.id)

    def test_filter_ai_category_combined_with_other_filters(self):
        """Test ai_category filter works with other filters."""
        # PR with code tool in repo-a
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member,
            github_repo="org/repo-a",
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
            state="merged",
        )
        # PR with code tool in repo-b
        PullRequestFactory(
            team=self.team,
            author=self.member,
            github_repo="org/repo-b",
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
            state="merged",
        )

        result = get_prs_queryset(
            self.team,
            {"ai_category": "code", "repo": "org/repo-a"},
        )

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().id, pr1.id)


class TestAICategoryFilterOptions(TestCase):
    """Tests for ai_categories in get_filter_options."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    def test_filter_options_includes_ai_categories(self):
        """Test that get_filter_options returns ai_categories."""
        options = get_filter_options(self.team)

        self.assertIn("ai_categories", options)

    def test_ai_categories_has_all_options(self):
        """Test that ai_categories includes code, review, and both."""
        options = get_filter_options(self.team)

        category_values = [cat["value"] for cat in options["ai_categories"]]
        self.assertIn("code", category_values)
        self.assertIn("review", category_values)
        self.assertIn("both", category_values)

    def test_ai_categories_has_display_labels(self):
        """Test that ai_categories has human-readable labels."""
        options = get_filter_options(self.team)

        for cat in options["ai_categories"]:
            self.assertIn("value", cat)
            self.assertIn("label", cat)
            # Labels should be non-empty
            self.assertTrue(cat["label"])


class TestReviewerNameFilterPendingState(TestCase):
    """Tests for reviewer_name filter showing only PRs where reviewer needs to take action.

    The reviewer_name filter shows PRs where the reviewer is still in the review process.

    Expected behavior:
    - EXCLUDE PRs where reviewer's latest review is 'approved' (done reviewing)
    - INCLUDE PRs where reviewer's latest review is 'commented' (still in review process)
    - INCLUDE PRs where reviewer's latest review is 'changes_requested' (still in review process)
    - INCLUDE PRs where reviewer's latest review is 'dismissed' (needs re-review)
    - When multiple reviews exist, only the LATEST review state matters
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, github_username="pr-author")
        self.reviewer = TeamMemberFactory(team=self.team, github_username="alice-reviewer")

    def test_excludes_prs_with_approved_latest_review(self):
        """Test that PRs with an approved review should NOT appear in pending reviews."""
        # Create open PR
        pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        # Reviewer already approved it
        PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.reviewer, state="approved")

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        # Should NOT find this PR since reviewer already approved
        self.assertEqual(result.count(), 0)

    def test_includes_prs_with_commented_latest_review(self):
        """Test that PRs with a commented review SHOULD appear (still in review process)."""
        # Create open PR
        pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        # Reviewer left a comment (still in review process)
        PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.reviewer, state="commented")

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        # SHOULD find this PR since reviewer hasn't approved yet
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr)

    def test_includes_prs_with_changes_requested_latest_review(self):
        """Test that PRs with changes_requested review SHOULD appear (still in review process)."""
        # Create open PR
        pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        # Reviewer requested changes (still in review process, will need to re-review)
        PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.reviewer, state="changes_requested")

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        # SHOULD find this PR since reviewer hasn't approved yet
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr)

    def test_includes_prs_with_dismissed_latest_review(self):
        """Test that PRs with a dismissed review SHOULD appear in pending reviews."""
        # Create open PR
        pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        # Reviewer's review was dismissed (needs to re-review)
        PRReviewFactory(team=self.team, pull_request=pr, reviewer=self.reviewer, state="dismissed")

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        # SHOULD find this PR since dismissed reviews require re-review
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr)

    def test_latest_review_wins_over_earlier(self):
        """Test that if reviewer commented then approved, PR should NOT appear."""
        from datetime import timedelta

        from django.utils import timezone

        pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        now = timezone.now()

        # First review: commented (older)
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            state="commented",
            submitted_at=now - timedelta(hours=2),
        )
        # Second review: approved (newer - this is the LATEST)
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            state="approved",
            submitted_at=now - timedelta(hours=1),
        )

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        # Should NOT find this PR since LATEST review is approved
        self.assertEqual(result.count(), 0)

    def test_dismissed_after_approval_requires_review(self):
        """Test that if reviewer approved then their review was dismissed, PR SHOULD appear."""
        from datetime import timedelta

        from django.utils import timezone

        pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        now = timezone.now()

        # First review: approved (older)
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            state="approved",
            submitted_at=now - timedelta(hours=2),
        )
        # Second review: dismissed (newer - this is the LATEST)
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            state="dismissed",
            submitted_at=now - timedelta(hours=1),
        )

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        # SHOULD find this PR since LATEST review is dismissed (needs re-review)
        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first(), pr)

    def test_mixed_approved_and_non_approved_prs(self):
        """Test that reviewer with 2 approved and 3 non-approved PRs shows only the 3 non-approved."""
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()

        # Create 2 PRs where reviewer approved (should be excluded)
        approved_prs = []
        for i in range(2):
            pr = PullRequestFactory(team=self.team, author=self.author, state="open")
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=self.reviewer,
                state="approved",
                submitted_at=now - timedelta(hours=i),
            )
            approved_prs.append(pr)

        # Create 3 PRs with non-approved states (should be included)
        non_approved_prs = []
        states = ["commented", "changes_requested", "dismissed"]
        for i, state in enumerate(states):
            pr = PullRequestFactory(team=self.team, author=self.author, state="open")
            PRReviewFactory(
                team=self.team,
                pull_request=pr,
                reviewer=self.reviewer,
                state=state,
                submitted_at=now - timedelta(hours=i),
            )
            non_approved_prs.append(pr)

        result = get_prs_queryset(self.team, {"reviewer_name": "@alice-reviewer"})

        # Should find the 3 non-approved PRs (commented, changes_requested, dismissed)
        self.assertEqual(result.count(), 3)
        result_ids = set(result.values_list("id", flat=True))
        expected_ids = {pr.id for pr in non_approved_prs}
        self.assertEqual(result_ids, expected_ids)


class TestAICategoryStats(TestCase):
    """Tests for AI category counts in get_pr_stats."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_stats_includes_code_ai_count(self):
        """Test that stats include code AI PR count."""
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],
        )
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["copilot"],
        )
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit"],  # Review
        )

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertIn("code_ai_count", stats)
        self.assertEqual(stats["code_ai_count"], 2)

    def test_stats_includes_review_ai_count(self):
        """Test that stats include review AI PR count."""
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["coderabbit"],
        )
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["greptile"],
        )
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],  # Code
        )

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertIn("review_ai_count", stats)
        self.assertEqual(stats["review_ai_count"], 2)

    def test_stats_includes_both_ai_count(self):
        """Test that stats include 'both' category count."""
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["cursor", "coderabbit"],  # Both
        )
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],  # Code only
        )

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertIn("both_ai_count", stats)
        self.assertEqual(stats["both_ai_count"], 1)

    def test_stats_category_counts_exclude_excluded_tools(self):
        """Test that category counts exclude non-AI tools like snyk."""
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["snyk"],  # Excluded
        )
        PullRequestFactory(
            team=self.team,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],  # Code
        )

        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["code_ai_count"], 1)
        # The snyk-only PR shouldn't count in any category

    def test_stats_empty_queryset_has_zero_category_counts(self):
        """Test that empty queryset has zero category counts."""
        qs = get_prs_queryset(self.team, {})
        stats = get_pr_stats(qs)

        self.assertEqual(stats["code_ai_count"], 0)
        self.assertEqual(stats["review_ai_count"], 0)
        self.assertEqual(stats["both_ai_count"], 0)
