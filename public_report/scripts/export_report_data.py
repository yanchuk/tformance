#!/usr/bin/env python3
"""
Export report data from database to CSV files.

This script queries the database and generates:
- team_summary.csv - Team-level metrics
- monthly_trends.csv - Monthly AI adoption by team
- ai_tools_monthly.csv - AI tool usage by month
- category_metrics.csv - Cycle/review time by AI category (with outlier filtering)

Usage:
    cd /Users/yanchuk/Documents/GitHub/tformance
    .venv/bin/python public_report/scripts/export_report_data.py

Requirements:
    - Django settings configured
    - Database access

Statistical Note:
    PRs with cycle_time_hours > MAX_CYCLE_TIME_HOURS are excluded from
    category_metrics.csv and within_team_comparison.csv to reduce skew
    from extreme outliers (blocked PRs, abandoned work, etc.).
"""

import csv
import os
import random
import statistics
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
MAX_CYCLE_TIME_HOURS = 200  # Filter outliers > 200h (reduces skew from 13.9x to 6.8x)
YEAR = 2025
OUTPUT_DIR = Path(__file__).parent.parent / "data"

# Tracking for transparency
outlier_stats = {"excluded_count": 0, "total_count": 0}


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


def calculate_bootstrap_ci(data: list, n_bootstrap: int = 1000, confidence: float = 0.95) -> tuple:
    """Calculate bootstrap confidence interval for the mean.

    Args:
        data: List of numeric values
        n_bootstrap: Number of bootstrap samples (default 1000)
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound) for the confidence interval
    """
    if not data or len(data) < 2:
        return (None, None)

    n = len(data)
    bootstrap_means = []

    for _ in range(n_bootstrap):
        # Sample with replacement
        sample = [random.choice(data) for _ in range(n)]
        bootstrap_means.append(statistics.mean(sample))

    # Sort and find percentiles
    bootstrap_means.sort()
    alpha = (1 - confidence) / 2
    lower_idx = int(n_bootstrap * alpha)
    upper_idx = int(n_bootstrap * (1 - alpha))

    return (round(bootstrap_means[lower_idx], 1), round(bootstrap_means[upper_idx], 1))


def calculate_delta_ci(
    treatment_data: list, control_data: list, n_bootstrap: int = 1000, confidence: float = 0.95
) -> tuple:
    """Calculate bootstrap confidence interval for percentage difference between means.

    Args:
        treatment_data: List of values for treatment group (AI PRs)
        control_data: List of values for control group (non-AI PRs)
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level

    Returns:
        Tuple of (lower_pct, upper_pct) for the percentage difference CI
    """
    if not treatment_data or not control_data or len(treatment_data) < 2 or len(control_data) < 2:
        return (None, None)

    bootstrap_deltas = []

    for _ in range(n_bootstrap):
        # Sample with replacement from each group
        treatment_sample = [random.choice(treatment_data) for _ in range(len(treatment_data))]
        control_sample = [random.choice(control_data) for _ in range(len(control_data))]

        treatment_mean = statistics.mean(treatment_sample)
        control_mean = statistics.mean(control_sample)

        if control_mean != 0:
            delta_pct = ((treatment_mean - control_mean) / control_mean) * 100
            bootstrap_deltas.append(delta_pct)

    if not bootstrap_deltas:
        return (None, None)

    # Sort and find percentiles
    bootstrap_deltas.sort()
    alpha = (1 - confidence) / 2
    lower_idx = int(len(bootstrap_deltas) * alpha)
    upper_idx = int(len(bootstrap_deltas) * (1 - alpha))

    return (round(bootstrap_deltas[lower_idx], 0), round(bootstrap_deltas[upper_idx], 0))


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


def export_ai_categories():
    """Export ai_categories.csv with Code AI vs Review AI breakdown."""
    print("Exporting ai_categories.csv...")

    # Import the categorization logic
    from apps.metrics.services.ai_categories import get_tool_category

    team_ids = get_teams_with_threshold()

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                tool,
                COUNT(*) as count
            FROM metrics_pullrequest pr
            CROSS JOIN LATERAL jsonb_array_elements_text(
                COALESCE(llm_summary->'ai'->'tools', ai_tools_detected)
            ) as tool
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND pr.team_id = ANY(%s)
            AND (
                (pr.llm_summary IS NOT NULL AND jsonb_array_length(pr.llm_summary->'ai'->'tools') > 0)
                OR (pr.ai_tools_detected IS NOT NULL AND jsonb_array_length(pr.ai_tools_detected) > 0)
            )
            GROUP BY tool
            ORDER BY count DESC
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )

        rows = cursor.fetchall()

    # Categorize tools and aggregate
    category_totals = {"code": 0, "review": 0, "unknown": 0}
    tool_categories = []

    for tool, count in rows:
        category = get_tool_category(tool)
        if category:
            category_totals[category] += count
        else:
            category_totals["unknown"] += count
        tool_categories.append({"tool": tool, "count": count, "category": category or "unknown"})

    # Calculate percentages
    total = sum(category_totals.values())
    category_pcts = {k: round(v * 100.0 / total, 1) if total > 0 else 0 for k, v in category_totals.items()}

    # Write category summary
    output_file = OUTPUT_DIR / "ai_categories.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["category", "count", "percentage"])
        writer.writeheader()
        for cat in ["code", "review", "unknown"]:
            writer.writerow({"category": cat, "count": category_totals[cat], "percentage": category_pcts[cat]})

    print(f"  Category breakdown: Code={category_pcts['code']}%, Review={category_pcts['review']}%")

    # Write tool-level categories
    output_file2 = OUTPUT_DIR / "ai_tools_with_categories.csv"
    with open(output_file2, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["tool", "count", "category"])
        writer.writeheader()
        writer.writerows(tool_categories)

    print(f"  Written {len(tool_categories)} tools with categories to {output_file2}")

    return {"totals": category_totals, "percentages": category_pcts, "tools": tool_categories}


def export_category_metrics():
    """Export category_metrics.csv with cycle/review time by AI category."""
    print("Exporting category_metrics.csv...")

    from apps.metrics.services.ai_categories import get_tool_category

    team_ids = get_teams_with_threshold()

    with connection.cursor() as cursor:
        # Get PRs with their detected tools
        cursor.execute(
            """
            WITH pr_tools AS (
                SELECT
                    pr.id,
                    pr.cycle_time_hours,
                    pr.review_time_hours,
                    pr.additions + pr.deletions as size,
                    jsonb_array_elements_text(
                        COALESCE(llm_summary->'ai'->'tools', ai_tools_detected)
                    ) as tool
                FROM metrics_pullrequest pr
                WHERE pr.pr_created_at >= %s
                AND pr.pr_created_at < %s
                AND pr.team_id = ANY(%s)
                AND pr.is_ai_assisted = true
                AND (
                    (pr.llm_summary IS NOT NULL AND jsonb_array_length(pr.llm_summary->'ai'->'tools') > 0)
                    OR (pr.ai_tools_detected IS NOT NULL AND jsonb_array_length(pr.ai_tools_detected) > 0)
                )
            )
            SELECT tool, cycle_time_hours, review_time_hours, size
            FROM pr_tools
            WHERE cycle_time_hours IS NOT NULL
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )
        rows = cursor.fetchall()

    # Aggregate by category, filtering outliers
    category_data = {"code": [], "review": []}
    ai_excluded = 0
    ai_total = 0

    for tool, cycle, review, size in rows:
        ai_total += 1
        # Skip outliers (PRs with extremely long cycle times)
        if cycle and float(cycle) > MAX_CYCLE_TIME_HOURS:
            ai_excluded += 1
            continue
        cat = get_tool_category(tool)
        if cat in category_data:
            category_data[cat].append({"cycle": cycle, "review": review, "size": size})

    print(f"  AI PRs: {ai_total} total, {ai_excluded} excluded (>{MAX_CYCLE_TIME_HOURS}h)")

    # Calculate averages and medians
    results = {}
    for cat, data in category_data.items():
        if data:
            cycle_values = [d["cycle"] for d in data if d["cycle"]]
            review_values = [d["review"] for d in data if d["review"]]
            size_values = [d["size"] for d in data if d["size"]]

            avg_cycle = sum(cycle_values) / len(cycle_values) if cycle_values else 0
            avg_review = sum(review_values) / len(review_values) if review_values else 0
            avg_size = sum(size_values) / len(size_values) if size_values else 0

            # Calculate medians
            median_cycle = statistics.median(cycle_values) if cycle_values else 0
            median_review = statistics.median(review_values) if review_values else 0
            median_size = statistics.median(size_values) if size_values else 0

            results[cat] = {
                "count": len(data),
                "avg_cycle_hours": round(avg_cycle, 1),
                "median_cycle_hours": round(median_cycle, 1),
                "avg_review_hours": round(avg_review, 1),
                "median_review_hours": round(median_review, 1),
                "avg_size": round(avg_size, 0),
                "median_size": round(median_size, 0),
            }

    # Get non-AI baseline for comparison (with medians) - filtered for outliers
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) as count,
                AVG(cycle_time_hours) as avg_cycle,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY cycle_time_hours) as median_cycle,
                AVG(review_time_hours) as avg_review,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY review_time_hours) as median_review,
                AVG(additions + deletions) as avg_size,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY additions + deletions) as median_size
            FROM metrics_pullrequest pr
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND pr.team_id = ANY(%s)
            AND pr.is_ai_assisted = false
            AND pr.cycle_time_hours IS NOT NULL
            AND pr.cycle_time_hours <= %s
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids, MAX_CYCLE_TIME_HOURS],
        )
        row = cursor.fetchone()
        results["none"] = {
            "count": row[0],
            "avg_cycle_hours": round(row[1], 1) if row[1] else None,
            "median_cycle_hours": round(row[2], 1) if row[2] else None,
            "avg_review_hours": round(row[3], 1) if row[3] else None,
            "median_review_hours": round(row[4], 1) if row[4] else None,
            "avg_size": round(row[5], 0) if row[5] else None,
            "median_size": round(row[6], 0) if row[6] else None,
        }
        print(f"  Baseline (non-AI): {row[0]} PRs (after filtering >{MAX_CYCLE_TIME_HOURS}h)")

    # Fetch raw baseline values for CI calculation (also filtered)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT cycle_time_hours, review_time_hours
            FROM metrics_pullrequest pr
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND pr.team_id = ANY(%s)
            AND pr.is_ai_assisted = false
            AND pr.cycle_time_hours IS NOT NULL
            AND pr.cycle_time_hours <= %s
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids, MAX_CYCLE_TIME_HOURS],
        )
        baseline_rows = cursor.fetchall()
        baseline_cycle = [float(r[0]) for r in baseline_rows if r[0]]
        baseline_review = [float(r[1]) for r in baseline_rows if r[1]]

    # Calculate deltas with confidence intervals
    baseline = results["none"]
    print("  Calculating bootstrap confidence intervals (1000 samples)...")
    for cat in ["code", "review"]:
        if cat in results and baseline["avg_cycle_hours"]:
            # Get raw values for this category
            cat_cycle = [float(d["cycle"]) for d in category_data[cat] if d.get("cycle")]
            cat_review = [float(d["review"]) for d in category_data[cat] if d.get("review")]

            # Point estimates
            results[cat]["cycle_delta_pct"] = round(
                (results[cat]["avg_cycle_hours"] - baseline["avg_cycle_hours"]) / baseline["avg_cycle_hours"] * 100, 0
            )
            results[cat]["review_delta_pct"] = round(
                (results[cat]["avg_review_hours"] - baseline["avg_review_hours"]) / baseline["avg_review_hours"] * 100,
                0,
            )

            # Bootstrap CIs for cycle time delta
            cycle_ci = calculate_delta_ci(cat_cycle, baseline_cycle)
            results[cat]["cycle_delta_ci_lower"] = cycle_ci[0]
            results[cat]["cycle_delta_ci_upper"] = cycle_ci[1]

            # Bootstrap CIs for review time delta
            review_ci = calculate_delta_ci(cat_review, baseline_review)
            results[cat]["review_delta_ci_lower"] = review_ci[0]
            results[cat]["review_delta_ci_upper"] = review_ci[1]

    # Write CSV
    output_file = OUTPUT_DIR / "category_metrics.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "category",
                "count",
                "avg_cycle_hours",
                "median_cycle_hours",
                "avg_review_hours",
                "median_review_hours",
                "avg_size",
                "median_size",
                "cycle_delta_pct",
                "cycle_delta_ci_lower",
                "cycle_delta_ci_upper",
                "review_delta_pct",
                "review_delta_ci_lower",
                "review_delta_ci_upper",
            ],
        )
        writer.writeheader()
        for cat in ["none", "code", "review"]:
            if cat in results:
                row = {"category": cat, **results[cat]}
                writer.writerow(row)

    code = results.get("code", {})
    review = results.get("review", {})
    print(f"  Category metrics: Code AI {code.get('cycle_delta_pct', 'N/A'):+.0f}% cycle time")
    if code.get("cycle_delta_ci_lower") is not None:
        ci_low, ci_high = code["cycle_delta_ci_lower"], code["cycle_delta_ci_upper"]
        print(f"                    (95% CI: {ci_low:+.0f}% to {ci_high:+.0f}%)")
    print(f"                    Review AI {review.get('cycle_delta_pct', 'N/A'):+.0f}% cycle time")
    if review.get("cycle_delta_ci_lower") is not None:
        ci_low, ci_high = review["cycle_delta_ci_lower"], review["cycle_delta_ci_upper"]
        print(f"                    (95% CI: {ci_low:+.0f}% to {ci_high:+.0f}%)")

    return results


def export_normalized_metrics():
    """Export size-normalized review time metrics.

    This addresses the confounding variable concern: AI-assisted PRs
    tend to be smaller, which could explain faster review times.
    By normalizing per 100 lines of code, we control for PR size.
    """
    print("Exporting normalized_metrics.csv...")

    from apps.metrics.services.ai_categories import get_tool_category

    team_ids = get_teams_with_threshold()

    # Get PRs with AI tools and calculate normalized metrics
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH pr_tools AS (
                SELECT
                    pr.id,
                    pr.review_time_hours,
                    pr.additions + pr.deletions as size,
                    jsonb_array_elements_text(
                        COALESCE(llm_summary->'ai'->'tools', ai_tools_detected)
                    ) as tool
                FROM metrics_pullrequest pr
                WHERE pr.pr_created_at >= %s
                AND pr.pr_created_at < %s
                AND pr.team_id = ANY(%s)
                AND pr.is_ai_assisted = true
                AND pr.review_time_hours IS NOT NULL
                AND pr.additions + pr.deletions > 0
                AND (
                    (pr.llm_summary IS NOT NULL AND jsonb_array_length(pr.llm_summary->'ai'->'tools') > 0)
                    OR (pr.ai_tools_detected IS NOT NULL AND jsonb_array_length(pr.ai_tools_detected) > 0)
                )
            )
            SELECT tool, review_time_hours, size
            FROM pr_tools
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )
        rows = cursor.fetchall()

    # Calculate normalized metrics by category
    category_data = {"code": [], "review": []}

    for tool, review, size in rows:
        cat = get_tool_category(tool)
        if cat in category_data and size > 0:
            # Review time per 100 lines (convert Decimal to float)
            normalized = (float(review) * 100.0) / float(size)
            category_data[cat].append(normalized)

    results = {}
    for cat, values in category_data.items():
        if values:
            results[cat] = {
                "count": len(values),
                "review_hours_per_100_lines": round(statistics.mean(values), 1),
            }

    # Get baseline (non-AI PRs)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) as count,
                AVG(review_time_hours * 100.0 / NULLIF(additions + deletions, 0)) as avg_normalized
            FROM metrics_pullrequest pr
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND pr.team_id = ANY(%s)
            AND pr.is_ai_assisted = false
            AND pr.review_time_hours IS NOT NULL
            AND pr.additions + pr.deletions > 0
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids],
        )
        row = cursor.fetchone()
        results["none"] = {
            "count": row[0],
            "review_hours_per_100_lines": round(float(row[1]), 1) if row[1] else None,
        }

    # Calculate deltas
    baseline = results["none"]["review_hours_per_100_lines"]
    for cat in ["code", "review"]:
        if cat in results and baseline:
            results[cat]["vs_baseline_pct"] = round(
                (results[cat]["review_hours_per_100_lines"] - baseline) / baseline * 100, 0
            )

    # Write CSV
    output_file = OUTPUT_DIR / "normalized_metrics.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["category", "count", "review_hours_per_100_lines", "vs_baseline_pct"],
        )
        writer.writeheader()
        for cat in ["none", "code", "review"]:
            if cat in results:
                row = {"category": cat, **results[cat]}
                writer.writerow(row)

    print(f"  Normalized: Baseline {results['none']['review_hours_per_100_lines']} hrs/100 lines")
    if "code" in results:
        print(f"              Code AI {results['code'].get('vs_baseline_pct', 'N/A')}% vs baseline")
    if "review" in results:
        print(f"              Review AI {results['review'].get('vs_baseline_pct', 'N/A')}% vs baseline")

    return results


def export_within_team_analysis():
    """Export within-team comparison of AI vs non-AI PRs.

    This analysis compares AI vs non-AI PRs within the same team,
    filtering for teams with at least 10 PRs in BOTH groups to ensure
    statistical validity. Also filters outliers (>MAX_CYCLE_TIME_HOURS).
    """
    print("Exporting within_team_comparison.csv...")

    team_ids = get_teams_with_threshold()

    # Get per-team comparison of cycle time for AI vs non-AI PRs
    # Filter for teams with 10+ PRs in both groups, and filter outliers
    with connection.cursor() as cursor:
        cursor.execute(
            """
            WITH team_stats AS (
                SELECT
                    t.name as team,
                    COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) as ai_prs,
                    COUNT(CASE WHEN NOT pr.is_ai_assisted THEN 1 END) as non_ai_prs,
                    AVG(CASE WHEN pr.is_ai_assisted THEN pr.cycle_time_hours END) as ai_cycle,
                    AVG(CASE WHEN NOT pr.is_ai_assisted THEN pr.cycle_time_hours END) as non_ai_cycle
                FROM teams_team t
                JOIN metrics_pullrequest pr ON pr.team_id = t.id
                WHERE pr.pr_created_at >= %s
                AND pr.pr_created_at < %s
                AND pr.team_id = ANY(%s)
                AND pr.state = 'merged'
                AND pr.cycle_time_hours IS NOT NULL
                AND pr.cycle_time_hours <= %s
                GROUP BY t.id, t.name
            )
            SELECT
                team,
                ai_prs,
                non_ai_prs,
                ROUND(ai_cycle::numeric, 1) as ai_cycle_hours,
                ROUND(non_ai_cycle::numeric, 1) as non_ai_cycle_hours,
                ROUND(((ai_cycle - non_ai_cycle) / NULLIF(non_ai_cycle, 0) * 100)::numeric, 1) as cycle_delta_pct,
                CASE WHEN ai_cycle < non_ai_cycle THEN 'faster' ELSE 'slower' END as ai_result
            FROM team_stats
            WHERE ai_prs >= 10 AND non_ai_prs >= 10
            ORDER BY cycle_delta_pct ASC
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01", team_ids, MAX_CYCLE_TIME_HOURS],
        )
        rows = cursor.fetchall()

    # Write CSV
    output_file = OUTPUT_DIR / "within_team_comparison.csv"
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "team",
                "ai_prs",
                "non_ai_prs",
                "ai_cycle_hours",
                "non_ai_cycle_hours",
                "cycle_delta_pct",
                "ai_result",
            ]
        )
        for row in rows:
            writer.writerow(row)

    # Calculate summary stats
    total_teams = len(rows)
    ai_faster = sum(1 for row in rows if row[6] == "faster")
    ai_slower = total_teams - ai_faster
    faster_pct = round(ai_faster / total_teams * 100, 0) if total_teams > 0 else 0
    slower_pct = round(ai_slower / total_teams * 100, 0) if total_teams > 0 else 0

    print(f"  {total_teams} teams with 10+ PRs in both AI and non-AI groups")
    print(f"  AI faster: {ai_faster} teams ({faster_pct:.0f}%)")
    print(f"  AI slower: {ai_slower} teams ({slower_pct:.0f}%)")

    return {
        "total_teams": total_teams,
        "ai_faster": ai_faster,
        "ai_slower": ai_slower,
        "faster_pct": faster_pct,
        "slower_pct": slower_pct,
        "teams": [
            {
                "team": row[0],
                "ai_prs": row[1],
                "non_ai_prs": row[2],
                "ai_cycle_hours": float(row[3]) if row[3] else None,
                "non_ai_cycle_hours": float(row[4]) if row[4] else None,
                "cycle_delta_pct": float(row[5]) if row[5] else None,
                "ai_result": row[6],
            }
            for row in rows
        ],
    }


def export_overall_stats():
    """Export overall statistics for the report header."""
    print("Calculating overall stats...")

    team_ids = get_teams_with_threshold()

    # First, get total counts across all OSS teams (for headline numbers)
    # OSS teams are identified by having "-demo" suffix in slug
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(DISTINCT t.id) as all_teams,
                COUNT(pr.id) as all_prs,
                COUNT(CASE WHEN pr.is_ai_assisted THEN 1 END) as all_ai_prs,
                COUNT(CASE WHEN pr.llm_summary IS NOT NULL THEN 1 END) as all_llm_analyzed
            FROM teams_team t
            JOIN metrics_pullrequest pr ON pr.team_id = t.id
            WHERE pr.pr_created_at >= %s
            AND pr.pr_created_at < %s
            AND t.slug LIKE '%%-demo'
        """,
            [f"{YEAR}-01-01", f"{YEAR + 1}-01-01"],
        )
        all_row = cursor.fetchone()

    all_stats = {
        "all_teams": all_row[0],
        "all_prs": all_row[1],
        "all_ai_prs": all_row[2],
        "all_llm_analyzed": all_row[3],
    }

    # Then get stats for teams with 500+ PRs (for detailed analysis)
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
        f.write("# Headline Numbers (All OSS Companies)\n")
        f.write(f"OSS Companies: {all_stats['all_teams']}\n")
        f.write(f"Total PRs: {all_stats['all_prs']:,}\n")
        f.write(f"AI-Assisted PRs: {all_stats['all_ai_prs']:,}\n")
        f.write(f"AI Adoption Rate: {round(all_stats['all_ai_prs'] / all_stats['all_prs'] * 100, 1)}%\n")
        llm_pct = round(all_stats["all_llm_analyzed"] / all_stats["all_prs"] * 100, 1)
        f.write(f"LLM Analyzed: {all_stats['all_llm_analyzed']:,} ({llm_pct}%)\n")
        f.write("\n# Detailed Analysis (Companies with 500+ PRs)\n")
        f.write(f"Companies (500+ PRs): {stats['teams']}\n")
        f.write(f"PRs from these companies: {stats['total_prs']:,}\n")
        f.write(f"AI Adoption Rate: {stats['ai_pct']}%\n")
        f.write("\nMetric Changes (AI vs Non-AI):\n")
        f.write(f"  Cycle Time: {'+' if stats['cycle_delta_pct'] > 0 else ''}{stats['cycle_delta_pct']}%\n")
        f.write(f"  Review Time: {'+' if stats['review_delta_pct'] > 0 else ''}{stats['review_delta_pct']}%\n")

    print(f"  Stats written to {output_file}")
    ai_pct = round(all_stats["all_ai_prs"] / all_stats["all_prs"] * 100, 1)
    print(f"\n  Summary: {all_stats['all_teams']} OSS companies, {all_stats['all_prs']:,} PRs, {ai_pct}% AI adoption")
    print(f"  Detailed: {stats['teams']} companies with 500+ PRs ({stats['total_prs']:,} PRs)")

    return stats, all_stats


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
    categories = export_ai_categories()
    cat_metrics = export_category_metrics()
    normalized = export_normalized_metrics()
    within_team = export_within_team_analysis()

    print(f"\n{'=' * 60}")
    print("Export complete!")
    print(f"{'=' * 60}")
    print(f"\nFiles created in {OUTPUT_DIR}:")
    print(f"  - team_summary.csv ({len(teams)} teams)")
    print(f"  - monthly_trends.csv ({len(monthly)} teams × 12 months)")
    print(f"  - ai_tools_monthly.csv ({len(tools)} tools × 12 months)")
    code_pct = categories["percentages"]["code"]
    review_pct = categories["percentages"]["review"]
    print(f"  - ai_categories.csv (Code: {code_pct}%, Review: {review_pct}%)")
    print("  - ai_tools_with_categories.csv")
    print("  - category_metrics.csv")
    print("  - normalized_metrics.csv")
    print(f"  - within_team_comparison.csv ({within_team['total_teams']} teams)")
    print("  - overall_stats.txt")

    # Print category impact summary
    if cat_metrics:
        print("\n📊 Category Impact Summary:")
        if "code" in cat_metrics:
            cycle = cat_metrics["code"].get("cycle_delta_pct", 0)
            review = cat_metrics["code"].get("review_delta_pct", 0)
            print(f"  Code AI: {cycle:+.0f}% cycle time, {review:+.0f}% review time")
        if "review" in cat_metrics:
            cycle = cat_metrics["review"].get("cycle_delta_pct", 0)
            review = cat_metrics["review"].get("review_delta_pct", 0)
            print(f"  Review AI: {cycle:+.0f}% cycle time, {review:+.0f}% review time")

    # Print normalized metrics summary
    if normalized:
        print("\n📏 Size-Normalized Review Time (hours per 100 lines):")
        baseline = normalized.get("none", {}).get("review_hours_per_100_lines", 0)
        for cat in ["code", "review"]:
            if cat in normalized:
                val = normalized[cat].get("review_hours_per_100_lines", 0)
                delta = normalized[cat].get("vs_baseline_pct", 0)
                label = "Code AI" if cat == "code" else "Review AI"
                print(f"  {label}: {val:.1f} ({delta:+.0f}% vs baseline {baseline:.1f})")


if __name__ == "__main__":
    main()
