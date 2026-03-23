"""OG image generation service using Pillow.

Generates branded 1200x630 PNG images for social media previews.
Images are pre-generated during the stats pipeline and served from MEDIA_ROOT.
"""

import io
import logging
import os
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps

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

        font_large = _get_font(50)
        font_medium = _get_font(30)
        font_small = _get_font(24)
        font_brand = _get_font(20)
        font_metric = _get_font(42)

        # Brand bar at top
        draw.rectangle([(0, 0), (OG_WIDTH, 4)], fill=ACCENT_COLOR)

        title_x = 60
        if _paste_logo(img, getattr(org_profile, "avatar_url", None), 1030, 56, 110):
            title_x = 60

        draw.text((title_x, 60), org_profile.display_name, fill=TEXT_COLOR, font=font_large)
        draw.text((title_x, 120), "Public GitHub delivery benchmarks", fill=MUTED_COLOR, font=font_medium)
        draw.text(
            (title_x, 168),
            "Cycle time, review load, and PR flow from merged pull requests.",
            fill=MUTED_COLOR,
            font=font_small,
        )

        y_metrics = 255
        metrics = [
            (_format_hours(org_stats.median_cycle_time_hours), "Median Cycle Time"),
            (
                _format_hours(getattr(org_stats, "median_review_time_hours", 0))
                if getattr(org_stats, "median_review_time_hours", None) is not None
                else f"{getattr(org_stats, 'active_contributors_90d', 0)}",
                "Median Review Time"
                if getattr(org_stats, "median_review_time_hours", None) is not None
                else "Active Contributors",
            ),
            (f"{org_stats.total_prs:,}", "Merged PRs"),
        ]
        x_offset = 60
        for value, label in metrics:
            _draw_metric(draw, x_offset, y_metrics, value, label, font_metric, font_small)
            x_offset += 355

        draw.rounded_rectangle([(60, 410), (OG_WIDTH - 60, 505)], radius=18, fill=(24, 33, 51))
        draw.text((90, 438), "AI-related signals", fill=MUTED_COLOR, font=font_small)
        draw.text(
            (90, 465),
            f"{float(getattr(org_stats, 'ai_assisted_pct', 0) or 0):.1f}% of recent work",
            fill=TEXT_COLOR,
            font=font_medium,
        )

        draw.text((60, 548), "tformance.com", fill=BRAND_COLOR, font=font_brand)
        draw.text((60, 576), "Public GitHub delivery benchmarks", fill=MUTED_COLOR, font=font_small)

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
        font_medium = _get_font(30)
        font_small = _get_font(24)
        font_brand = _get_font(20)
        font_metric = _get_font(40)

        draw.rectangle([(0, 0), (OG_WIDTH, 4)], fill=ACCENT_COLOR)

        _paste_logo(img, getattr(org_profile, "avatar_url", None), 1030, 56, 110)

        draw.text((60, 58), org_profile.display_name, fill=MUTED_COLOR, font=font_medium)
        draw.text((60, 108), repo_profile.display_name, fill=TEXT_COLOR, font=font_large)
        draw.text((60, 164), "Public GitHub delivery benchmarks", fill=MUTED_COLOR, font=font_small)

        y_metrics = 245
        metrics = [
            (_format_hours(repo_stats.median_cycle_time_hours), "Median Cycle Time"),
            (
                _format_hours(getattr(repo_stats, "median_review_time_hours", 0))
                if getattr(repo_stats, "median_review_time_hours", None) is not None
                else _format_hours(getattr(repo_stats, "review_time_hours", 0)),
                "Median Review Time",
            ),
            (f"{repo_stats.total_prs:,}", "Merged PRs"),
        ]
        x_offset = 60
        for value, label in metrics:
            _draw_metric(draw, x_offset, y_metrics, value, label, font_metric, font_small)
            x_offset += 355

        draw.rounded_rectangle([(60, 400), (OG_WIDTH - 60, 505)], radius=18, fill=(24, 33, 51))
        draw.text((90, 428), "AI-related signals", fill=MUTED_COLOR, font=font_small)
        draw.text(
            (90, 455),
            f"{float(getattr(repo_stats, 'ai_assisted_pct', 0) or 0):.1f}% of recent work",
            fill=TEXT_COLOR,
            font=font_medium,
        )

        draw.text((60, 548), "tformance.com", fill=BRAND_COLOR, font=font_brand)
        draw.text((60, 576), "Public GitHub delivery benchmarks", fill=MUTED_COLOR, font=font_small)

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


def _draw_metric(draw, x: int, y: int, value: str, label: str, value_font, label_font) -> None:
    draw.text((x, y), value, fill=ACCENT_COLOR, font=value_font)
    draw.text((x, y + 56), label, fill=MUTED_COLOR, font=label_font)


def _format_hours(value) -> str:
    hours = float(value or 0)
    if 0 < hours < 1:
        return "<1h"
    return f"{hours:.1f}h"


def _paste_logo(img, avatar_url: str | None, x: int, y: int, size: int) -> bool:
    if not avatar_url:
        return False

    try:
        if avatar_url.startswith(("http://", "https://")):
            with urlopen(avatar_url, timeout=5) as response:
                logo = Image.open(io.BytesIO(response.read())).convert("RGBA")
        elif os.path.exists(avatar_url):
            logo = Image.open(avatar_url).convert("RGBA")
        else:
            return False

        logo = ImageOps.fit(logo, (size, size))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (size, size)], radius=24, fill=255)
        img.paste(logo, (x, y), mask)
        return True
    except Exception:
        logger.debug("Unable to load org logo for OG image", exc_info=True)
        return False
