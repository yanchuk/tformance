"""
URL configuration for the insights app.
"""

from django.urls import path

from apps.insights import views

app_name = "insights"

# Team-scoped URL patterns (mounted under /a/<team_slug>/insights/)
# Tuple format: (patterns_list, namespace)
team_urlpatterns = (
    [
        path("summary/", views.get_summary, name="summary"),
        path("ask/", views.ask_question, name="ask"),
        path("suggested/", views.suggested_questions, name="suggested"),
    ],
    "insights",
)
