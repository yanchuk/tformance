from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from apps.public.decorators import public_org_required
from apps.web.meta import absolute_url

from .helpers import build_org_base_context


@cache_page(3600)
@require_http_methods(["GET"])
@public_org_required
def org_analytics(request, slug) -> HttpResponse:
    """Public analytics tab using read-only wrappers around existing metric partials."""
    context = build_org_base_context(request, slug, active_public_tab="analytics")
    profile = context["org_profile"]
    context.update(
        {
            "page_title": f"{profile.display_name} Analytics Dashboard",
            "page_description": (
                f"Read-only analytics for {profile.display_name}: AI adoption, cycle time, "
                "quality indicators, and team health trends."
            ),
            "page_canonical_url": absolute_url(reverse("public:org_analytics", kwargs={"slug": slug})),
        }
    )
    return TemplateResponse(request, "public/org_analytics.html", context)
