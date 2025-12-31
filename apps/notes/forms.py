"""
Forms for the Personal PR Notes feature.
"""

from django import forms

from apps.notes.models import FLAG_CHOICES, PRNote


class NoteForm(forms.ModelForm):
    """Form for creating and editing PR notes."""

    class Meta:
        model = PRNote
        fields = ["content", "flag"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full h-32",
                    "placeholder": "Add your observations about this PR...",
                    "rows": 4,
                }
            ),
            "flag": forms.Select(
                attrs={
                    "class": "select select-bordered w-full",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Override choices to include empty option with better label
        self.fields["flag"].choices = FLAG_CHOICES
        # Make content optional (can save with just a flag)
        self.fields["content"].required = False

    def clean_content(self):
        """Validate content length."""
        content = self.cleaned_data.get("content", "")
        if len(content) > 2000:
            raise forms.ValidationError("Content cannot exceed 2000 characters.")
        return content

    def clean(self):
        """Validate that either content or flag is provided."""
        cleaned_data = super().clean()
        content = cleaned_data.get("content", "").strip()
        flag = cleaned_data.get("flag", "")

        # At least one of content or flag must be provided
        if not content and not flag:
            raise forms.ValidationError("Please provide content or select a flag to mark this PR.")

        return cleaned_data
