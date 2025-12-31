"""
Factory Boy factories for metrics models.

Basic Usage:
    from apps.metrics.factories import TeamMemberFactory, PullRequestFactory

    # Create a single instance
    member = TeamMemberFactory()

    # Create with specific attributes
    member = TeamMemberFactory(display_name="John Doe", role="lead")

    # Create multiple instances
    members = TeamMemberFactory.create_batch(5)

    # Build without saving (for unit tests)
    member = TeamMemberFactory.build()

Performance Best Practices:
--------------------------

1. ALWAYS pass team= to related factories to avoid creating duplicate teams:

   # GOOD - all objects share the same team
   team = TeamFactory()
   member = TeamMemberFactory(team=team)
   pr = PullRequestFactory(team=team, author=member)

   # BAD - each factory creates its own team (3 teams created!)
   member = TeamMemberFactory()
   pr = PullRequestFactory()

2. Use create_batch() with explicit team for multiple objects:

   # GOOD - 5 members, 1 team
   team = TeamFactory()
   members = TeamMemberFactory.create_batch(5, team=team)

   # BAD - 5 members, 5 teams (SubFactory creates new team each time)
   members = TeamMemberFactory.create_batch(5)

3. For Django TestCase, use setUpTestData() for class-level sharing:

   class TestSomething(TestCase):
       @classmethod
       def setUpTestData(cls):
           cls.team = TeamFactory()
           cls.members = TeamMemberFactory.create_batch(5, team=cls.team)

       def test_read_only(self):
           # Data created once, reused across all test methods
           assert len(self.members) == 5

4. Pass related objects explicitly instead of letting SubFactory create them:

   # GOOD - explicit control
   pr = PullRequestFactory(team=team, author=member)
   review = PRReviewFactory(team=team, pull_request=pr, reviewer=member2)

   # BAD - SubFactory creates new author (new TeamMember + potentially new Team)
   pr = PullRequestFactory()
   review = PRReviewFactory(pull_request=pr)

5. Use build() for unit tests that don't need DB:

   # GOOD - no database hit
   pr = PullRequestFactory.build(title="Test PR")
   assert detect_ai_patterns(pr.body) == []

   # Avoid create() when you don't need persistence
   pr = PullRequestFactory.create()  # Unnecessary DB write

See conftest.py for shared fixtures: team_with_members, sample_prs, team_context
"""

import random
import uuid
from datetime import timedelta
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.teams.models import Team

from .models import (
    AIUsageDaily,
    Commit,
    DailyInsight,
    Deployment,
    JiraIssue,
    PRCheckRun,
    PRComment,
    PRFile,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    ReviewerCorrelation,
    TeamMember,
    WeeklyMetrics,
)


class TeamFactory(DjangoModelFactory):
    """Factory for Team model.

    Uses UUID-based slugs to avoid collisions in parallel test workers.
    Sequence counters are per-process, so xdist workers all start at 0.
    """

    class Meta:
        model = Team

    name = factory.LazyFunction(lambda: f"Team {uuid.uuid4().hex[:8]}")
    slug = factory.LazyFunction(lambda: f"team-{uuid.uuid4().hex[:12]}")


class TeamMemberFactory(DjangoModelFactory):
    """Factory for TeamMember model.

    Uses Sequence for display_name, email, and github_username to guarantee
    uniqueness and avoid constraint violations in parallel tests.
    """

    class Meta:
        model = TeamMember

    team = factory.SubFactory(TeamFactory)
    # Use Sequence instead of Faker to guarantee unique values across tests
    display_name = factory.Sequence(lambda n: f"Developer {n}")
    email = factory.Sequence(lambda n: f"developer{n}@example.com")
    github_username = factory.Sequence(lambda n: f"developer{n}")
    github_id = factory.Sequence(lambda n: str(10000 + n))
    jira_account_id = factory.Sequence(lambda n: f"jira-{n}")
    slack_user_id = factory.Sequence(lambda n: f"U{n:08d}")
    role = factory.Iterator(["developer", "developer", "developer", "lead"])  # 75% developers
    is_active = True


class PullRequestFactory(DjangoModelFactory):
    """Factory for PullRequest model.

    Performance: Always pass team= and author= explicitly to avoid creating
    unnecessary Team and TeamMember objects via SubFactory cascade.

    Example:
        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, author=member)  # GOOD
        pr = PullRequestFactory()  # BAD - creates new team + author
    """

    class Meta:
        model = PullRequest

    team = factory.SubFactory(TeamFactory)
    github_pr_id = factory.Sequence(lambda n: n + 1)
    github_repo = factory.Iterator(["org/frontend", "org/backend", "org/api", "org/infra"])
    title = factory.Faker("sentence", nb_words=6)
    author = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    state = factory.Iterator(["merged", "merged", "merged", "open", "closed"])  # 60% merged

    pr_created_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))
    merged_at = factory.LazyAttribute(
        lambda o: o.pr_created_at + timedelta(hours=random.randint(2, 72)) if o.state == "merged" else None
    )
    first_review_at = factory.LazyAttribute(
        lambda o: o.pr_created_at + timedelta(hours=random.randint(1, 24)) if o.state != "open" else None
    )

    cycle_time_hours = factory.LazyAttribute(
        lambda o: Decimal(str(round((o.merged_at - o.pr_created_at).total_seconds() / 3600, 2)))
        if o.merged_at
        else None
    )
    review_time_hours = factory.LazyAttribute(
        lambda o: Decimal(str(round((o.first_review_at - o.pr_created_at).total_seconds() / 3600, 2)))
        if o.first_review_at
        else None
    )

    additions = factory.LazyFunction(lambda: random.randint(10, 500))
    deletions = factory.LazyFunction(lambda: random.randint(5, 200))
    is_revert = factory.LazyFunction(lambda: random.random() < 0.05)  # 5% reverts
    is_hotfix = factory.LazyFunction(lambda: random.random() < 0.1)  # 10% hotfixes
    jira_key = ""

    # AI tracking fields
    body = ""
    is_ai_assisted = False
    ai_tools_detected = factory.LazyFunction(list)


class PRReviewFactory(DjangoModelFactory):
    """Factory for PRReview model.

    Performance: Pass team=, pull_request=, and reviewer= explicitly.
    Without these, SubFactory creates new objects for each field.

    Example:
        team = TeamFactory()
        pr = PullRequestFactory(team=team, author=member1)
        review = PRReviewFactory(team=team, pull_request=pr, reviewer=member2)  # GOOD
        review = PRReviewFactory()  # BAD - creates team, PR, author, reviewer
    """

    class Meta:
        model = PRReview

    team = factory.SubFactory(TeamFactory)
    pull_request = factory.SubFactory(PullRequestFactory, team=factory.SelfAttribute("..team"))
    reviewer = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    state = factory.Iterator(["approved", "approved", "changes_requested", "commented"])
    body = ""
    submitted_at = factory.LazyAttribute(
        lambda o: o.pull_request.pr_created_at + timedelta(hours=random.randint(1, 24))
        if o.pull_request.pr_created_at
        else timezone.now()
    )

    # AI tracking fields
    is_ai_review = False
    ai_reviewer_type = ""


class PRCommentFactory(DjangoModelFactory):
    """Factory for PRComment model."""

    class Meta:
        model = PRComment

    team = factory.SubFactory(TeamFactory)
    pull_request = factory.SubFactory(PullRequestFactory, team=factory.SelfAttribute("..team"))
    github_comment_id = factory.Sequence(lambda n: 200000 + n)
    author = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    body = factory.Faker("paragraph", nb_sentences=3)
    comment_type = factory.Iterator(["issue", "issue", "review"])  # 66% issue comments
    path = factory.LazyAttribute(
        lambda o: factory.Iterator(["src/app.py", "src/utils.py", "README.md", "tests/test_models.py"]).evaluate(
            None, None, None
        )
        if o.comment_type == "review"
        else None
    )
    line = factory.LazyAttribute(lambda o: random.randint(1, 500) if o.comment_type == "review" else None)
    in_reply_to_id = None  # Most comments are not replies
    comment_created_at = factory.LazyAttribute(
        lambda o: o.pull_request.pr_created_at + timedelta(hours=random.randint(1, 48))
        if o.pull_request.pr_created_at
        else timezone.now()
    )
    comment_updated_at = factory.LazyAttribute(
        lambda o: o.comment_created_at + timedelta(hours=random.randint(0, 12))
        if random.random() < 0.2
        else None  # 20% of comments are edited
    )


class PRCheckRunFactory(DjangoModelFactory):
    """Factory for PRCheckRun model."""

    class Meta:
        model = PRCheckRun

    team = factory.SubFactory(TeamFactory)
    pull_request = factory.SubFactory(PullRequestFactory, team=factory.SelfAttribute("..team"))
    github_check_run_id = factory.Sequence(lambda n: 100000 + n)
    name = factory.Iterator(["pytest", "eslint", "build", "deploy", "type-check", "integration-tests"])
    status = factory.Iterator(["completed", "completed", "completed", "in_progress"])
    conclusion = factory.LazyAttribute(
        lambda o: random.choice(["success", "success", "success", "failure", "skipped"])
        if o.status == "completed"
        else None
    )
    started_at = factory.LazyAttribute(
        lambda o: o.pull_request.pr_created_at + timedelta(minutes=random.randint(1, 30))
        if o.pull_request.pr_created_at
        else timezone.now() - timedelta(minutes=random.randint(1, 30))
    )
    completed_at = factory.LazyAttribute(
        lambda o: o.started_at + timedelta(minutes=random.randint(1, 15)) if o.status == "completed" else None
    )
    duration_seconds = factory.LazyAttribute(
        lambda o: int((o.completed_at - o.started_at).total_seconds()) if o.completed_at and o.started_at else None
    )


class CommitFactory(DjangoModelFactory):
    """Factory for Commit model."""

    class Meta:
        model = Commit

    team = factory.SubFactory(TeamFactory)
    github_sha = factory.LazyFunction(lambda: "".join(random.choices("0123456789abcdef", k=40)))
    github_repo = factory.Iterator(["org/frontend", "org/backend", "org/api", "org/infra"])
    author = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    message = factory.Faker("sentence", nb_words=8)
    committed_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(1, 30)))
    additions = factory.LazyFunction(lambda: random.randint(5, 200))
    deletions = factory.LazyFunction(lambda: random.randint(2, 100))
    pull_request = None  # Often standalone commits

    # AI tracking fields
    is_ai_assisted = False
    ai_co_authors = factory.LazyFunction(list)


class DeploymentFactory(DjangoModelFactory):
    """Factory for Deployment model."""

    class Meta:
        model = Deployment

    team = factory.SubFactory(TeamFactory)
    github_deployment_id = factory.Sequence(lambda n: 100000 + n)
    github_repo = factory.Iterator(["org/frontend", "org/backend", "org/api", "org/infra"])
    environment = factory.Iterator(["production", "production", "staging", "development"])  # 50% production
    status = factory.Iterator(["success", "success", "success", "failure", "pending"])  # 60% success
    creator = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    deployed_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=random.randint(1, 168)))
    pull_request = None  # Optional FK
    sha = factory.LazyFunction(lambda: "".join(random.choices("0123456789abcdef", k=40)))


class PRFileFactory(DjangoModelFactory):
    """Factory for PRFile model - files changed in a pull request."""

    class Meta:
        model = PRFile

    team = factory.SubFactory(TeamFactory)
    pull_request = factory.SubFactory("apps.metrics.factories.PullRequestFactory", team=factory.SelfAttribute("..team"))
    filename = factory.LazyFunction(
        lambda: random.choice(
            [
                f"src/components/{random.choice(['Button', 'Modal', 'Form', 'Card'])}.tsx",
                f"apps/{random.choice(['users', 'metrics', 'teams'])}/views.py",
                f"apps/{random.choice(['users', 'metrics'])}/tests/test_views.py",
                f"docs/{random.choice(['setup', 'api', 'deployment'])}.md",
                ".github/workflows/ci.yml",
            ]
        )
    )
    status = factory.Iterator(["modified", "modified", "modified", "added", "removed"])  # Most files are modified
    additions = factory.LazyFunction(lambda: random.randint(5, 200))
    deletions = factory.LazyFunction(lambda: random.randint(0, 100))
    changes = factory.LazyAttribute(lambda o: o.additions + o.deletions)
    file_category = factory.LazyAttribute(lambda o: PRFile.categorize_file(o.filename))


class JiraIssueFactory(DjangoModelFactory):
    """Factory for JiraIssue model."""

    class Meta:
        model = JiraIssue

    team = factory.SubFactory(TeamFactory)
    jira_key = factory.Sequence(lambda n: f"PROJ-{n + 100}")
    jira_id = factory.Sequence(lambda n: str(20000 + n))
    summary = factory.Faker("sentence", nb_words=8)
    issue_type = factory.Iterator(["Story", "Story", "Bug", "Task", "Subtask"])
    status = factory.Iterator(["Done", "Done", "In Progress", "To Do", "In Review"])
    assignee = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    story_points = factory.LazyFunction(lambda: Decimal(str(random.choice([1, 2, 3, 5, 8, 13]))))
    sprint_id = factory.Sequence(lambda n: str(100 + (n % 10)))
    sprint_name = factory.LazyAttribute(lambda o: f"Sprint {o.sprint_id}")
    issue_created_at = factory.LazyFunction(lambda: timezone.now() - timedelta(days=random.randint(7, 60)))
    resolved_at = factory.LazyAttribute(
        lambda o: o.issue_created_at + timedelta(days=random.randint(1, 14)) if o.status == "Done" else None
    )
    cycle_time_hours = factory.LazyAttribute(
        lambda o: Decimal(str(round((o.resolved_at - o.issue_created_at).total_seconds() / 3600, 2)))
        if o.resolved_at
        else None
    )


class AIUsageDailyFactory(DjangoModelFactory):
    """Factory for AIUsageDaily model."""

    class Meta:
        model = AIUsageDaily

    team = factory.SubFactory(TeamFactory)
    member = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    date = factory.LazyFunction(lambda: (timezone.now() - timedelta(days=random.randint(0, 30))).date())
    source = factory.Iterator(["copilot", "copilot", "cursor"])
    active_hours = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(1, 8), 2))))
    suggestions_shown = factory.LazyFunction(lambda: random.randint(50, 500))
    suggestions_accepted = factory.LazyAttribute(lambda o: int(o.suggestions_shown * random.uniform(0.2, 0.5)))
    acceptance_rate = factory.LazyAttribute(
        lambda o: Decimal(str(round(o.suggestions_accepted / o.suggestions_shown * 100, 2)))
        if o.suggestions_shown > 0
        else Decimal("0")
    )


class PRSurveyFactory(DjangoModelFactory):
    """Factory for PRSurvey model."""

    class Meta:
        model = PRSurvey

    team = factory.SubFactory(TeamFactory)
    pull_request = factory.SubFactory(PullRequestFactory, team=factory.SelfAttribute("..team"))
    author = factory.LazyAttribute(lambda o: o.pull_request.author)
    author_ai_assisted = factory.LazyFunction(lambda: random.choice([True, False, None]))
    author_responded_at = factory.LazyAttribute(
        lambda o: timezone.now() - timedelta(hours=random.randint(1, 48)) if o.author_ai_assisted is not None else None
    )
    author_response_source = factory.LazyAttribute(
        lambda o: random.choice(["github", "slack", "web"]) if o.author_ai_assisted is not None else None
    )
    ai_modification_effort = factory.LazyAttribute(
        lambda o: random.choice(["none", "minor", "moderate", "major"]) if o.author_ai_assisted else None
    )
    token_expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(days=7))


class PRSurveyReviewFactory(DjangoModelFactory):
    """Factory for PRSurveyReview model."""

    class Meta:
        model = PRSurveyReview

    team = factory.SubFactory(TeamFactory)
    survey = factory.SubFactory(PRSurveyFactory, team=factory.SelfAttribute("..team"))
    reviewer = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    quality_rating = factory.Iterator([1, 2, 2, 3, 3, 3])  # Skew toward higher ratings
    ai_guess = factory.LazyFunction(lambda: random.choice([True, False]))
    guess_correct = factory.LazyAttribute(
        lambda o: o.ai_guess == o.survey.author_ai_assisted if o.survey.author_ai_assisted is not None else None
    )
    responded_at = factory.LazyFunction(lambda: timezone.now() - timedelta(hours=random.randint(1, 72)))
    response_source = factory.LazyFunction(lambda: random.choice(["github", "slack", "web"]))


class WeeklyMetricsFactory(DjangoModelFactory):
    """Factory for WeeklyMetrics model."""

    class Meta:
        model = WeeklyMetrics

    team = factory.SubFactory(TeamFactory)
    member = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    week_start = factory.LazyFunction(
        lambda: (timezone.now() - timedelta(days=random.randint(0, 8) * 7)).date()
        - timedelta(days=(timezone.now() - timedelta(days=random.randint(0, 8) * 7)).weekday())
    )

    # Delivery metrics
    prs_merged = factory.LazyFunction(lambda: random.randint(2, 10))
    avg_cycle_time_hours = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(8, 72), 2))))
    avg_review_time_hours = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(2, 24), 2))))
    commits_count = factory.LazyFunction(lambda: random.randint(10, 50))
    lines_added = factory.LazyFunction(lambda: random.randint(200, 2000))
    lines_removed = factory.LazyFunction(lambda: random.randint(100, 1000))

    # Quality metrics
    revert_count = factory.LazyFunction(lambda: random.choice([0, 0, 0, 0, 1]))  # Mostly 0
    hotfix_count = factory.LazyFunction(lambda: random.choice([0, 0, 0, 1, 1, 2]))

    # Jira metrics
    story_points_completed = factory.LazyFunction(lambda: Decimal(str(random.choice([5, 8, 13, 21]))))
    issues_resolved = factory.LazyFunction(lambda: random.randint(3, 12))

    # AI metrics
    ai_assisted_prs = factory.LazyAttribute(lambda o: random.randint(0, o.prs_merged))

    # Survey metrics
    avg_quality_rating = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(2.0, 3.0), 2))))
    surveys_completed = factory.LazyAttribute(lambda o: random.randint(0, o.prs_merged))
    guess_accuracy = factory.LazyFunction(lambda: Decimal(str(round(random.uniform(40, 80), 2))))


class ReviewerCorrelationFactory(DjangoModelFactory):
    """Factory for ReviewerCorrelation model."""

    class Meta:
        model = ReviewerCorrelation

    team = factory.SubFactory(TeamFactory)
    reviewer_1 = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    reviewer_2 = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
    prs_reviewed_together = factory.LazyFunction(lambda: random.randint(5, 30))
    agreements = factory.LazyAttribute(lambda o: int(o.prs_reviewed_together * random.uniform(0.6, 0.95)))
    disagreements = factory.LazyAttribute(lambda o: o.prs_reviewed_together - o.agreements)


class DailyInsightFactory(DjangoModelFactory):
    """Factory for DailyInsight model."""

    class Meta:
        model = DailyInsight

    team = factory.SubFactory(TeamFactory)
    date = factory.LazyFunction(lambda: (timezone.now() - timedelta(days=random.randint(0, 30))).date())
    category = factory.Iterator(["trend", "anomaly", "comparison", "action"])
    priority = factory.Iterator(["high", "medium", "low"])
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph", nb_sentences=2)
    metric_type = factory.Iterator(["cycle_time", "review_time", "pr_size", "review_rounds"])
    metric_value = factory.LazyFunction(
        lambda: {
            "current_value": round(random.uniform(10, 100), 2),
            "previous_value": round(random.uniform(10, 100), 2),
            "change_percent": round(random.uniform(-50, 50), 2),
        }
    )
    comparison_period = factory.Iterator(["week_over_week", "month_over_month", ""])
    is_dismissed = False
    dismissed_at = None
