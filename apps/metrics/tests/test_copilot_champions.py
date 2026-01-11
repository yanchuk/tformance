"""
Tests for Copilot Champions identification service.

TDD approach: Tests written first, implementation follows.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    AIUsageDailyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)

# Import will fail until we create the service (TDD RED phase)
from apps.metrics.services.copilot_champions import get_copilot_champions


def make_aware_datetime(d: date) -> datetime:
    """Convert a date to a timezone-aware datetime at midnight."""
    return timezone.make_aware(datetime.combine(d, datetime.min.time()))


class TestGetCopilotChampions(TestCase):
    """Tests for the get_copilot_champions function."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all tests."""
        cls.team = TeamFactory()
        cls.end_date = date.today()
        cls.start_date = cls.end_date - timedelta(days=30)

    def test_returns_top_3_champions_by_default(self):
        """Should return top 3 champions when more are available."""
        # Create 5 members with varying Copilot usage and PR performance
        members = TeamMemberFactory.create_batch(5, team=self.team)

        for i, member in enumerate(members):
            # Higher index = better performance (for predictable ordering)
            acceptance_rate = 30 + (i * 10)  # 30%, 40%, 50%, 60%, 70%

            # Create 7 days of Copilot usage (meets 5-day minimum)
            for day in range(7):
                suggestions = 100 + (i * 20)
                accepted = int(suggestions * acceptance_rate / 100)
                AIUsageDailyFactory(
                    team=self.team,
                    member=member,
                    date=self.start_date + timedelta(days=day),
                    source="copilot",
                    suggestions_shown=suggestions,
                    suggestions_accepted=accepted,
                    acceptance_rate=Decimal(str(acceptance_rate)),
                )

            # Create 5 PRs (meets 3-PR minimum)
            for _ in range(5):
                PullRequestFactory(
                    team=self.team,
                    author=member,
                    state="merged",
                    merged_at=make_aware_datetime(self.start_date + timedelta(days=5)),
                    cycle_time_hours=Decimal(str(48 - i * 8)),  # Lower is better
                    is_revert=False,
                )

        champions = get_copilot_champions(self.team, self.start_date, self.end_date)

        self.assertEqual(len(champions), 3)
        # Best performers should be at the top (highest index members)
        self.assertGreater(champions[0]["overall_score"], champions[1]["overall_score"])
        self.assertGreater(champions[1]["overall_score"], champions[2]["overall_score"])

    def test_returns_empty_list_when_no_copilot_data(self):
        """Should return empty list when team has no Copilot usage."""
        empty_team = TeamFactory()
        member = TeamMemberFactory(team=empty_team)

        # Create PRs but no Copilot usage
        PullRequestFactory.create_batch(
            5,
            team=empty_team,
            author=member,
            state="merged",
        )

        champions = get_copilot_champions(empty_team, self.start_date, self.end_date)

        self.assertEqual(champions, [])

    def test_excludes_members_below_activity_threshold(self):
        """Should exclude members with less than 5 days of Copilot activity."""
        member_active = TeamMemberFactory(team=self.team)
        member_inactive = TeamMemberFactory(team=self.team)

        # Active member: 7 days of usage
        for day in range(7):
            AIUsageDailyFactory(
                team=self.team,
                member=member_active,
                date=self.start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=50,
                acceptance_rate=Decimal("50"),
            )

        # Inactive member: only 3 days of usage (below threshold)
        for day in range(3):
            AIUsageDailyFactory(
                team=self.team,
                member=member_inactive,
                date=self.start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=200,
                suggestions_accepted=150,
                acceptance_rate=Decimal("75"),  # Even with high acceptance
            )

        # Both need PRs
        for member in [member_active, member_inactive]:
            PullRequestFactory.create_batch(
                5,
                team=self.team,
                author=member,
                state="merged",
            )

        champions = get_copilot_champions(self.team, self.start_date, self.end_date)

        member_ids = [c["member_id"] for c in champions]
        self.assertIn(member_active.id, member_ids)
        self.assertNotIn(member_inactive.id, member_ids)

    def test_excludes_members_below_pr_threshold(self):
        """Should exclude members with fewer than 3 merged PRs."""
        member_active = TeamMemberFactory(team=self.team)
        member_few_prs = TeamMemberFactory(team=self.team)

        # Both have good Copilot usage
        for member in [member_active, member_few_prs]:
            for day in range(7):
                AIUsageDailyFactory(
                    team=self.team,
                    member=member,
                    date=self.start_date + timedelta(days=day),
                    source="copilot",
                    suggestions_shown=100,
                    suggestions_accepted=50,
                    acceptance_rate=Decimal("50"),
                )

        # Active member: 5 PRs (meets threshold)
        PullRequestFactory.create_batch(
            5,
            team=self.team,
            author=member_active,
            state="merged",
        )

        # Few PRs member: only 2 PRs (below threshold)
        PullRequestFactory.create_batch(
            2,
            team=self.team,
            author=member_few_prs,
            state="merged",
        )

        champions = get_copilot_champions(self.team, self.start_date, self.end_date)

        member_ids = [c["member_id"] for c in champions]
        self.assertIn(member_active.id, member_ids)
        self.assertNotIn(member_few_prs.id, member_ids)

    def test_excludes_members_below_acceptance_rate_threshold(self):
        """Should exclude members with acceptance rate below 20%."""
        member_good = TeamMemberFactory(team=self.team)
        member_low_acceptance = TeamMemberFactory(team=self.team)

        # Good member: 50% acceptance
        for day in range(7):
            AIUsageDailyFactory(
                team=self.team,
                member=member_good,
                date=self.start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=50,
                acceptance_rate=Decimal("50"),
            )

        # Low acceptance member: 15% (below 20% threshold)
        for day in range(7):
            AIUsageDailyFactory(
                team=self.team,
                member=member_low_acceptance,
                date=self.start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=15,
                acceptance_rate=Decimal("15"),
            )

        for member in [member_good, member_low_acceptance]:
            PullRequestFactory.create_batch(
                5,
                team=self.team,
                author=member,
                state="merged",
            )

        champions = get_copilot_champions(self.team, self.start_date, self.end_date)

        member_ids = [c["member_id"] for c in champions]
        self.assertIn(member_good.id, member_ids)
        self.assertNotIn(member_low_acceptance.id, member_ids)

    def test_includes_stats_in_response(self):
        """Should include detailed stats for each champion."""
        member = TeamMemberFactory(team=self.team)

        for day in range(7):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                date=self.start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=45,
                acceptance_rate=Decimal("45"),
            )

        for _ in range(5):
            PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                cycle_time_hours=Decimal("24"),
                is_revert=False,
            )

        champions = get_copilot_champions(self.team, self.start_date, self.end_date)

        self.assertEqual(len(champions), 1)
        champion = champions[0]

        # Check required fields
        self.assertIn("member_id", champion)
        self.assertIn("display_name", champion)
        self.assertIn("github_username", champion)
        self.assertIn("overall_score", champion)
        self.assertIn("stats", champion)

        # Check stats structure
        stats = champion["stats"]
        self.assertIn("acceptance_rate", stats)
        self.assertIn("prs_merged", stats)
        self.assertIn("avg_cycle_time_hours", stats)
        self.assertIn("revert_rate", stats)

    def test_calculates_revert_rate_correctly(self):
        """Should calculate revert rate from is_revert boolean."""
        member = TeamMemberFactory(team=self.team)

        for day in range(7):
            AIUsageDailyFactory(
                team=self.team,
                member=member,
                date=self.start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=50,
                acceptance_rate=Decimal("50"),
            )

        # 4 normal PRs + 1 revert = 20% revert rate
        PullRequestFactory.create_batch(
            4,
            team=self.team,
            author=member,
            state="merged",
            is_revert=False,
        )
        PullRequestFactory(
            team=self.team,
            author=member,
            state="merged",
            is_revert=True,
        )

        champions = get_copilot_champions(self.team, self.start_date, self.end_date)

        self.assertEqual(len(champions), 1)
        self.assertAlmostEqual(champions[0]["stats"]["revert_rate"], 0.2, places=2)

    def test_respects_top_n_parameter(self):
        """Should return specified number of champions."""
        members = TeamMemberFactory.create_batch(10, team=self.team)

        for member in members:
            for day in range(7):
                AIUsageDailyFactory(
                    team=self.team,
                    member=member,
                    date=self.start_date + timedelta(days=day),
                    source="copilot",
                    suggestions_shown=100,
                    suggestions_accepted=50,
                    acceptance_rate=Decimal("50"),
                )
            PullRequestFactory.create_batch(
                5,
                team=self.team,
                author=member,
                state="merged",
            )

        # Request top 5 instead of default 3
        champions = get_copilot_champions(self.team, self.start_date, self.end_date, top_n=5)

        self.assertEqual(len(champions), 5)

    def test_deterministic_ordering_on_tie(self):
        """Should have deterministic ordering when scores are equal."""
        member1 = TeamMemberFactory(team=self.team)
        member2 = TeamMemberFactory(team=self.team)

        # Identical Copilot usage and PR performance
        for member in [member1, member2]:
            for day in range(7):
                AIUsageDailyFactory(
                    team=self.team,
                    member=member,
                    date=self.start_date + timedelta(days=day),
                    source="copilot",
                    suggestions_shown=100,
                    suggestions_accepted=50,
                    acceptance_rate=Decimal("50"),
                )
            for _ in range(5):
                PullRequestFactory(
                    team=self.team,
                    author=member,
                    state="merged",
                    cycle_time_hours=Decimal("24"),
                    is_revert=False,
                )

        # Run twice - should get same order
        champions1 = get_copilot_champions(self.team, self.start_date, self.end_date)
        champions2 = get_copilot_champions(self.team, self.start_date, self.end_date)

        self.assertEqual(
            [c["member_id"] for c in champions1],
            [c["member_id"] for c in champions2],
        )


class TestCopilotChampionsTeamIsolation(TestCase):
    """Tests for TEAM001 compliance - team isolation."""

    def test_only_returns_champions_from_specified_team(self):
        """Should not include members from other teams (TEAM001)."""
        team1 = TeamFactory()
        team2 = TeamFactory()

        member1 = TeamMemberFactory(team=team1)
        member2 = TeamMemberFactory(team=team2)

        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # Both members have identical, excellent stats
        for member, team in [(member1, team1), (member2, team2)]:
            for day in range(7):
                AIUsageDailyFactory(
                    team=team,
                    member=member,
                    date=start_date + timedelta(days=day),
                    source="copilot",
                    suggestions_shown=100,
                    suggestions_accepted=70,
                    acceptance_rate=Decimal("70"),
                )
            PullRequestFactory.create_batch(
                5,
                team=team,
                author=member,
                state="merged",
            )

        # Query for team1 only
        champions = get_copilot_champions(team1, start_date, end_date)

        member_ids = [c["member_id"] for c in champions]
        self.assertIn(member1.id, member_ids)
        self.assertNotIn(member2.id, member_ids)


class TestCopilotChampionsEdgeCases(TestCase):
    """Edge case tests for Copilot Champions."""

    def test_member_with_copilot_but_no_prs(self):
        """Should not include member with Copilot usage but no PRs."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)

        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # Good Copilot usage
        for day in range(7):
            AIUsageDailyFactory(
                team=team,
                member=member,
                date=start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=50,
                acceptance_rate=Decimal("50"),
            )

        # No PRs created

        champions = get_copilot_champions(team, start_date, end_date)

        self.assertEqual(champions, [])

    def test_member_with_prs_but_no_copilot(self):
        """Should not include member with PRs but no Copilot usage."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)

        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # Good PR performance
        PullRequestFactory.create_batch(
            10,
            team=team,
            author=member,
            state="merged",
            cycle_time_hours=Decimal("12"),
        )

        # No Copilot usage

        champions = get_copilot_champions(team, start_date, end_date)

        self.assertEqual(champions, [])

    def test_all_members_below_threshold(self):
        """Should return empty when all members are below thresholds."""
        team = TeamFactory()
        members = TeamMemberFactory.create_batch(3, team=team)

        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        # All members have only 2 days of Copilot (below 5-day threshold)
        for member in members:
            for day in range(2):
                AIUsageDailyFactory(
                    team=team,
                    member=member,
                    date=start_date + timedelta(days=day),
                    source="copilot",
                    suggestions_shown=100,
                    suggestions_accepted=50,
                    acceptance_rate=Decimal("50"),
                )
            PullRequestFactory.create_batch(
                5,
                team=team,
                author=member,
                state="merged",
            )

        champions = get_copilot_champions(team, start_date, end_date)

        self.assertEqual(champions, [])

    def test_filters_by_date_range(self):
        """Should only consider data within the specified date range."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)

        # Date ranges
        old_start = date.today() - timedelta(days=60)
        current_start = date.today() - timedelta(days=30)
        current_end = date.today()

        # Old data (outside range) - should be ignored
        for day in range(7):
            AIUsageDailyFactory(
                team=team,
                member=member,
                date=old_start + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=80,
                acceptance_rate=Decimal("80"),
            )
        PullRequestFactory.create_batch(
            5,
            team=team,
            author=member,
            state="merged",
            merged_at=make_aware_datetime(old_start + timedelta(days=5)),
        )

        # Query current range (no data there)
        champions = get_copilot_champions(team, current_start, current_end)

        self.assertEqual(champions, [])

    def test_only_counts_merged_prs(self):
        """Should only count merged PRs, not open or closed."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)

        start_date = date.today() - timedelta(days=30)
        end_date = date.today()

        for day in range(7):
            AIUsageDailyFactory(
                team=team,
                member=member,
                date=start_date + timedelta(days=day),
                source="copilot",
                suggestions_shown=100,
                suggestions_accepted=50,
                acceptance_rate=Decimal("50"),
            )

        # 2 merged PRs (below 3-PR threshold)
        PullRequestFactory.create_batch(
            2,
            team=team,
            author=member,
            state="merged",
        )
        # 5 open PRs (should not count)
        PullRequestFactory.create_batch(
            5,
            team=team,
            author=member,
            state="open",
        )
        # 3 closed PRs (should not count)
        PullRequestFactory.create_batch(
            3,
            team=team,
            author=member,
            state="closed",
        )

        champions = get_copilot_champions(team, start_date, end_date)

        # Should be excluded because only 2 merged PRs
        self.assertEqual(champions, [])
