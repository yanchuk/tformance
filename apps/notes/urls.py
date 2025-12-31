"""
URL configuration for the notes app.
"""

from django.urls import path

from apps.notes import views

app_name = "notes"

# Team-scoped URL patterns (mounted under /app/notes/)
team_urlpatterns = (
    [
        path("", views.my_notes, name="my_notes"),
        path("pr/<int:pr_id>/", views.note_form, name="note_form"),
        path("pr/<int:pr_id>/delete/", views.delete_note, name="delete_note"),
        path("pr/<int:pr_id>/inline/", views.inline_note, name="inline_note"),
        path("<int:note_id>/toggle-resolve/", views.toggle_resolve, name="toggle_resolve"),
    ],
    "notes",
)
