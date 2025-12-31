"""
Tests for the PRNote form.

TDD RED phase: These tests should FAIL initially.
"""

from django.test import TestCase

from apps.notes.models import FLAG_CHOICES


class TestNoteForm(TestCase):
    """Tests for NoteForm."""

    def test_form_has_expected_fields(self):
        """Test that form has content and flag fields."""
        from apps.notes.forms import NoteForm

        form = NoteForm()
        self.assertIn("content", form.fields)
        self.assertIn("flag", form.fields)
        # Should NOT include user, pull_request, is_resolved, resolved_at
        self.assertNotIn("user", form.fields)
        self.assertNotIn("pull_request", form.fields)
        self.assertNotIn("is_resolved", form.fields)
        self.assertNotIn("resolved_at", form.fields)

    def test_content_max_length_validation(self):
        """Test that content over 2000 chars is rejected."""
        from apps.notes.forms import NoteForm

        # Valid content
        form = NoteForm(data={"content": "x" * 2000, "flag": ""})
        self.assertTrue(form.is_valid())

        # Invalid - too long
        form = NoteForm(data={"content": "x" * 2001, "flag": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("content", form.errors)

    def test_empty_form_allowed_for_starring(self):
        """Test that empty content AND empty flag is valid (just starred)."""
        from apps.notes.forms import NoteForm

        # Empty content AND empty flag should be valid - allows quick starring
        form = NoteForm(data={"content": "", "flag": ""})
        self.assertTrue(form.is_valid())

    def test_content_optional_when_flag_provided(self):
        """Test that content is optional if flag is provided."""
        from apps.notes.forms import NoteForm

        form = NoteForm(data={"content": "", "flag": "important"})
        self.assertTrue(form.is_valid())

    def test_flag_optional_when_content_provided(self):
        """Test that flag is optional if content is provided."""
        from apps.notes.forms import NoteForm

        form = NoteForm(data={"content": "Some note text", "flag": ""})
        self.assertTrue(form.is_valid())

    def test_flag_choices(self):
        """Test that flag accepts valid choices."""
        from apps.notes.forms import NoteForm

        # Valid flag values
        for flag_value, _ in FLAG_CHOICES:
            form = NoteForm(data={"content": "Test note", "flag": flag_value})
            self.assertTrue(form.is_valid(), f"Flag '{flag_value}' should be valid")

    def test_invalid_flag_rejected(self):
        """Test that invalid flag values are rejected."""
        from apps.notes.forms import NoteForm

        form = NoteForm(data={"content": "Test note", "flag": "invalid_flag"})
        self.assertFalse(form.is_valid())
        self.assertIn("flag", form.errors)

    def test_form_has_daisyui_classes(self):
        """Test that form widgets have DaisyUI CSS classes."""
        from apps.notes.forms import NoteForm

        form = NoteForm()

        # Content should be a textarea with DaisyUI classes
        content_widget = form.fields["content"].widget
        self.assertIn("textarea", content_widget.attrs.get("class", ""))

        # Flag should be a select with DaisyUI classes
        flag_widget = form.fields["flag"].widget
        self.assertIn("select", flag_widget.attrs.get("class", ""))

    def test_content_placeholder(self):
        """Test that content field has a helpful placeholder."""
        from apps.notes.forms import NoteForm

        form = NoteForm()
        placeholder = form.fields["content"].widget.attrs.get("placeholder", "")
        self.assertTrue(len(placeholder) > 0, "Content should have a placeholder")
