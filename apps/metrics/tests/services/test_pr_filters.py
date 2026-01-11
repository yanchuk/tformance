"""TDD tests for pr_filters.py - extracted filter functions.

These tests verify the filter functions work correctly in isolation,
complementing the integration tests in test_pr_list_service.py.
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PullRequestFactory, TeamFactory
from apps.metrics.models import PullRequest
from apps.metrics.services.pr_filters import (
    _calculate_long_cycle_threshold,
    apply_date_range_filter,
    apply_issue_type_filter,
)
from apps.teams.context import set_current_team, unset_current_team


class TestApplyDateRangeFilter(TestCase):
    """TDD tests for apply_date_range_filter()."""

    def setUp(self):
        self.team = TeamFactory()
        self.base_date = timezone.now()
        # Set team context for for_team manager
        self._team_token = set_current_team(self.team)

    def tearDown(self):
        unset_current_team(self._team_token)

    def test_returns_all_when_no_dates_provided(self):
        """No date filter should return all PRs."""
        PullRequestFactory.create_batch(3, team=self.team)
        qs = PullRequest.for_team.filter(team=self.team)

        result = apply_date_range_filter(qs, state_filter=None, date_from=None, date_to=None)

        self.assertEqual(result.count(), 3)

    def test_open_state_filters_by_created_at(self):
        """Open PRs should be filtered by pr_created_at, not merged_at."""
        # Create an open PR created yesterday
        yesterday = self.base_date - timedelta(days=1)
        PullRequestFactory(
            team=self.team,
            state="open",
            pr_created_at=yesterday,
            merged_at=None,
        )
        # Create an open PR created 10 days ago (outside range)
        old_date = self.base_date - timedelta(days=10)
        PullRequestFactory(
            team=self.team,
            state="open",
            pr_created_at=old_date,
            merged_at=None,
        )

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_date_range_filter(
            qs,
            state_filter="open",
            date_from=(self.base_date - timedelta(days=5)).date(),
            date_to=None,
        )

        self.assertEqual(result.count(), 1)

    def test_merged_state_filters_by_merged_at(self):
        """Merged PRs should be filtered by merged_at."""
        yesterday = self.base_date - timedelta(days=1)
        PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=self.base_date - timedelta(days=30),  # Created long ago
            merged_at=yesterday,  # But merged yesterday
        )
        # Create a PR merged 10 days ago (outside range)
        old_date = self.base_date - timedelta(days=10)
        PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=self.base_date - timedelta(days=30),
            merged_at=old_date,
        )

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_date_range_filter(
            qs,
            state_filter="merged",
            date_from=(self.base_date - timedelta(days=5)).date(),
            date_to=None,
        )

        self.assertEqual(result.count(), 1)

    def test_all_states_uses_or_query(self):
        """All states (None) should use appropriate field per state."""
        yesterday = self.base_date - timedelta(days=1)

        # Open PR created yesterday (should match)
        PullRequestFactory(
            team=self.team,
            state="open",
            pr_created_at=yesterday,
            merged_at=None,
        )
        # Merged PR merged yesterday (should match)
        PullRequestFactory(
            team=self.team,
            state="merged",
            pr_created_at=self.base_date - timedelta(days=30),
            merged_at=yesterday,
        )
        # Open PR created 10 days ago (should NOT match)
        old_date = self.base_date - timedelta(days=10)
        PullRequestFactory(
            team=self.team,
            state="open",
            pr_created_at=old_date,
            merged_at=None,
        )

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_date_range_filter(
            qs,
            state_filter=None,  # All states
            date_from=(self.base_date - timedelta(days=5)).date(),
            date_to=None,
        )

        self.assertEqual(result.count(), 2)

    def test_date_to_is_inclusive(self):
        """date_to should include PRs on that exact date."""
        target_date = self.base_date.date()
        PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=self.base_date,
        )

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_date_range_filter(
            qs,
            state_filter="merged",
            date_from=None,
            date_to=target_date,
        )

        self.assertEqual(result.count(), 1)


class TestApplyIssueTypeFilter(TestCase):
    """TDD tests for apply_issue_type_filter()."""

    def setUp(self):
        self.team = TeamFactory()
        self._team_token = set_current_team(self.team)

    def tearDown(self):
        unset_current_team(self._team_token)

    def test_returns_all_when_no_issue_type(self):
        """No issue type should return all PRs."""
        PullRequestFactory.create_batch(3, team=self.team)
        qs = PullRequest.for_team.filter(team=self.team)

        result = apply_issue_type_filter(qs, issue_type=None)

        self.assertEqual(result.count(), 3)

    def test_revert_filter_returns_only_reverts(self):
        """Revert filter should return only is_revert=True PRs."""
        PullRequestFactory(team=self.team, is_revert=True)
        PullRequestFactory(team=self.team, is_revert=False)

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="revert")

        self.assertEqual(result.count(), 1)
        self.assertTrue(result.first().is_revert)

    def test_hotfix_filter_excludes_reverts(self):
        """Hotfix filter should exclude reverts (priority rule)."""
        # Hotfix that is also a revert (should NOT be included)
        PullRequestFactory(team=self.team, is_hotfix=True, is_revert=True)
        # Hotfix that is not a revert (should be included)
        PullRequestFactory(team=self.team, is_hotfix=True, is_revert=False)

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="hotfix")

        self.assertEqual(result.count(), 1)
        self.assertFalse(result.first().is_revert)

    def test_long_cycle_uses_dynamic_threshold(self):
        """Long cycle filter should use 2x team average threshold."""
        # Create PRs with cycle times: 10, 20, 30, 100
        # Average = (10 + 20 + 30 + 100) / 4 = 40, threshold = 80
        # Only the 100-hour PR exceeds 80
        PullRequestFactory(team=self.team, cycle_time_hours=10, is_revert=False, is_hotfix=False)
        PullRequestFactory(team=self.team, cycle_time_hours=20, is_revert=False, is_hotfix=False)
        PullRequestFactory(team=self.team, cycle_time_hours=30, is_revert=False, is_hotfix=False)
        # This one exceeds 2x avg (>80)
        PullRequestFactory(team=self.team, cycle_time_hours=100, is_revert=False, is_hotfix=False)

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="long_cycle")

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().cycle_time_hours, 100)

    def test_long_cycle_excludes_reverts_and_hotfixes(self):
        """Long cycle filter should exclude reverts and hotfixes."""
        # Create PRs to establish a baseline
        # With 10, 10, 10, 10, 10, 500 the average = 91.67, threshold = 183.33
        # So 500 hours exceeds the threshold
        PullRequestFactory(team=self.team, cycle_time_hours=10, is_revert=False, is_hotfix=False)
        PullRequestFactory(team=self.team, cycle_time_hours=10, is_revert=False, is_hotfix=False)
        PullRequestFactory(team=self.team, cycle_time_hours=10, is_revert=False, is_hotfix=False)

        # Long cycle time but is_revert - should NOT match
        PullRequestFactory(team=self.team, cycle_time_hours=10, is_revert=True, is_hotfix=False)
        # Long cycle time but is_hotfix - should NOT match
        PullRequestFactory(team=self.team, cycle_time_hours=10, is_revert=False, is_hotfix=True)
        # Very long cycle time (>threshold), not revert/hotfix - should match
        PullRequestFactory(team=self.team, cycle_time_hours=500, is_revert=False, is_hotfix=False)

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="long_cycle")

        # Should only match the last one (500 hours, not revert/hotfix)
        self.assertEqual(result.count(), 1)
        pr = result.first()
        self.assertFalse(pr.is_revert)
        self.assertFalse(pr.is_hotfix)
        self.assertEqual(pr.cycle_time_hours, 500)

    def test_large_pr_filter_checks_line_count(self):
        """Large PR filter should check additions + deletions > 500."""
        # Small PR (should NOT match)
        PullRequestFactory(team=self.team, additions=100, deletions=50, is_revert=False, is_hotfix=False)
        # Large PR (should match)
        PullRequestFactory(team=self.team, additions=400, deletions=200, is_revert=False, is_hotfix=False)

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="large_pr")

        self.assertEqual(result.count(), 1)
        pr = result.first()
        self.assertGreater(pr.additions + pr.deletions, 500)

    def test_large_pr_excludes_long_cycle_prs(self):
        """Large PR filter should exclude PRs with long cycle time."""
        # Create baseline PRs to establish threshold
        PullRequestFactory(team=self.team, cycle_time_hours=10, additions=100, deletions=50)

        # Large PR with long cycle (> 2x avg = 20) - should NOT match
        PullRequestFactory(
            team=self.team,
            additions=400,
            deletions=200,
            cycle_time_hours=50,
            is_revert=False,
            is_hotfix=False,
        )
        # Large PR with normal cycle - should match
        PullRequestFactory(
            team=self.team,
            additions=400,
            deletions=200,
            cycle_time_hours=5,
            is_revert=False,
            is_hotfix=False,
        )

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="large_pr")

        self.assertEqual(result.count(), 1)

    def test_missing_jira_filter_checks_empty_key(self):
        """Missing Jira filter should find PRs with empty jira_key."""
        # PR with Jira key (should NOT match)
        PullRequestFactory(team=self.team, jira_key="PROJ-123", additions=100, deletions=50)
        # PR without Jira key (should match)
        PullRequestFactory(
            team=self.team,
            jira_key="",
            additions=100,
            deletions=50,
            is_revert=False,
            is_hotfix=False,
        )

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="missing_jira")

        self.assertEqual(result.count(), 1)
        self.assertEqual(result.first().jira_key, "")

    def test_missing_jira_excludes_large_prs(self):
        """Missing Jira filter should exclude large PRs (>500 lines)."""
        # Large PR without Jira (should NOT match - captured by large_pr filter)
        PullRequestFactory(
            team=self.team,
            jira_key="",
            additions=400,
            deletions=200,
            is_revert=False,
            is_hotfix=False,
        )
        # Small PR without Jira (should match)
        PullRequestFactory(
            team=self.team,
            jira_key="",
            additions=100,
            deletions=50,
            is_revert=False,
            is_hotfix=False,
        )

        qs = PullRequest.for_team.filter(team=self.team)
        result = apply_issue_type_filter(qs, issue_type="missing_jira")

        self.assertEqual(result.count(), 1)
        pr = result.first()
        self.assertLessEqual(pr.additions + pr.deletions, 500)

    def test_unknown_issue_type_returns_all(self):
        """Unknown issue type should return all PRs unchanged."""
        PullRequestFactory.create_batch(3, team=self.team)
        qs = PullRequest.for_team.filter(team=self.team)

        result = apply_issue_type_filter(qs, issue_type="unknown_type")

        self.assertEqual(result.count(), 3)


class TestCalculateLongCycleThreshold(TestCase):
    """TDD tests for _calculate_long_cycle_threshold()."""

    def setUp(self):
        self.team = TeamFactory()
        self._team_token = set_current_team(self.team)

    def tearDown(self):
        unset_current_team(self._team_token)

    def test_returns_2x_average(self):
        """Threshold should be 2x the average cycle time."""
        # Average = (10 + 20 + 30) / 3 = 20, threshold = 40
        PullRequestFactory(team=self.team, cycle_time_hours=10)
        PullRequestFactory(team=self.team, cycle_time_hours=20)
        PullRequestFactory(team=self.team, cycle_time_hours=30)

        qs = PullRequest.for_team.filter(team=self.team)
        threshold = _calculate_long_cycle_threshold(qs)

        self.assertEqual(threshold, 40.0)

    def test_returns_high_default_when_no_data(self):
        """No cycle time data should return 999999 (effectively no filter)."""
        # Create PRs with NULL cycle_time_hours
        PullRequestFactory(team=self.team, cycle_time_hours=None)
        PullRequestFactory(team=self.team, cycle_time_hours=None)

        qs = PullRequest.for_team.filter(team=self.team)
        threshold = _calculate_long_cycle_threshold(qs)

        self.assertEqual(threshold, 999999)

    def test_ignores_null_cycle_times_in_average(self):
        """NULL cycle times should not affect the average calculation."""
        PullRequestFactory(team=self.team, cycle_time_hours=10)
        PullRequestFactory(team=self.team, cycle_time_hours=20)
        PullRequestFactory(team=self.team, cycle_time_hours=None)  # Should be ignored

        qs = PullRequest.for_team.filter(team=self.team)
        threshold = _calculate_long_cycle_threshold(qs)

        # Average = (10 + 20) / 2 = 15, threshold = 30
        self.assertEqual(threshold, 30.0)
