"""
Create demo users for showcasing Tformance to potential customers.

Creates demo users with email/password authentication and adds them to
their respective teams with appropriate roles. Idempotent — safe to rerun.

Usage:
    python manage.py setup_demo_users
    python manage.py setup_demo_users --list
    python manage.py setup_demo_users --clear

Demo accounts created:
    - demo@posthog.com / show_me_posthog_data → PostHog Analytics team
    - demo@polar.sh / show_me_polar_data → Polar.sh team
    - demo@n8n.io / show_me_n8n_data → n8n team
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.teams.models import Membership, Team
from apps.teams.roles import ROLE_ADMIN
from apps.web.meta import get_server_root

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
    {
        "email": "demo@n8n.io",
        "password": "show_me_n8n_data",
        "first_name": "n8n",
        "last_name": "Demo",
        "team_slug": "n8n-demo",
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

    def _get_login_url(self):
        return f"{get_server_root()}/accounts/login/"

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
        self.stdout.write(f"\nLogin URL: {self._get_login_url()}")
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
        """Create or update demo users and add them to teams. Idempotent."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Setting Up Demo Users")
        self.stdout.write("=" * 60)

        created_count = 0
        updated_count = 0
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

            if dry_run:
                exists = User.objects.filter(email=email).exists()
                action = "update" if exists else "create"
                self.stdout.write(f"\nWould {action}: {email} → {team.name}")
                if not team.dashboard_accessible:
                    self.stdout.write("  Would set onboarding_complete=True")
                continue

            # Upsert user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email,
                    "first_name": config["first_name"],
                    "last_name": config["last_name"],
                },
            )
            user.set_password(config["password"])
            user.save(update_fields=["password"])

            # Ensure membership exists
            _membership, mem_created = Membership.objects.get_or_create(
                team=team,
                user=user,
                defaults={"role": config["role"]},
            )

            # Ensure dashboard is accessible
            if not team.dashboard_accessible:
                team.onboarding_complete = True
                team.save(update_fields=["onboarding_complete"])
                self.stdout.write(self.style.WARNING(f"  ⚠ Set onboarding_complete=True for {team.name}"))

            if created:
                self.stdout.write(self.style.SUCCESS(f"\n✓ Created: {email}"))
                created_count += 1
            else:
                self.stdout.write(self.style.SUCCESS(f"\n✓ Updated: {email}"))
                updated_count += 1

            self.stdout.write(f"  Password: {config['password']}")
            self.stdout.write(f"  Team: {team.name} ({team_slug})")
            self.stdout.write(f"  Role: {config['role']}")
            self.stdout.write(f"  Membership: {'created' if mem_created else 'exists'}")

        # Summary
        self.stdout.write("\n" + "=" * 60)
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes made"))
        else:
            self.stdout.write(f"Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}")
        self.stdout.write("=" * 60)

        # Print login instructions
        if created_count > 0 or updated_count > 0:
            self.stdout.write("\n" + self.style.SUCCESS("Demo users ready!"))
            self.stdout.write(f"\nLogin at: {self._get_login_url()}")
            self.stdout.write("\nCredentials:")
            for config in DEMO_USERS:
                self.stdout.write(f"  {config['email']} / {config['password']}")
