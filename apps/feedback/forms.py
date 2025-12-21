"""
Forms for the AI feedback app.
"""

from django import forms

from apps.feedback.models import AIFeedback


class FeedbackForm(forms.ModelForm):
    """Form for creating AI feedback."""

    class Meta:
        model = AIFeedback
        fields = ["category", "description", "pull_request", "file_path", "language"]
        widgets = {
            "description": forms.Textarea(
                attrs={
                    "class": "textarea textarea-bordered w-full",
                    "rows": 3,
                    "placeholder": "Describe what went wrong with the AI-generated code...",
                }
            ),
            "category": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "file_path": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "e.g., src/components/Button.tsx",
                }
            ),
            "language": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "e.g., python, typescript",
                }
            ),
        }
