"""Tests for data migrations."""

from django.test import TestCase

from apps.metrics.factories import PullRequestFactory, TeamFactory


class TestBackfillJiraKey(TestCase):
    """Tests for backfill_jira_key data migration."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def test_migration_extracts_jira_key_from_pr_title(self):
        """Test that migration extracts Jira key from PR titles."""
        # Arrange - create PRs with Jira keys in titles but empty jira_key field
        pr1 = PullRequestFactory(
            team=self.team,
            title="PROJ-123 Add user authentication",
            jira_key="",
        )
        pr2 = PullRequestFactory(
            team=self.team,
            title="Fix: ABC-456 login issue",
            jira_key="",
        )
        pr3 = PullRequestFactory(
            team=self.team,
            title="[DEV-789] Important feature",
            jira_key="",
        )

        # Import the migration function
        from apps.metrics.migrations.backfill_jira_key import backfill_jira_key

        # Act - run the backfill function
        backfill_jira_key()

        # Assert - jira_key should be extracted from titles
        pr1.refresh_from_db()
        pr2.refresh_from_db()
        pr3.refresh_from_db()

        self.assertEqual(pr1.jira_key, "PROJ-123")
        self.assertEqual(pr2.jira_key, "ABC-456")
        self.assertEqual(pr3.jira_key, "DEV-789")

    def test_migration_skips_prs_with_existing_jira_key(self):
        """Test that migration does not overwrite existing jira_key values."""
        # Arrange - create a PR with jira_key already set
        pr = PullRequestFactory(
            team=self.team,
            title="PROJ-999 Update feature",
            jira_key="ORIGINAL-123",
        )

        # Import the migration function
        from apps.metrics.migrations.backfill_jira_key import backfill_jira_key

        # Act - run the backfill function
        backfill_jira_key()

        # Assert - jira_key should remain unchanged
        pr.refresh_from_db()
        self.assertEqual(pr.jira_key, "ORIGINAL-123")

    def test_migration_leaves_empty_when_no_jira_key_in_title(self):
        """Test that migration leaves jira_key empty if no key found in title."""
        # Arrange - create a PR without a Jira key in title
        pr = PullRequestFactory(
            team=self.team,
            title="Fix the login bug",
            jira_key="",
        )

        # Import the migration function
        from apps.metrics.migrations.backfill_jira_key import backfill_jira_key

        # Act - run the backfill function
        backfill_jira_key()

        # Assert - jira_key should remain empty
        pr.refresh_from_db()
        self.assertEqual(pr.jira_key, "")

    def test_migration_handles_multiple_prs_correctly(self):
        """Test that migration processes multiple PRs in a single run."""
        # Arrange - create multiple PRs with different scenarios
        pr_with_key = PullRequestFactory(
            team=self.team,
            title="PROJ-111 First PR",
            jira_key="",
        )
        pr_without_key = PullRequestFactory(
            team=self.team,
            title="Random PR title",
            jira_key="",
        )
        pr_already_has_key = PullRequestFactory(
            team=self.team,
            title="PROJ-222 Second PR",
            jira_key="EXISTING-333",
        )

        # Import the migration function
        from apps.metrics.migrations.backfill_jira_key import backfill_jira_key

        # Act - run the backfill function
        backfill_jira_key()

        # Assert - each PR should be handled correctly
        pr_with_key.refresh_from_db()
        pr_without_key.refresh_from_db()
        pr_already_has_key.refresh_from_db()

        self.assertEqual(pr_with_key.jira_key, "PROJ-111")
        self.assertEqual(pr_without_key.jira_key, "")
        self.assertEqual(pr_already_has_key.jira_key, "EXISTING-333")

    def test_migration_handles_jira_key_anywhere_in_title(self):
        """Test that migration extracts Jira key regardless of position in title."""
        # Arrange - create PRs with Jira keys in different positions
        pr1 = PullRequestFactory(
            team=self.team,
            title="PROJ-100 at the start",
            jira_key="",
        )
        pr2 = PullRequestFactory(
            team=self.team,
            title="In the middle PROJ-200 of title",
            jira_key="",
        )
        pr3 = PullRequestFactory(
            team=self.team,
            title="At the end PROJ-300",
            jira_key="",
        )

        # Import the migration function
        from apps.metrics.migrations.backfill_jira_key import backfill_jira_key

        # Act - run the backfill function
        backfill_jira_key()

        # Assert - all should extract correctly
        pr1.refresh_from_db()
        pr2.refresh_from_db()
        pr3.refresh_from_db()

        self.assertEqual(pr1.jira_key, "PROJ-100")
        self.assertEqual(pr2.jira_key, "PROJ-200")
        self.assertEqual(pr3.jira_key, "PROJ-300")

    def test_migration_extracts_first_jira_key_when_multiple_present(self):
        """Test that migration extracts only the first Jira key when multiple are present."""
        # Arrange - create a PR with multiple Jira keys
        pr = PullRequestFactory(
            team=self.team,
            title="FIRST-111 and SECOND-222 are both present",
            jira_key="",
        )

        # Import the migration function
        from apps.metrics.migrations.backfill_jira_key import backfill_jira_key

        # Act - run the backfill function
        backfill_jira_key()

        # Assert - should extract only the first key
        pr.refresh_from_db()
        self.assertEqual(pr.jira_key, "FIRST-111")
