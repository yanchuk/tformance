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
        # LLM feedback endpoints
        path("llm/submit/", views.submit_llm_feedback, name="llm_submit"),
        path("llm/<int:pk>/comment/", views.add_llm_feedback_comment, name="llm_comment"),
        path(
            "llm/<str:content_type>/<str:content_id>/",
            views.get_llm_feedback,
            name="llm_get",
        ),
    ],
    "feedback",
)
