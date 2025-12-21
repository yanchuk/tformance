from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    JiraIssue,
    TeamMember,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


class TestJiraIssueModel(TestCase):
    """Tests for JiraIssue model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.assignee = TeamMember.objects.create(
            team=self.team1, display_name="Alice Developer", jira_account_id="alice-jira-123"
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_jira_issue_creation_with_required_fields(self):
        """Test that JiraIssue can be created with required fields (jira_key, jira_id, team)."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-123", jira_id="10001")
        self.assertEqual(issue.jira_key, "PROJ-123")
        self.assertEqual(issue.jira_id, "10001")
        self.assertEqual(issue.team, self.team1)
        self.assertIsNotNone(issue.pk)

    def test_jira_issue_creation_with_all_fields(self):
        """Test that JiraIssue can be created with all fields."""
        created = django_timezone.now()
        resolved = django_timezone.now()

        issue = JiraIssue.objects.create(
            team=self.team1,
            jira_key="PROJ-456",
            jira_id="10002",
            summary="Implement new feature",
            issue_type="Story",
            status="Done",
            assignee=self.assignee,
            story_points=Decimal("5.0"),
            sprint_id="sprint-100",
            sprint_name="Sprint 10",
            issue_created_at=created,
            resolved_at=resolved,
            cycle_time_hours=Decimal("72.50"),
        )
        self.assertEqual(issue.jira_key, "PROJ-456")
        self.assertEqual(issue.jira_id, "10002")
        self.assertEqual(issue.summary, "Implement new feature")
        self.assertEqual(issue.issue_type, "Story")
        self.assertEqual(issue.status, "Done")
        self.assertEqual(issue.assignee, self.assignee)
        self.assertEqual(issue.story_points, Decimal("5.0"))
        self.assertEqual(issue.sprint_id, "sprint-100")
        self.assertEqual(issue.sprint_name, "Sprint 10")
        self.assertEqual(issue.issue_created_at, created)
        self.assertEqual(issue.resolved_at, resolved)
        self.assertEqual(issue.cycle_time_hours, Decimal("72.50"))

    def test_unique_constraint_team_jira_id_enforced(self):
        """Test that unique constraint on (team, jira_id) is enforced."""
        JiraIssue.objects.create(team=self.team1, jira_key="PROJ-100", jira_id="unique-jira-1")
        # Attempt to create another issue with same team and jira_id
        with self.assertRaises(IntegrityError):
            JiraIssue.objects.create(team=self.team1, jira_key="PROJ-101", jira_id="unique-jira-1")

    def test_same_jira_id_allowed_for_different_teams(self):
        """Test that same jira_id is allowed for different teams."""
        issue1 = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-200", jira_id="shared-jira-1")
        issue2 = JiraIssue.objects.create(team=self.team2, jira_key="PROJ-200", jira_id="shared-jira-1")
        self.assertEqual(issue1.jira_id, issue2.jira_id)
        self.assertNotEqual(issue1.team, issue2.team)

    def test_jira_issue_assignee_fk_with_set_null(self):
        """Test that JiraIssue.assignee FK uses SET_NULL when TeamMember is deleted."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-300", jira_id="10003", assignee=self.assignee)
        self.assertEqual(issue.assignee, self.assignee)

        # Delete the assignee
        self.assignee.delete()

        # Refresh issue from database
        issue.refresh_from_db()
        self.assertIsNone(issue.assignee)

    def test_jira_issue_assignee_can_be_null(self):
        """Test that JiraIssue.assignee can be null (unassigned)."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-301", jira_id="10004")
        self.assertIsNone(issue.assignee)

    def test_jira_issue_story_points_can_be_decimal(self):
        """Test that JiraIssue.story_points can be decimal values (0.5, 1.5, 3.0, etc.)."""
        issue_half = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-400", jira_id="10005", story_points=Decimal("0.5")
        )
        self.assertEqual(issue_half.story_points, Decimal("0.5"))

        issue_one_half = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-401", jira_id="10006", story_points=Decimal("1.5")
        )
        self.assertEqual(issue_one_half.story_points, Decimal("1.5"))

        issue_three = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-402", jira_id="10007", story_points=Decimal("3.0")
        )
        self.assertEqual(issue_three.story_points, Decimal("3.0"))

    def test_jira_issue_story_points_can_be_null(self):
        """Test that JiraIssue.story_points can be null (not estimated)."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-403", jira_id="10008")
        self.assertIsNone(issue.story_points)

    def test_jira_issue_synced_at_auto_updates_on_save(self):
        """Test that JiraIssue.synced_at auto-updates when model is saved."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-500", jira_id="10009")
        original_synced_at = issue.synced_at
        self.assertIsNotNone(original_synced_at)

        # Update and save
        issue.status = "In Progress"
        issue.save()

        # Refresh from database
        issue.refresh_from_db()
        self.assertGreaterEqual(issue.synced_at, original_synced_at)

    def test_jira_issue_for_team_manager_filters_by_current_team(self):
        """Test that JiraIssue.for_team manager filters by current team context."""
        # Create issues for both teams
        issue1 = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-600", jira_id="10010")
        issue2 = JiraIssue.objects.create(team=self.team2, jira_key="PROJ-601", jira_id="10011")

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_issues = list(JiraIssue.for_team.all())
        self.assertEqual(len(team1_issues), 1)
        self.assertEqual(team1_issues[0].pk, issue1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_issues = list(JiraIssue.for_team.all())
        self.assertEqual(len(team2_issues), 1)
        self.assertEqual(team2_issues[0].pk, issue2.pk)

    def test_jira_issue_for_team_manager_with_context_manager(self):
        """Test that JiraIssue.for_team works with context manager."""
        # Create issues for both teams
        JiraIssue.objects.create(team=self.team1, jira_key="PROJ-700", jira_id="10012")
        JiraIssue.objects.create(team=self.team2, jira_key="PROJ-701", jira_id="10013")

        with current_team(self.team1):
            self.assertEqual(JiraIssue.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(JiraIssue.for_team.count(), 1)

    def test_jira_issue_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that JiraIssue.for_team returns empty queryset when no team is set."""
        JiraIssue.objects.create(team=self.team1, jira_key="PROJ-800", jira_id="10014")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(JiraIssue.for_team.count(), 0)

    def test_jira_issue_str_returns_jira_key(self):
        """Test that JiraIssue.__str__ returns jira_key."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-900", jira_id="10015")
        self.assertEqual(str(issue), "PROJ-900")

    def test_jira_issue_has_created_at_from_base_model(self):
        """Test that JiraIssue inherits created_at from BaseModel."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1000", jira_id="10016")
        self.assertIsNotNone(issue.created_at)

    def test_jira_issue_has_updated_at_from_base_model(self):
        """Test that JiraIssue inherits updated_at from BaseModel."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1001", jira_id="10017")
        self.assertIsNotNone(issue.updated_at)

    def test_jira_issue_updated_at_changes_on_save(self):
        """Test that updated_at timestamp changes when JiraIssue is saved."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1002", jira_id="10018")
        original_updated_at = issue.updated_at

        # Update and save
        issue.summary = "Updated summary"
        issue.save()

        # Refresh from database
        issue.refresh_from_db()
        self.assertGreater(issue.updated_at, original_updated_at)

    def test_jira_issue_has_team_foreign_key_from_base_team_model(self):
        """Test that JiraIssue has team ForeignKey from BaseTeamModel."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1003", jira_id="10019")
        self.assertEqual(issue.team, self.team1)
        self.assertIsInstance(issue.team, Team)

    def test_jira_issue_issue_type_choices(self):
        """Test that JiraIssue.issue_type can store different issue types."""
        story = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1100", jira_id="10020", issue_type="Story")
        self.assertEqual(story.issue_type, "Story")

        bug = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1101", jira_id="10021", issue_type="Bug")
        self.assertEqual(bug.issue_type, "Bug")

        task = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1102", jira_id="10022", issue_type="Task")
        self.assertEqual(task.issue_type, "Task")

        epic = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1103", jira_id="10023", issue_type="Epic")
        self.assertEqual(epic.issue_type, "Epic")

    def test_jira_issue_status_choices(self):
        """Test that JiraIssue.status can store different status values."""
        todo = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1200", jira_id="10024", status="To Do")
        self.assertEqual(todo.status, "To Do")

        in_progress = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-1201", jira_id="10025", status="In Progress"
        )
        self.assertEqual(in_progress.status, "In Progress")

        done = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1202", jira_id="10026", status="Done")
        self.assertEqual(done.status, "Done")

    def test_jira_issue_verbose_name(self):
        """Test that JiraIssue has correct verbose_name."""
        self.assertEqual(JiraIssue._meta.verbose_name, "Jira Issue")

    def test_jira_issue_verbose_name_plural(self):
        """Test that JiraIssue has correct verbose_name_plural."""
        self.assertEqual(JiraIssue._meta.verbose_name_plural, "Jira Issues")


class TestJiraIssuePRLinking(TestCase):
    """Tests for JiraIssue-PullRequest bidirectional linking via jira_key."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.metrics.factories import TeamFactory

        self.team1 = TeamFactory()
        self.team2 = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_related_prs_returns_prs_with_matching_jira_key(self):
        """Test that related_prs returns PRs with matching jira_key."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-123"
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-123" (same team)
        pr_matching = PullRequestFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-456" (same team, different key)
        pr_different = PullRequestFactory(team=self.team1, jira_key="PROJ-456")

        # Assert related_prs contains only the matching PR
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0].pk, pr_matching.pk)
        self.assertNotIn(pr_different, related)

    def test_related_prs_returns_empty_queryset_when_no_matches(self):
        """Test that related_prs returns empty queryset when no matches."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-789"
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-789")

        # Create PR with different jira_key
        PullRequestFactory(team=self.team1, jira_key="PROJ-999")

        # Assert related_prs is empty
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 0)

    def test_related_prs_respects_team_isolation(self):
        """Test that related_prs respects team isolation."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-123" in team1
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-123" in team1
        pr_team1 = PullRequestFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-123" in team2 (different team!)
        pr_team2 = PullRequestFactory(team=self.team2, jira_key="PROJ-123")

        # Assert related_prs only contains the PR from team1
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0].pk, pr_team1.pk)
        self.assertNotIn(pr_team2, related)

    def test_related_prs_returns_multiple_prs_for_same_jira_key(self):
        """Test that related_prs returns multiple PRs for same jira_key."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-100"
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-100")

        # Create 3 PRs all with jira_key="PROJ-100"
        pr1 = PullRequestFactory(team=self.team1, jira_key="PROJ-100")
        pr2 = PullRequestFactory(team=self.team1, jira_key="PROJ-100")
        pr3 = PullRequestFactory(team=self.team1, jira_key="PROJ-100")

        # Assert related_prs contains all 3 PRs
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 3)
        self.assertIn(pr1, related)
        self.assertIn(pr2, related)
        self.assertIn(pr3, related)
