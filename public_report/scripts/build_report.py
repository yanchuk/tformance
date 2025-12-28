#!/usr/bin/env python3
"""
Build the AI Impact Report from Jinja2 templates.

This script:
1. Loads data from CSV files in docs/data/
2. Renders Jinja2 templates from docs/templates/
3. Writes the final HTML to docs/index.html

Usage:
    cd /Users/yanchuk/Documents/GitHub/tformance
    .venv/bin/python docs/scripts/build_report.py
"""

import csv
import json
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

# Paths
DOCS_DIR = Path(__file__).parent.parent
TEMPLATES_DIR = DOCS_DIR / "templates"
DATA_DIR = DOCS_DIR / "data"
OUTPUT_FILE = DOCS_DIR / "index.html"


def load_csv(filename: str) -> list[dict]:
    """Load a CSV file and return list of dicts."""
    filepath = DATA_DIR / filename
    if not filepath.exists():
        print(f"  Warning: {filename} not found")
        return []

    with open(filepath, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Convert numeric fields
    for row in rows:
        for key, value in row.items():
            if value == "" or value is None:
                row[key] = None
            elif key in ("total_prs", "ai_prs", "count"):
                row[key] = int(value)
            elif "pct" in key or "delta" in key or "hours" in key:
                try:
                    row[key] = float(value)
                except (ValueError, TypeError):
                    row[key] = None

    return rows


def load_overall_stats() -> dict:
    """Load overall stats from text file."""
    filepath = DATA_DIR / "overall_stats.txt"
    if not filepath.exists():
        return {}

    stats = {}
    with open(filepath) as f:
        for line in f:
            if ":" in line and not line.startswith("#") and not line.startswith("="):
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                # Try to parse as number
                try:
                    if "." in value:
                        stats[key] = float(value.replace(",", "").replace("%", ""))
                    else:
                        stats[key] = int(value.replace(",", ""))
                except ValueError:
                    stats[key] = value
    return stats


def load_tool_trends() -> dict:
    """Load AI tools monthly data and pivot to {month: {tool: count}}."""
    rows = load_csv("ai_tools_monthly.csv")
    if not rows:
        return {}

    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    trends = {}

    for row in rows:
        tool = row.get("tool", "").lower()
        for i, month in enumerate(months):
            month_key = f"2025-{i + 1:02d}"
            if month_key not in trends:
                trends[month_key] = {}
            try:
                trends[month_key][tool] = int(row.get(month, 0) or 0)
            except (ValueError, TypeError):
                trends[month_key][tool] = 0

    return trends


def load_all_data() -> dict:
    """Load all data files into a context dict."""
    print("Loading data...")

    data = {
        "team_summary": load_csv("team_summary.csv"),
        "monthly_trends": load_csv("monthly_trends.csv"),
        "ai_categories": load_csv("ai_categories.csv"),
        "category_metrics": load_csv("category_metrics.csv"),
        "normalized_metrics": load_csv("normalized_metrics.csv"),
        "within_team_comparison": load_csv("within_team_comparison.csv"),
        "tool_trends": load_tool_trends(),
        "overall_stats": load_overall_stats(),
        "generated_at": datetime.now().isoformat(),
    }

    # Convert team_summary to JS-compatible format
    data["team_data_js"] = [
        {
            "team": row["team"],
            "total": row["total_prs"],
            "ai_pct": row["ai_pct"],
            "cycle_delta": row.get("cycle_delta_pct"),
            "review_delta": row.get("review_delta_pct"),
            "size_delta": row.get("size_delta_pct"),
        }
        for row in data["team_summary"]
    ]

    print(f"  Loaded {len(data['team_summary'])} teams")
    print(f"  Loaded {len(data['tool_trends'])} months of tool data")

    return data


def build_report():
    """Build the report HTML from templates."""
    print(f"\nBuilding report from {TEMPLATES_DIR}")

    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=False,  # We're generating HTML, not escaping it
    )

    # Load data
    data = load_all_data()

    # Render base template
    print("Rendering templates...")
    template = env.get_template("base.html.j2")
    html = template.render(data=data, tojson=json.dumps)

    # Write output
    print(f"Writing to {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w") as f:
        f.write(html)

    print(f"\nDone! Generated {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    build_report()
