"""Tests for _resolve_member github_id backfill in PRPersistenceService.

Verifies that when a TeamMember is first created without a github_id
(e.g., seen as a reviewer), then later encountered with a github_id
(e.g., as a PR author), the existing record gets backfilled.
"""

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import TeamMember
from apps.metrics.seeding.persistence import PRPersistenceService


class ResolveMemberGithubIdBackfillTests(TestCase):
    """Test _resolve_member backfills github_id on existing members."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    def _make_service(self):
        return PRPersistenceService(self.team)

    def test_backfills_github_id_on_existing_member_without_one(self):
        """Member created without github_id, later call with github_id=12345 updates it."""
        # Create member without github_id (simulates reviewer-first creation)
        TeamMember.objects.create(
            team=self.team,
            github_username="alice",
            display_name="alice",
            github_id="",
        )

        service = self._make_service()
        member = service._resolve_member("alice", github_id=12345)

        assert member.github_id == "12345"
        # Verify DB is also updated
        member.refresh_from_db()
        assert member.github_id == "12345"

    def test_does_not_overwrite_existing_github_id(self):
        """Member already has github_id=99999, call with different github_id=12345 keeps 99999."""
        TeamMember.objects.create(
            team=self.team,
            github_username="bob",
            display_name="bob",
            github_id="99999",
        )

        service = self._make_service()
        member = service._resolve_member("bob", github_id=12345)

        assert member.github_id == "99999"
        member.refresh_from_db()
        assert member.github_id == "99999"

    def test_backfills_cached_member_github_id(self):
        """Cached member without github_id gets updated on subsequent call with github_id."""
        service = self._make_service()

        # First call: creates member without github_id (as reviewer)
        member1 = service._resolve_member("carol", github_id=0)
        assert not member1.github_id  # falsy: 0 or ""

        # Second call: same login, now with github_id (as PR author)
        member2 = service._resolve_member("carol", github_id=54321)

        # In-memory cache object should be updated
        assert member2.github_id == "54321"
        assert member1 is member2  # same object from cache

        # DB should also be updated
        db_member = TeamMember.objects.get(team=self.team, github_username="carol")
        assert db_member.github_id == "54321"

    def test_github_id_zero_does_not_overwrite(self):
        """github_id=0 (falsy) should NOT trigger any update on existing member."""
        TeamMember.objects.create(
            team=self.team,
            github_username="dave",
            display_name="dave",
            github_id="",
        )

        service = self._make_service()
        member = service._resolve_member("dave", github_id=0)

        assert member.github_id == ""
        member.refresh_from_db()
        assert member.github_id == ""
