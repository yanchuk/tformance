"""
Management command to shift demo data dates for a team.

Shifts all date-based fields forward so data falls within dashboard
time windows (7/30/90 days).

Usage:
    python manage.py fix_gumroad_dates --team Gumroad --days 68
    python manage.py fix_gumroad_dates --team Gumroad --dry-run
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.metrics.models import (
    AIUsageDaily,
    Commit,
    PRCheckRun,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    WeeklyMetrics,
)
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Shift demo data dates to fall within dashboard windows"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            default="Gumroad",
            help="Team name to shift dates for",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=68,
            help="Number of days to shift forward (default: 68)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        team_name = options["team"]
        days_delta = timedelta(days=options["days"])
        dry_run = options["dry_run"]

        try:
            team = Team.objects.get(name=team_name)
        except Team.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Team '{team_name}' not found"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        self.stdout.write(f"Shifting dates for team '{team_name}' by {options['days']} days")

        # Shift PRs
        prs = PullRequest.objects.filter(team=team)
        pr_count = 0
        for pr in prs:
            changed = False
            if pr.merged_at:
                pr.merged_at += days_delta
                changed = True
            if pr.pr_created_at:
                pr.pr_created_at += days_delta
                changed = True
            if pr.first_review_at:
                pr.first_review_at += days_delta
                changed = True
            if changed and not dry_run:
                pr.save(update_fields=["merged_at", "pr_created_at", "first_review_at"])
                pr_count += 1
            elif changed:
                pr_count += 1
        self.stdout.write(f"  PRs: {pr_count} shifted")

        # Shift Reviews
        reviews = PRReview.objects.filter(team=team)
        review_count = 0
        for review in reviews:
            if review.submitted_at:
                review.submitted_at += days_delta
                if not dry_run:
                    review.save(update_fields=["submitted_at"])
                review_count += 1
        self.stdout.write(f"  Reviews: {review_count} shifted")

        # Shift Commits
        commits = Commit.objects.filter(team=team)
        commit_count = 0
        for commit in commits:
            if commit.committed_at:
                commit.committed_at += days_delta
                if not dry_run:
                    commit.save(update_fields=["committed_at"])
                commit_count += 1
        self.stdout.write(f"  Commits: {commit_count} shifted")

        # Shift Check Runs
        check_runs = PRCheckRun.objects.filter(team=team)
        check_count = 0
        for check in check_runs:
            changed = False
            if check.started_at:
                check.started_at += days_delta
                changed = True
            if check.completed_at:
                check.completed_at += days_delta
                changed = True
            if changed and not dry_run:
                check.save(update_fields=["started_at", "completed_at"])
                check_count += 1
            elif changed:
                check_count += 1
        self.stdout.write(f"  Check Runs: {check_count} shifted")

        # Shift Surveys
        surveys = PRSurvey.objects.filter(team=team)
        survey_count = 0
        for survey in surveys:
            changed = False
            if survey.author_responded_at:
                survey.author_responded_at += days_delta
                changed = True
            if changed and not dry_run:
                survey.save(update_fields=["author_responded_at"])
                survey_count += 1
            elif changed:
                survey_count += 1
        self.stdout.write(f"  Surveys: {survey_count} shifted")

        # Shift Survey Reviews
        survey_reviews = PRSurveyReview.objects.filter(survey__team=team)
        sr_count = 0
        for sr in survey_reviews:
            if sr.responded_at:
                sr.responded_at += days_delta
                if not dry_run:
                    sr.save(update_fields=["responded_at"])
                sr_count += 1
        self.stdout.write(f"  Survey Reviews: {sr_count} shifted")

        # Shift WeeklyMetrics
        weekly = WeeklyMetrics.objects.filter(team=team)
        weekly_count = 0
        for wm in weekly:
            wm.week_start += days_delta
            if not dry_run:
                wm.save(update_fields=["week_start"])
            weekly_count += 1
        self.stdout.write(f"  Weekly Metrics: {weekly_count} shifted")

        # Shift AI Usage Daily
        ai_usage = AIUsageDaily.objects.filter(team=team)
        ai_count = 0
        for au in ai_usage:
            au.date += days_delta
            if not dry_run:
                au.save(update_fields=["date"])
            ai_count += 1
        self.stdout.write(f"  AI Usage Daily: {ai_count} shifted")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete - no changes saved"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully shifted all dates by {options['days']} days"))
