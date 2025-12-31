"""tformance URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/stable/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.api.v2.views import PagesAPIViewSet
from wagtail.contrib.sitemaps import Sitemap
from wagtail.documents import urls as wagtaildocs_urls

from apps.feedback.urls import team_urlpatterns as feedback_team_urls
from apps.insights.urls import team_urlpatterns as insights_team_urls
from apps.integrations.urls import team_urlpatterns as integrations_team_urls
from apps.metrics.urls import team_urlpatterns as metrics_team_urls
from apps.notes.urls import team_urlpatterns as notes_team_urls
from apps.pullrequests.urls import team_urlpatterns as pullrequests_team_urls
from apps.subscriptions.urls import team_urlpatterns as subscriptions_team_urls
from apps.teams.urls import team_urlpatterns as single_team_urls
from apps.web.sitemaps import StaticViewSitemap
from apps.web.urls import team_urlpatterns as web_team_urls

PagesAPIViewSet.schema = None  # hacky workaround for https://github.com/wagtail/wagtail/issues/8583

sitemaps = {
    "static": StaticViewSitemap(),
    "wagtail": Sitemap(),
}

# urls that are unique to using a team should go here
team_urlpatterns = [
    path("", include(web_team_urls)),
    path("subscription/", include(subscriptions_team_urls)),
    path("team/", include(single_team_urls)),
    path("integrations/", include(integrations_team_urls)),
    path("metrics/", include(metrics_team_urls)),
    path("pull-requests/", include(pullrequests_team_urls)),  # Standalone PR page
    path("insights/", include(insights_team_urls)),
    path("feedback/", include(feedback_team_urls)),
    path("notes/", include(notes_team_urls)),
]

urlpatterns = [
    # redirect Django admin login to main login page
    path("admin/login/", RedirectView.as_view(pattern_name="account_login")),
    path("admin/", admin.site.urls),
    path("dashboard/", include("apps.dashboard.urls")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django.contrib.sitemaps.views.sitemap"),
    path("app/", include(team_urlpatterns)),
    path("accounts/", include("allauth.urls")),
    path("users/", include("apps.users.urls")),
    path("subscriptions/", include("apps.subscriptions.urls")),
    path("teams/", include("apps.teams.urls")),
    path("integrations/", include("apps.integrations.urls")),  # Non-team integrations URLs (webhooks)
    path("onboarding/", include("apps.onboarding.urls")),
    path("auth/", include("apps.auth.urls")),
    path("", include("apps.web.urls")),
    path("support/", include("apps.support.urls")),
    path("celery-progress/", include("celery_progress.urls")),
    # API docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    # Optional UI - you may wish to remove one of these depending on your preference
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/schema/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # djstripe urls - for webhooks
    path("stripe/", include("djstripe.urls", namespace="djstripe")),
    # hijack urls for impersonation
    path("hijack/", include("hijack.urls", namespace="hijack")),
    # wagtail config
    # redirect Wagtail admin login to main login page
    path("cms/login/", RedirectView.as_view(pattern_name="account_login")),
    path("cms/", include(wagtailadmin_urls)),
    path("documents/", include(wagtaildocs_urls)),
    path("content/", include(wagtail_urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Debug-only URLs
if settings.DEBUG:
    urlpatterns = [path("__reload__/", include("django_browser_reload.urls"))] + urlpatterns
