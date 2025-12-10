"""
Tests for GitHub pull_request webhook event processing.

Tests the handle_pull_request_event function that processes GitHub webhook
payloads and creates/updates PullRequest records.
"""

from datetime import UTC, datetime
from decimal import Decimal

from django.test import TestCase

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.models import PRReview, PullRequest


class TestPullRequestEventHandler(TestCase):
    """Tests for handle_pull_request_event webhook processor."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(
            team=self.team,
            github_id="12345",
            github_username="developer",
            display_name="John Developer",
        )

    def _make_payload(self, action="opened", **overrides):
        """Create a GitHub webhook payload with sensible defaults."""
        pr_data = {
            "id": 123456789,
            "number": 42,
            "title": "Add new feature",
            "state": "open",
            "merged": False,
            "user": {"id": 12345, "login": "developer"},
            "created_at": "2025-01-01T10:00:00Z",
            "merged_at": None,
            "additions": 150,
            "deletions": 50,
        }
        pr_data.update(overrides)

        return {
            "action": action,
            "pull_request": pr_data,
            "repository": {"full_name": "acme-corp/api-server"},
        }

    def test_opened_action_creates_pull_request_record(self):
        """Test that 'opened' action creates a new PullRequest record."""
        from apps.metrics.processors import handle_pull_request_event

        payload = self._make_payload(action="opened")

        result = handle_pull_request_event(self.team, payload)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, PullRequest)
        self.assertEqual(result.github_pr_id, 123456789)
        self.assertEqual(result.github_repo, "acme-corp/api-server")
        self.assertEqual(result.title, "Add new feature")
        self.assertEqual(result.state, "open")
        self.assertEqual(result.author, self.author)
        self.assertEqual(result.additions, 150)
        self.assertEqual(result.deletions, 50)

    def test_closed_merged_updates_state_to_merged_and_sets_merged_at(self):
        """Test that 'closed' action with merged=true updates state to 'merged' and sets merged_at."""
        from apps.metrics.processors import handle_pull_request_event

        # First create the PR with 'opened'
        payload_opened = self._make_payload(action="opened")
        handle_pull_request_event(self.team, payload_opened)

        # Now close it with merged=true
        merged_at_time = "2025-01-02T15:00:00Z"
        payload_merged = self._make_payload(
            action="closed",
            state="closed",
            merged=True,
            merged_at=merged_at_time,
        )

        result = handle_pull_request_event(self.team, payload_merged)

        self.assertEqual(result.state, "merged")
        self.assertIsNotNone(result.merged_at)
        self.assertEqual(
            result.merged_at.isoformat(),
            datetime.fromisoformat(merged_at_time.replace("Z", "+00:00")).isoformat(),
        )

    def test_closed_not_merged_updates_state_to_closed(self):
        """Test that 'closed' action with merged=false updates state to 'closed'."""
        from apps.metrics.processors import handle_pull_request_event

        # First create the PR
        payload_opened = self._make_payload(action="opened")
        handle_pull_request_event(self.team, payload_opened)

        # Now close it without merging
        payload_closed = self._make_payload(
            action="closed",
            state="closed",
            merged=False,
        )

        result = handle_pull_request_event(self.team, payload_closed)

        self.assertEqual(result.state, "closed")
        self.assertIsNone(result.merged_at)

    def test_reopened_action_updates_state_back_to_open(self):
        """Test that 'reopened' action updates state back to 'open'."""
        from apps.metrics.processors import handle_pull_request_event

        # Create and close the PR
        payload_opened = self._make_payload(action="opened")
        pr = handle_pull_request_event(self.team, payload_opened)

        payload_closed = self._make_payload(action="closed", state="closed", merged=False)
        pr = handle_pull_request_event(self.team, payload_closed)
        self.assertEqual(pr.state, "closed")

        # Now reopen it
        payload_reopened = self._make_payload(action="reopened", state="open")
        result = handle_pull_request_event(self.team, payload_reopened)

        self.assertEqual(result.state, "open")

    def test_edited_action_updates_title(self):
        """Test that 'edited' action updates the PR title."""
        from apps.metrics.processors import handle_pull_request_event

        # Create the PR
        payload_opened = self._make_payload(action="opened", title="Original title")
        pr = handle_pull_request_event(self.team, payload_opened)
        self.assertEqual(pr.title, "Original title")

        # Edit the title
        payload_edited = self._make_payload(action="edited", title="Updated title")
        result = handle_pull_request_event(self.team, payload_edited)

        self.assertEqual(result.title, "Updated title")

    def test_author_matched_to_team_member_by_github_id(self):
        """Test that PR author is correctly matched to TeamMember by github_id."""
        from apps.metrics.processors import handle_pull_request_event

        # Create a different member with a specific github_id
        other_member = TeamMemberFactory(
            team=self.team,
            github_id="99999",
            github_username="other_dev",
            display_name="Other Developer",
        )

        payload = self._make_payload(
            action="opened",
            user={"id": 99999, "login": "other_dev"},
        )

        result = handle_pull_request_event(self.team, payload)

        self.assertEqual(result.author, other_member)
        self.assertNotEqual(result.author, self.author)

    def test_unknown_author_sets_author_none_gracefully(self):
        """Test that unknown author (not in TeamMember) sets author=None gracefully."""
        from apps.metrics.processors import handle_pull_request_event

        payload = self._make_payload(
            action="opened",
            user={"id": 88888, "login": "unknown_dev"},  # No matching TeamMember
        )

        result = handle_pull_request_event(self.team, payload)

        self.assertIsNotNone(result)
        self.assertIsNone(result.author)

    def test_cycle_time_hours_calculated_correctly_when_merged(self):
        """Test that cycle_time_hours is calculated correctly when PR is merged."""
        from apps.metrics.processors import handle_pull_request_event

        created_at = "2025-01-01T10:00:00Z"
        merged_at = "2025-01-02T15:00:00Z"  # 29 hours later

        payload = self._make_payload(
            action="closed",
            state="closed",
            merged=True,
            created_at=created_at,
            merged_at=merged_at,
        )

        result = handle_pull_request_event(self.team, payload)

        # Cycle time should be 29 hours (29.0)
        self.assertIsNotNone(result.cycle_time_hours)
        self.assertEqual(result.cycle_time_hours, Decimal("29.00"))

    def test_is_revert_detection_title_contains_revert(self):
        """Test that is_revert is detected when title contains 'Revert'."""
        from apps.metrics.processors import handle_pull_request_event

        payload = self._make_payload(
            action="opened",
            title='Revert "Add broken feature"',
        )

        result = handle_pull_request_event(self.team, payload)

        self.assertTrue(result.is_revert)

    def test_is_hotfix_detection_title_contains_hotfix(self):
        """Test that is_hotfix is detected when title contains 'hotfix'."""
        from apps.metrics.processors import handle_pull_request_event

        payload = self._make_payload(
            action="opened",
            title="Hotfix: critical production bug",
        )

        result = handle_pull_request_event(self.team, payload)

        self.assertTrue(result.is_hotfix)

    def test_duplicate_events_are_idempotent(self):
        """Test that processing the same PR event twice doesn't duplicate records."""
        from apps.metrics.processors import handle_pull_request_event

        payload = self._make_payload(action="opened")

        # Process the same event twice
        result1 = handle_pull_request_event(self.team, payload)
        result2 = handle_pull_request_event(self.team, payload)

        # Should be the same record
        self.assertEqual(result1.pk, result2.pk)

        # Should only have one PR in the database
        pr_count = PullRequest.objects.filter(
            team=self.team,
            github_pr_id=123456789,
            github_repo="acme-corp/api-server",
        ).count()
        self.assertEqual(pr_count, 1)


class TestPullRequestReviewEventHandler(TestCase):
    """Tests for handle_pull_request_review_event webhook processor."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(
            team=self.team,
            github_id="12345",
            github_username="developer",
            display_name="John Developer",
        )
        self.reviewer = TeamMemberFactory(
            team=self.team,
            github_id="54321",
            github_username="reviewer",
            display_name="Jane Reviewer",
        )
        # Create a PR that reviews will be attached to
        self.pr = PullRequestFactory(
            team=self.team,
            github_pr_id=123456789,
            github_repo="acme-corp/api-server",
            author=self.author,
            pr_created_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=UTC),
        )

    def _make_review_payload(self, action="submitted", **overrides):
        """Create a GitHub pull_request_review webhook payload with sensible defaults."""
        # Separate payload-level overrides from review-level overrides
        pull_request = overrides.pop("pull_request", None)
        repository = overrides.pop("repository", None)

        review_data = {
            "id": 456789,
            "user": {"id": 54321, "login": "reviewer"},
            "state": "approved",
            "submitted_at": "2025-01-01T12:00:00Z",
        }
        review_data.update(overrides)

        payload = {
            "action": action,
            "review": review_data,
            "pull_request": pull_request
            or {
                "id": 123456789,
                "number": 42,
            },
            "repository": repository or {"full_name": "acme-corp/api-server"},
        }

        return payload

    def test_submitted_action_creates_pr_review_record(self):
        """Test that 'submitted' action creates a new PRReview record."""
        from apps.metrics.processors import handle_pull_request_review_event

        payload = self._make_review_payload(action="submitted")

        result = handle_pull_request_review_event(self.team, payload)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, PRReview)
        self.assertEqual(result.pull_request, self.pr)
        self.assertEqual(result.reviewer, self.reviewer)
        self.assertEqual(result.state, "approved")

    def test_reviewer_matched_to_team_member_by_github_id(self):
        """Test that reviewer is correctly matched to TeamMember by github_id."""
        from apps.metrics.processors import handle_pull_request_review_event

        # Create another team member to review
        other_reviewer = TeamMemberFactory(
            team=self.team,
            github_id="99999",
            github_username="other_reviewer",
            display_name="Other Reviewer",
        )

        payload = self._make_review_payload(
            action="submitted",
            user={"id": 99999, "login": "other_reviewer"},
        )

        result = handle_pull_request_review_event(self.team, payload)

        self.assertEqual(result.reviewer, other_reviewer)
        self.assertNotEqual(result.reviewer, self.reviewer)

    def test_unknown_reviewer_sets_reviewer_none(self):
        """Test that unknown reviewer (not in TeamMember) sets reviewer=None gracefully."""
        from apps.metrics.processors import handle_pull_request_review_event

        payload = self._make_review_payload(
            action="submitted",
            user={"id": 88888, "login": "unknown_reviewer"},  # No matching TeamMember
        )

        result = handle_pull_request_review_event(self.team, payload)

        self.assertIsNotNone(result)
        self.assertIsNone(result.reviewer)

    def test_review_state_approved_mapped_correctly(self):
        """Test that 'approved' review state is mapped correctly."""
        from apps.metrics.processors import handle_pull_request_review_event

        payload = self._make_review_payload(
            action="submitted",
            state="approved",
        )

        result = handle_pull_request_review_event(self.team, payload)

        self.assertEqual(result.state, "approved")

    def test_review_state_changes_requested_mapped_correctly(self):
        """Test that 'changes_requested' review state is mapped correctly."""
        from apps.metrics.processors import handle_pull_request_review_event

        payload = self._make_review_payload(
            action="submitted",
            state="changes_requested",
        )

        result = handle_pull_request_review_event(self.team, payload)

        self.assertEqual(result.state, "changes_requested")

    def test_review_state_commented_mapped_correctly(self):
        """Test that 'commented' review state is mapped correctly."""
        from apps.metrics.processors import handle_pull_request_review_event

        payload = self._make_review_payload(
            action="submitted",
            state="commented",
        )

        result = handle_pull_request_review_event(self.team, payload)

        self.assertEqual(result.state, "commented")

    def test_first_review_updates_pull_request_first_review_at(self):
        """Test that the first review updates PullRequest.first_review_at."""
        from apps.metrics.processors import handle_pull_request_review_event

        # Ensure PR has no first_review_at initially
        self.pr.first_review_at = None
        self.pr.save()

        submitted_at = "2025-01-01T12:00:00Z"
        payload = self._make_review_payload(
            action="submitted",
            submitted_at=submitted_at,
        )

        handle_pull_request_review_event(self.team, payload)

        # Refresh the PR from database
        self.pr.refresh_from_db()

        self.assertIsNotNone(self.pr.first_review_at)
        expected_time = datetime.fromisoformat(submitted_at.replace("Z", "+00:00"))
        self.assertEqual(self.pr.first_review_at, expected_time)

    def test_review_time_hours_calculated_on_first_review(self):
        """Test that review_time_hours is calculated when first review is submitted."""
        from apps.metrics.processors import handle_pull_request_review_event

        # Ensure PR has no first_review_at or review_time_hours initially
        self.pr.first_review_at = None
        self.pr.review_time_hours = None
        self.pr.save()

        # PR created at 10:00, review submitted at 12:00 (2 hours later)
        submitted_at = "2025-01-01T12:00:00Z"
        payload = self._make_review_payload(
            action="submitted",
            submitted_at=submitted_at,
        )

        handle_pull_request_review_event(self.team, payload)

        # Refresh the PR from database
        self.pr.refresh_from_db()

        self.assertIsNotNone(self.pr.review_time_hours)
        self.assertEqual(self.pr.review_time_hours, Decimal("2.00"))

    def test_second_review_does_not_overwrite_first_review_at(self):
        """Test that a second review doesn't overwrite the first_review_at timestamp."""
        from apps.metrics.processors import handle_pull_request_review_event

        # First review at 12:00
        first_review_time = "2025-01-01T12:00:00Z"
        payload1 = self._make_review_payload(
            action="submitted",
            submitted_at=first_review_time,
        )
        handle_pull_request_review_event(self.team, payload1)

        # Capture the first review time
        self.pr.refresh_from_db()
        first_review_at = self.pr.first_review_at

        # Second review at 14:00
        second_review_time = "2025-01-01T14:00:00Z"
        payload2 = self._make_review_payload(
            action="submitted",
            submitted_at=second_review_time,
            user={"id": 12345, "login": "developer"},  # Different reviewer
        )
        handle_pull_request_review_event(self.team, payload2)

        # Check that first_review_at didn't change
        self.pr.refresh_from_db()
        self.assertEqual(self.pr.first_review_at, first_review_at)

    def test_review_on_non_existent_pr_is_handled_gracefully(self):
        """Test that review on non-existent PR returns None gracefully."""
        from apps.metrics.processors import handle_pull_request_review_event

        payload = self._make_review_payload(
            action="submitted",
            pull_request={"id": 999999999, "number": 999},  # Non-existent PR
        )

        result = handle_pull_request_review_event(self.team, payload)

        self.assertIsNone(result)

    def test_duplicate_review_events_are_idempotent(self):
        """Test that processing the same review event twice doesn't duplicate records."""
        from apps.metrics.processors import handle_pull_request_review_event

        payload = self._make_review_payload(action="submitted")

        # Process the same event twice
        result1 = handle_pull_request_review_event(self.team, payload)
        result2 = handle_pull_request_review_event(self.team, payload)

        # Should be the same record
        self.assertEqual(result1.pk, result2.pk)

        # Should only have one review in the database
        review_count = PRReview.objects.filter(
            team=self.team,
            pull_request=self.pr,
        ).count()
        self.assertEqual(review_count, 1)
