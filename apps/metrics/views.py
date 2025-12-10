from django.template.response import TemplateResponse

from apps.teams.decorators import login_and_team_required


@login_and_team_required
def home(request, team_slug: str):
    template = "metrics/metrics_home.html#page-content" if request.htmx else "metrics/metrics_home.html"

    return TemplateResponse(request, template, {"active_tab": "metrics"})
