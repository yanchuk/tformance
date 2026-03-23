"""OG image view endpoints.

Serves pre-generated PNG images from MEDIA_ROOT/public_og/.
No generation on request — images are created during stats pipeline.
"""

import os

from django.conf import settings
from django.http import FileResponse, Http404


def og_org_image(request, slug):
    """Serve pre-generated org OG image."""
    path = os.path.join(settings.MEDIA_ROOT, "public_og", f"{slug}.png")
    if not os.path.exists(path):
        raise Http404
    return FileResponse(open(path, "rb"), content_type="image/png")


def og_repo_image(request, slug, repo_slug):
    """Serve pre-generated repo OG image."""
    path = os.path.join(settings.MEDIA_ROOT, "public_og", f"{slug}_{repo_slug}.png")
    if not os.path.exists(path):
        raise Http404
    return FileResponse(open(path, "rb"), content_type="image/png")
