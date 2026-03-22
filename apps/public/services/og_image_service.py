"""OG image generation service using Pillow.

Generates branded 1200x630 PNG images for social media previews.
Images are pre-generated during the stats pipeline and served from MEDIA_ROOT.
"""

import io
import logging
import os

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# OG image dimensions (standard for social media)
OG_WIDTH = 1200
OG_HEIGHT = 630

# Colors
BG_COLOR = (17, 24, 39)  # dark navy (matches tformance dark theme)
TEXT_COLOR = (255, 255, 255)
ACCENT_COLOR = (99, 102, 241)  # indigo-500
MUTED_COLOR = (156, 163, 175)  # gray-400
BRAND_COLOR = (139, 92, 246)  # violet-500


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Get a font, falling back to default if system fonts unavailable."""
    for font_path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
    ]:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()


class OGImageService:
    """Generates branded OG images with org/repo metrics."""

    @staticmethod
    def generate_org_image(org_profile, org_stats) -> bytes:
        """Generate a 1200x630 PNG for an organization."""
        img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        font_large = _get_font(48)
        font_medium = _get_font(32)
        font_small = _get_font(24)
        font_brand = _get_font(20)

        # Brand bar at top
        draw.rectangle([(0, 0), (OG_WIDTH, 4)], fill=ACCENT_COLOR)

        # Org name
        draw.text((60, 60), org_profile.display_name, fill=TEXT_COLOR, font=font_large)

        # Subtitle
        draw.text((60, 130), "Engineering Benchmarks", fill=MUTED_COLOR, font=font_medium)

        # Metrics row
        y_metrics = 220
        metrics = [
            (f"{org_stats.ai_assisted_pct:.0f}%", "AI Adoption"),
            (f"{org_stats.median_cycle_time_hours:.0f}h", "Cycle Time"),
            (f"{org_stats.total_prs:,}", "Merged PRs"),
        ]
        x_offset = 60
        for value, label in metrics:
            draw.text((x_offset, y_metrics), value, fill=ACCENT_COLOR, font=font_large)
            draw.text((x_offset, y_metrics + 60), label, fill=MUTED_COLOR, font=font_small)
            x_offset += 350

        # Divider
        draw.line([(60, 400), (OG_WIDTH - 60, 400)], fill=MUTED_COLOR, width=1)

        # Brand
        draw.text((60, 430), "tformance.com", fill=BRAND_COLOR, font=font_brand)
        draw.text((60, 460), "Open Source Engineering Analytics", fill=MUTED_COLOR, font=font_small)

        # Bottom accent bar
        draw.rectangle([(0, OG_HEIGHT - 4), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def generate_repo_image(repo_profile, repo_stats, org_profile) -> bytes:
        """Generate a 1200x630 PNG for a repository."""
        img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        font_large = _get_font(48)
        font_medium = _get_font(32)
        font_small = _get_font(24)
        font_brand = _get_font(20)

        # Brand bar at top
        draw.rectangle([(0, 0), (OG_WIDTH, 4)], fill=ACCENT_COLOR)

        # Org / Repo name
        draw.text((60, 50), org_profile.display_name, fill=MUTED_COLOR, font=font_medium)
        draw.text((60, 100), repo_profile.display_name, fill=TEXT_COLOR, font=font_large)

        # Metrics row
        y_metrics = 200
        metrics = [
            (f"{repo_stats.ai_assisted_pct:.0f}%", "AI Adoption"),
            (f"{repo_stats.median_cycle_time_hours:.0f}h", "Cycle Time"),
            (f"{repo_stats.total_prs:,}", "Merged PRs"),
        ]
        x_offset = 60
        for value, label in metrics:
            draw.text((x_offset, y_metrics), value, fill=ACCENT_COLOR, font=font_large)
            draw.text((x_offset, y_metrics + 60), label, fill=MUTED_COLOR, font=font_small)
            x_offset += 350

        # Divider
        draw.line([(60, 380), (OG_WIDTH - 60, 380)], fill=MUTED_COLOR, width=1)

        # Brand
        draw.text((60, 410), "tformance.com", fill=BRAND_COLOR, font=font_brand)
        draw.text((60, 440), "Open Source Engineering Analytics", fill=MUTED_COLOR, font=font_small)

        # Bottom accent bar
        draw.rectangle([(0, OG_HEIGHT - 4), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def generate_and_save_org(org_profile, org_stats, media_root: str) -> str:
        """Generate and save org OG image. Returns the file path."""
        og_dir = os.path.join(media_root, "public_og")
        os.makedirs(og_dir, exist_ok=True)
        path = os.path.join(og_dir, f"{org_profile.public_slug}.png")
        data = OGImageService.generate_org_image(org_profile, org_stats)
        with open(path, "wb") as f:
            f.write(data)
        return path

    @staticmethod
    def generate_and_save_repo(repo_profile, repo_stats, org_profile, media_root: str) -> str:
        """Generate and save repo OG image. Returns the file path."""
        og_dir = os.path.join(media_root, "public_og")
        os.makedirs(og_dir, exist_ok=True)
        path = os.path.join(og_dir, f"{org_profile.public_slug}_{repo_profile.repo_slug}.png")
        data = OGImageService.generate_repo_image(repo_profile, repo_stats, org_profile)
        with open(path, "wb") as f:
            f.write(data)
        return path
