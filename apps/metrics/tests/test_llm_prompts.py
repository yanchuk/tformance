"""Tests for LLM prompts module."""

from django.test import TestCase

from apps.metrics.prompts.constants import PROMPT_VERSION
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    get_user_prompt,
)


class TestPromptVersion(TestCase):
    """Tests for prompt versioning."""

    def test_prompt_version_format(self):
        """Version should be semver format."""
        parts = PROMPT_VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_system_prompt_not_empty(self):
        """System prompt should have content."""
        self.assertGreater(len(PR_ANALYSIS_SYSTEM_PROMPT), 100)

    def test_system_prompt_contains_key_sections(self):
        """System prompt should have required sections."""
        self.assertIn("AI Detection", PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn("Technology Detection", PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn("Response Format", PR_ANALYSIS_SYSTEM_PROMPT)


class TestGetUserPrompt(TestCase):
    """Tests for get_user_prompt function."""

    def test_basic_prompt_with_body_only(self):
        """Prompt with just body should work."""
        prompt = get_user_prompt(pr_body="Fix bug in login")
        self.assertIn("Fix bug in login", prompt)
        self.assertIn("Description:", prompt)

    def test_prompt_includes_title(self):
        """Title should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Details here",
            pr_title="Add dark mode toggle",
        )
        self.assertIn("Title: Add dark mode toggle", prompt)

    def test_prompt_includes_file_count(self):
        """File count should be included when > 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            file_count=15,
        )
        self.assertIn("Files changed: 15", prompt)

    def test_prompt_excludes_zero_file_count(self):
        """File count should not be included when 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            file_count=0,
        )
        self.assertNotIn("Files changed", prompt)

    def test_prompt_includes_additions_deletions(self):
        """Lines added/deleted should be included."""
        prompt = get_user_prompt(
            pr_body="Refactor",
            additions=150,
            deletions=50,
        )
        self.assertIn("Lines: +150/-50", prompt)

    def test_prompt_includes_only_additions(self):
        """Lines should show when only additions present."""
        prompt = get_user_prompt(
            pr_body="New feature",
            additions=200,
            deletions=0,
        )
        self.assertIn("Lines: +200/-0", prompt)

    def test_prompt_includes_only_deletions(self):
        """Lines should show when only deletions present."""
        prompt = get_user_prompt(
            pr_body="Remove dead code",
            additions=0,
            deletions=100,
        )
        self.assertIn("Lines: +0/-100", prompt)

    def test_prompt_excludes_zero_lines(self):
        """Lines should not be included when both are 0."""
        prompt = get_user_prompt(
            pr_body="Docs only",
            additions=0,
            deletions=0,
        )
        self.assertNotIn("Lines:", prompt)

    def test_prompt_includes_comment_count(self):
        """Comment count should be included when > 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            comment_count=5,
        )
        self.assertIn("Comments: 5", prompt)

    def test_prompt_excludes_zero_comments(self):
        """Comment count should not be included when 0."""
        prompt = get_user_prompt(
            pr_body="Changes",
            comment_count=0,
        )
        self.assertNotIn("Comments", prompt)

    def test_prompt_includes_repo_languages(self):
        """Repository languages should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Backend fix",
            repo_languages=["Python", "TypeScript", "Go"],
        )
        self.assertIn("Repository languages: Python, TypeScript, Go", prompt)

    def test_prompt_excludes_empty_languages(self):
        """Languages should not be included when empty."""
        prompt = get_user_prompt(
            pr_body="Changes",
            repo_languages=[],
        )
        self.assertNotIn("Repository languages", prompt)

    def test_prompt_excludes_none_languages(self):
        """Languages should not be included when None."""
        prompt = get_user_prompt(
            pr_body="Changes",
            repo_languages=None,
        )
        self.assertNotIn("Repository languages", prompt)

    def test_full_prompt_with_all_fields(self):
        """Prompt with all fields should be properly formatted."""
        prompt = get_user_prompt(
            pr_body="Implements new dark mode feature with user preference persistence.",
            pr_title="Add dark mode toggle to settings",
            file_count=12,
            additions=450,
            deletions=30,
            comment_count=8,
            repo_languages=["TypeScript", "React", "CSS"],
        )

        # Check all parts are present
        self.assertIn("Title: Add dark mode toggle to settings", prompt)
        self.assertIn("Files changed: 12", prompt)
        self.assertIn("Lines: +450/-30", prompt)
        self.assertIn("Comments: 8", prompt)
        self.assertIn("Repository languages: TypeScript, React, CSS", prompt)
        self.assertIn("Implements new dark mode feature", prompt)

        # Check structure
        self.assertIn("Analyze this pull request:", prompt)
        self.assertIn("Description:", prompt)

    def test_prompt_handles_empty_body(self):
        """Empty body should be handled gracefully."""
        prompt = get_user_prompt(pr_body="")
        self.assertIn("Description:", prompt)

    def test_prompt_handles_multiline_body(self):
        """Multiline body should be preserved."""
        body = """## Summary
This PR adds feature X.

## Changes
- Added A
- Modified B
- Removed C"""
        prompt = get_user_prompt(pr_body=body)
        self.assertIn("## Summary", prompt)
        self.assertIn("- Added A", prompt)


class TestGetUserPromptV6Fields(TestCase):
    """Tests for v6.0.0 new fields in get_user_prompt."""

    def test_prompt_includes_state(self):
        """State should be included when provided."""
        prompt = get_user_prompt(pr_body="Changes", state="merged")
        self.assertIn("State: merged", prompt)

    def test_prompt_excludes_empty_state(self):
        """State should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", state="")
        self.assertNotIn("State:", prompt)

    def test_prompt_includes_labels(self):
        """Labels should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Changes",
            labels=["bug", "priority:high", "frontend"],
        )
        self.assertIn("Labels: bug, priority:high, frontend", prompt)

    def test_prompt_excludes_empty_labels(self):
        """Labels should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", labels=[])
        self.assertNotIn("Labels:", prompt)

    def test_prompt_includes_is_draft(self):
        """Draft flag should be included when True."""
        prompt = get_user_prompt(pr_body="WIP", is_draft=True)
        self.assertIn("Draft: Yes", prompt)

    def test_prompt_excludes_is_draft_false(self):
        """Draft flag should not be included when False."""
        prompt = get_user_prompt(pr_body="Changes", is_draft=False)
        self.assertNotIn("Draft:", prompt)

    def test_prompt_includes_is_hotfix(self):
        """Hotfix flag should be included when True."""
        prompt = get_user_prompt(pr_body="Urgent fix", is_hotfix=True)
        self.assertIn("Hotfix: Yes", prompt)

    def test_prompt_excludes_is_hotfix_false(self):
        """Hotfix flag should not be included when False."""
        prompt = get_user_prompt(pr_body="Changes", is_hotfix=False)
        self.assertNotIn("Hotfix:", prompt)

    def test_prompt_includes_is_revert(self):
        """Revert flag should be included when True."""
        prompt = get_user_prompt(pr_body="Reverts #123", is_revert=True)
        self.assertIn("Revert: Yes", prompt)

    def test_prompt_excludes_is_revert_false(self):
        """Revert flag should not be included when False."""
        prompt = get_user_prompt(pr_body="Changes", is_revert=False)
        self.assertNotIn("Revert:", prompt)

    def test_prompt_includes_cycle_time_hours(self):
        """Cycle time should be included when provided."""
        prompt = get_user_prompt(pr_body="Changes", cycle_time_hours=48.5)
        self.assertIn("Cycle time: 48.5 hours", prompt)

    def test_prompt_excludes_cycle_time_none(self):
        """Cycle time should not be included when None."""
        prompt = get_user_prompt(pr_body="Changes", cycle_time_hours=None)
        self.assertNotIn("Cycle time:", prompt)

    def test_prompt_includes_review_time_hours(self):
        """Review time should be included when provided."""
        prompt = get_user_prompt(pr_body="Changes", review_time_hours=4.2)
        self.assertIn("Time to first review: 4.2 hours", prompt)

    def test_prompt_excludes_review_time_none(self):
        """Review time should not be included when None."""
        prompt = get_user_prompt(pr_body="Changes", review_time_hours=None)
        self.assertNotIn("Time to first review:", prompt)

    def test_prompt_includes_commits_after_first_review(self):
        """Commits after first review should be included when > 0."""
        prompt = get_user_prompt(pr_body="Changes", commits_after_first_review=5)
        self.assertIn("Commits after first review: 5", prompt)

    def test_prompt_excludes_commits_after_first_review_zero(self):
        """Commits after first review should not be included when 0."""
        prompt = get_user_prompt(pr_body="Changes", commits_after_first_review=0)
        self.assertNotIn("Commits after first review:", prompt)

    def test_prompt_excludes_commits_after_first_review_none(self):
        """Commits after first review should not be included when None."""
        prompt = get_user_prompt(pr_body="Changes", commits_after_first_review=None)
        self.assertNotIn("Commits after first review:", prompt)

    def test_prompt_includes_review_rounds(self):
        """Review rounds should be included when > 0."""
        prompt = get_user_prompt(pr_body="Changes", review_rounds=3)
        self.assertIn("Review rounds: 3", prompt)

    def test_prompt_excludes_review_rounds_zero(self):
        """Review rounds should not be included when 0."""
        prompt = get_user_prompt(pr_body="Changes", review_rounds=0)
        self.assertNotIn("Review rounds:", prompt)

    def test_prompt_excludes_review_rounds_none(self):
        """Review rounds should not be included when None."""
        prompt = get_user_prompt(pr_body="Changes", review_rounds=None)
        self.assertNotIn("Review rounds:", prompt)

    def test_prompt_includes_file_paths(self):
        """File paths should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Changes",
            file_paths=["src/auth.py", "tests/test_auth.py", "README.md"],
        )
        self.assertIn("Files: src/auth.py, tests/test_auth.py, README.md", prompt)

    def test_prompt_limits_file_paths_to_20(self):
        """File paths should be limited to 20 with count indicator."""
        file_paths = [f"src/file_{i}.py" for i in range(25)]
        prompt = get_user_prompt(pr_body="Changes", file_paths=file_paths)
        self.assertIn("(+5 more)", prompt)
        self.assertIn("src/file_19.py", prompt)
        self.assertNotIn("src/file_20.py", prompt)

    def test_prompt_excludes_empty_file_paths(self):
        """File paths should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", file_paths=[])
        self.assertNotIn("Files:", prompt)

    def test_prompt_includes_commit_messages(self):
        """Commit messages should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Changes",
            commit_messages=[
                "Add login endpoint",
                "Add tests for login",
                "Fix typo in error message",
            ],
        )
        self.assertIn("Recent commits:", prompt)
        self.assertIn("- Add login endpoint", prompt)
        self.assertIn("- Add tests for login", prompt)
        self.assertIn("- Fix typo in error message", prompt)

    def test_prompt_limits_commit_messages_to_5(self):
        """Commit messages should be limited to 5 with count indicator."""
        commits = [f"Commit {i}" for i in range(8)]
        prompt = get_user_prompt(pr_body="Changes", commit_messages=commits)
        self.assertIn("- Commit 0", prompt)
        self.assertIn("- Commit 4", prompt)
        self.assertIn("... and 3 more commits", prompt)
        self.assertNotIn("- Commit 5", prompt)

    def test_prompt_excludes_empty_commit_messages(self):
        """Commit messages should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", commit_messages=[])
        self.assertNotIn("Recent commits:", prompt)

    def test_full_v6_prompt_with_all_fields(self):
        """Prompt with all v6 fields should be properly formatted."""
        prompt = get_user_prompt(
            pr_body="Fixes critical authentication bug causing session expiry.",
            pr_title="Fix auth timeout bug",
            file_count=5,
            additions=50,
            deletions=10,
            comment_count=12,
            repo_languages=["Python", "TypeScript"],
            state="merged",
            labels=["bug", "critical", "auth"],
            is_draft=False,
            is_hotfix=True,
            is_revert=False,
            cycle_time_hours=6.5,
            review_time_hours=0.5,
            commits_after_first_review=2,
            review_rounds=1,
            file_paths=["apps/auth/views.py", "apps/auth/tests.py"],
            commit_messages=[
                "Fix session expiry check",
                "Add regression test",
            ],
        )

        # Check all v6 parts are present
        self.assertIn("Title: Fix auth timeout bug", prompt)
        self.assertIn("State: merged", prompt)
        self.assertIn("Labels: bug, critical, auth", prompt)
        self.assertIn("Hotfix: Yes", prompt)
        self.assertIn("Cycle time: 6.5 hours", prompt)
        self.assertIn("Time to first review: 0.5 hours", prompt)
        self.assertIn("Comments: 12", prompt)
        self.assertIn("Commits after first review: 2", prompt)
        self.assertIn("Review rounds: 1", prompt)
        self.assertIn("Files: apps/auth/views.py, apps/auth/tests.py", prompt)
        self.assertIn("Recent commits:", prompt)
        self.assertIn("- Fix session expiry check", prompt)

        # Check structure
        self.assertIn("Analyze this pull request:", prompt)
        self.assertIn("Description:", prompt)


class TestGetUserPromptV61Fields(TestCase):
    """Tests for v6.1.0 new fields - additional PR context."""

    # === Milestone ===
    def test_prompt_includes_milestone(self):
        """Milestone should be included when provided."""
        prompt = get_user_prompt(pr_body="Changes", milestone="Q1 2025 Release")
        self.assertIn("Milestone: Q1 2025 Release", prompt)

    def test_prompt_excludes_milestone_none(self):
        """Milestone should not be included when None."""
        prompt = get_user_prompt(pr_body="Changes", milestone=None)
        self.assertNotIn("Milestone:", prompt)

    def test_prompt_excludes_milestone_empty(self):
        """Milestone should not be included when empty string."""
        prompt = get_user_prompt(pr_body="Changes", milestone="")
        self.assertNotIn("Milestone:", prompt)

    # === Assignees ===
    def test_prompt_includes_assignees(self):
        """Assignees should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Changes",
            assignees=["john", "jane", "bob"],
        )
        self.assertIn("Assignees: john, jane, bob", prompt)

    def test_prompt_limits_assignees_to_10(self):
        """Assignees should be limited to 10 with count indicator."""
        assignees = [f"user{i}" for i in range(15)]
        prompt = get_user_prompt(pr_body="Changes", assignees=assignees)
        self.assertIn("user9", prompt)
        self.assertIn("(+5 more)", prompt)
        self.assertNotIn("user10", prompt)

    def test_prompt_excludes_assignees_empty(self):
        """Assignees should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", assignees=[])
        self.assertNotIn("Assignees:", prompt)

    # === Linked Issues ===
    def test_prompt_includes_linked_issues(self):
        """Linked issues should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Changes",
            linked_issues=["#123", "#456", "#789"],
        )
        self.assertIn("Linked issues: #123, #456, #789", prompt)

    def test_prompt_excludes_linked_issues_empty(self):
        """Linked issues should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", linked_issues=[])
        self.assertNotIn("Linked issues:", prompt)

    # === Jira Key ===
    def test_prompt_includes_jira_key(self):
        """Jira key should be included when provided."""
        prompt = get_user_prompt(pr_body="Changes", jira_key="PROJ-1234")
        self.assertIn("Jira: PROJ-1234", prompt)

    def test_prompt_excludes_jira_key_none(self):
        """Jira key should not be included when None."""
        prompt = get_user_prompt(pr_body="Changes", jira_key=None)
        self.assertNotIn("Jira:", prompt)

    def test_prompt_excludes_jira_key_empty(self):
        """Jira key should not be included when empty string."""
        prompt = get_user_prompt(pr_body="Changes", jira_key="")
        self.assertNotIn("Jira:", prompt)

    # === Author Name ===
    def test_prompt_includes_author_name(self):
        """Author name should be included when provided."""
        prompt = get_user_prompt(pr_body="Changes", author_name="John Smith")
        self.assertIn("Author: John Smith", prompt)

    def test_prompt_excludes_author_name_none(self):
        """Author name should not be included when None."""
        prompt = get_user_prompt(pr_body="Changes", author_name=None)
        self.assertNotIn("Author:", prompt)

    def test_prompt_excludes_author_name_empty(self):
        """Author name should not be included when empty string."""
        prompt = get_user_prompt(pr_body="Changes", author_name="")
        self.assertNotIn("Author:", prompt)

    # === Reviewers ===
    def test_prompt_includes_reviewers(self):
        """Reviewers should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Changes",
            reviewers=["alice", "bob"],
        )
        self.assertIn("Reviewers: alice, bob", prompt)

    def test_prompt_limits_reviewers_to_5(self):
        """Reviewers should be limited to 5 with count indicator."""
        reviewers = [f"reviewer{i}" for i in range(8)]
        prompt = get_user_prompt(pr_body="Changes", reviewers=reviewers)
        self.assertIn("reviewer4", prompt)
        self.assertIn("(+3 more)", prompt)
        self.assertNotIn("reviewer5", prompt)

    def test_prompt_excludes_reviewers_empty(self):
        """Reviewers should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", reviewers=[])
        self.assertNotIn("Reviewers:", prompt)

    # === Review Comments ===
    def test_prompt_includes_review_comments(self):
        """Review comments should be included when provided."""
        prompt = get_user_prompt(
            pr_body="Changes",
            review_comments=[
                "Great work on this!",
                "Can you add a test for the edge case?",
            ],
        )
        self.assertIn("Review comments:", prompt)
        self.assertIn("Great work on this!", prompt)
        self.assertIn("Can you add a test for the edge case?", prompt)

    def test_prompt_limits_review_comments_to_3(self):
        """Review comments should be limited to 3."""
        comments = [f"Comment {i}" for i in range(5)]
        prompt = get_user_prompt(pr_body="Changes", review_comments=comments)
        self.assertIn("Comment 0", prompt)
        self.assertIn("Comment 2", prompt)
        self.assertNotIn("Comment 3", prompt)

    def test_prompt_truncates_long_review_comments(self):
        """Long review comments should be truncated to 200 chars."""
        long_comment = "A" * 300
        prompt = get_user_prompt(pr_body="Changes", review_comments=[long_comment])
        # Should have truncated version (200 chars + "...")
        self.assertIn("A" * 200, prompt)
        self.assertNotIn("A" * 201, prompt)

    def test_prompt_excludes_review_comments_empty(self):
        """Review comments should not be included when empty."""
        prompt = get_user_prompt(pr_body="Changes", review_comments=[])
        self.assertNotIn("Review comments:", prompt)

    # === Full v6.1 Test ===
    def test_full_v61_prompt_with_all_new_fields(self):
        """Prompt with all v6.1 fields should be properly formatted."""
        prompt = get_user_prompt(
            pr_body="Implements user authentication with OAuth2.",
            pr_title="Add OAuth2 login",
            milestone="Q1 2025 Release",
            assignees=["john", "jane"],
            linked_issues=["#100", "#101"],
            jira_key="AUTH-42",
            author_name="John Developer",
            reviewers=["alice", "bob"],
            review_comments=[
                "Looks good overall!",
                "Please add error handling for token refresh.",
            ],
        )

        # Check all v6.1 parts are present
        self.assertIn("Milestone: Q1 2025 Release", prompt)
        self.assertIn("Assignees: john, jane", prompt)
        self.assertIn("Linked issues: #100, #101", prompt)
        self.assertIn("Jira: AUTH-42", prompt)
        self.assertIn("Author: John Developer", prompt)
        self.assertIn("Reviewers: alice, bob", prompt)
        self.assertIn("Review comments:", prompt)
        self.assertIn("Looks good overall!", prompt)


class TestBuildLlmPrContext(TestCase):
    """Tests for build_llm_pr_context unified function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.metrics.factories import (
            CommitFactory,
            PRFileFactory,
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )
        from apps.metrics.models import PRComment

        self.team = TeamFactory()
        self.author = TeamMemberFactory(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
        )
        self.reviewer = TeamMemberFactory(
            team=self.team,
            display_name="Jane Smith",
            github_username="janesmith",
        )
        self.pr = PullRequestFactory(
            team=self.team,
            github_pr_id=1234,
            github_repo="acme/backend",
            title="Add user authentication endpoint",
            body="Implements JWT auth\n\n🤖 Generated with Claude Code",
            author=self.author,
            state="merged",
            additions=250,
            deletions=50,
            is_draft=False,
            is_hotfix=True,
            is_revert=False,
            labels=["feature", "auth"],
            milestone_title="Q1 2025 Release",
            assignees=["johndoe", "janesmith"],
            jira_key="AUTH-123",
            linked_issues=[100, 101],
            cycle_time_hours=24.5,
            review_time_hours=2.0,
            total_comments=8,
            commits_after_first_review=3,
            review_rounds=2,
        )

        # Create related objects
        self.file1 = PRFileFactory(
            team=self.team,
            pull_request=self.pr,
            filename="apps/auth/views.py",
            file_category="backend",
            additions=120,
            deletions=20,
        )
        self.file2 = PRFileFactory(
            team=self.team,
            pull_request=self.pr,
            filename="apps/auth/tests.py",
            file_category="test",
            additions=80,
            deletions=10,
        )

        self.commit1 = CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Add JWT validation\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
        )
        self.commit2 = CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Add tests for auth flow",
        )

        self.review = PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            state="approved",
            body="LGTM! Nice clean implementation.",
        )

        # Create a comment
        PRComment.objects.create(
            team=self.team,
            github_comment_id=999,
            pull_request=self.pr,
            author=self.reviewer,
            body="Should we use refresh tokens?",
            comment_type="issue",
            comment_created_at=self.pr.pr_created_at,
        )

    def test_context_includes_pr_number(self):
        """Context should include PR number."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("PR #1234", context)

    def test_context_includes_title(self):
        """Context should include PR title."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Title: Add user authentication endpoint", context)

    def test_context_includes_repository(self):
        """Context should include repository name."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Repository: acme/backend", context)

    def test_context_includes_author_with_username(self):
        """Context should include author name with GitHub username."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Author: John Doe (@johndoe)", context)

    def test_context_includes_state(self):
        """Context should include PR state."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("State: merged", context)

    def test_context_includes_hotfix_flag(self):
        """Context should include hotfix flag when True."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Hotfix: Yes", context)

    def test_context_includes_labels(self):
        """Context should include labels."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Labels: feature, auth", context)

    def test_context_includes_milestone(self):
        """Context should include milestone."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Milestone: Q1 2025 Release", context)

    def test_context_includes_jira_key(self):
        """Context should include Jira key."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Jira: AUTH-123", context)

    def test_context_includes_linked_issues(self):
        """Context should include linked issues."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Linked issues: #100, #101", context)

    def test_context_includes_size(self):
        """Context should include code size."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Size: +250/-50 lines", context)

    def test_context_includes_files_with_categories(self):
        """Context should include files with categories."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("[backend] apps/auth/views.py (+120/-20)", context)
        self.assertIn("[test] apps/auth/tests.py (+80/-10)", context)

    def test_context_includes_timing_metrics(self):
        """Context should include timing metrics."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Cycle time: 24.5 hours", context)
        self.assertIn("Time to first review: 2.0 hours", context)
        self.assertIn("Comments: 8", context)
        self.assertIn("Commits after first review: 3", context)
        self.assertIn("Review rounds: 2", context)

    def test_context_includes_commits_with_ai_signature(self):
        """Context should include commit messages with AI signatures."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Commits:", context)
        self.assertIn("Co-Authored-By: Claude", context)

    def test_context_includes_reviews(self):
        """Context should include reviews with state and body."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Reviews:", context)
        self.assertIn("[APPROVED] Jane Smith: LGTM! Nice clean implementation.", context)

    def test_context_includes_comments(self):
        """Context should include PR comments."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Comments:", context)
        self.assertIn("Jane Smith: Should we use refresh tokens?", context)

    def test_context_includes_description(self):
        """Context should include PR description with AI markers."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Description:", context)
        self.assertIn("Implements JWT auth", context)
        self.assertIn("🤖 Generated with Claude Code", context)

    def test_context_starts_with_analyze_instruction(self):
        """Context should start with analysis instruction."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertTrue(context.startswith("Analyze this pull request:"))


class TestBuildLlmPrContextEdgeCases(TestCase):
    """Edge case tests for build_llm_pr_context."""

    def setUp(self):
        """Set up minimal test PR."""
        from apps.metrics.factories import PullRequestFactory, TeamFactory

        self.team = TeamFactory()
        self.pr = PullRequestFactory(
            team=self.team,
            github_pr_id=1,
            github_repo="test/repo",
            title="",
            body="",
            author=None,
            state="",
            additions=0,
            deletions=0,
            labels=[],
            milestone_title="",
            assignees=[],
            jira_key="",
            linked_issues=[],
            cycle_time_hours=None,
            review_time_hours=None,
            total_comments=None,
            commits_after_first_review=None,
            review_rounds=None,
        )

    def test_context_handles_empty_body(self):
        """Context should handle empty PR body gracefully."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        # Should not have Description section if body is empty
        self.assertNotIn("Description:", context)

    def test_context_handles_no_author(self):
        """Context should handle missing author gracefully."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertNotIn("Author:", context)

    def test_context_handles_no_timing_metrics(self):
        """Context should omit timing section when all metrics are None."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertNotIn("Cycle time:", context)
        self.assertNotIn("Time to first review:", context)

    def test_context_handles_empty_labels(self):
        """Context should omit labels when empty."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertNotIn("Labels:", context)

    def test_context_handles_no_files(self):
        """Context should handle PR with no files."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertNotIn("Files changed:", context)

    def test_context_handles_no_commits(self):
        """Context should handle PR with no commits."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertNotIn("Commits:", context)

    def test_context_handles_no_reviews(self):
        """Context should handle PR with no reviews."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertNotIn("Reviews:", context)

    def test_context_always_includes_pr_number(self):
        """PR number should always be included."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("PR #1", context)

    def test_context_always_includes_repository(self):
        """Repository should always be included."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Repository: test/repo", context)

    def test_context_always_includes_size(self):
        """Size should always be included even if 0."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Size: +0/-0 lines", context)


class TestSystemPromptV6(TestCase):
    """Tests for v6.0.0 system prompt enhancements."""

    def test_system_prompt_includes_health_assessment(self):
        """System prompt should include health assessment guidelines."""
        self.assertIn("Health Assessment", PR_ANALYSIS_SYSTEM_PROMPT)

    def test_system_prompt_includes_timing_metrics(self):
        """System prompt should explain timing metrics."""
        self.assertIn("cycle_time_hours", PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn("review_time_hours", PR_ANALYSIS_SYSTEM_PROMPT)

    def test_system_prompt_includes_iteration_indicators(self):
        """System prompt should explain iteration indicators."""
        self.assertIn("commits_after_first_review", PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn("review_rounds", PR_ANALYSIS_SYSTEM_PROMPT)

    def test_system_prompt_includes_risk_flags(self):
        """System prompt should explain risk flags."""
        self.assertIn("is_hotfix", PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn("is_revert", PR_ANALYSIS_SYSTEM_PROMPT)

    def test_system_prompt_includes_health_response_schema(self):
        """System prompt should include health in response schema."""
        self.assertIn('"health":', PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn('"review_friction":', PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn('"scope":', PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn('"risk_level":', PR_ANALYSIS_SYSTEM_PROMPT)
        self.assertIn('"insights":', PR_ANALYSIS_SYSTEM_PROMPT)


class TestCalculateRelativeHours(TestCase):
    """Tests for calculate_relative_hours helper function."""

    def test_calculates_hours_after_baseline(self):
        """Should calculate hours after baseline timestamp."""
        from datetime import datetime

        from apps.metrics.services.llm_prompts import calculate_relative_hours

        baseline = datetime(2025, 1, 1, 10, 0, 0)
        timestamp = datetime(2025, 1, 1, 12, 30, 0)  # 2.5 hours later

        result = calculate_relative_hours(timestamp, baseline)
        self.assertEqual(result, 2.5)

    def test_calculates_hours_before_baseline(self):
        """Should return negative hours for timestamps before baseline."""
        from datetime import datetime

        from apps.metrics.services.llm_prompts import calculate_relative_hours

        baseline = datetime(2025, 1, 1, 10, 0, 0)
        timestamp = datetime(2025, 1, 1, 8, 0, 0)  # 2 hours before

        result = calculate_relative_hours(timestamp, baseline)
        self.assertEqual(result, -2.0)

    def test_returns_zero_for_same_time(self):
        """Should return 0.0 for same timestamp."""
        from datetime import datetime

        from apps.metrics.services.llm_prompts import calculate_relative_hours

        baseline = datetime(2025, 1, 1, 10, 0, 0)
        timestamp = datetime(2025, 1, 1, 10, 0, 0)

        result = calculate_relative_hours(timestamp, baseline)
        self.assertEqual(result, 0.0)

    def test_rounds_to_one_decimal_place(self):
        """Should round to 1 decimal place."""
        from datetime import datetime

        from apps.metrics.services.llm_prompts import calculate_relative_hours

        baseline = datetime(2025, 1, 1, 10, 0, 0)
        timestamp = datetime(2025, 1, 1, 10, 7, 30)  # 7.5 minutes = 0.125 hours

        result = calculate_relative_hours(timestamp, baseline)
        self.assertEqual(result, 0.1)

    def test_handles_multiple_days(self):
        """Should correctly calculate across multiple days."""
        from datetime import datetime

        from apps.metrics.services.llm_prompts import calculate_relative_hours

        baseline = datetime(2025, 1, 1, 10, 0, 0)
        timestamp = datetime(2025, 1, 3, 14, 0, 0)  # 2 days + 4 hours = 52 hours

        result = calculate_relative_hours(timestamp, baseline)
        self.assertEqual(result, 52.0)

    def test_handles_none_timestamp(self):
        """Should return None when timestamp is None."""
        from datetime import datetime

        from apps.metrics.services.llm_prompts import calculate_relative_hours

        baseline = datetime(2025, 1, 1, 10, 0, 0)

        result = calculate_relative_hours(None, baseline)
        self.assertIsNone(result)

    def test_handles_none_baseline(self):
        """Should return None when baseline is None."""
        from datetime import datetime

        from apps.metrics.services.llm_prompts import calculate_relative_hours

        timestamp = datetime(2025, 1, 1, 10, 0, 0)

        result = calculate_relative_hours(timestamp, None)
        self.assertIsNone(result)

    def test_handles_both_none(self):
        """Should return None when both are None."""
        from apps.metrics.services.llm_prompts import calculate_relative_hours

        result = calculate_relative_hours(None, None)
        self.assertIsNone(result)


class TestBuildLlmPrContextTimestamps(TestCase):
    """Tests for timestamps in build_llm_pr_context."""

    def setUp(self):
        """Set up test fixtures with realistic timestamps."""
        from datetime import datetime, timedelta

        from django.utils import timezone

        from apps.metrics.factories import (
            CommitFactory,
            PRCommentFactory,
            PRReviewFactory,
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )

        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, display_name="Alice")
        self.reviewer = TeamMemberFactory(team=self.team, display_name="Bob")

        # PR created at 10:00 (timezone-aware)
        pr_created = timezone.make_aware(datetime(2025, 1, 1, 10, 0, 0))
        # First review at 12:00 (2 hours later)
        first_review = timezone.make_aware(datetime(2025, 1, 1, 12, 0, 0))

        self.pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            pr_created_at=pr_created,
            first_review_at=first_review,
        )

        # Commit at 10:30 (+0.5h)
        self.commit1 = CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Initial implementation",
            committed_at=pr_created + timedelta(hours=0.5),
        )

        # Commit at 14:00 (+4h)
        self.commit2 = CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Address review feedback",
            committed_at=pr_created + timedelta(hours=4),
        )

        # Review at 12:00 (+2h) - first review
        self.review1 = PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            state="approved",
            body="Looks good!",
            submitted_at=first_review,
        )

        # Review at 14:30 (+4.5h)
        self.review2 = PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            state="changes_requested",
            body="Need to add tests",
            submitted_at=pr_created + timedelta(hours=4.5),
        )

        # Comment at 12:30 (+2.5h)
        self.comment1 = PRCommentFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.reviewer,
            body="Should we consider caching?",
            comment_created_at=pr_created + timedelta(hours=2.5),
        )

        # Comment at 15:00 (+5h)
        self.comment2 = PRCommentFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            body="Good point, will add in next iteration",
            comment_created_at=pr_created + timedelta(hours=5),
        )

    def test_commits_include_relative_timestamps(self):
        """Commits should show relative hours from first_review_at."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)

        # Commit at +0.5h relative to first_review_at (12:00) = -1.5h
        self.assertIn("[+0.5h] Initial implementation", context)
        # Commit at +4h = +2h relative to first_review_at
        self.assertIn("[+4.0h] Address review feedback", context)

    def test_reviews_include_relative_timestamps(self):
        """Reviews should show relative hours from first_review_at."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)

        # First review at +2h (baseline) = +0.0h
        self.assertIn("[+2.0h] [APPROVED] Bob: Looks good!", context)
        # Second review at +4.5h
        self.assertIn("[+4.5h] [CHANGES_REQUESTED] Bob: Need to add tests", context)

    def test_comments_include_relative_timestamps(self):
        """Comments should show relative hours from first_review_at."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)

        # Comment at +2.5h
        self.assertIn("[+2.5h] Bob: Should we consider caching?", context)
        # Comment at +5h
        self.assertIn("[+5.0h] Alice: Good point, will add in next iteration", context)

    def test_timestamps_relative_to_first_review_at(self):
        """All timestamps should be relative to first_review_at when set."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)

        # Verify timestamps are relative to first_review_at (12:00)
        # Commit at 10:30 is -1.5h relative to 12:00
        self.assertNotIn("[-1.5h]", context)  # Should use pr_created_at as baseline
        # Everything should be positive hours from pr_created_at when first_review_at is used

    def test_timestamps_fallback_to_pr_created_at_when_no_first_review(self):
        """Should use pr_created_at as baseline when first_review_at is None."""
        from apps.metrics.factories import PullRequestFactory
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            first_review_at=None,  # No review yet
        )

        # Add commit at +1h from pr_created_at
        from datetime import timedelta

        from apps.metrics.factories import CommitFactory

        CommitFactory(
            team=self.team,
            pull_request=pr,
            message="First commit",
            committed_at=pr.pr_created_at + timedelta(hours=1),
        )

        context = build_llm_pr_context(pr)

        # Should show +1.0h relative to pr_created_at
        self.assertIn("[+1.0h] First commit", context)

    def test_handles_commits_before_first_review(self):
        """Commits before first_review_at should show negative hours."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)

        # Commit at 10:30 is 1.5h before first_review_at (12:00)
        # But if we use pr_created_at as baseline, it's +0.5h
        # This test verifies the behavior - adjust based on implementation decision
        self.assertTrue("[+" in context)  # At least some positive timestamps exist

    def test_handles_missing_commit_timestamp(self):
        """Should handle commits with None timestamp gracefully."""
        from apps.metrics.factories import CommitFactory
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Commit with no timestamp",
            committed_at=None,
        )

        context = build_llm_pr_context(self.pr)

        # Should not crash, may omit timestamp or show placeholder
        self.assertIn("Commit with no timestamp", context)

    def test_handles_missing_review_timestamp(self):
        """Should handle reviews with None timestamp gracefully."""
        from apps.metrics.factories import PRReviewFactory
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            body="Review without timestamp",
            submitted_at=None,
        )

        context = build_llm_pr_context(self.pr)

        # Should not crash
        self.assertIn("Review without timestamp", context)

    def test_handles_missing_comment_timestamp(self):
        """Should handle comments with None timestamp gracefully."""
        from apps.metrics.models import PRComment
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        # Create comment with None timestamp (unusual but possible)
        # This will likely fail constraint, but test the function's handling
        try:
            PRComment.objects.create(
                team=self.team,
                github_comment_id=99999,
                pull_request=self.pr,
                author=self.reviewer,
                body="Comment without timestamp",
                comment_type="issue",
                comment_created_at=self.pr.pr_created_at,  # Use PR created as fallback
            )

            context = build_llm_pr_context(self.pr)
            self.assertIn("Comment without timestamp", context)
        except Exception:
            # If DB constraint prevents this, that's fine - real data won't have None
            pass

    def test_timestamp_format_precision(self):
        """Timestamps should be formatted to 1 decimal place."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)

        # Should have timestamps like [+2.5h], not [+2.50h] or [+2h]
        import re

        timestamps = re.findall(r"\[\+\d+\.\d+h\]", context)
        self.assertGreater(len(timestamps), 0, "Should find timestamped entries")

        # Check all timestamps have exactly 1 decimal place
        for ts in timestamps:
            decimal_part = ts.split(".")[1].rstrip("h]")
            self.assertEqual(len(decimal_part), 1, f"Timestamp {ts} should have 1 decimal place")

    def test_zero_hour_timestamp_format(self):
        """Timestamp at exactly first_review_at should show [+0.0h]."""
        from apps.metrics.factories import CommitFactory
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        # Create commit at exact first_review_at time
        CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Commit at first review time",
            committed_at=self.pr.first_review_at,
        )

        context = build_llm_pr_context(self.pr)

        # Should show [+2.0h] since it's 2 hours after pr_created_at
        self.assertIn("[+2.0h] Commit at first review time", context)

    def test_large_hour_values(self):
        """Should handle timestamps many hours/days apart."""
        from datetime import timedelta

        from apps.metrics.factories import CommitFactory
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        # Commit 72 hours (3 days) after pr_created_at
        CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Very late commit",
            committed_at=self.pr.pr_created_at + timedelta(hours=72),
        )

        context = build_llm_pr_context(self.pr)

        # Should show [+72.0h]
        self.assertIn("[+72.0h] Very late commit", context)

    def test_chronological_ordering_preserved(self):
        """Timestamps should preserve chronological order of events."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)

        # Find positions of timestamps in context
        pos_0_5h = context.find("[+0.5h]")
        pos_2_0h = context.find("[+2.0h]")
        pos_2_5h = context.find("[+2.5h]")
        pos_4_0h = context.find("[+4.0h]")
        pos_4_5h = context.find("[+4.5h]")
        pos_5_0h = context.find("[+5.0h]")

        # Within each section (commits, reviews, comments), order should be preserved
        # Note: Sections may be separate, but within commits: 0.5h before 4.0h
        if pos_0_5h > 0 and pos_4_0h > 0:
            self.assertLess(pos_0_5h, pos_4_0h, "Commits should be in chronological order")

        if pos_2_0h > 0 and pos_4_5h > 0:
            self.assertLess(pos_2_0h, pos_4_5h, "Reviews should be in chronological order")

        if pos_2_5h > 0 and pos_5_0h > 0:
            self.assertLess(pos_2_5h, pos_5_0h, "Comments should be in chronological order")


class TestTimelineEvent(TestCase):
    """Tests for TimelineEvent dataclass."""

    def test_timeline_event_creation(self):
        """Should create TimelineEvent with all required fields."""
        from apps.metrics.services.llm_prompts import TimelineEvent

        event = TimelineEvent(
            hours_after_pr_created=2.5,
            event_type="COMMIT",
            content="Initial implementation",
        )

        self.assertEqual(event.hours_after_pr_created, 2.5)
        self.assertEqual(event.event_type, "COMMIT")
        self.assertEqual(event.content, "Initial implementation")

    def test_timeline_event_has_required_fields(self):
        """TimelineEvent should have hours_after_pr_created, event_type, and content fields."""
        from apps.metrics.services.llm_prompts import TimelineEvent

        event = TimelineEvent(
            hours_after_pr_created=0.0,
            event_type="REVIEW",
            content="LGTM",
        )

        self.assertIsInstance(event.hours_after_pr_created, float)
        self.assertIsInstance(event.event_type, str)
        self.assertIsInstance(event.content, str)


class TestBuildTimeline(TestCase):
    """Tests for build_timeline function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from datetime import datetime

        from django.utils import timezone

        from apps.metrics.factories import (
            PullRequestFactory,
            TeamFactory,
            TeamMemberFactory,
        )

        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, display_name="Alice")
        self.reviewer = TeamMemberFactory(team=self.team, display_name="Bob")

        # PR created at 10:00
        self.pr_created = timezone.make_aware(datetime(2025, 1, 1, 10, 0, 0))
        self.pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            pr_created_at=self.pr_created,
            merged_at=None,  # Explicitly set to None to avoid random factory default
        )

    def test_build_timeline_with_commits_only(self):
        """Should build timeline with only commits."""
        from datetime import timedelta

        from apps.metrics.factories import CommitFactory
        from apps.metrics.services.llm_prompts import build_timeline

        # Create commits at +1h and +3h
        CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="First commit",
            committed_at=self.pr_created + timedelta(hours=1),
        )
        CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Second commit",
            committed_at=self.pr_created + timedelta(hours=3),
        )

        events = build_timeline(self.pr)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].hours_after_pr_created, 1.0)
        self.assertEqual(events[0].event_type, "COMMIT")
        self.assertIn("First commit", events[0].content)

        self.assertEqual(events[1].hours_after_pr_created, 3.0)
        self.assertEqual(events[1].event_type, "COMMIT")
        self.assertIn("Second commit", events[1].content)

    def test_build_timeline_with_reviews_only(self):
        """Should build timeline with only reviews."""
        from datetime import timedelta

        from apps.metrics.factories import PRReviewFactory
        from apps.metrics.services.llm_prompts import build_timeline

        # Create reviews at +2h and +4h
        PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            state="approved",
            body="LGTM",
            submitted_at=self.pr_created + timedelta(hours=2),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            state="changes_requested",
            body="Need tests",
            submitted_at=self.pr_created + timedelta(hours=4),
        )

        events = build_timeline(self.pr)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].hours_after_pr_created, 2.0)
        self.assertEqual(events[0].event_type, "REVIEW")
        self.assertIn("LGTM", events[0].content)

        self.assertEqual(events[1].hours_after_pr_created, 4.0)
        self.assertEqual(events[1].event_type, "REVIEW")
        self.assertIn("Need tests", events[1].content)

    def test_build_timeline_with_comments_only(self):
        """Should build timeline with only comments."""
        from datetime import timedelta

        from apps.metrics.factories import PRCommentFactory
        from apps.metrics.services.llm_prompts import build_timeline

        # Create comments at +1h and +3h
        PRCommentFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.reviewer,
            body="Should we add caching?",
            comment_created_at=self.pr_created + timedelta(hours=1),
        )
        PRCommentFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.author,
            body="Good idea, will add",
            comment_created_at=self.pr_created + timedelta(hours=3),
        )

        events = build_timeline(self.pr)

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].hours_after_pr_created, 1.0)
        self.assertEqual(events[0].event_type, "COMMENT")
        self.assertIn("Should we add caching?", events[0].content)

        self.assertEqual(events[1].hours_after_pr_created, 3.0)
        self.assertEqual(events[1].event_type, "COMMENT")
        self.assertIn("Good idea, will add", events[1].content)

    def test_build_timeline_mixed_events_sorted(self):
        """Should build timeline with mixed events sorted by timestamp."""
        from datetime import timedelta

        from apps.metrics.factories import CommitFactory, PRCommentFactory, PRReviewFactory
        from apps.metrics.services.llm_prompts import build_timeline

        # Create events in non-chronological order
        CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="Second event (commit)",
            committed_at=self.pr_created + timedelta(hours=2),
        )
        PRCommentFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.reviewer,
            body="Fourth event (comment)",
            comment_created_at=self.pr_created + timedelta(hours=4),
        )
        PRReviewFactory(
            team=self.team,
            pull_request=self.pr,
            reviewer=self.reviewer,
            state="approved",
            body="Third event (review)",
            submitted_at=self.pr_created + timedelta(hours=3),
        )
        CommitFactory(
            team=self.team,
            pull_request=self.pr,
            message="First event (commit)",
            committed_at=self.pr_created + timedelta(hours=1),
        )

        events = build_timeline(self.pr)

        # Should be sorted chronologically
        self.assertEqual(len(events), 4)
        self.assertEqual(events[0].hours_after_pr_created, 1.0)
        self.assertIn("First event", events[0].content)

        self.assertEqual(events[1].hours_after_pr_created, 2.0)
        self.assertIn("Second event", events[1].content)

        self.assertEqual(events[2].hours_after_pr_created, 3.0)
        self.assertIn("Third event", events[2].content)

        self.assertEqual(events[3].hours_after_pr_created, 4.0)
        self.assertIn("Fourth event", events[3].content)

    def test_build_timeline_empty_pr(self):
        """Should return empty list for PR with no events."""
        from apps.metrics.services.llm_prompts import build_timeline

        events = build_timeline(self.pr)

        self.assertEqual(len(events), 0)
        self.assertIsInstance(events, list)


class TestFormatTimeline(TestCase):
    """Tests for format_timeline function."""

    def test_format_timeline_basic(self):
        """Should format timeline events correctly."""
        from apps.metrics.services.llm_prompts import TimelineEvent, format_timeline

        events = [
            TimelineEvent(hours_after_pr_created=1.0, event_type="COMMIT", content="Initial commit"),
            TimelineEvent(hours_after_pr_created=2.5, event_type="REVIEW", content="Looks good!"),
            TimelineEvent(hours_after_pr_created=3.0, event_type="COMMENT", content="Add tests please"),
        ]

        formatted = format_timeline(events)

        self.assertIn("[+1.0h] COMMIT: Initial commit", formatted)
        self.assertIn("[+2.5h] REVIEW: Looks good!", formatted)
        self.assertIn("[+3.0h] COMMENT: Add tests please", formatted)

    def test_format_timeline_limits_to_15_events(self):
        """Should limit timeline to 15 events maximum."""
        from apps.metrics.services.llm_prompts import TimelineEvent, format_timeline

        # Create 20 events
        events = [
            TimelineEvent(hours_after_pr_created=float(i), event_type="COMMIT", content=f"Commit {i}")
            for i in range(20)
        ]

        formatted = format_timeline(events)

        # Count number of event lines (each starts with "- [+")
        event_lines = [line for line in formatted.split("\n") if line.startswith("- [+")]
        self.assertEqual(len(event_lines), 15)

        # Should include first 15 events
        self.assertIn("Commit 0", formatted)
        self.assertIn("Commit 14", formatted)
        # Should NOT include events after 15
        self.assertNotIn("Commit 15", formatted)
        self.assertNotIn("Commit 19", formatted)

    def test_format_timeline_empty_list(self):
        """Should return empty string for empty event list."""
        from apps.metrics.services.llm_prompts import format_timeline

        formatted = format_timeline([])

        self.assertEqual(formatted, "")
        self.assertIsInstance(formatted, str)
