"""
Tests for PRCache - GitHub PR caching for real project seeding.

Follows TDD approach - tests written BEFORE implementation.
These tests should all FAIL until PRCache is implemented.
"""

import json
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

from django.test import TestCase

from apps.metrics.seeding.pr_cache import PRCache


class TestPRCacheSave(TestCase):
    """Tests for PRCache.save() method - serializes to JSON file."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / ".seeding_cache"

    def test_saves_to_correct_path(self):
        """Test that cache saves to .seeding_cache/{org}/{repo}.json."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[{"number": 1, "title": "Test PR"}],
        )

        # Patch get_cache_path to use temp directory
        expected_path = self.cache_dir / "octocat" / "hello-world.json"
        with patch.object(PRCache, "get_cache_path", return_value=expected_path):
            cache.save()

        # Verify file was created
        self.assertTrue(expected_path.exists())
        self.assertTrue(expected_path.is_file())

    def test_serializes_datetime_to_iso(self):
        """Test that datetime fields are serialized to ISO 8601 format."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 30, 45, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[{"number": 1}],
        )

        expected_path = self.cache_dir / "octocat" / "hello-world.json"
        with patch.object(PRCache, "get_cache_path", return_value=expected_path):
            cache.save()

        # Read and verify JSON content
        with open(expected_path) as f:
            data = json.load(f)

        self.assertEqual(data["fetched_at"], "2025-12-24T12:30:45+00:00")
        self.assertEqual(data["since_date"], "2025-01-01")

    def test_serializes_date_to_iso(self):
        """Test that date fields are serialized to ISO 8601 format (YYYY-MM-DD)."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 6, 15),
            prs=[],
        )

        expected_path = self.cache_dir / "octocat" / "hello-world.json"
        with patch.object(PRCache, "get_cache_path", return_value=expected_path):
            cache.save()

        with open(expected_path) as f:
            data = json.load(f)

        self.assertEqual(data["since_date"], "2025-06-15")

    def test_creates_directory_if_not_exists(self):
        """Test that save() creates parent directories if they don't exist."""
        cache = PRCache(
            repo="microsoft/vscode",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
        )

        # Use a path that definitely doesn't exist
        expected_path = self.cache_dir / "microsoft" / "vscode.json"
        self.assertFalse(expected_path.parent.exists())

        with patch.object(PRCache, "get_cache_path", return_value=expected_path):
            cache.save()

        # Directory should now exist
        self.assertTrue(expected_path.parent.exists())
        self.assertTrue(expected_path.exists())

    def test_saves_pr_data_as_list(self):
        """Test that PR data is saved correctly as a list."""
        prs = [
            {"number": 1, "title": "First PR", "state": "merged"},
            {"number": 2, "title": "Second PR", "state": "open"},
        ]
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=prs,
        )

        expected_path = self.cache_dir / "octocat" / "hello-world.json"
        with patch.object(PRCache, "get_cache_path", return_value=expected_path):
            cache.save()

        with open(expected_path) as f:
            data = json.load(f)

        self.assertEqual(data["prs"], prs)
        self.assertEqual(len(data["prs"]), 2)


class TestPRCacheLoad(TestCase):
    """Tests for PRCache.load() classmethod - loads from JSON file."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / ".seeding_cache"

    def test_loads_existing_cache(self):
        """Test that load() successfully loads an existing cache file."""
        # Create a cache file
        cache_path = self.cache_dir / "octocat" / "hello-world.json"
        cache_path.parent.mkdir(parents=True)

        cache_data = {
            "repo": "octocat/hello-world",
            "fetched_at": "2025-12-24T12:30:45+00:00",
            "since_date": "2025-01-01",
            "prs": [{"number": 1, "title": "Test PR"}],
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        # Load the cache
        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache = PRCache.load("octocat/hello-world")

        # Verify loaded data
        self.assertIsNotNone(cache)
        self.assertEqual(cache.repo, "octocat/hello-world")
        self.assertEqual(cache.since_date, date(2025, 1, 1))
        self.assertEqual(len(cache.prs), 1)

    def test_returns_none_for_missing_file(self):
        """Test that load() returns None when cache file doesn't exist."""
        cache_path = self.cache_dir / "nonexistent" / "repo.json"

        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache = PRCache.load("nonexistent/repo")

        self.assertIsNone(cache)

    def test_parses_datetime_from_iso(self):
        """Test that datetime fields are correctly parsed from ISO format."""
        cache_path = self.cache_dir / "octocat" / "hello-world.json"
        cache_path.parent.mkdir(parents=True)

        cache_data = {
            "repo": "octocat/hello-world",
            "fetched_at": "2025-12-24T15:45:30+00:00",
            "since_date": "2025-01-01",
            "prs": [],
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache = PRCache.load("octocat/hello-world")

        # Verify datetime parsing
        self.assertEqual(cache.fetched_at, datetime(2025, 12, 24, 15, 45, 30, tzinfo=UTC))

    def test_parses_date_from_iso(self):
        """Test that date fields are correctly parsed from ISO format."""
        cache_path = self.cache_dir / "octocat" / "hello-world.json"
        cache_path.parent.mkdir(parents=True)

        cache_data = {
            "repo": "octocat/hello-world",
            "fetched_at": "2025-12-24T12:00:00+00:00",
            "since_date": "2024-06-15",
            "prs": [],
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache = PRCache.load("octocat/hello-world")

        # Verify date parsing
        self.assertEqual(cache.since_date, date(2024, 6, 15))

    def test_loads_pr_data_correctly(self):
        """Test that PR data list is loaded correctly."""
        cache_path = self.cache_dir / "octocat" / "hello-world.json"
        cache_path.parent.mkdir(parents=True)

        prs = [
            {"number": 1, "title": "First", "author": "alice"},
            {"number": 2, "title": "Second", "author": "bob"},
        ]
        cache_data = {
            "repo": "octocat/hello-world",
            "fetched_at": "2025-12-24T12:00:00+00:00",
            "since_date": "2025-01-01",
            "prs": prs,
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache = PRCache.load("octocat/hello-world")

        self.assertEqual(cache.prs, prs)
        self.assertEqual(len(cache.prs), 2)


class TestPRCacheIsValid(TestCase):
    """Tests for PRCache.is_valid() method - validates cache freshness."""

    def test_valid_when_since_date_matches(self):
        """Test that cache is valid when since_date matches exactly."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
        )

        self.assertTrue(cache.is_valid(since_date=date(2025, 1, 1)))

    def test_invalid_when_since_date_differs(self):
        """Test that cache is invalid when since_date doesn't match."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
        )

        # Different since_date should make cache invalid
        self.assertFalse(cache.is_valid(since_date=date(2025, 6, 1)))

    def test_invalid_when_requested_since_date_is_earlier(self):
        """Test that cache is invalid when requested since_date is earlier than cached."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 6, 1),
            prs=[],
        )

        # Requesting earlier date should invalidate cache
        self.assertFalse(cache.is_valid(since_date=date(2025, 1, 1)))

    def test_invalid_when_requested_since_date_is_later(self):
        """Test that cache is invalid when requested since_date is later than cached."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
        )

        # Requesting later date should invalidate cache
        self.assertFalse(cache.is_valid(since_date=date(2025, 6, 1)))


class TestPRCacheGetCachePath(TestCase):
    """Tests for PRCache.get_cache_path() staticmethod."""

    def test_returns_correct_path_for_repo(self):
        """Test that get_cache_path returns correct path structure."""
        repo = "octocat/hello-world"

        path = PRCache.get_cache_path(repo)

        # Should be a Path object
        self.assertIsInstance(path, Path)

        # Should match pattern: .seeding_cache/{org}/{repo}.json
        self.assertEqual(path.name, "hello-world.json")
        self.assertEqual(path.parent.name, "octocat")
        self.assertEqual(path.parent.parent.name, ".seeding_cache")

    def test_returns_correct_path_for_different_org(self):
        """Test path for different organization."""
        repo = "microsoft/vscode"

        path = PRCache.get_cache_path(repo)

        self.assertEqual(path.name, "vscode.json")
        self.assertEqual(path.parent.name, "microsoft")

    def test_handles_repo_name_with_hyphens(self):
        """Test that repo names with hyphens are handled correctly."""
        repo = "facebook/react-native"

        path = PRCache.get_cache_path(repo)

        self.assertEqual(path.name, "react-native.json")
        self.assertEqual(path.parent.name, "facebook")

    def test_path_is_relative_to_project_root(self):
        """Test that path is relative to project root (where manage.py is)."""
        repo = "octocat/hello-world"

        path = PRCache.get_cache_path(repo)

        # Path should contain .seeding_cache as a component
        self.assertIn(".seeding_cache", str(path))


class TestPRCacheRepoPushedAt(TestCase):
    """Tests for PRCache.repo_pushed_at field - detects if repo has changed.

    GitHub API best practices recommend checking if data has changed before
    re-fetching. This field stores when the repo was last pushed to, allowing
    us to skip fetching if nothing has changed.
    See: https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api
    """

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_dir = Path(self.temp_dir) / ".seeding_cache"

    def test_cache_stores_repo_pushed_at(self):
        """Test that PRCache can store repo_pushed_at timestamp."""
        pushed_at = datetime(2025, 12, 20, 10, 30, 0, tzinfo=UTC)
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
            repo_pushed_at=pushed_at,
        )

        self.assertEqual(cache.repo_pushed_at, pushed_at)

    def test_cache_saves_repo_pushed_at_to_json(self):
        """Test that repo_pushed_at is serialized to JSON."""
        pushed_at = datetime(2025, 12, 20, 10, 30, 0, tzinfo=UTC)
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
            repo_pushed_at=pushed_at,
        )

        cache_path = self.cache_dir / "octocat" / "hello-world.json"
        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache.save()

        with open(cache_path) as f:
            data = json.load(f)

        self.assertEqual(data["repo_pushed_at"], "2025-12-20T10:30:00+00:00")

    def test_cache_loads_repo_pushed_at_from_json(self):
        """Test that repo_pushed_at is deserialized from JSON."""
        cache_path = self.cache_dir / "octocat" / "hello-world.json"
        cache_path.parent.mkdir(parents=True)

        cache_data = {
            "repo": "octocat/hello-world",
            "fetched_at": "2025-12-24T12:00:00+00:00",
            "since_date": "2025-01-01",
            "prs": [],
            "repo_pushed_at": "2025-12-20T10:30:00+00:00",
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache = PRCache.load("octocat/hello-world")

        self.assertEqual(cache.repo_pushed_at, datetime(2025, 12, 20, 10, 30, 0, tzinfo=UTC))

    def test_cache_handles_missing_repo_pushed_at(self):
        """Test that old cache files without repo_pushed_at field still load."""
        cache_path = self.cache_dir / "octocat" / "hello-world.json"
        cache_path.parent.mkdir(parents=True)

        # Old cache format without repo_pushed_at
        cache_data = {
            "repo": "octocat/hello-world",
            "fetched_at": "2025-12-24T12:00:00+00:00",
            "since_date": "2025-01-01",
            "prs": [],
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

        with patch.object(PRCache, "get_cache_path", return_value=cache_path):
            cache = PRCache.load("octocat/hello-world")

        # Should load successfully with None for repo_pushed_at
        self.assertIsNotNone(cache)
        self.assertIsNone(cache.repo_pushed_at)

    def test_is_valid_with_unchanged_repo(self):
        """Test that cache is valid when repo hasn't been pushed to since fetch."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
            repo_pushed_at=datetime(2025, 12, 20, 10, 0, 0, tzinfo=UTC),
        )

        # Repo hasn't changed (same pushed_at timestamp)
        current_pushed_at = datetime(2025, 12, 20, 10, 0, 0, tzinfo=UTC)
        self.assertTrue(cache.is_valid(since_date=date(2025, 1, 1), repo_pushed_at=current_pushed_at))

    def test_is_valid_with_changed_repo(self):
        """Test that cache is invalid when repo has been pushed to since fetch."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
            repo_pushed_at=datetime(2025, 12, 20, 10, 0, 0, tzinfo=UTC),
        )

        # Repo has been pushed to since cache was created
        current_pushed_at = datetime(2025, 12, 25, 15, 0, 0, tzinfo=UTC)
        self.assertFalse(cache.is_valid(since_date=date(2025, 1, 1), repo_pushed_at=current_pushed_at))

    def test_is_valid_without_repo_pushed_at_param_falls_back(self):
        """Test that is_valid works when repo_pushed_at is not provided (backward compat)."""
        cache = PRCache(
            repo="octocat/hello-world",
            fetched_at=datetime(2025, 12, 24, 12, 0, 0, tzinfo=UTC),
            since_date=date(2025, 1, 1),
            prs=[],
            repo_pushed_at=datetime(2025, 12, 20, 10, 0, 0, tzinfo=UTC),
        )

        # When repo_pushed_at is not provided, should fall back to since_date check only
        self.assertTrue(cache.is_valid(since_date=date(2025, 1, 1)))
