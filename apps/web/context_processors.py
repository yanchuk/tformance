from copy import copy

from django.conf import settings

from .meta import absolute_url, get_server_root


def project_meta(request):
    # modify these values as needed and add whatever else you want globally available here
    project_data = copy(settings.PROJECT_METADATA)
    project_data["TITLE"] = "{} | {}".format(project_data["NAME"], project_data["DESCRIPTION"])
    return {
        "project_meta": project_data,
        "server_url": get_server_root(),
        "page_url": absolute_url(request.path),
        "page_title": "",
        "page_description": "",
        "page_image": "",
        "light_theme": settings.LIGHT_THEME,
        "dark_theme": settings.DARK_THEME,
        "current_theme": request.COOKIES.get("theme", ""),
        "dark_mode": request.COOKIES.get("theme", "") == settings.DARK_THEME,
        "turnstile_key": getattr(settings, "TURNSTILE_KEY", None),
    }


def google_analytics_id(request):
    """
    Adds google analytics id to all requests
    """
    if settings.GOOGLE_ANALYTICS_ID:
        return {
            "GOOGLE_ANALYTICS_ID": settings.GOOGLE_ANALYTICS_ID,
        }
    else:
        return {}


def posthog_config(request):
    """
    Adds PostHog configuration to all requests.

    Exposes POSTHOG_API_KEY and POSTHOG_HOST for the JS SDK initialization.
    Only exposes values if POSTHOG_API_KEY is configured.
    """
    posthog_api_key = getattr(settings, "POSTHOG_API_KEY", "")
    if posthog_api_key:
        return {
            "POSTHOG_API_KEY": posthog_api_key,
            "POSTHOG_HOST": getattr(settings, "POSTHOG_HOST", "https://us.i.posthog.com"),
        }
    return {}
