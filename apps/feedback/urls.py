"""
URL configuration for the feedback app.
"""

from django.urls import path

from apps.feedback import views

app_name = "feedback"

# Team-scoped URL patterns (mounted under /app/feedback/)
# Tuple format: (patterns_list, namespace)
team_urlpatterns = (
    [
        path("", views.dashboard, name="dashboard"),
        path("create/", views.create_feedback, name="create"),
        path("cto-summary/", views.cto_summary, name="cto_summary"),
        path("<int:pk>/", views.feedback_detail, name="detail"),
        path("<int:pk>/resolve/", views.resolve_feedback, name="resolve"),
    ],
    "feedback",
)
