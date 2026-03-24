from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_GET

from apps.public.decorators import public_org_required
from apps.web.meta import absolute_url

from .helpers import build_org_base_context, get_org_og_image_url


@cache_page(3600)
@require_GET
@public_org_required
def org_analytics(request, slug) -> HttpResponse:
    """Public analytics support page for detailed metric exploration."""
    context = build_org_base_context(request, slug, active_public_tab="analytics")
    profile = context["org_profile"]
    context.update(
        {
            "page_title": f"{profile.display_name} Delivery & AI Trends",
            "page_description": (
                f"Detailed {profile.display_name} delivery and AI adoption trends across public GitHub pull requests."
            ),
            "page_canonical_url": absolute_url(reverse("public:org_detail", kwargs={"slug": slug})),
            "page_robots": "noindex,follow",
            "page_image": get_org_og_image_url(slug),
        }
    )
    return TemplateResponse(request, "public/org_analytics.html", context)
