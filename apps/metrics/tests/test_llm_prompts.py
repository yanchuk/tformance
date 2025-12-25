"""Tests for LLM prompts module."""

from django.test import TestCase

from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    PROMPT_VERSION,
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
        self.assertIn("[APPROVED] janesmith: LGTM! Nice clean implementation.", context)

    def test_context_includes_comments(self):
        """Context should include PR comments."""
        from apps.metrics.services.llm_prompts import build_llm_pr_context

        context = build_llm_pr_context(self.pr)
        self.assertIn("Comments:", context)
        self.assertIn("janesmith: Should we use refresh tokens?", context)

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
