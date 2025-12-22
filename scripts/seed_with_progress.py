#!/usr/bin/env python
"""
Progress-tracking wrapper for real project seeding.

Features:
- Displays detailed progress with timing
- Batch processing with state persistence
- Resume capability from last checkpoint
- Statistics output at each stage

Usage:
    # Full seeding with progress
    python scripts/seed_with_progress.py

    # Seed specific project
    python scripts/seed_with_progress.py --project posthog

    # Resume from checkpoint
    python scripts/seed_with_progress.py --resume

    # Custom batch size
    python scripts/seed_with_progress.py --batch-size 50

    # Clear and start fresh
    python scripts/seed_with_progress.py --clear
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env file if it exists
from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")

import django  # noqa: E402

django.setup()

from apps.metrics.seeding.real_project_seeder import (  # noqa: E402
    RealProjectSeeder,
    clear_project_data,
)
from apps.metrics.seeding.real_projects import REAL_PROJECTS, get_project  # noqa: E402

# Checkpoint file for resume capability
CHECKPOINT_FILE = PROJECT_ROOT / ".seeding_checkpoint.json"


def load_checkpoint():
    """Load checkpoint from file."""
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return None


def save_checkpoint(data):
    """Save checkpoint to file."""
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)


def clear_checkpoint():
    """Remove checkpoint file."""
    if CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()


def format_duration(seconds):
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = seconds // 60
    remaining_seconds = seconds % 60
    return f"{int(minutes)}m {int(remaining_seconds)}s"


def print_header(text):
    """Print a header with separators."""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def print_progress(step, total, message, start_time=None):
    """Print progress with optional timing."""
    progress = f"[{step}/{total}]"
    if start_time:
        elapsed = time.time() - start_time
        print(f"{progress} {message} ({format_duration(elapsed)})")
    else:
        print(f"{progress} {message}")


def create_progress_callback(start_time):
    """Create a progress callback function for the seeder."""
    last_fetch_progress = [0]  # Use list to allow mutation in closure

    def callback(step: str, current: int, total: int, message: str):
        elapsed = time.time() - start_time

        if step == "fetch":
            # Show fetch progress every 10 PRs or at key milestones
            if current == 0 or current == total or current - last_fetch_progress[0] >= 10:
                last_fetch_progress[0] = current
                pct = (current / total * 100) if total > 0 else 0
                print(f"   📥 {message} [{pct:.0f}%] ({format_duration(elapsed)})")
        elif step == "seed":
            # Show main seeding steps
            print(f"   [{current}/{total}] {message} ({format_duration(elapsed)})")

    return callback


def seed_project_with_progress(project_name, options, checkpoint=None):
    """Seed a single project with detailed progress tracking.

    Args:
        project_name: Name of the project to seed.
        options: Command line options.
        checkpoint: Optional checkpoint data for resume.

    Returns:
        dict with seeding statistics.
    """
    config = get_project(project_name)

    print_header(f"Seeding: {config.team_name}")
    print(f"  Repository: {config.repo_full_name}")
    print(f"  Max PRs: {options.max_prs or config.max_prs}")
    print(f"  Max Members: {options.max_members or config.max_members}")
    print(f"  Days Back: {options.days_back or config.days_back}")

    # Apply overrides from options (create new config since dataclass is frozen)
    from dataclasses import replace

    if options.max_prs or options.max_members or options.days_back:
        updates = {}
        if options.max_prs:
            updates["max_prs"] = options.max_prs
        if options.max_members:
            updates["max_members"] = options.max_members
        if options.days_back:
            updates["days_back"] = options.days_back
        config = replace(config, **updates)

    # Get GitHub token(s)
    token = options.github_token or os.environ.get("GITHUB_SEEDING_TOKENS")
    if not token:
        print("\n❌ Error: GitHub token required")
        print("   Set GITHUB_SEEDING_TOKENS environment variable (comma-separated for multiple tokens)")
        sys.exit(1)

    # Clear if requested
    if options.clear:
        print(f"\n⏳ Clearing existing data for {config.team_slug}...")
        if clear_project_data(config.team_slug):
            print("   ✅ Data cleared")
        else:
            print("   ℹ️  No existing data to clear")

    # Create seeder
    start_time = time.time()

    print("\n📊 Starting seeding process...")
    print("-" * 40)

    # Step 1: Initialize seeder with progress callback
    step_start = time.time()
    print_progress(1, 6, "Initializing seeder...")

    progress_callback = create_progress_callback(start_time)

    seeder = RealProjectSeeder(
        config=config,
        random_seed=options.seed,
        github_token=token,
        progress_callback=progress_callback,
    )

    print_progress(1, 6, "Seeder initialized", step_start)

    # Save checkpoint
    save_checkpoint(
        {
            "project": project_name,
            "step": 1,
            "started_at": datetime.now().isoformat(),
            "options": {
                "max_prs": options.max_prs,
                "max_members": options.max_members,
                "days_back": options.days_back,
                "seed": options.seed,
            },
        }
    )

    # Run seeding (progress is reported via callback)
    try:
        print("\n🚀 Running seeding pipeline...")
        stats = seeder.seed()

        elapsed = time.time() - start_time
        print(f"\n✅ Seeding complete! ({format_duration(elapsed)})")

    except Exception as e:
        # Save error checkpoint
        save_checkpoint(
            {
                "project": project_name,
                "step": 2,
                "error": str(e),
                "failed_at": datetime.now().isoformat(),
            }
        )
        raise

    # Clear checkpoint on success
    clear_checkpoint()

    return stats


def print_stats(stats):
    """Print seeding statistics."""
    print("\n" + "=" * 40)
    print(" 📊 Seeding Statistics")
    print("=" * 40)
    print(f"  Team created:       {'Yes' if stats.team_created else 'No (existing)'}")
    print(f"  Team members:       {stats.team_members_created}")
    print(f"  Pull requests:      {stats.prs_created}")
    print(f"  Reviews:            {stats.reviews_created}")
    print(f"  Commits:            {stats.commits_created}")
    print(f"  Files:              {stats.files_created}")
    print(f"  Check runs:         {stats.check_runs_created}")
    print(f"  Jira issues:        {stats.jira_issues_created}")
    print(f"  Surveys:            {stats.surveys_created}")
    print(f"  Survey reviews:     {stats.survey_reviews_created}")
    print(f"  AI usage records:   {stats.ai_usage_records}")
    print(f"  Weekly metrics:     {stats.weekly_metrics_created}")
    print(f"  GitHub API calls:   {stats.github_api_calls}")
    print("=" * 40)


def main():
    parser = argparse.ArgumentParser(description="Seed demo data from real GitHub projects with progress tracking")
    parser.add_argument(
        "--project",
        choices=list(REAL_PROJECTS.keys()) + ["all"],
        help="Project to seed ('all' for all projects)",
    )
    parser.add_argument(
        "--max-prs",
        type=int,
        help="Override maximum PRs to fetch",
    )
    parser.add_argument(
        "--max-members",
        type=int,
        help="Override maximum team members",
    )
    parser.add_argument(
        "--days-back",
        type=int,
        help="Override number of days of history to fetch",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--github-token",
        help="GitHub PAT (defaults to GITHUB_SEEDING_TOKENS env var)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing project data before seeding",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of PRs to process per batch (default: 100)",
    )
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="List available projects and exit",
    )

    args = parser.parse_args()

    # List projects
    if args.list_projects:
        print_header("Available Projects")
        for name, config in REAL_PROJECTS.items():
            print(f"\n  {name}")
            print(f"    Repository: {config.repo_full_name}")
            print(f"    Team: {config.team_name} ({config.team_slug})")
            print(f"    Max PRs: {config.max_prs}")
            print(f"    AI adoption rate: {config.ai_base_adoption_rate:.0%}")
        return

    # Check for resume
    checkpoint = None
    if args.resume:
        checkpoint = load_checkpoint()
        if checkpoint:
            print(f"\n📂 Found checkpoint from {checkpoint.get('started_at', 'unknown')}")
            print(f"   Project: {checkpoint.get('project', 'unknown')}")
            print(f"   Step: {checkpoint.get('step', 'unknown')}")
            if "error" in checkpoint:
                print(f"   Last error: {checkpoint.get('error')}")
            args.project = checkpoint.get("project")
        else:
            print("\n❌ No checkpoint found to resume from")
            return

    # Determine projects to seed
    projects = list(REAL_PROJECTS.keys()) if args.project == "all" or not args.project else [args.project]

    print_header(f"Seeding {len(projects)} Project(s)")
    print(f"  Projects: {', '.join(projects)}")

    total_start = time.time()
    all_stats = []

    for i, project_name in enumerate(projects, 1):
        try:
            print(f"\n[{i}/{len(projects)}] Processing {project_name}...")
            stats = seed_project_with_progress(project_name, args, checkpoint)
            all_stats.append((project_name, stats))
            print_stats(stats)
        except Exception as e:
            print(f"\n❌ Error seeding {project_name}: {e}")
            if len(projects) > 1:
                print("   Continuing with next project...")
            else:
                raise

    # Final summary
    total_time = time.time() - total_start
    print_header("Seeding Complete!")
    print(f"  Total projects: {len(all_stats)}")
    print(f"  Total time: {format_duration(total_time)}")

    if all_stats:
        total_prs = sum(s.prs_created for _, s in all_stats)
        total_members = sum(s.team_members_created for _, s in all_stats)
        print(f"  Total PRs: {total_prs}")
        print(f"  Total members: {total_members}")


if __name__ == "__main__":
    main()
