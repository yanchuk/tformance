"""
Create demo users for showcasing Tformance to potential customers.

Creates demo users with email/password authentication and adds them to
their respective teams with appropriate roles.

Usage:
    python manage.py setup_demo_users
    python manage.py setup_demo_users --list
    python manage.py setup_demo_users --clear

Demo accounts created:
    - demo@posthog.com / show_me_posthog_data → PostHog Analytics team
    - demo@polar.sh / show_me_polar_data → Polar.sh team
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN

User = get_user_model()


# Demo user configurations
DEMO_USERS = [
    {
        "email": "demo@posthog.com",
        "password": "show_me_posthog_data",
        "first_name": "PostHog",
        "last_name": "Demo",
        "team_slug": "posthog-demo",
        "role": ROLE_ADMIN,
    },
    {
        "email": "demo@polar.sh",
        "password": "show_me_polar_data",
        "first_name": "Polar",
        "last_name": "Demo",
        "team_slug": "polar-demo",
        "role": ROLE_ADMIN,
    },
]


class Command(BaseCommand):
    help = "Create demo users for showcasing Tformance"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="List demo user credentials without creating",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove existing demo users before creating",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def handle(self, *args, **options):
        if options["list"]:
            self._list_demo_users()
            return

        if options["clear"]:
            self._clear_demo_users(dry_run=options["dry_run"])

        self._create_demo_users(dry_run=options["dry_run"])

    def _list_demo_users(self):
        """List demo user credentials."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Demo User Credentials")
        self.stdout.write("=" * 60)

        for config in DEMO_USERS:
            team_slug = config["team_slug"]
            try:
                team = Team.objects.get(slug=team_slug)
                team_status = f"✓ Team exists: {team.name}"
            except Team.DoesNotExist:
                team_status = "✗ Team not found"

            self.stdout.write(f"\n  Email:    {config['email']}")
            self.stdout.write(f"  Password: {config['password']}")
            self.stdout.write(f"  Team:     {team_slug} ({team_status})")

            # Check if user exists
            try:
                user = User.objects.get(email=config["email"])
                self.stdout.write(self.style.SUCCESS(f"  Status:   User exists (ID: {user.id})"))
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING("  Status:   User not created yet"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("\nLogin URL: https://dev2.ianchuk.com/accounts/login/")
        self.stdout.write("=" * 60 + "\n")

    def _clear_demo_users(self, dry_run: bool = False):
        """Remove existing demo users."""
        self.stdout.write("\nClearing existing demo users...")

        for config in DEMO_USERS:
            try:
                user = User.objects.get(email=config["email"])
                if dry_run:
                    self.stdout.write(f"  Would delete: {config['email']}")
                else:
                    user.delete()
                    self.stdout.write(self.style.SUCCESS(f"  Deleted: {config['email']}"))
            except User.DoesNotExist:
                self.stdout.write(f"  Not found: {config['email']}")

    @transaction.atomic
    def _create_demo_users(self, dry_run: bool = False):
        """Create demo users and add them to teams."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Creating Demo Users")
        self.stdout.write("=" * 60)

        created_count = 0
        skipped_count = 0

        for config in DEMO_USERS:
            email = config["email"]
            team_slug = config["team_slug"]

            # Check if team exists
            try:
                team = Team.objects.get(slug=team_slug)
            except Team.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"\n✗ Team not found: {team_slug} - skipping {email}"))
                skipped_count += 1
                continue

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(f"\n⏭ User already exists: {email}")
                skipped_count += 1
                continue

            if dry_run:
                self.stdout.write(f"\nWould create: {email} → {team.name}")
                continue

            # Create user (use email as username)
            user = User.objects.create_user(
                username=email,
                email=email,
                password=config["password"],
                first_name=config["first_name"],
                last_name=config["last_name"],
            )

            # Add user to team
            Membership.objects.create(
                team=team,
                user=user,
                role=config["role"],
            )

            self.stdout.write(self.style.SUCCESS(f"\n✓ Created: {email}"))
            self.stdout.write(f"  Password: {config['password']}")
            self.stdout.write(f"  Team: {team.name} ({team_slug})")
            self.stdout.write(f"  Role: {config['role']}")
            created_count += 1

        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
        else:
            self.stdout.write(f"Created: {created_count}, Skipped: {skipped_count}")
        self.stdout.write("=" * 60)

        # Print login instructions
        if created_count > 0:
            self.stdout.write("\n" + self.style.SUCCESS("Demo users ready!"))
            self.stdout.write("\nLogin at: https://dev2.ianchuk.com/accounts/login/")
            self.stdout.write("\nCredentials:")
            for config in DEMO_USERS:
                self.stdout.write(f"  {config['email']} / {config['password']}")
