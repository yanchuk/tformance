"""Context processor for public view mode.

Makes is_public_view and public_slug available in all templates
without passing through every view context.
"""


def public_mode(request):
    profile = getattr(request, "public_profile", None)
    return {
        "is_public_view": getattr(request, "is_public_view", False),
        "public_profile": profile,
        "public_slug": profile.public_slug if profile else None,
    }
