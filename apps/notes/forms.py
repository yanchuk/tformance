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

    def clean_content(self):
        """Validate content length."""
        content = self.cleaned_data.get("content", "")
        if len(content) > 2000:
            raise forms.ValidationError("Content cannot exceed 2000 characters.")
        return content
