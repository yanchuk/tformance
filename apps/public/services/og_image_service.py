"""OG image generation service using Pillow.

Generates branded 1200x630 PNG images for social media previews.
Images are pre-generated during the stats pipeline and served from MEDIA_ROOT.
"""

import io
import logging
import os
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

# OG image dimensions (standard for social media)
OG_WIDTH = 1200
OG_HEIGHT = 630

# Brand colors (light theme — matches website tformance-light)
BG_COLOR = (250, 250, 248)  # #FAFAF8 warm off-white
TEXT_COLOR = (31, 41, 55)  # #1F2937 dark gray
MUTED_COLOR = (107, 114, 128)  # #6B7280 gray-500
ACCENT_COLOR = (249, 115, 22)  # #F97316 coral orange
AI_BADGE_BG = (255, 247, 237)  # #FFF7ED warm orange-50 (coral tint for AI badge)

# Bundled font path
_FONT_DIR = Path(__file__).resolve().parents[3] / "static" / "fonts"
_DM_SANS = _FONT_DIR / "DMSans.ttf"

# System font fallbacks
_SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
]

# Max character widths before truncation
_MAX_TITLE_CHARS = 32
_MAX_AI_TOOLS_CHARS = 40


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load DM Sans font with weight selection, falling back to system fonts."""
    if _DM_SANS.exists():
        try:
            font = ImageFont.truetype(str(_DM_SANS), size)
            variation = "Bold" if bold else "Regular"
            font.set_variation_by_name(variation)
            return font
        except Exception:
            pass

    for font_path in _SYSTEM_FONTS:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1] + "\u2026"


def _truncate_to_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """Truncate text with ellipsis to fit within pixel width."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_width:
        return text
    ellipsis = "\u2026"
    for i in range(len(text), 0, -1):
        candidate = text[:i] + ellipsis
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return candidate
    return ellipsis


class OGImageService:
    """Generates branded OG images with org/repo metrics."""

    @staticmethod
    def generate_org_image(org_profile, org_stats) -> bytes:
        """Generate a 1200x630 PNG for an organization."""
        img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        font_title = _get_font(72, bold=True)
        font_subtitle = _get_font(24, bold=False)
        font_metric_value = _get_font(68, bold=True)
        font_metric_label = _get_font(24, bold=False)
        font_ai = _get_font(28, bold=False)
        font_brand = _get_font(28, bold=True)

        # Top accent bar
        draw.rectangle([(0, 0), (OG_WIDTH, 8)], fill=ACCENT_COLOR)

        # Logo inline with title
        logo_size = 72
        logo_x = 60
        title_x = 60
        has_logo = _paste_logo(img, getattr(org_profile, "avatar_url", None), logo_x, 42, logo_size)
        if has_logo:
            title_x = logo_x + logo_size + 20

        # Title + subtitle (pixel-based truncation for large font)
        max_title_w = OG_WIDTH - title_x - 80  # leave right margin
        title = _truncate_to_width(draw, org_profile.display_name, font_title, max_title_w)
        draw.text((title_x, 45), title, fill=TEXT_COLOR, font=font_title)
        draw.text((title_x, 128), "Public GitHub Delivery Benchmarks", fill=MUTED_COLOR, font=font_subtitle)

        # Metrics row
        y_metrics = 230
        metrics = _build_org_metrics(org_stats)
        _draw_metrics_row(draw, 60, y_metrics, metrics, font_metric_value, font_metric_label)

        # AI badge — coral-tinted background
        ai_line = _build_ai_line(org_stats)
        if ai_line:
            _draw_ai_badge(draw, 60, 420, ai_line, font_ai)

        # Brand motif — geometric circles on right side
        _draw_brand_motif(img)
        draw = ImageDraw.Draw(img)  # refresh draw after composite

        # Footer: brand name in dark text with coral dot accent
        _draw_brand_footer(draw, font_brand)

        # Bottom accent bar
        draw.rectangle([(0, OG_HEIGHT - 8), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    @staticmethod
    def generate_repo_image(repo_profile, repo_stats, org_profile) -> bytes:
        """Generate a 1200x630 PNG for a repository."""
        img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
        draw = ImageDraw.Draw(img)

        font_org = _get_font(38, bold=True)  # Fix 3: larger/bolder org name
        font_repo = _get_font(62, bold=True)
        font_subtitle = _get_font(22, bold=False)
        font_metric_value = _get_font(64, bold=True)
        font_metric_label = _get_font(24, bold=False)
        font_ai = _get_font(28, bold=False)
        font_brand = _get_font(28, bold=True)

        # Top accent bar
        draw.rectangle([(0, 0), (OG_WIDTH, 8)], fill=ACCENT_COLOR)

        # Logo inline with org/repo name
        logo_size = 72
        logo_x = 60
        title_x = 60
        has_logo = _paste_logo(img, getattr(org_profile, "avatar_url", None), logo_x, 35, logo_size)
        if has_logo:
            title_x = logo_x + logo_size + 20

        # Org name / repo name (pixel-based truncation)
        max_title_w = OG_WIDTH - title_x - 80
        org_name = _truncate_to_width(draw, org_profile.display_name, font_org, max_title_w - 30)
        repo_name = _truncate_to_width(draw, repo_profile.display_name, font_repo, max_title_w)
        draw.text((title_x, 30), f"{org_name} /", fill=TEXT_COLOR, font=font_org)
        draw.text((title_x, 72), repo_name, fill=TEXT_COLOR, font=font_repo)
        draw.text((title_x, 145), "Public GitHub Delivery Benchmarks", fill=MUTED_COLOR, font=font_subtitle)

        # Metrics row
        y_metrics = 240
        metrics = _build_repo_metrics(repo_stats)
        _draw_metrics_row(draw, 60, y_metrics, metrics, font_metric_value, font_metric_label)

        # AI badge — coral-tinted background
        ai_line = _build_ai_line(repo_stats)
        if ai_line:
            _draw_ai_badge(draw, 60, 430, ai_line, font_ai)

        # Brand motif
        _draw_brand_motif(img)
        draw = ImageDraw.Draw(img)

        # Footer: brand name in dark text with coral dot accent
        _draw_brand_footer(draw, font_brand)

        # Bottom accent bar
        draw.rectangle([(0, OG_HEIGHT - 8), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

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


def _build_org_metrics(stats) -> list[tuple[str, str]]:
    """Build metrics list for org OG image."""
    return [
        (_format_hours(stats.median_cycle_time_hours), "Cycle Time"),
        (
            _format_hours(getattr(stats, "median_review_time_hours", 0))
            if getattr(stats, "median_review_time_hours", None) is not None
            else f"{getattr(stats, 'active_contributors_90d', 0)}",
            "Review Time" if getattr(stats, "median_review_time_hours", None) is not None else "Contributors",
        ),
        (f"{stats.total_prs:,}", "Merged PRs"),
    ]


def _build_repo_metrics(stats) -> list[tuple[str, str]]:
    """Build metrics list for repo OG image."""
    return [
        (_format_hours(stats.median_cycle_time_hours), "Cycle Time"),
        (
            _format_hours(getattr(stats, "median_review_time_hours", 0))
            if getattr(stats, "median_review_time_hours", None) is not None
            else _format_hours(getattr(stats, "review_time_hours", 0)),
            "Review Time",
        ),
        (f"{stats.total_prs:,}", "Merged PRs"),
    ]


def _build_ai_line(stats) -> str:
    """Build the AI info text line. Returns empty string if no AI data."""
    ai_pct = float(getattr(stats, "ai_assisted_pct", 0) or 0)
    if ai_pct <= 0:
        return ""

    line = f"{ai_pct:.0f}% AI-Assisted"

    # Try to get tool names
    tools = getattr(stats, "top_ai_tools", None)
    if not tools:
        # Repo stats: try breakdown_data
        breakdown = getattr(stats, "breakdown_data", None)
        if breakdown and isinstance(breakdown, dict):
            tools = breakdown.get("ai_tools", [])

    if tools and isinstance(tools, list):
        tool_names = [str(t.get("name", "")) if isinstance(t, dict) else str(t) for t in tools[:3]]
        tool_names = [n for n in tool_names if n]  # filter empty
        if tool_names:
            tools_str = _truncate(", ".join(tool_names), _MAX_AI_TOOLS_CHARS)
            line += f"  \u00b7  {tools_str}"

    return line


def _draw_brand_motif(img: Image.Image) -> None:
    """Draw subtle geometric brand motif on the right side of the image.

    Overlapping coral-orange circle outlines at low opacity, creating
    a distinctive visual anchor without competing with content.
    """
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    # Coral with low opacity for subtlety
    stroke_color = (*ACCENT_COLOR, 30)  # ~12% opacity
    fill_color = (*ACCENT_COLOR, 12)  # ~5% opacity

    # Large circle — anchored bottom-right, mostly off-canvas
    cx, cy, r = OG_WIDTH - 80, OG_HEIGHT - 100, 280
    od.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=stroke_color, width=3)

    # Medium circle — overlapping, offset up-left
    cx2, cy2, r2 = OG_WIDTH - 200, OG_HEIGHT - 260, 180
    od.ellipse([(cx2 - r2, cy2 - r2), (cx2 + r2, cy2 + r2)], outline=stroke_color, width=2)
    od.ellipse([(cx2 - r2 + 8, cy2 - r2 + 8), (cx2 + r2 - 8, cy2 + r2 - 8)], fill=fill_color)

    # Small accent circle — solid fill, top-right area
    cx3, cy3, r3 = OG_WIDTH - 120, 180, 50
    od.ellipse([(cx3 - r3, cy3 - r3), (cx3 + r3, cy3 + r3)], fill=(*ACCENT_COLOR, 18))

    # Composite onto image
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def _draw_ai_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font) -> None:
    """Draw AI info as a branded badge with coral-tinted background."""
    bbox = draw.textbbox((x, y), text, font=font)
    pad_x, pad_y = 16, 10
    draw.rounded_rectangle(
        [(bbox[0] - pad_x, bbox[1] - pad_y), (bbox[2] + pad_x, bbox[3] + pad_y)],
        radius=12,
        fill=AI_BADGE_BG,
    )
    draw.text((x, y), text, fill=MUTED_COLOR, font=font)


def _draw_brand_footer(draw: ImageDraw.ImageDraw, font) -> None:
    """Draw brand footer with dark text and coral dot accent."""
    brand_text = "tformance.com"
    brand_bbox = draw.textbbox((0, 0), brand_text, font=font)
    brand_w = brand_bbox[2] - brand_bbox[0]
    brand_h = brand_bbox[3] - brand_bbox[1]
    bx = OG_WIDTH - 60 - brand_w
    by = 555
    # Coral dot before brand name
    dot_r = 6
    draw.ellipse(
        [(bx - dot_r * 2 - 12, by + brand_h // 2 - dot_r), (bx - 12, by + brand_h // 2 + dot_r)],
        fill=ACCENT_COLOR,
    )
    draw.text((bx, by), brand_text, fill=TEXT_COLOR, font=font)


def _draw_metrics_row(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    metrics: list[tuple[str, str]],
    value_font,
    label_font,
) -> None:
    """Draw a row of 3 metrics with values and labels."""
    spacing = 370
    for i, (value, label) in enumerate(metrics):
        mx = x + i * spacing
        draw.text((mx, y), value, fill=TEXT_COLOR, font=value_font)
        draw.text((mx, y + 85), label, fill=MUTED_COLOR, font=label_font)


def _format_hours(value) -> str:
    hours = float(value or 0)
    if 0 < hours < 1:
        return "<1h"
    return f"{hours:.1f}h"


def _paste_logo(img, avatar_url: str | None, x: int, y: int, size: int) -> bool:
    """Download and paste org logo with rounded corners. Returns True if successful."""
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
        ImageDraw.Draw(mask).rounded_rectangle([(0, 0), (size, size)], radius=14, fill=255)
        # Composite onto white background to avoid transparency artifacts on light bg
        bg = Image.new("RGB", (size, size), BG_COLOR)
        bg.paste(logo, (0, 0), mask)
        img.paste(bg, (x, y))
        return True
    except Exception:
        logger.debug("Unable to load org logo for OG image", exc_info=True)
        return False
