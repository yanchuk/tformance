from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    PRFile,
    PullRequest,
    TeamMember,
)
from apps.teams.context import unset_current_team
from apps.teams.models import Team


class TestPRFileModel(TestCase):
    """Tests for PRFile model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
            github_id="123",
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team,
            github_pr_id=1,
            github_repo="org/repo",
            title="Test PR",
            author=self.author,
            state="open",
            pr_created_at=django_timezone.now(),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_file_creation(self):
        """Test that PRFile can be created with all required fields."""
        pr_file = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/components/Button.tsx",
            status="modified",
            additions=10,
            deletions=5,
            changes=15,
            file_category="frontend",
        )
        self.assertEqual(pr_file.filename, "src/components/Button.tsx")
        self.assertEqual(pr_file.status, "modified")
        self.assertEqual(pr_file.additions, 10)
        self.assertEqual(pr_file.deletions, 5)
        self.assertEqual(pr_file.changes, 15)
        self.assertEqual(pr_file.file_category, "frontend")
        self.assertIsNotNone(pr_file.pk)

    def test_pr_file_pull_request_relationship(self):
        """Test that PRFile has correct foreign key relationship with PullRequest."""
        file1 = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/app.py",
            status="modified",
            additions=20,
            deletions=10,
            changes=30,
            file_category="backend",
        )
        file2 = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="README.md",
            status="modified",
            additions=5,
            deletions=2,
            changes=7,
            file_category="docs",
        )

        # Test forward relationship
        self.assertEqual(file1.pull_request, self.pull_request)
        self.assertEqual(file2.pull_request, self.pull_request)

        # Test reverse relationship via related_name='files'
        files = self.pull_request.files.all()
        self.assertEqual(files.count(), 2)
        self.assertIn(file1, files)
        self.assertIn(file2, files)

    def test_pr_file_unique_constraint(self):
        """Test that unique constraint on (team, pull_request, filename) is enforced."""
        PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/utils.py",
            status="added",
            additions=100,
            deletions=0,
            changes=100,
            file_category="backend",
        )
        # Attempt to create another file with same team, pull_request, and filename
        with self.assertRaises(IntegrityError):
            PRFile.objects.create(
                team=self.team,
                pull_request=self.pull_request,
                filename="src/utils.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                file_category="backend",
            )

    def test_pr_file_categorize_frontend(self):
        """Test that frontend files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/App.tsx"), "frontend")
        self.assertEqual(PRFile.categorize_file("components/Button.jsx"), "frontend")
        self.assertEqual(PRFile.categorize_file("pages/Home.vue"), "frontend")
        self.assertEqual(PRFile.categorize_file("styles/main.css"), "frontend")
        self.assertEqual(PRFile.categorize_file("styles/app.scss"), "frontend")
        self.assertEqual(PRFile.categorize_file("templates/index.html"), "frontend")

    def test_pr_file_categorize_backend(self):
        """Test that backend files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/app.py"), "backend")
        self.assertEqual(PRFile.categorize_file("main.go"), "backend")
        self.assertEqual(PRFile.categorize_file("src/Main.java"), "backend")
        self.assertEqual(PRFile.categorize_file("app/controllers/user.rb"), "backend")
        self.assertEqual(PRFile.categorize_file("src/lib.rs"), "backend")

    def test_pr_file_categorize_test(self):
        """Test that test files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/app_test.py"), "test")
        self.assertEqual(PRFile.categorize_file("test_utils.py"), "test")
        self.assertEqual(PRFile.categorize_file("tests/integration_test.go"), "test")
        self.assertEqual(PRFile.categorize_file("components/Button.spec.tsx"), "test")
        self.assertEqual(PRFile.categorize_file("app.spec.js"), "test")

    def test_pr_file_categorize_docs(self):
        """Test that documentation files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("README.md"), "docs")
        self.assertEqual(PRFile.categorize_file("docs/setup.rst"), "docs")
        self.assertEqual(PRFile.categorize_file("CHANGELOG.txt"), "docs")

    def test_pr_file_categorize_config(self):
        """Test that configuration files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("package.json"), "config")
        self.assertEqual(PRFile.categorize_file("config.yaml"), "config")
        self.assertEqual(PRFile.categorize_file("settings.yml"), "config")
        self.assertEqual(PRFile.categorize_file("pyproject.toml"), "config")
        self.assertEqual(PRFile.categorize_file("setup.ini"), "config")
        self.assertEqual(PRFile.categorize_file(".env"), "config")

    def test_pr_file_categorize_other(self):
        """Test that unrecognized files are categorized as 'other'."""
        self.assertEqual(PRFile.categorize_file("data.csv"), "other")
        self.assertEqual(PRFile.categorize_file("image.png"), "other")
        self.assertEqual(PRFile.categorize_file("unknown.xyz"), "other")
