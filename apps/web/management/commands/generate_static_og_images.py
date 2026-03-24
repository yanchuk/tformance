"""Generate static OG images for marketing pages.

Writes directly to static/images/ so they can be committed to git
and baked into the Docker image during collectstatic.

Usage:
    python manage.py generate_static_og_images
"""

import os
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate static OG images for landing, report, pricing, features pages"

    def handle(self, *args, **options):
        from apps.web.services.og_image_service import (
            generate_features_image,
            generate_landing_image,
            generate_pricing_image,
            generate_report_image,
        )

        static_dir = Path(__file__).resolve().parents[4] / "static" / "images"
        os.makedirs(static_dir, exist_ok=True)

        images = [
            ("og-image.png", generate_landing_image, "Landing/general"),
            ("og-report.png", generate_report_image, "AI Impact Report"),
            ("og-pricing.png", generate_pricing_image, "Pricing"),
            ("og-features.png", generate_features_image, "Features"),
        ]

        for filename, generator, label in images:
            path = static_dir / filename
            data = generator()
            with open(path, "wb") as f:
                f.write(data)
            self.stdout.write(f"  {label}: {path} ({len(data):,} bytes)")

        self.stdout.write(self.style.SUCCESS(f"\nGenerated {len(images)} OG images in {static_dir}"))
