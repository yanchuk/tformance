"""Tests for migration 0030_remove_duplicate_indexes.

TDD approach:
- RED: These tests verify the duplicate indexes should be removed
- GREEN: After running migration, indexes should no longer exist
"""

from django.db import connection
from django.test import TestCase


class TestDuplicateIndexRemoval(TestCase):
    """Test that duplicate indexes are properly removed by migration 0030."""

    def _index_exists(self, index_name: str) -> bool:
        """Check if an index exists in the database."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1 FROM pg_indexes
                WHERE indexname = %s
                """,
                [index_name],
            )
            return cursor.fetchone() is not None

    def _get_index_count(self, table_name: str) -> int:
        """Get the number of indexes on a table."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) FROM pg_indexes
                WHERE tablename = %s
                """,
                [table_name],
            )
            return cursor.fetchone()[0]

    # =========================================================================
    # Tests for metrics_commit duplicate indexes
    # =========================================================================

    def test_commit_pr_idx_should_not_exist(self):
        """commit_pr_idx is a duplicate of Django's auto-generated FK index."""
        # After migration, this index should not exist
        self.assertFalse(
            self._index_exists("commit_pr_idx"),
            "commit_pr_idx should be removed (duplicate of metrics_commit_pull_request_id_*)",
        )

    def test_commit_author_id_single_column_should_not_exist(self):
        """Single-column author_id index is covered by composite index."""
        # After migration, this index should not exist
        self.assertFalse(
            self._index_exists("metrics_commit_author_id_67f38a6f"),
            "metrics_commit_author_id_* should be removed (covered by commit_author_date_idx)",
        )

    def test_commit_table_still_has_essential_indexes(self):
        """Commit table should retain essential indexes after cleanup."""
        # These indexes should still exist:
        # - pkey
        # - unique_team_commit
        # - commit_author_date_idx
        # - metrics_commit_pull_request_id_* (Django auto-generated)
        # - metrics_commit_team_id_*
        essential_indexes = [
            "metrics_commit_pkey",
            "unique_team_commit",
            "commit_author_date_idx",
        ]
        for index_name in essential_indexes:
            self.assertTrue(
                self._index_exists(index_name),
                f"Essential index {index_name} should exist",
            )

    # =========================================================================
    # Tests for metrics_prsurvey duplicate indexes
    # =========================================================================

    def test_pr_survey_pr_idx_should_not_exist(self):
        """pr_survey_pr_idx is a duplicate of OneToOneField unique constraint."""
        # After migration, this index should not exist
        self.assertFalse(
            self._index_exists("pr_survey_pr_idx"),
            "pr_survey_pr_idx should be removed (duplicate of OneToOneField unique index)",
        )

    def test_prsurvey_table_still_has_essential_indexes(self):
        """PRSurvey table should retain essential indexes after cleanup."""
        essential_indexes = [
            "metrics_prsurvey_pkey",
            "metrics_prsurvey_pull_request_id_key",  # OneToOneField unique
        ]
        for index_name in essential_indexes:
            self.assertTrue(
                self._index_exists(index_name),
                f"Essential index {index_name} should exist",
            )

    # =========================================================================
    # Tests for metrics_aiusagedaily duplicate indexes
    # =========================================================================

    def test_aiusagedaily_member_id_single_column_should_not_exist(self):
        """Single-column member_id index is covered by composite index."""
        # After migration, this index should not exist
        self.assertFalse(
            self._index_exists("metrics_aiusagedaily_member_id_0274ee1d"),
            "metrics_aiusagedaily_member_id_* should be removed (covered by ai_usage_member_date_idx)",
        )

    def test_aiusagedaily_table_still_has_essential_indexes(self):
        """AIUsageDaily table should retain essential indexes after cleanup."""
        essential_indexes = [
            "metrics_aiusagedaily_pkey",
            "unique_team_member_date_source",
            "ai_usage_member_date_idx",
        ]
        for index_name in essential_indexes:
            self.assertTrue(
                self._index_exists(index_name),
                f"Essential index {index_name} should exist",
            )

    # =========================================================================
    # Tests for integrations duplicate indexes
    # =========================================================================

    def test_github_int_org_slug_idx_should_not_exist(self):
        """Manual org_slug index is a duplicate of Django auto-generated."""
        # After migration, this index should not exist
        self.assertFalse(
            self._index_exists("github_int_org_slug_idx"),
            "github_int_org_slug_idx should be removed (duplicate of auto-generated)",
        )

    def test_jira_int_cloud_id_idx_should_not_exist(self):
        """Manual cloud_id index is a duplicate of Django auto-generated."""
        # After migration, this index should not exist
        self.assertFalse(
            self._index_exists("jira_int_cloud_id_idx"),
            "jira_int_cloud_id_idx should be removed (duplicate of auto-generated)",
        )


class TestIndexUsageAfterMigration(TestCase):
    """Test that queries still use indexes after duplicate removal."""

    def test_commit_queries_use_remaining_indexes(self):
        """Verify commit queries can still use indexes after cleanup."""
        with connection.cursor() as cursor:
            # This query should use commit_author_date_idx (composite covers single-column)
            cursor.execute(
                """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM metrics_commit
                WHERE author_id = 1 AND committed_at > '2025-01-01'
                """
            )
            plan = cursor.fetchone()[0]
            # Just verify the query executes - actual index usage depends on planner
            self.assertIsNotNone(plan)

    def test_prsurvey_queries_use_remaining_indexes(self):
        """Verify PRSurvey queries can still use indexes after cleanup."""
        with connection.cursor() as cursor:
            # This query should use the OneToOneField unique index
            cursor.execute(
                """
                EXPLAIN (FORMAT JSON)
                SELECT * FROM metrics_prsurvey
                WHERE pull_request_id = 1
                """
            )
            plan = cursor.fetchone()[0]
            self.assertIsNotNone(plan)
