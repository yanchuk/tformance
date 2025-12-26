#!/usr/bin/env python3
"""
Export report data from database to CSV files.

This script queries the database and generates:
- team_summary.csv - Team-level metrics
- monthly_trends.csv - Monthly AI adoption by team
- ai_tools_monthly.csv - AI tool usage by month

Usage:
    cd /Users/yanchuk/Documents/GitHub/tformance
    .venv/bin/python docs/scripts/export_report_data.py

Requirements:
    - Django settings configured
    - Database access
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")

import django

django.setup()

from django.db import connection  # noqa: E402

# Configuration
MIN_PRS_THRESHOLD = 500  # Teams must have at least this many PRs
YEAR = 2025
OUTPUT_DIR = Path(__file__).parent.parent / "data"


def get_teams_with_threshold():
    """Get team IDs that meet the PR threshold."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT team_id
            FROM metrics_pullrequest
            WHERE pr_created_at >= %s AND pr_created_at < %s
            GROUP BY team_id
            HAVING COUNT(*) >= %s
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", MIN_PRS_THRESHOLD],
        )
        return [row[0] for row in cursor.fetchall()]


def export_team_summary():
    """Export team_summary.csv with metrics for each team."""
    print("Exporting team_summary.csv...")

    team_ids = get_teams_with_threshold()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                t.name as team,
                COUNT(pr.id) as total_prs,
                COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) as ai_prs,
                ROUND(
                    COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) * 100.0
                    / NULLIF(COUNT(pr.id), 0), 1
                ) as ai_pct,
                ROUND(AVG(CASE WHEN pr.is_ai_assisted AND pr.cycle_time_hours IS NOT NULL
                    THEN pr.cycle_time_hours END), 1) as ai_cycle_time,
                ROUND(AVG(CASE WHEN NOT pr.is_ai_assisted AND pr.cycle_time_hours IS NOT NULL
                    THEN pr.cycle_time_hours END), 1) as non_ai_cycle_time,
                ROUND(AVG(CASE WHEN pr.is_ai_assisted AND pr.review_time_hours IS NOT NULL
                    THEN pr.review_time_hours END), 1) as ai_review_time,
                ROUND(AVG(CASE WHEN NOT pr.is_ai_assisted AND pr.review_time_hours IS NOT NULL
                    THEN pr.review_time_hours END), 1) as non_ai_review_time,
                ROUND(AVG(CASE WHEN pr.is_ai_assisted THEN pr.additions + pr.deletions END), 0) as ai_size,
                ROUND(AVG(CASE WHEN NOT pr.is_ai_assisted THEN pr.additions + pr.deletions END), 0) as non_ai_size
            FROM teams_team t
            JOIN metrics_pullrequest pr ON pr.team_id = t.id
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND t.id = ANY(%s)
            GROUP BY t.id, t.name
            ORDER BY COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) * 100.0
                / NULLIF(COUNT(pr.id), 0) DESC NULLS LAST
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )

        rows = cursor.fetchall()
        columns = [
            "team",
            "total_prs",
            "ai_prs",
            "ai_pct",
            "ai_cycle_time",
            "non_ai_cycle_time",
            "ai_review_time",
            "non_ai_review_time",
            "ai_size",
            "non_ai_size",
        ]

    # Calculate deltas
    output_rows = []
    for row in rows:
        data = dict(zip(columns, row, strict=False))

        # Calculate percentage changes (AI vs non-AI)
        if data["non_ai_cycle_time"] and data["ai_cycle_time"]:
            cycle_delta = round(
                (data["ai_cycle_time"] - data["non_ai_cycle_time"]) / data["non_ai_cycle_time"] * 100, 0
            )
        else:
            cycle_delta = None

        if data["non_ai_review_time"] and data["ai_review_time"]:
            review_delta = round(
                (data["ai_review_time"] - data["non_ai_review_time"]) / data["non_ai_review_time"] * 100, 0
            )
        else:
            review_delta = None

        if data["non_ai_size"] and data["ai_size"]:
            size_delta = round((data["ai_size"] - data["non_ai_size"]) / data["non_ai_size"] * 100, 0)
        else:
            size_delta = None

        output_rows.append(
            {
                "team": data["team"],
                "total_prs": data["total_prs"],
                "ai_prs": data["ai_prs"],
                "ai_pct": data["ai_pct"],
                "cycle_delta_pct": cycle_delta,
                "review_delta_pct": review_delta,
                "size_delta_pct": size_delta,
            }
        )

    # Write CSV
    output_file = OUTPUT_DIR / "team_summary.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "team",
                "total_prs",
                "ai_prs",
                "ai_pct",
                "cycle_delta_pct",
                "review_delta_pct",
                "size_delta_pct",
            ],
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"  Written {len(output_rows)} teams to {output_file}")
    return output_rows


def export_monthly_trends():
    """Export monthly_trends.csv with AI adoption by team per month."""
    print("Exporting monthly_trends.csv...")

    team_ids = get_teams_with_threshold()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                t.name as team,
                DATE_TRUNC('month', pr.pr_created_at)::date as month,
                COUNT(pr.id) as total_prs,
                COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) as ai_prs,
                ROUND(
                    COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) * 100.0
                    / NULLIF(COUNT(pr.id), 0), 1
                ) as ai_pct
            FROM teams_team t
            JOIN metrics_pullrequest pr ON pr.team_id = t.id
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND t.id = ANY(%s)
            GROUP BY t.id, t.name, DATE_TRUNC('month', pr.pr_created_at)
            ORDER BY t.name, month
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )

        rows = cursor.fetchall()

    # Pivot to wide format (team, jan, feb, mar, ...)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    team_data = {}

    for team, month, _total, _ai, pct in rows:
        if team not in team_data:
            team_data[team] = {m: None for m in months}
        month_idx = month.month - 1
        team_data[team][months[month_idx]] = pct

    # Write CSV
    output_file = OUTPUT_DIR / "monthly_trends.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["team"] + months)
        writer.writeheader()
        for team, data in sorted(team_data.items()):
            row = {"team": team, **data}
            writer.writerow(row)

    print(f"  Written {len(team_data)} teams to {output_file}")
    return team_data


def export_ai_tools_monthly():
    """Export ai_tools_monthly.csv with tool usage by month."""
    print("Exporting ai_tools_monthly.csv...")

    team_ids = get_teams_with_threshold()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                DATE_TRUNC('month', pr.pr_created_at)::date as month,
                tool,
                COUNT(*) as count
            FROM metrics_pullrequest pr
            CROSS JOIN LATERAL jsonb_array_elements_text(llm_summary->'ai'->'tools') as tool
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND pr.team_id = ANY(%s)
            AND pr.llm_summary IS NOT NULL
            AND pr.llm_summary->'ai'->'tools' IS NOT NULL
            AND jsonb_array_length(pr.llm_summary->'ai'->'tools') > 0
            GROUP BY month, tool
            ORDER BY month, count DESC
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )

        rows = cursor.fetchall()

    # Get top tools overall
    tool_totals = {}
    for _month, tool, count in rows:
        tool_totals[tool] = tool_totals.get(tool, 0) + count

    top_tools = sorted(tool_totals.keys(), key=lambda t: tool_totals[t], reverse=True)[:12]

    # Pivot to wide format
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    tool_data = {tool: {m: 0 for m in months} for tool in top_tools}

    for month, tool, count in rows:
        if tool in top_tools:
            month_idx = month.month - 1
            tool_data[tool][months[month_idx]] = count

    # Write CSV
    output_file = OUTPUT_DIR / "ai_tools_monthly.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["tool"] + months)
        writer.writeheader()
        for tool in top_tools:
            row = {"tool": tool, **tool_data[tool]}
            writer.writerow(row)

    print(f"  Written {len(top_tools)} tools to {output_file}")
    return tool_data


def export_overall_stats():
    """Export overall statistics for the report header."""
    print("Calculating overall stats...")

    team_ids = get_teams_with_threshold()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT t.id) as teams,
                COUNT(pr.id) as total_prs,
                COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) as ai_prs,
                ROUND(
                    COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) * 100.0
                    / NULLIF(COUNT(pr.id), 0), 1
                ) as ai_pct,
                COUNT(CASE WHEN pr.llm_summary IS NOT NULL THEN 1 END) as llm_analyzed,
                ROUND(
                    AVG(CASE WHEN pr.is_ai_assisted THEN pr.review_time_hours END) -
                    AVG(CASE WHEN NOT pr.is_ai_assisted THEN pr.review_time_hours END), 1
                ) as review_time_diff,
                ROUND(
                    (AVG(CASE WHEN pr.is_ai_assisted THEN pr.cycle_time_hours END) -
                    AVG(CASE WHEN NOT pr.is_ai_assisted THEN pr.cycle_time_hours END)) /
                    NULLIF(AVG(CASE WHEN NOT pr.is_ai_assisted
                        THEN pr.cycle_time_hours END), 0) * 100, 0
                ) as cycle_delta_pct,
                ROUND(
                    (AVG(CASE WHEN pr.is_ai_assisted THEN pr.review_time_hours END) -
                    AVG(CASE WHEN NOT pr.is_ai_assisted THEN pr.review_time_hours END)) /
                    NULLIF(AVG(CASE WHEN NOT pr.is_ai_assisted
                        THEN pr.review_time_hours END), 0) * 100, 0
                ) as review_delta_pct
            FROM teams_team t
            JOIN metrics_pullrequest pr ON pr.team_id = t.id
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND t.id = ANY(%s)
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )

        row = cursor.fetchone()

    stats = {
        "teams": row[0],
        "total_prs": row[1],
        "ai_prs": row[2],
        "ai_pct": row[3],
        "llm_analyzed": row[4],
        "review_time_diff": row[5],
        "cycle_delta_pct": row[6],
        "review_delta_pct": row[7],
    }

    # Write to file for reference
    output_file = OUTPUT_DIR / "overall_stats.txt"
    with open(output_file, "w") as f:
        f.write(f"Report Statistics - Generated {datetime.now().isoformat()}\n")
        f.write(f"{'=' * 50}\n\n")
        f.write(f"Teams: {stats['teams']}\n")
        f.write(f"Total PRs: {stats['total_prs']:,}\n")
        f.write(f"AI-Assisted PRs: {stats['ai_prs']:,}\n")
        f.write(f"AI Adoption Rate: {stats['ai_pct']}%\n")
        f.write(
            f"LLM Analyzed: {stats['llm_analyzed']:,} ({round(stats['llm_analyzed'] / stats['total_prs'] * 100, 1)}%)\n"
        )
        f.write("\nMetric Changes (AI vs Non-AI):\n")
        f.write(f"  Cycle Time: {'+' if stats['cycle_delta_pct'] > 0 else ''}{stats['cycle_delta_pct']}%\n")
        f.write(f"  Review Time: {'+' if stats['review_delta_pct'] > 0 else ''}{stats['review_delta_pct']}%\n")

    print(f"  Stats written to {output_file}")
    print(f"\n  Summary: {stats['teams']} teams, {stats['total_prs']:,} PRs, {stats['ai_pct']}% AI adoption")

    return stats


def main():
    print(f"\n{'=' * 60}")
    print(f"Report Data Export - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")
    print(f"Configuration: MIN_PRS_THRESHOLD={MIN_PRS_THRESHOLD}, YEAR={YEAR}")
    print(f"Output directory: {OUTPUT_DIR}\n")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Export all data
    export_overall_stats()
    teams = export_team_summary()
    monthly = export_monthly_trends()
    tools = export_ai_tools_monthly()

    print(f"\n{'=' * 60}")
    print("Export complete!")
    print(f"{'=' * 60}")
    print(f"\nFiles created in {OUTPUT_DIR}:")
    print(f"  - team_summary.csv ({len(teams)} teams)")
    print(f"  - monthly_trends.csv ({len(monthly)} teams × 12 months)")
    print(f"  - ai_tools_monthly.csv ({len(tools)} tools × 12 months)")
    print("  - overall_stats.txt")


if __name__ == "__main__":
    main()
