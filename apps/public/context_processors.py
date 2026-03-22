"""Context processor for public view mode.

Makes is_public_view and public_slug available in all templates
without passing through every view context.
"""

from apps.public.constants import FRESHNESS_COPY, PRIMARY_CTA_TEXT, SECONDARY_CTA_TEXT


def public_mode(request):
    profile = getattr(request, "public_profile", None)
    return {
        "is_public_view": getattr(request, "is_public_view", False),
        "public_profile": profile,
        "public_slug": profile.public_slug if profile else None,
        "primary_cta_text": PRIMARY_CTA_TEXT,
        "secondary_cta_text": SECONDARY_CTA_TEXT,
        "freshness_copy": FRESHNESS_COPY,
    }
