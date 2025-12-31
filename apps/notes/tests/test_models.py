"""
Tests for the PRNote model.

TDD RED phase: These tests should FAIL initially.
"""

from django.db import IntegrityError
from django.test import TestCase

from apps.metrics.factories import PullRequestFactory, TeamFactory
from apps.users.models import CustomUser


class TestPRNote(TestCase):
    """Tests for PRNote model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="testuser@example.com",
            email="testuser@example.com",
            password="testpass123",
        )
        self.pr = PullRequestFactory(team=self.team)

    def test_create_note(self):
        """Test creating a basic note."""
        from apps.notes.models import PRNote

        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="This is a test note about the PR.",
        )

        self.assertIsNotNone(note.id)
        self.assertEqual(note.user, self.user)
        self.assertEqual(note.pull_request, self.pr)
        self.assertEqual(note.content, "This is a test note about the PR.")
        self.assertEqual(note.flag, "")
        self.assertFalse(note.is_resolved)
        self.assertIsNone(note.resolved_at)
        self.assertIsNotNone(note.created_at)
        self.assertIsNotNone(note.updated_at)

    def test_create_note_with_flag(self):
        """Test creating a note with a flag."""
        from apps.notes.models import PRNote

        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="AI detection seems wrong here.",
            flag="false_positive",
        )

        self.assertEqual(note.flag, "false_positive")

    def test_unique_constraint_user_pr(self):
        """Test that a user can only have one note per PR."""
        from apps.notes.models import PRNote

        # Create first note
        PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="First note",
        )

        # Attempt to create second note for same user/PR should fail
        with self.assertRaises(IntegrityError):
            PRNote.objects.create(
                user=self.user,
                pull_request=self.pr,
                content="Second note - should fail",
            )

    def test_different_users_can_note_same_pr(self):
        """Test that different users can have notes on the same PR."""
        from apps.notes.models import PRNote

        user2 = CustomUser.objects.create_user(
            username="otheruser@example.com",
            email="otheruser@example.com",
            password="testpass123",
        )

        # Both users can create notes on the same PR
        note1 = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="User 1's note",
        )
        note2 = PRNote.objects.create(
            user=user2,
            pull_request=self.pr,
            content="User 2's note",
        )

        self.assertNotEqual(note1.id, note2.id)
        self.assertEqual(PRNote.objects.filter(pull_request=self.pr).count(), 2)

    def test_cascade_delete_on_pr(self):
        """Test that notes are deleted when their PR is deleted."""
        from apps.notes.models import PRNote

        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="This note will be deleted with PR",
        )
        note_id = note.id

        # Delete the PR
        self.pr.delete()

        # Note should be gone
        self.assertFalse(PRNote.objects.filter(id=note_id).exists())

    def test_cascade_delete_on_user(self):
        """Test that notes are deleted when their user is deleted."""
        from apps.notes.models import PRNote

        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="This note will be deleted with user",
        )
        note_id = note.id

        # Delete the user
        self.user.delete()

        # Note should be gone
        self.assertFalse(PRNote.objects.filter(id=note_id).exists())

    def test_flag_choices(self):
        """Test that only valid flag values are allowed."""
        from apps.notes.models import FLAG_CHOICES, PRNote

        # Valid flags should work
        valid_flags = ["", "false_positive", "review_later", "important", "concern"]
        for flag_value in valid_flags:
            note = PRNote(
                user=self.user,
                pull_request=self.pr,
                content=f"Note with flag: {flag_value}",
                flag=flag_value,
            )
            note.full_clean()  # Should not raise

        # Check FLAG_CHOICES has expected values
        flag_values = [choice[0] for choice in FLAG_CHOICES]
        self.assertIn("false_positive", flag_values)
        self.assertIn("review_later", flag_values)
        self.assertIn("important", flag_values)
        self.assertIn("concern", flag_values)

    def test_str_representation(self):
        """Test the string representation of a note."""
        from apps.notes.models import PRNote

        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="Test note",
            flag="review_later",
        )

        # Should include PR number and flag
        str_repr = str(note)
        self.assertIn(str(self.pr.github_pr_id), str_repr)

    def test_ordering_by_created_at_desc(self):
        """Test that notes are ordered by created_at descending."""
        from apps.notes.models import PRNote

        pr2 = PullRequestFactory(team=self.team)
        pr3 = PullRequestFactory(team=self.team)

        # Create notes in order
        note1 = PRNote.objects.create(user=self.user, pull_request=self.pr, content="First")
        note2 = PRNote.objects.create(user=self.user, pull_request=pr2, content="Second")
        note3 = PRNote.objects.create(user=self.user, pull_request=pr3, content="Third")

        notes = list(PRNote.objects.filter(user=self.user))

        # Most recent first
        self.assertEqual(notes[0], note3)
        self.assertEqual(notes[1], note2)
        self.assertEqual(notes[2], note1)

    def test_content_max_length(self):
        """Test that content respects max length."""
        from apps.notes.models import PRNote

        # Create note with max length content
        max_content = "x" * 2000
        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content=max_content,
        )
        self.assertEqual(len(note.content), 2000)

    def test_resolved_at_set_on_resolve(self):
        """Test that resolved_at is set when marking as resolved."""
        from django.utils import timezone

        from apps.notes.models import PRNote

        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="To be resolved",
        )

        self.assertFalse(note.is_resolved)
        self.assertIsNone(note.resolved_at)

        # Resolve the note
        note.is_resolved = True
        note.resolved_at = timezone.now()
        note.save()

        note.refresh_from_db()
        self.assertTrue(note.is_resolved)
        self.assertIsNotNone(note.resolved_at)
