"""URL patterns for unified OAuth callbacks."""

from django.urls import path

from . import views

app_name = "tformance_auth"

urlpatterns = [
    path("github/callback/", views.github_callback, name="github_callback"),
]
