"""OG image view endpoints.

Serves pre-generated PNG images from MEDIA_ROOT/public_og/.
No generation on request — images are created during stats pipeline.
Falls back to the static general OG image if pre-generated file is missing.
"""

import os

from django.conf import settings
from django.http import FileResponse
from django.shortcuts import redirect
from django.templatetags.static import static

FALLBACK_OG_IMAGE = "images/og-image.png"


def og_org_image(request, slug):
    """Serve pre-generated org OG image, or redirect to static fallback."""
    path = os.path.join(settings.MEDIA_ROOT, "public_og", f"{slug}.png")
    if not os.path.exists(path):
        return redirect(static(FALLBACK_OG_IMAGE))
    return FileResponse(open(path, "rb"), content_type="image/png")


def og_repo_image(request, slug, repo_slug):
    """Serve pre-generated repo OG image, or redirect to static fallback."""
    path = os.path.join(settings.MEDIA_ROOT, "public_og", f"{slug}_{repo_slug}.png")
    if not os.path.exists(path):
        return redirect(static(FALLBACK_OG_IMAGE))
    return FileResponse(open(path, "rb"), content_type="image/png")
