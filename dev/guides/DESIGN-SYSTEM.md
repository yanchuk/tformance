# Design System Guide

> Back to [CLAUDE.md](../../CLAUDE.md)

The visual design follows the **"Easy Eyes Dashboard"** direction - inspired by the [Easy Eyes VS Code theme](https://github.com/vvhg1/easyeyes) for reduced eye strain.

**DO NOT CHANGE THEME COLORS WITHOUT EXPLICIT USER APPROVAL**

## Design Resources

| File | Purpose |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | Design tokens & CSS classes |
| `assets/styles/site-tailwind.css` | Theme definitions |
| `tailwind.config.js` | Tailwind configuration |

## Color System Architecture

**IMPORTANT: Always use semantic DaisyUI colors, never hardcoded Tailwind colors.**

Colors are managed at three levels:
1. **DaisyUI Themes** (`site-tailwind.css`) - Define `tformance` (dark) and `tformance-light` themes
2. **Semantic Classes** (`design-system.css`) - App-specific `app-*` classes for common patterns
3. **Light Theme Overrides** (`site-tailwind.css`) - WCAG AA contrast fixes for light theme

## Color Usage Rules

| Use Case | Correct Class | Avoid |
|----------|--------------|-------|
| Primary text | `text-base-content` | `text-white`, `text-stone-*` |
| Secondary text | `text-base-content/80` | `text-gray-400`, `text-stone-400` |
| Muted text | `text-base-content/70` | `text-gray-500` |
| Backgrounds | `bg-base-100`, `bg-base-200` | `bg-deep`, `bg-surface`, `bg-neutral-*` |
| Borders | `border-base-300` | `border-elevated`, `border-neutral-*` |
| Success/positive | `text-success`, `app-status-connected` | `text-emerald-*`, `text-green-*` |
| Error/negative | `text-error` | `text-red-*` |
| Warning | `text-warning` | `text-amber-*` |
| Primary accent | `text-primary`, `bg-primary` | `text-orange-*`, `bg-accent-primary` |

## DaisyUI Theme Tokens (Easy Eyes Inspired)

| Token | Dark (`tformance`) | Light (`tformance-light`) |
|-------|-------------------|--------------------------|
| `base-100` | `#1e1e1e` (soft dark) | `#FAFAF8` |
| `base-200` | `#2a2a28` (warm elevated) | `#FFFFFF` |
| `base-300` | `#3c3c3a` (warm borders) | `#E5E7EB` |
| `base-content` | `#ccc9c0` (Easy Eyes text) | `#1F2937` |
| `primary` | `#F97316` (coral orange) | `#C2410C` |
| `secondary` | `#ffe96e` (golden amber) | `#FDA4AF` |
| `accent` | `#5a9997` (Easy Eyes teal) | `#10B981` |

## Typography

| Font | Usage |
|------|-------|
| **DM Sans** | UI text, headings |
| **JetBrains Mono** | Code, metrics, data values |

## Design Principles

1. **Easy on the eyes** - Soft dark backgrounds, warm text colors
2. **Warm over cold** - Use coral/orange accents instead of typical blue/purple
3. **WCAG AA compliant** - All color combinations meet 4.5:1+ contrast ratio
4. **Semantic colors** - Use DaisyUI tokens that adapt to theme
5. **Terminal aesthetic** - Monospace fonts for data, dark backgrounds

## CSS Classes

Use the `app-*` prefixed utility classes from `design-system.css`:

```html
<!-- Cards -->
<div class="app-card">...</div>
<div class="app-card-interactive">...</div>

<!-- Buttons -->
<button class="app-btn-primary">Primary</button>
<button class="app-btn-secondary">Secondary</button>

<!-- Stats -->
<div class="app-stat-value app-stat-value-positive">+12%</div>
<div class="app-stat-value app-stat-value-negative">-5%</div>

<!-- Badges -->
<span class="app-badge app-badge-success">Active</span>

<!-- Status indicators -->
<span class="app-status-connected">Connected</span>
<span class="app-status-disconnected">Disconnected</span>
<span class="app-status-error">Error</span>
```
