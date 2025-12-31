"""
Views for the Personal PR Notes feature.
"""

from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.metrics.models import PullRequest
from apps.notes.forms import NoteForm
from apps.notes.models import FLAG_CHOICES, PRNote
from apps.teams.decorators import login_and_team_required


def _is_htmx(request):
    """Check if request is from HTMX."""
    return request.headers.get("HX-Request") == "true"


@login_and_team_required
def note_form(request, pr_id):
    """
    Display and handle the note form for a PR.

    GET: Display form (empty or pre-filled if note exists)
    POST: Create or update note
    """
    # Get the PR (must belong to current team)
    try:
        pr = PullRequest.for_team.get(pk=pr_id)
    except PullRequest.DoesNotExist as err:
        raise Http404("Pull request not found") from err

    # Get existing note for this user/PR (if any)
    try:
        note = PRNote.objects.get(user=request.user, pull_request=pr)
        is_edit = True
    except PRNote.DoesNotExist:
        note = None
        is_edit = False

    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.pull_request = pr
            note.save()

            if _is_htmx(request):
                return render(
                    request,
                    "notes/partials/note_success.html",
                    {"note": note, "pr": pr, "is_edit": is_edit},
                )
            # For non-HTMX, redirect to PR list
            return redirect("metrics:pr_list")
        else:
            # Form has errors
            context = {
                "form": form,
                "pr": pr,
                "is_edit": is_edit,
            }
            template = "notes/partials/note_form.html" if _is_htmx(request) else "notes/note_form.html"
            return render(request, template, context)

    # GET request - show the form
    form = NoteForm(instance=note)
    context = {
        "form": form,
        "pr": pr,
        "is_edit": is_edit,
        "note": note,
    }

    template = "notes/partials/note_form.html" if _is_htmx(request) else "notes/note_form.html"
    return render(request, template, context)


@login_and_team_required
def delete_note(request, pr_id):
    """
    Delete a note for a PR.

    Only accepts POST requests.
    Only allows deleting the user's own note.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Get the PR (must belong to current team)
    try:
        pr = PullRequest.for_team.get(pk=pr_id)
    except PullRequest.DoesNotExist as err:
        raise Http404("Pull request not found") from err

    # Get the user's note for this PR
    try:
        note = PRNote.objects.get(user=request.user, pull_request=pr)
    except PRNote.DoesNotExist as err:
        raise Http404("Note not found") from err

    # Delete the note
    note.delete()

    if _is_htmx(request):
        return HttpResponse("")  # Return empty for HTMX swap

    return redirect("metrics:pr_list")


@login_and_team_required
def my_notes(request):
    """
    Display the user's notes with optional filtering.

    Query params:
    - flag: Filter by flag (false_positive, review_later, important, concern)
    - resolved: Filter by resolved status (true/false)
    """
    notes = (
        PRNote.objects.filter(user=request.user)
        .select_related("pull_request", "pull_request__author")
        .order_by("-created_at")
    )

    # Apply flag filter
    flag = request.GET.get("flag")
    if flag:
        notes = notes.filter(flag=flag)

    # Apply resolved filter
    resolved = request.GET.get("resolved")
    if resolved == "true":
        notes = notes.filter(is_resolved=True)
    elif resolved == "false":
        notes = notes.filter(is_resolved=False)

    context = {
        "notes": notes,
        "current_flag": flag,
        "current_resolved": resolved,
        "flag_choices": FLAG_CHOICES,
    }

    return render(request, "notes/my_notes.html", context)


@login_and_team_required
def toggle_resolve(request, note_id):
    """
    Toggle the resolved status of a note.

    Only accepts POST requests.
    Only allows toggling the user's own note.
    """
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Get the user's note
    try:
        note = PRNote.objects.get(pk=note_id, user=request.user)
    except PRNote.DoesNotExist as err:
        raise Http404("Note not found") from err

    # Toggle resolved status
    if note.is_resolved:
        note.is_resolved = False
        note.resolved_at = None
    else:
        note.is_resolved = True
        note.resolved_at = timezone.now()
    note.save()

    if _is_htmx(request):
        return render(
            request,
            "notes/partials/note_row.html",
            {"note": note},
        )

    return redirect("notes:my_notes")


def _get_pr_and_note(pr_id, user):
    """Fetch PR and optional user note."""
    try:
        pr = PullRequest.for_team.get(pk=pr_id)
    except PullRequest.DoesNotExist as err:
        raise Http404("Pull request not found") from err
    try:
        note = PRNote.objects.get(user=user, pull_request=pr)
    except PRNote.DoesNotExist:
        note = None
    return pr, note


@login_and_team_required
def inline_note(request, pr_id):
    """
    Inline note form/preview for PR list.

    GET: Returns form (new) or preview (existing note)
    POST: Creates/updates note and returns preview
    DELETE: Removes note and returns empty response
    """
    pr, note = _get_pr_and_note(pr_id, request.user)

    if request.method == "DELETE":
        if note:
            note.delete()
        return HttpResponse("", status=200)

    if request.method == "POST":
        form = NoteForm(request.POST, instance=note)
        if form.is_valid():
            note = form.save(commit=False)
            note.user = request.user
            note.pull_request = pr
            note.save()
            # Return preview template after save
            return render(
                request,
                "notes/partials/inline_note_preview.html",
                {"pr": pr, "note": note, "form": NoteForm(instance=note)},
            )
        # Return form with errors
        return render(
            request,
            "notes/partials/inline_note_form.html",
            {"pr": pr, "note": note, "form": form},
        )

    # GET: Return preview if note exists, form if not
    template = "notes/partials/inline_note_preview.html" if note else "notes/partials/inline_note_form.html"
    return render(
        request,
        template,
        {"pr": pr, "note": note, "form": NoteForm(instance=note)},
    )
