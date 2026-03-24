# OG Image Design Guide

Reference for creating and maintaining Open Graph social preview images across tformance.com.

## Design Principles

From Codex review and iterative testing:

- **One focal idea** per card — title or metrics, not both competing
- **2-3 oversized data points** for data cards (68px Bold)
- **Large margins** (60px) on all sides
- **White/light background** for maximum social feed contrast
- **No emoji** — breaks Pillow rendering on Linux without emoji fonts
- **Top + bottom coral accent bars** (8px) frame the card
- **Brand footer** as bottom-right signature with coral dot accent
- **At 300px thumbnail** (typical social feed): title + metrics must be readable, everything else is secondary detail

## Copy Rules

From product DNA (`prd/dna_codex.md`) and ICP (`prd/icp_target_audience_codex.md`):

- **Lead with delivery, AI supports** — never headline AI as the product
- **No overclaims**: use "signals" not "ROI", "patterns" not "impact", "where PRs get stuck" not "explanations"
- **Audience is CTOs** who need defensible answers, not developers
- **If you can't defend a claim on the destination page, don't put it on the OG**
- Keep copy scannable: max 2 lines of subtitle, 3 metrics, 1 supporting line

### Words to avoid

| Avoid | Use instead | Why |
|-------|-------------|-----|
| AI ROI | AI Signals | Can't prove ROI |
| AI Impact | Delivery Patterns | Makes AI the headline |
| Explanations | Where PRs get stuck | Overclaims causal understanding |
| Proven | Observed / Patterns show | Nothing proven without controlled study |
| Productivity | Delivery | Productivity is loaded/surveillance-adjacent |

## Brand System

### Colors

| Purpose | Hex | RGB | Usage |
|---------|-----|-----|-------|
| Background | `#FAFAF8` | `(250, 250, 248)` | Canvas fill (warm off-white) |
| Text | `#1F2937` | `(31, 41, 55)` | Headlines, metric values, titles |
| Muted | `#6B7280` | `(107, 114, 128)` | Labels, subtitles, descriptions |
| Accent | `#F97316` | `(249, 115, 22)` | Coral orange — bars, brand name dot |
| AI Badge BG | `#FFF7ED` | `(255, 247, 237)` | Warm tint behind AI-Assisted badge |

### Typography

- **Font**: DM Sans variable (`static/fonts/DMSans.ttf`)
- **Bold**: `set_variation_by_name("Bold")` — titles, metric values, brand name
- **Regular**: `set_variation_by_name("Regular")` — subtitles, labels, descriptions
- Title: 62-72px Bold
- Metric values: 64-68px Bold
- Subtitles: 24-28px Regular
- Labels: 22-24px Regular

### Layout Elements

- **Accent bars**: 8px top + 8px bottom, `ACCENT_COLOR`
- **Logo**: 72px, rounded corners (radius 14), inline left of title
- **Brand footer**: dark text "tformance.com" at bottom-right, coral dot accent to its left
- **AI badge**: rounded rectangle with `AI_BADGE_BG` fill, `MUTED_COLOR` text
- **Margins**: 60px all sides

## Technical Reference

### Generators

| Type | File | Generates |
|------|------|-----------|
| Dynamic (org/repo) | `apps/public/services/og_image_service.py` | Per-org and per-repo OG images at runtime |
| Static (marketing) | `apps/web/services/og_image_service.py` | Landing, report, pricing, features OG images |

### Dimensions

- **Standard**: 1200x630 pixels (all social platforms)
- **Format**: PNG
- **File size target**: 25-45KB

### Commands

```bash
# Generate static OG images (committed to git)
python manage.py generate_static_og_images

# Regenerate dynamic OG images (on Unraid after deploy)
python manage.py rebuild_public_catalog_snapshots
```

### Font Loading

```python
from PIL import ImageFont

font = ImageFont.truetype("static/fonts/DMSans.ttf", 72)
font.set_variation_by_name("Bold")  # or "Regular"
```

Fallback chain: DM Sans -> DejaVuSans (Linux) -> Helvetica (macOS) -> Pillow default.

### Pixel-Based Truncation

For large fonts, use `_truncate_to_width(draw, text, font, max_width)` instead of character-count truncation. This prevents text overflowing the canvas.

## Pre-Ship Checklist

Run before shipping any new or modified OG image:

1. Footer contrast >= 4.5:1 (dark text on white, not coral on white)
2. AI badge uses coral-tinted background (`#FFF7ED`), not floating text
3. No overclaim words: ROI, impact, explanations, proven
4. Title readable at 300px width (simulate by shrinking browser)
5. Test with long names (truncation with ellipsis)
6. Test with missing data (null stats, no logo, no AI tools)
7. Run `pytest apps/public/tests/test_public_og_images.py -v`
8. Visual review: `open static/images/og-*.png`

## Deployment

| Image type | Where generated | Where stored | When to regenerate |
|-----------|----------------|-------------|-------------------|
| Static (landing, report, pricing, features) | Local dev -> git commit | `static/images/` -> Docker via collectstatic | Only when copy/design changes |
| Dynamic (org/repo) | Runtime on Unraid | `MEDIA_ROOT/public_og/` | After deploy with new design, or during daily stats pipeline |
