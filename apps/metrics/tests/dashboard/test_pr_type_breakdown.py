"""Tests for get_pr_type_breakdown and related functions."""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.services.dashboard_service import get_pr_type_breakdown


class TestGetPRTypeBreakdown(TestCase):
    """Tests for get_pr_type_breakdown function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.end_date = date.today()
        self.start_date = self.end_date - timedelta(days=30)

    def _create_pr_with_type(self, pr_type, is_ai_assisted=False, llm_summary=None):
        """Helper to create a PR with a specific type via labels or llm_summary."""
        merge_date = self.end_date - timedelta(days=5)

        if llm_summary is None:
            # Use labels to infer type
            labels = [pr_type] if pr_type != "unknown" else []
            llm_summary_data = None
        else:
            labels = []
            llm_summary_data = llm_summary

        return PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            labels=labels,
            llm_summary=llm_summary_data,
            is_ai_assisted=is_ai_assisted,
        )

    def test_returns_list_of_dicts(self):
        """get_pr_type_breakdown returns list of dicts."""
        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)
        self.assertIsInstance(result, list)

    def test_returns_empty_list_when_no_prs(self):
        """Returns empty list when no PRs exist."""
        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)
        self.assertEqual(result, [])

    def test_each_entry_has_type_count_and_percentage(self):
        """Each entry has type, count, and percentage keys."""
        self._create_pr_with_type("feature")

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        self.assertGreater(len(result), 0)
        entry = result[0]
        self.assertIn("type", entry)
        self.assertIn("count", entry)
        self.assertIn("percentage", entry)

    def test_counts_prs_by_type(self):
        """Counts number of PRs for each type."""
        # Create 3 feature PRs
        for _ in range(3):
            self._create_pr_with_type("feature")

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        # Find the feature entry
        feature_entry = next((r for r in result if r["type"] == "feature"), None)
        self.assertIsNotNone(feature_entry)
        self.assertEqual(feature_entry["count"], 3)

    def test_calculates_percentage_correctly(self):
        """Calculates percentage of total PRs for each type."""
        # 3 features + 1 bugfix = 75% features, 25% bugfix
        for _ in range(3):
            self._create_pr_with_type("feature")
        self._create_pr_with_type("bugfix")

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        feature_entry = next((r for r in result if r["type"] == "feature"), None)
        bugfix_entry = next((r for r in result if r["type"] == "bugfix"), None)

        self.assertEqual(feature_entry["percentage"], 75.0)
        self.assertEqual(bugfix_entry["percentage"], 25.0)

    def test_orders_by_count_descending(self):
        """Results are ordered by count (highest first)."""
        # 1 feature, 3 bugfix, 2 refactor
        self._create_pr_with_type("feature")
        for _ in range(3):
            self._create_pr_with_type("bugfix")
        for _ in range(2):
            self._create_pr_with_type("refactor")

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        # Should be ordered: bugfix (3), refactor (2), feature (1)
        self.assertEqual(result[0]["type"], "bugfix")
        self.assertEqual(result[0]["count"], 3)
        self.assertEqual(result[1]["type"], "refactor")
        self.assertEqual(result[1]["count"], 2)
        self.assertEqual(result[2]["type"], "feature")
        self.assertEqual(result[2]["count"], 1)

    def test_filters_by_ai_assisted_yes(self):
        """ai_assisted='yes' only includes AI-assisted PRs."""
        # 2 AI-assisted features
        for _ in range(2):
            self._create_pr_with_type("feature", is_ai_assisted=True)
        # 3 non-AI features
        for _ in range(3):
            self._create_pr_with_type("feature", is_ai_assisted=False)

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date, ai_assisted="yes")

        feature_entry = next((r for r in result if r["type"] == "feature"), None)
        self.assertEqual(feature_entry["count"], 2)

    def test_filters_by_ai_assisted_no(self):
        """ai_assisted='no' only includes non-AI-assisted PRs."""
        # 2 AI-assisted features
        for _ in range(2):
            self._create_pr_with_type("feature", is_ai_assisted=True)
        # 3 non-AI features
        for _ in range(3):
            self._create_pr_with_type("feature", is_ai_assisted=False)

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date, ai_assisted="no")

        feature_entry = next((r for r in result if r["type"] == "feature"), None)
        self.assertEqual(feature_entry["count"], 3)

    def test_ai_assisted_all_includes_both(self):
        """ai_assisted='all' includes both AI and non-AI PRs."""
        # 2 AI-assisted features
        for _ in range(2):
            self._create_pr_with_type("feature", is_ai_assisted=True)
        # 3 non-AI features
        for _ in range(3):
            self._create_pr_with_type("feature", is_ai_assisted=False)

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date, ai_assisted="all")

        feature_entry = next((r for r in result if r["type"] == "feature"), None)
        self.assertEqual(feature_entry["count"], 5)

    def test_uses_llm_summary_type_when_available(self):
        """Uses LLM-detected type from llm_summary when available."""
        # Create PR with llm_summary containing type
        llm_summary = {"summary": {"type": "refactor"}}
        self._create_pr_with_type("feature", llm_summary=llm_summary)  # label is 'feature' but llm says 'refactor'

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        # Should use the llm_summary type (refactor), not the label (feature)
        types = [r["type"] for r in result]
        self.assertIn("refactor", types)

    def test_filters_by_team(self):
        """Only includes PRs from the specified team."""
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)

        # Our team PR
        self._create_pr_with_type("feature")

        # Other team PR
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=timezone.make_aware(
                timezone.datetime.combine(self.end_date - timedelta(days=5), timezone.datetime.min.time())
            ),
            labels=["bugfix"],
        )

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        # Should only have the feature PR from our team
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "feature")

    def test_handles_unknown_type(self):
        """PRs without recognizable type are classified as 'unknown'."""
        # Create PR with no labels and no llm_summary
        merge_date = self.end_date - timedelta(days=5)
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime.combine(merge_date, timezone.datetime.min.time())),
            labels=[],
            llm_summary=None,
        )

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        # Should have unknown type
        types = [r["type"] for r in result]
        self.assertIn("unknown", types)

    def test_only_includes_merged_prs(self):
        """Only includes merged PRs, not open or closed."""
        # Merged PR
        self._create_pr_with_type("feature")

        # Open PR
        PullRequestFactory(
            team=self.team,
            author=self.member,
            state="open",
            merged_at=None,
            labels=["bugfix"],
        )

        result = get_pr_type_breakdown(self.team, self.start_date, self.end_date)

        # Should only count the merged feature PR
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "feature")
