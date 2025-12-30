"""URL patterns for standalone Pull Requests page."""

from django.urls import path

from apps.metrics.views import pr_list, pr_list_export, pr_list_table

app_name = "pullrequests"

# These URLs are mounted at /app/pull-requests/ (team-scoped)
team_urlpatterns = (
    [
        path("", pr_list, name="pr_list"),
        path("table/", pr_list_table, name="pr_list_table"),
        path("export/", pr_list_export, name="pr_list_export"),
    ],
    "pullrequests",
)

# Also provide top-level URL names for reverse()
urlpatterns = []
