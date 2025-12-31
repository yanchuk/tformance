"""
Tests for the PR Notes views.

TDD RED phase: These tests should FAIL initially.
"""

from django.test import TestCase

from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.notes.factories import PRNoteFactory
from apps.notes.models import PRNote
from apps.teams.models import Membership
from apps.teams.roles import ROLE_ADMIN
from apps.users.models import CustomUser


class NotesViewTestCase(TestCase):
    """Base test case for notes views."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="test@example.com",
            email="test@example.com",
            password="testpass123",
        )
        # Add user to team as admin
        Membership.objects.create(
            team=self.team,
            user=self.user,
            role=ROLE_ADMIN,
        )
        self.member = TeamMemberFactory(team=self.team, email=self.user.email)
        self.client.login(email="test@example.com", password="testpass123")
        # Set team in session
        session = self.client.session
        session["team"] = self.team.id
        session.save()

        # Create a PR for testing
        self.pr = PullRequestFactory(team=self.team)

    def get_note_form_url(self, pr_id):
        """Get the note form URL."""
        return f"/app/notes/pr/{pr_id}/"

    def get_delete_note_url(self, pr_id):
        """Get the delete note URL."""
        return f"/app/notes/pr/{pr_id}/delete/"


class TestNoteForm(NotesViewTestCase):
    """Tests for the note_form view."""

    def test_form_requires_login(self):
        """Test that form requires authentication."""
        self.client.logout()
        response = self.client.get(self.get_note_form_url(self.pr.id))
        self.assertEqual(response.status_code, 302)

    def test_form_returns_200(self):
        """Test that form returns 200 for authenticated users."""
        response = self.client.get(self.get_note_form_url(self.pr.id))
        self.assertEqual(response.status_code, 200)

    def test_form_returns_empty_for_new(self):
        """Test that form is empty when no note exists."""
        response = self.client.get(self.get_note_form_url(self.pr.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="content"')
        # Form should not have existing content
        self.assertNotContains(response, "existing note content")

    def test_form_returns_filled_for_existing(self):
        """Test that form is pre-filled when note exists."""
        PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="My existing note content",
            flag="review_later",
        )

        response = self.client.get(self.get_note_form_url(self.pr.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My existing note content")

    def test_form_shows_pr_context(self):
        """Test that form shows PR context (title, number)."""
        response = self.client.get(self.get_note_form_url(self.pr.id))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(self.pr.github_pr_id))

    def test_cannot_see_other_users_notes(self):
        """Test that user cannot see another user's note."""
        other_user = CustomUser.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpass123",
        )
        PRNote.objects.create(
            user=other_user,
            pull_request=self.pr,
            content="Other user's private note",
            flag="important",
        )

        response = self.client.get(self.get_note_form_url(self.pr.id))
        self.assertEqual(response.status_code, 200)
        # Should not see other user's note content
        self.assertNotContains(response, "Other user's private note")

    def test_create_new_note(self):
        """Test creating a new note via POST."""
        response = self.client.post(
            self.get_note_form_url(self.pr.id),
            data={
                "content": "My new note about this PR",
                "flag": "false_positive",
            },
        )

        # Should redirect or return success
        self.assertIn(response.status_code, [200, 302])

        # Note should be created
        note = PRNote.objects.get(user=self.user, pull_request=self.pr)
        self.assertEqual(note.content, "My new note about this PR")
        self.assertEqual(note.flag, "false_positive")

    def test_update_existing_note(self):
        """Test updating an existing note via POST."""
        note = PRNote.objects.create(
            user=self.user,
            pull_request=self.pr,
            content="Original content",
            flag="",
        )

        response = self.client.post(
            self.get_note_form_url(self.pr.id),
            data={
                "content": "Updated content",
                "flag": "concern",
            },
        )

        self.assertIn(response.status_code, [200, 302])

        # Note should be updated
        note.refresh_from_db()
        self.assertEqual(note.content, "Updated content")
        self.assertEqual(note.flag, "concern")

    def test_htmx_request_returns_partial(self):
        """Test that HTMX request returns modal partial."""
        response = self.client.get(
            self.get_note_form_url(self.pr.id),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Should contain modal structure
        self.assertContains(response, 'class="modal')

    def test_htmx_post_returns_success_partial(self):
        """Test that HTMX POST returns success partial."""
        response = self.client.post(
            self.get_note_form_url(self.pr.id),
            data={
                "content": "Test note",
                "flag": "",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)

    def test_invalid_pr_returns_404(self):
        """Test that non-existent PR returns 404."""
        response = self.client.get(self.get_note_form_url(99999))
        self.assertEqual(response.status_code, 404)

    def test_other_team_pr_returns_404(self):
        """Test that PR from another team returns 404."""
        other_team = TeamFactory()
        other_pr = PullRequestFactory(team=other_team)

        response = self.client.get(self.get_note_form_url(other_pr.id))
        self.assertEqual(response.status_code, 404)

    def test_form_validation_error(self):
        """Test that form validation errors are shown."""
        response = self.client.post(
            self.get_note_form_url(self.pr.id),
            data={
                "content": "",  # Empty content should fail
                "flag": "",
            },
        )
        # Should return 200 with form errors (not redirect)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "required")


class TestDeleteNote(NotesViewTestCase):
    """Tests for the delete_note view."""

    def test_delete_requires_login(self):
        """Test that delete requires authentication."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr)
        self.client.logout()
        response = self.client.post(self.get_delete_note_url(self.pr.id))
        self.assertEqual(response.status_code, 302)
        # Note should still exist
        self.assertTrue(PRNote.objects.filter(id=note.id).exists())

    def test_delete_own_note(self):
        """Test that user can delete their own note."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr)
        response = self.client.post(self.get_delete_note_url(self.pr.id))
        self.assertIn(response.status_code, [200, 302])
        # Note should be deleted
        self.assertFalse(PRNote.objects.filter(id=note.id).exists())

    def test_cannot_delete_others_note(self):
        """Test that user cannot delete another user's note."""
        other_user = CustomUser.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpass123",
        )
        other_note = PRNoteFactory(user=other_user, pull_request=self.pr)
        response = self.client.post(self.get_delete_note_url(self.pr.id))
        # Should return 404 (no note found for this user)
        self.assertEqual(response.status_code, 404)
        # Other user's note should still exist
        self.assertTrue(PRNote.objects.filter(id=other_note.id).exists())

    def test_delete_nonexistent_note_returns_404(self):
        """Test that deleting non-existent note returns 404."""
        response = self.client.post(self.get_delete_note_url(self.pr.id))
        self.assertEqual(response.status_code, 404)

    def test_delete_only_accepts_post(self):
        """Test that delete only works with POST method."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr)
        response = self.client.get(self.get_delete_note_url(self.pr.id))
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
        # Note should still exist
        self.assertTrue(PRNote.objects.filter(id=note.id).exists())

    def test_htmx_delete_returns_empty(self):
        """Test that HTMX delete returns empty response for swap."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr)
        response = self.client.post(
            self.get_delete_note_url(self.pr.id),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        # Should return empty or confirmation content
        self.assertFalse(PRNote.objects.filter(id=note.id).exists())


class TestMyNotes(NotesViewTestCase):
    """Tests for the my_notes view."""

    def get_my_notes_url(self):
        """Get the my notes URL."""
        return "/app/notes/"

    def test_my_notes_requires_login(self):
        """Test that my notes requires authentication."""
        self.client.logout()
        response = self.client.get(self.get_my_notes_url())
        self.assertEqual(response.status_code, 302)

    def test_my_notes_returns_200(self):
        """Test that my notes returns 200 for authenticated users."""
        response = self.client.get(self.get_my_notes_url())
        self.assertEqual(response.status_code, 200)

    def test_my_notes_shows_user_notes(self):
        """Test that my notes shows the user's notes."""
        PRNoteFactory(user=self.user, pull_request=self.pr, content="Note one")
        pr2 = PullRequestFactory(team=self.team)
        PRNoteFactory(user=self.user, pull_request=pr2, content="Note two")

        response = self.client.get(self.get_my_notes_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Note one")
        self.assertContains(response, "Note two")

    def test_my_notes_does_not_show_others_notes(self):
        """Test that my notes does not show other users' notes."""
        other_user = CustomUser.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpass123",
        )
        PRNoteFactory(user=other_user, pull_request=self.pr, content="Other user note")
        PRNoteFactory(user=self.user, pull_request=self.pr, content="My note")

        response = self.client.get(self.get_my_notes_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My note")
        self.assertNotContains(response, "Other user note")

    def test_my_notes_filter_by_flag(self):
        """Test filtering notes by flag."""
        PRNoteFactory(user=self.user, pull_request=self.pr, content="Important note", flag="important")
        pr2 = PullRequestFactory(team=self.team)
        PRNoteFactory(user=self.user, pull_request=pr2, content="Review later note", flag="review_later")

        # Filter by important
        response = self.client.get(self.get_my_notes_url() + "?flag=important")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Important note")
        self.assertNotContains(response, "Review later note")

    def test_my_notes_filter_by_resolved(self):
        """Test filtering notes by resolved status."""
        PRNoteFactory(user=self.user, pull_request=self.pr, content="Resolved note", is_resolved=True)
        pr2 = PullRequestFactory(team=self.team)
        PRNoteFactory(user=self.user, pull_request=pr2, content="Open note", is_resolved=False)

        # Filter by resolved
        response = self.client.get(self.get_my_notes_url() + "?resolved=true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Resolved note")
        self.assertNotContains(response, "Open note")

        # Filter by unresolved
        response = self.client.get(self.get_my_notes_url() + "?resolved=false")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open note")
        self.assertNotContains(response, "Resolved note")

    def test_my_notes_shows_pr_context(self):
        """Test that my notes shows PR context."""
        PRNoteFactory(user=self.user, pull_request=self.pr)
        response = self.client.get(self.get_my_notes_url())
        self.assertEqual(response.status_code, 200)
        # Should show PR number
        self.assertContains(response, str(self.pr.github_pr_id))

    def test_my_notes_empty_state(self):
        """Test that my notes shows empty state when no notes."""
        response = self.client.get(self.get_my_notes_url())
        self.assertEqual(response.status_code, 200)
        # Should show some empty state message
        self.assertContains(response, "No notes")

    def test_my_notes_ordered_by_recent(self):
        """Test that notes are ordered by most recent first."""
        PRNoteFactory(user=self.user, pull_request=self.pr, content="First note")
        pr2 = PullRequestFactory(team=self.team)
        PRNoteFactory(user=self.user, pull_request=pr2, content="Second note")

        response = self.client.get(self.get_my_notes_url())
        content = response.content.decode()
        # Second note should appear before first note
        self.assertLess(content.find("Second note"), content.find("First note"))


class TestToggleResolve(NotesViewTestCase):
    """Tests for the toggle_resolve view."""

    def get_toggle_resolve_url(self, note_id):
        """Get the toggle resolve URL."""
        return f"/app/notes/{note_id}/toggle-resolve/"

    def test_toggle_requires_login(self):
        """Test that toggle requires authentication."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr, is_resolved=False)
        self.client.logout()
        response = self.client.post(self.get_toggle_resolve_url(note.id))
        self.assertEqual(response.status_code, 302)
        # Note should still be unresolved
        note.refresh_from_db()
        self.assertFalse(note.is_resolved)

    def test_toggle_only_accepts_post(self):
        """Test that toggle only works with POST method."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr, is_resolved=False)
        response = self.client.get(self.get_toggle_resolve_url(note.id))
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
        # Note should still be unresolved
        note.refresh_from_db()
        self.assertFalse(note.is_resolved)

    def test_toggle_resolve_on(self):
        """Test toggling a note to resolved."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr, is_resolved=False)
        response = self.client.post(self.get_toggle_resolve_url(note.id))
        self.assertIn(response.status_code, [200, 302])
        note.refresh_from_db()
        self.assertTrue(note.is_resolved)
        self.assertIsNotNone(note.resolved_at)

    def test_toggle_resolve_off(self):
        """Test toggling a note back to unresolved."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr, is_resolved=True)
        response = self.client.post(self.get_toggle_resolve_url(note.id))
        self.assertIn(response.status_code, [200, 302])
        note.refresh_from_db()
        self.assertFalse(note.is_resolved)
        self.assertIsNone(note.resolved_at)

    def test_cannot_toggle_others_note(self):
        """Test that user cannot toggle another user's note."""
        other_user = CustomUser.objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="testpass123",
        )
        other_note = PRNoteFactory(user=other_user, pull_request=self.pr, is_resolved=False)
        response = self.client.post(self.get_toggle_resolve_url(other_note.id))
        self.assertEqual(response.status_code, 404)
        # Other user's note should still be unresolved
        other_note.refresh_from_db()
        self.assertFalse(other_note.is_resolved)

    def test_toggle_nonexistent_note_returns_404(self):
        """Test that toggling non-existent note returns 404."""
        response = self.client.post(self.get_toggle_resolve_url(99999))
        self.assertEqual(response.status_code, 404)

    def test_htmx_toggle_returns_partial(self):
        """Test that HTMX toggle returns partial for swap."""
        note = PRNoteFactory(user=self.user, pull_request=self.pr, is_resolved=False)
        response = self.client.post(
            self.get_toggle_resolve_url(note.id),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        note.refresh_from_db()
        self.assertTrue(note.is_resolved)
