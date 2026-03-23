"""Forms for the public analytics app."""

import re

from django import forms

from apps.public.models import PublicRepoRequest

GITHUB_REPO_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+/?$")


class RepoRequestForm(forms.ModelForm):
    """Form for OSS maintainers to request their repo be added."""

    class Meta:
        model = PublicRepoRequest
        fields = ["github_url", "email", "role"]
        widgets = {
            "github_url": forms.URLInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "https://github.com/org/repo",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "you@example.com",
                }
            ),
            "role": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def clean_github_url(self):
        url = self.cleaned_data["github_url"].rstrip("/")
        if not GITHUB_REPO_RE.match(url + "/"):
            raise forms.ValidationError(
                "Please enter a valid GitHub repository URL (e.g. https://github.com/org/repo)."
            )
        return url
