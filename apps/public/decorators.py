from functools import wraps

from django.http import Http404

from apps.public.models import PublicOrgProfile, PublicRepoProfile
from apps.teams.context import set_current_team, unset_current_team


def public_org_required(view_func):
    """Resolve public org from URL slug and bind team context for the request."""

    @wraps(view_func)
    def _inner(request, *args, **kwargs):
        slug = kwargs.get("slug") or kwargs.get("public_slug")
        if not slug:
            raise Http404

        try:
            profile = PublicOrgProfile.objects.select_related("team", "stats").get(
                public_slug=slug,
                is_public=True,
            )
        except PublicOrgProfile.DoesNotExist as exc:
            raise Http404 from exc

        if not profile.has_sufficient_data:
            raise Http404

        request.team = profile.team
        request.public_profile = profile
        request.is_public_view = True

        token = set_current_team(profile.team)
        try:
            return view_func(request, *args, **kwargs)
        finally:
            unset_current_team(token)

    return _inner


def public_repo_required(view_func):
    """Resolve public repo from org slug + repo slug, bind both to request."""

    @wraps(view_func)
    def _inner(request, *args, **kwargs):
        slug = kwargs.get("slug")
        repo_slug = kwargs.get("repo_slug")
        if not slug or not repo_slug:
            raise Http404

        try:
            profile = PublicOrgProfile.objects.select_related("team", "stats").get(
                public_slug=slug,
                is_public=True,
            )
        except PublicOrgProfile.DoesNotExist as exc:
            raise Http404 from exc

        if not profile.has_sufficient_data:
            raise Http404

        try:
            repo_profile = PublicRepoProfile.objects.select_related("org_profile").get(
                org_profile=profile,
                repo_slug=repo_slug,
                is_public=True,
            )
        except PublicRepoProfile.DoesNotExist as exc:
            raise Http404 from exc

        request.team = profile.team
        request.public_profile = profile
        request.repo_profile = repo_profile
        request.is_public_view = True

        token = set_current_team(profile.team)
        try:
            return view_func(request, *args, **kwargs)
        finally:
            unset_current_team(token)

    return _inner
