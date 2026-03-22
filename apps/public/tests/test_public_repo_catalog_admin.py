"""Tests for the DB-driven public repo catalog (Task 1).

Covers: new PublicRepoProfile fields, PublicRepoSyncState model,
consolidated save() override, enhanced admin, and data migration.
"""

import pytest
from django.db import IntegrityError
from django.test import TestCase

from apps.public.models import PublicOrgProfile, PublicRepoProfile, PublicRepoSyncState
from apps.teams.models import Team

# ---------------------------------------------------------------------------
# Data migration test helpers
# ---------------------------------------------------------------------------
MIGRATE_FROM = [("public", "0005_public_repo_sync_state")]
MIGRATE_TO = [("public", "0006_seed_catalog_state")]


class PublicRepoProfileFieldTests(TestCase):
    """Step 1.1: New catalog fields exist with correct defaults."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Test Team", slug="test-team")
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="test-org",
            industry="analytics",
            display_name="Test Org",
            is_public=True,
        )

    def test_new_catalog_fields_exist_with_correct_defaults(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="test-org/test-repo",
            repo_slug="test-repo",
            display_name="Test Repo",
        )
        repo.refresh_from_db()

        assert repo.sync_enabled is True
        assert repo.insights_enabled is False
        assert repo.initial_backfill_days == 180
        assert repo.display_order == 0


class PublicRepoSyncStateModelTests(TestCase):
    """Step 1.2: PublicRepoSyncState model exists with correct fields."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Sync Team", slug="sync-team")
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="sync-org",
            industry="analytics",
            display_name="Sync Org",
            is_public=True,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="sync-org/sync-repo",
            repo_slug="sync-repo",
            display_name="Sync Repo",
        )

    def test_sync_state_model_exists_with_correct_fields(self):
        # sync_state is auto-created by save() override — verify its defaults
        state = self.repo_profile.sync_state
        state.refresh_from_db()

        assert state.status == "pending_backfill"
        assert state.last_successful_sync_at is None
        assert state.last_attempted_sync_at is None
        assert state.last_synced_updated_at is None
        assert state.checkpoint_payload == {}
        assert state.last_error == ""
        assert state.last_backfill_completed_at is None

    def test_sync_state_is_onetoone_with_repo_profile(self):
        # sync_state already exists (auto-created) — second create should fail
        with pytest.raises(IntegrityError):
            PublicRepoSyncState.objects.create(repo_profile=self.repo_profile)


class ConsolidatedSaveTests(TestCase):
    """Step 1.3: save() auto-creates sync state and derives team from org_profile."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Save Team", slug="save-team")
        cls.other_team = Team.objects.create(name="Other Team", slug="other-team")
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="save-org",
            industry="analytics",
            display_name="Save Org",
            is_public=True,
        )

    def test_creating_repo_profile_auto_creates_sync_state(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="save-org/save-repo",
            repo_slug="save-repo",
            display_name="Save Repo",
        )
        assert PublicRepoSyncState.objects.filter(repo_profile=repo).exists()
        assert repo.sync_state.status == "pending_backfill"

    def test_saving_existing_repo_profile_does_not_duplicate_sync_state(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="save-org/dup-repo",
            repo_slug="dup-repo",
            display_name="Dup Repo",
        )
        # Save again
        repo.display_name = "Updated Name"
        repo.save()
        assert PublicRepoSyncState.objects.filter(repo_profile=repo).count() == 1

    def test_team_auto_derived_from_org_profile_on_create(self):
        # Pass no team — should be derived from org_profile.team
        repo = PublicRepoProfile(
            org_profile=self.org_profile,
            github_repo="save-org/derive-repo",
            repo_slug="derive-repo",
            display_name="Derive Repo",
        )
        repo.save()
        repo.refresh_from_db()
        assert repo.team == self.org_profile.team

    def test_team_corrected_on_save_if_mismatched(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.other_team,  # deliberately wrong
            github_repo="save-org/mismatch-repo",
            repo_slug="mismatch-repo",
            display_name="Mismatch Repo",
        )
        repo.refresh_from_db()
        assert repo.team == self.org_profile.team  # should be corrected


class PublicRepoProfileAdminTests(TestCase):
    """Step 1.4: Enhanced admin with conditional readonly and new fields."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Admin Team", slug="admin-team")
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="admin-org",
            industry="analytics",
            display_name="Admin Org",
            is_public=True,
        )

    def _get_admin(self):
        from django.contrib.admin.sites import AdminSite

        from apps.public.admin import PublicRepoProfileAdmin

        return PublicRepoProfileAdmin(PublicRepoProfile, AdminSite())

    def test_repo_slug_editable_before_first_sync(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="admin-org/editable-repo",
            repo_slug="editable-repo",
            display_name="Editable Repo",
        )
        # sync_state should be pending_backfill (auto-created)
        admin_instance = self._get_admin()
        readonly = admin_instance.get_readonly_fields(request=None, obj=repo)
        assert "repo_slug" not in readonly
        assert "github_repo" not in readonly

    def test_repo_slug_readonly_after_first_sync(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="admin-org/locked-repo",
            repo_slug="locked-repo",
            display_name="Locked Repo",
        )
        # Transition sync state to ready
        repo.sync_state.status = "ready"
        repo.sync_state.save()

        admin_instance = self._get_admin()
        readonly = admin_instance.get_readonly_fields(request=None, obj=repo)
        assert "repo_slug" in readonly
        assert "github_repo" in readonly

    def test_team_always_readonly_in_admin(self):
        admin_instance = self._get_admin()
        # Check for new objects (obj=None)
        readonly = admin_instance.get_readonly_fields(request=None, obj=None)
        assert "team" in readonly

    def test_admin_list_display_includes_new_fields(self):
        admin_instance = self._get_admin()
        assert "sync_enabled" in admin_instance.list_display
        assert "insights_enabled" in admin_instance.list_display
        assert "display_order" in admin_instance.list_display

    def test_admin_readonly_handles_missing_sync_state(self):
        """Pre-migration profiles without sync_state don't crash admin."""
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="admin-org/nosync-repo",
            repo_slug="nosync-repo",
            display_name="No Sync Repo",
        )
        # Delete the auto-created sync state to simulate pre-migration data
        PublicRepoSyncState.objects.filter(repo_profile=repo).delete()

        admin_instance = self._get_admin()
        # Should not raise an exception
        readonly = admin_instance.get_readonly_fields(request=None, obj=repo)
        # Without sync state, repo_slug should remain editable (safe default)
        assert "repo_slug" not in readonly


class DataMigrationTests(TestCase):
    """Step 1.5: Data migration seeds insights_enabled and creates sync states."""

    def test_migration_seeds_insights_enabled_from_flagship(self):
        """is_flagship=True repos should get insights_enabled=True after migration."""
        from django.core.management import call_command
        from django.db import connection
        from django.db.migrations.executor import MigrationExecutor

        executor = MigrationExecutor(connection)

        # Roll back to state before the data migration
        executor.migrate(MIGRATE_FROM)
        executor.loader.build_graph()

        # Use historical models (no save() override at this point)
        old_state = executor.loader.project_state(MIGRATE_FROM)
        OldTeam = old_state.apps.get_model("teams", "Team")
        OldOrg = old_state.apps.get_model("public", "PublicOrgProfile")
        OldRepo = old_state.apps.get_model("public", "PublicRepoProfile")

        team = OldTeam.objects.create(name="Mig Team", slug="mig-team")
        org = OldOrg.objects.create(
            team_id=team.pk,
            public_slug="mig-org",
            industry="analytics",
            display_name="Mig Org",
            is_public=True,
        )
        flagship_repo = OldRepo.objects.create(
            org_profile_id=org.pk,
            team_id=team.pk,
            github_repo="mig-org/flagship",
            repo_slug="flagship",
            display_name="Flagship",
            is_flagship=True,
        )
        non_flagship_repo = OldRepo.objects.create(
            org_profile_id=org.pk,
            team_id=team.pk,
            github_repo="mig-org/secondary",
            repo_slug="secondary",
            display_name="Secondary",
            is_flagship=False,
        )

        # Run the data migration
        executor = MigrationExecutor(connection)
        executor.migrate(MIGRATE_TO)
        executor.loader.build_graph()

        new_state = executor.loader.project_state(MIGRATE_TO)
        NewRepo = new_state.apps.get_model("public", "PublicRepoProfile")
        NewSyncState = new_state.apps.get_model("public", "PublicRepoSyncState")

        flagship = NewRepo.objects.get(pk=flagship_repo.pk)
        secondary = NewRepo.objects.get(pk=non_flagship_repo.pk)

        # Flagship should get insights_enabled=True
        assert flagship.insights_enabled is True
        # Non-flagship should remain False
        assert secondary.insights_enabled is False

        # Both should have sync states created (use _id for historical models)
        assert NewSyncState.objects.filter(repo_profile_id=flagship.pk).exists()
        assert NewSyncState.objects.filter(repo_profile_id=secondary.pk).exists()

        # Both should be pending_backfill (no PublicRepoStats exist)
        assert NewSyncState.objects.get(repo_profile_id=flagship.pk).status == "pending_backfill"
        assert NewSyncState.objects.get(repo_profile_id=secondary.pk).status == "pending_backfill"

        # Cleanup: re-migrate forward to latest for other tests
        call_command("migrate", verbosity=0)
