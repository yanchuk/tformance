"""Shared PR + child record persistence from FetchedPRFull data.

Used by:
- public_sync.py (GitHub sync for public repos)
- local_reconciliation.py (cache-based reconciliation)

Does NOT replace RealProjectSeeder (which uses Factories for demo data).
"""

import logging
from decimal import Decimal

from django.db import transaction

from apps.metrics.models import Commit, PRCheckRun, PRFile, PRReview, PullRequest, TeamMember
from apps.metrics.services.ai_detector import detect_ai_in_text, detect_ai_reviewer, parse_co_authors

logger = logging.getLogger(__name__)


class PRPersistenceService:
    """Persist PR + child records from FetchedPRFull dataclass data.

    Designed for idempotent operations with ignore_conflicts=True
    on bulk_create to handle reruns safely.
    """

    def __init__(self, team):
        self.team = team
        self._member_cache: dict[str, TeamMember] = {}

    def build_member_cache(self, fetched_prs: list) -> None:
        """Pre-fetch/create all TeamMembers referenced in fetched PRs.

        Populates self._member_cache for fast lookups during persistence.
        """
        logins = set()
        for pr in fetched_prs:
            if pr.author_login:
                logins.add(pr.author_login)
            for review in pr.reviews or []:
                if review.reviewer_login:
                    logins.add(review.reviewer_login)
            for commit in pr.commits or []:
                if commit.author_login:
                    logins.add(commit.author_login)

        if not logins:
            return

        existing = {m.github_username: m for m in TeamMember.objects.filter(team=self.team, github_username__in=logins)}

        missing_logins = logins - existing.keys()
        if missing_logins:
            TeamMember.objects.bulk_create(
                [TeamMember(team=self.team, github_username=login, display_name=login) for login in missing_logins],
                ignore_conflicts=True,
            )
            for m in TeamMember.objects.filter(team=self.team, github_username__in=missing_logins):
                existing[m.github_username] = m

        self._member_cache.update(existing)

    def _resolve_member(self, login: str | None, github_id: int = 0) -> TeamMember | None:
        """Find or create TeamMember with in-memory cache.

        Backfills github_id when a valid one is provided but the existing
        member record has it empty (e.g., first seen as reviewer without ID,
        later seen as PR author with ID).
        """
        if not login:
            return None

        if login in self._member_cache:
            member = self._member_cache[login]
            if github_id and not member.github_id:
                member.github_id = str(github_id)
                member.save(update_fields=["github_id"])
            return member

        member, created = TeamMember.objects.get_or_create(
            team=self.team,
            github_username=login,
            defaults={"display_name": login, "github_id": github_id},
        )
        if not created and github_id and not member.github_id:
            member.github_id = str(github_id)
            member.save(update_fields=["github_id"])

        self._member_cache[login] = member
        return member

    @transaction.atomic
    def create_pr(self, pr_data, github_repo: str) -> PullRequest:
        """Create PR with all children in atomic transaction."""
        author = self._resolve_member(pr_data.author_login, getattr(pr_data, "author_id", 0))

        cycle_time = Decimal(str(round(pr_data.cycle_time_hours, 2))) if pr_data.cycle_time_hours else None
        review_time = Decimal(str(round(pr_data.review_time_hours, 2))) if pr_data.review_time_hours else None

        # AI detection on PR text
        ai_result = detect_ai_in_text(f"{pr_data.title or ''}\n{pr_data.body or ''}")

        state = "merged" if pr_data.is_merged else pr_data.state

        pr = PullRequest.objects.create(  # noqa: TEAM001 - cross-team for public analytics
            team=self.team,
            github_repo=github_repo,
            github_pr_id=pr_data.github_pr_id,
            title=pr_data.title or "",
            body=pr_data.body or "",
            state=state,
            pr_created_at=pr_data.created_at,
            merged_at=pr_data.merged_at,
            first_review_at=pr_data.first_review_at,
            cycle_time_hours=cycle_time,
            review_time_hours=review_time,
            author=author,
            additions=pr_data.additions or 0,
            deletions=pr_data.deletions or 0,
            is_ai_assisted=ai_result["is_ai_assisted"],
            ai_tools_detected=ai_result["ai_tools"],
            is_draft=pr_data.is_draft or False,
            labels=pr_data.labels or [],
            milestone_title=pr_data.milestone_title or "",
            assignees=pr_data.assignees or [],
            linked_issues=pr_data.linked_issues or [],
        )

        self._create_reviews(pr, pr_data)
        self._create_commits(pr, pr_data, github_repo)
        self._create_files(pr, pr_data)
        self._create_check_runs(pr, pr_data)

        return pr

    def update_stale_pr(self, pr: PullRequest, pr_data) -> None:
        """Update only changed core fields via field comparison."""
        updated_fields = []

        def _update_if_changed(field_name, new_value):
            if getattr(pr, field_name) != new_value:
                setattr(pr, field_name, new_value)
                updated_fields.append(field_name)

        _update_if_changed("title", pr_data.title or "")
        _update_if_changed("body", pr_data.body or "")

        state = "merged" if pr_data.is_merged else pr_data.state
        _update_if_changed("state", state)

        _update_if_changed("additions", pr_data.additions or 0)
        _update_if_changed("deletions", pr_data.deletions or 0)
        _update_if_changed("is_draft", getattr(pr_data, "is_draft", False))
        _update_if_changed("labels", getattr(pr_data, "labels", []) or [])
        _update_if_changed("milestone_title", getattr(pr_data, "milestone_title", "") or "")
        _update_if_changed("assignees", getattr(pr_data, "assignees", []) or [])
        _update_if_changed("linked_issues", getattr(pr_data, "linked_issues", []) or [])

        # Update merged_at if it changed
        if pr_data.merged_at and pr_data.merged_at != pr.merged_at:
            pr.merged_at = pr_data.merged_at
            updated_fields.append("merged_at")

        # Recalculate timing if merge timestamp changed
        if "merged_at" in updated_fields or pr.first_review_at is None:
            if pr_data.first_review_at:
                pr.first_review_at = pr_data.first_review_at
                updated_fields.append("first_review_at")
            if pr_data.cycle_time_hours:
                pr.cycle_time_hours = Decimal(str(round(pr_data.cycle_time_hours, 2)))
                updated_fields.append("cycle_time_hours")
            if pr_data.review_time_hours:
                pr.review_time_hours = Decimal(str(round(pr_data.review_time_hours, 2)))
                updated_fields.append("review_time_hours")

        # Re-run AI detection if title/body changed
        if "title" in updated_fields or "body" in updated_fields:
            ai_result = detect_ai_in_text(f"{pr.title}\n{pr.body}")
            pr.is_ai_assisted = ai_result["is_ai_assisted"]
            pr.ai_tools_detected = ai_result["ai_tools"]
            updated_fields.extend(["is_ai_assisted", "ai_tools_detected"])

        if updated_fields:
            pr.save(update_fields=list(set(updated_fields)) + ["updated_at"])

    def repair_partial_pr(self, pr: PullRequest, pr_data, github_repo: str | None = None) -> dict:
        """Add missing children without touching PR core fields.

        Returns dict with counts of added children.
        """
        repo = github_repo or pr.github_repo
        added = {"reviews": 0, "commits": 0, "files": 0, "check_runs": 0}

        added["reviews"] = self._create_reviews(pr, pr_data)
        added["commits"] = self._create_commits(pr, pr_data, repo)
        added["files"] = self._create_files(pr, pr_data)
        added["check_runs"] = self._create_check_runs(pr, pr_data)

        # Update derived timing fields if they were missing
        if pr.first_review_at is None and pr_data.first_review_at:
            pr.first_review_at = pr_data.first_review_at
            update_fields = ["first_review_at", "updated_at"]
            if pr_data.review_time_hours and pr.review_time_hours is None:
                pr.review_time_hours = Decimal(str(round(pr_data.review_time_hours, 2)))
                update_fields.append("review_time_hours")
            pr.save(update_fields=update_fields)

        return added

    def _create_reviews(self, pr: PullRequest, pr_data) -> int:
        """Bulk create reviews with ignore_conflicts. Returns count created."""
        if not pr_data.reviews:
            return 0

        reviews_to_create = []
        for review in pr_data.reviews:
            reviewer = self._resolve_member(review.reviewer_login)
            ai_result = detect_ai_reviewer(review.reviewer_login)

            reviews_to_create.append(
                PRReview(
                    team=self.team,
                    pull_request=pr,
                    github_review_id=review.github_review_id,
                    reviewer=reviewer,
                    state=review.state.lower() if review.state else "commented",
                    body=review.body or "",
                    submitted_at=review.submitted_at,
                    is_ai_review=ai_result["is_ai"],
                    ai_reviewer_type=ai_result["ai_type"],
                )
            )

        if reviews_to_create:
            created = PRReview.objects.bulk_create(reviews_to_create, ignore_conflicts=True)
            return len(created)
        return 0

    def _create_commits(self, pr: PullRequest, pr_data, github_repo: str) -> int:
        """Bulk create commits with ignore_conflicts. Returns count created."""
        if not pr_data.commits:
            return 0

        commits_to_create = []
        for commit in pr_data.commits:
            author = self._resolve_member(commit.author_login) or pr.author
            co_author_result = parse_co_authors(commit.message)

            commits_to_create.append(
                Commit(
                    team=self.team,
                    pull_request=pr,
                    github_sha=commit.sha,
                    github_repo=github_repo,
                    author=author,
                    message=commit.message[:500] if commit.message else "",
                    committed_at=commit.committed_at,
                    additions=commit.additions,
                    deletions=commit.deletions,
                    is_ai_assisted=co_author_result["has_ai_co_authors"],
                    ai_co_authors=co_author_result["ai_co_authors"],
                )
            )

        if commits_to_create:
            created = Commit.objects.bulk_create(commits_to_create, ignore_conflicts=True)
            return len(created)
        return 0

    def _create_files(self, pr: PullRequest, pr_data) -> int:
        """Bulk create files with ignore_conflicts. Returns count created."""
        if not pr_data.files:
            return 0

        files_to_create = []
        for file_data in pr_data.files:
            changes = file_data.additions + file_data.deletions
            files_to_create.append(
                PRFile(
                    team=self.team,
                    pull_request=pr,
                    filename=file_data.filename,
                    status=file_data.status,
                    additions=file_data.additions,
                    deletions=file_data.deletions,
                    changes=changes,
                    file_category=PRFile.categorize_file(file_data.filename),
                )
            )

        if files_to_create:
            created = PRFile.objects.bulk_create(files_to_create, ignore_conflicts=True)
            return len(created)
        return 0

    def _create_check_runs(self, pr: PullRequest, pr_data) -> int:
        """Bulk create check runs with ignore_conflicts. Returns count created."""
        if not pr_data.check_runs:
            return 0

        check_runs_to_create = []
        for cr in pr_data.check_runs:
            duration = None
            if cr.started_at and cr.completed_at:
                duration = int((cr.completed_at - cr.started_at).total_seconds())

            check_runs_to_create.append(
                PRCheckRun(
                    team=self.team,
                    pull_request=pr,
                    github_check_run_id=cr.github_id,
                    name=cr.name,
                    status=cr.status,
                    conclusion=cr.conclusion,
                    started_at=cr.started_at,
                    completed_at=cr.completed_at,
                    duration_seconds=duration,
                )
            )

        if check_runs_to_create:
            created = PRCheckRun.objects.bulk_create(check_runs_to_create, ignore_conflicts=True)
            return len(created)
        return 0
