"""Static OG image generator for marketing/landing pages.

Generates branded 1200x630 PNG images for non-dynamic pages (landing, report,
pricing, features). Uses the same brand system as the public OG image service.

Usage:
    python manage.py generate_static_og_images
"""

import io

from PIL import Image, ImageDraw

from apps.public.services.og_image_service import (
    ACCENT_COLOR,
    BG_COLOR,
    MUTED_COLOR,
    OG_HEIGHT,
    OG_WIDTH,
    TEXT_COLOR,
    _draw_brand_footer,
    _draw_brand_motif,
    _get_font,
)


def generate_landing_image() -> bytes:
    """Generate OG image for the landing/home page."""
    img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(80, bold=True)
    font_subtitle = _get_font(34, bold=False)
    font_caps = _get_font(34, bold=True)
    font_integrations = _get_font(30, bold=False)

    # Top accent bar
    draw.rectangle([(0, 0), (OG_WIDTH, 8)], fill=ACCENT_COLOR)

    # Content block — vertically centered (total block ~330px, centered in 630-16=614px usable)
    # Center offset: (614 - 330) / 2 + 8 = ~150
    y0 = 100

    # Title
    draw.text((60, y0), "Tformance", fill=TEXT_COLOR, font=font_title)

    # Subtitle
    draw.text((60, y0 + 100), "Engineering Delivery Analytics", fill=MUTED_COLOR, font=font_subtitle)
    draw.text((60, y0 + 145), "for CTOs who need defensible answers", fill=MUTED_COLOR, font=font_subtitle)

    # Capabilities
    draw.text((60, y0 + 240), "Cycle Time  \u00b7  Review Health  \u00b7  AI Signals", fill=TEXT_COLOR, font=font_caps)

    # Integrations
    draw.text((60, y0 + 295), "GitHub  \u00b7  Jira  \u00b7  Slack", fill=MUTED_COLOR, font=font_integrations)

    # Brand motif
    _draw_brand_motif(img)
    draw = ImageDraw.Draw(img)

    # Footer
    _draw_brand_footer(draw, _get_font(28, bold=True))

    # Bottom accent bar
    draw.rectangle([(0, OG_HEIGHT - 8), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_report_image() -> bytes:
    """Generate OG image for the AI Impact Report page."""
    img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(62, bold=True)
    font_subtitle = _get_font(30, bold=False)
    font_metric_value = _get_font(64, bold=True)
    font_metric_label = _get_font(30, bold=False)

    # Top accent bar
    draw.rectangle([(0, 0), (OG_WIDTH, 8)], fill=ACCENT_COLOR)

    # Title
    draw.text((60, 45), "Delivery Patterns in", fill=MUTED_COLOR, font=font_subtitle)
    draw.text((60, 85), "AI-Assisted PRs", fill=TEXT_COLOR, font=font_title)

    # Subtitle — tight below title
    draw.text((60, 160), "167K+ PRs across 127 open-source projects", fill=MUTED_COLOR, font=font_subtitle)

    # Metrics row — close to subtitle
    y = 245
    spacing = 380
    metrics = [
        ("11% lower", "Cycle Time"),
        ("23% higher", "PR Volume"),
        ("34%", "AI-Assisted PRs"),
    ]
    for i, (value, label) in enumerate(metrics):
        mx = 60 + i * spacing
        draw.text((mx, y), value, fill=TEXT_COLOR, font=font_metric_value)
        draw.text((mx, y + 85), label, fill=MUTED_COLOR, font=font_metric_label)

    # Brand motif
    _draw_brand_motif(img)
    draw = ImageDraw.Draw(img)

    # Footer
    _draw_brand_footer(draw, _get_font(28, bold=True))

    # Bottom accent bar
    draw.rectangle([(0, OG_HEIGHT - 8), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_pricing_image() -> bytes:
    """Generate OG image for the pricing page."""
    img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(62, bold=True)
    font_subtitle = _get_font(30, bold=False)
    font_caps = _get_font(30, bold=True)
    font_caps_muted = _get_font(30, bold=False)

    # Top accent bar
    draw.rectangle([(0, 0), (OG_WIDTH, 8)], fill=ACCENT_COLOR)

    # Content block — vertically centered (~280px block in 614px usable)
    y0 = 120

    # Title
    draw.text((60, y0), "Tformance Pricing", fill=TEXT_COLOR, font=font_title)

    # Subtitle
    draw.text((60, y0 + 90), "Delivery analytics for smaller", fill=MUTED_COLOR, font=font_subtitle)
    draw.text((60, y0 + 130), "engineering teams", fill=MUTED_COLOR, font=font_subtitle)

    # Value props
    draw.text((60, y0 + 220), "GitHub-first setup  \u00b7  Fast time to value", fill=TEXT_COLOR, font=font_caps)
    draw.text((60, y0 + 270), "No enterprise complexity", fill=MUTED_COLOR, font=font_caps_muted)

    # Brand motif
    _draw_brand_motif(img)
    draw = ImageDraw.Draw(img)

    # Footer
    _draw_brand_footer(draw, _get_font(28, bold=True))

    # Bottom accent bar
    draw.rectangle([(0, OG_HEIGHT - 8), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_features_image() -> bytes:
    """Generate OG image for the features page."""
    img = Image.new("RGB", (OG_WIDTH, OG_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _get_font(62, bold=True)
    font_subtitle = _get_font(28, bold=False)
    font_feature = _get_font(34, bold=True)
    font_feature_label = _get_font(26, bold=False)

    # Top accent bar
    draw.rectangle([(0, 0), (OG_WIDTH, 8)], fill=ACCENT_COLOR)

    # Title
    draw.text((60, 50), "See How Your", fill=TEXT_COLOR, font=font_title)
    draw.text((60, 122), "Team Delivers", fill=TEXT_COLOR, font=font_title)

    # Subtitle — tight below title
    draw.text((60, 210), "Delivery dashboards, AI signals,", fill=MUTED_COLOR, font=font_subtitle)
    draw.text((60, 248), "and where PRs get stuck", fill=MUTED_COLOR, font=font_subtitle)

    # Feature columns — close to subtitle
    y = 330
    spacing = 370
    features = [
        ("Delivery", "Dashboard"),
        ("PR Explorer", "& Filters"),
        ("AI Signals", "& Patterns"),
    ]
    for i, (name, label) in enumerate(features):
        mx = 60 + i * spacing
        draw.text((mx, y), name, fill=TEXT_COLOR, font=font_feature)
        draw.text((mx, y + 48), label, fill=MUTED_COLOR, font=font_feature_label)

    # Brand motif
    _draw_brand_motif(img)
    draw = ImageDraw.Draw(img)

    # Footer
    _draw_brand_footer(draw, _get_font(28, bold=True))

    # Bottom accent bar
    draw.rectangle([(0, OG_HEIGHT - 8), (OG_WIDTH, OG_HEIGHT)], fill=ACCENT_COLOR)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
