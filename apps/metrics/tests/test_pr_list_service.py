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
