"""Bootstrap Django Site domain for deployment environments.

Usage:
    python manage.py bootstrap_site_domain --domain dev2.ianchuk.com --name Tformance
"""

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Set the Django Site domain and name for the current SITE_ID"

    def add_arguments(self, parser):
        parser.add_argument("--domain", required=True, help="Site domain (e.g., dev2.ianchuk.com)")
        parser.add_argument("--name", required=True, help="Site display name (e.g., Tformance)")

    def handle(self, *args, **options):
        site, created = Site.objects.update_or_create(
            id=settings.SITE_ID,
            defaults={
                "domain": options["domain"],
                "name": options["name"],
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(f"{action} site: {site.domain} ({site.name})")
