"""
Fetch PRs from public OSS repositories for AI detection training/validation.

Uses gh CLI for GitHub interaction.

Usage:
    python apps/metrics/scripts/fetch_oss_prs.py [--tier TIER] [--search QUERY]

Examples:
    python apps/metrics/scripts/fetch_oss_prs.py --tier 1
    python apps/metrics/scripts/fetch_oss_prs.py --search "Generated with Claude Code"
"""

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Setup Django if running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")
    import django

    django.setup()

from apps.metrics.services.ai_detector import detect_ai_in_text


@dataclass
class FetchedPR:
    """PR data fetched from GitHub."""

    repo: str
    number: int
    title: str
    body: str
    author: str
    created_at: str
    merged_at: str | None


# =============================================================================
# Repository Tiers
# =============================================================================

# Tier 1: High confidence signal (explicit AI disclosure culture)
TIER1_REPOS = [
    ("antiwork", "gumroad"),  # PRIMARY - 68% have AI Disclosure section
    ("anthropic", "anthropic-cookbook"),
    ("anthropic", "courses"),
    ("supabase", "supabase"),
    ("cal-com", "cal.com"),
]

# Tier 2: AI tool/framework repos (high false positive risk)
# Product mentions ≠ AI authoring - need careful filtering
TIER2_REPOS = [
    ("vercel", "ai"),
    ("langchain-ai", "langchain"),
    ("openai", "openai-python"),
]

# Tier 3: General OSS (low AI signal, good for negative examples)
TIER3_REPOS = [
    ("microsoft", "vscode"),
    ("facebook", "react"),
    ("django", "django"),
    ("rails", "rails"),
]


def fetch_prs_with_gh(owner: str, repo: str, limit: int = 100) -> list[FetchedPR]:
    """Fetch PRs using gh CLI."""

    cmd = [
        "gh",
        "pr",
        "list",
        "--repo",
        f"{owner}/{repo}",
        "--limit",
        str(limit),
        "--state",
        "all",
        "--json",
        "number,title,body,author,createdAt,mergedAt",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            print(f"Error fetching {owner}/{repo}: {result.stderr}")
            return []

        data = json.loads(result.stdout)
        prs = []

        for pr_data in data:
            pr = FetchedPR(
                repo=f"{owner}/{repo}",
                number=pr_data["number"],
                title=pr_data.get("title", ""),
                body=pr_data.get("body", "") or "",
                author=pr_data.get("author", {}).get("login", "unknown") if pr_data.get("author") else "unknown",
                created_at=pr_data.get("createdAt", ""),
                merged_at=pr_data.get("mergedAt"),
            )
            prs.append(pr)

        return prs

    except subprocess.TimeoutExpired:
        print(f"Timeout fetching {owner}/{repo}")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return []


def search_prs_with_gh(query: str, limit: int = 100) -> list[dict]:
    """Search PRs across GitHub using gh CLI."""

    cmd = [
        "gh",
        "search",
        "prs",
        query,
        "--limit",
        str(limit),
        "--json",
        "repository,number,title,body,author,createdAt",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"Error searching: {result.stderr}")
            return []

        return json.loads(result.stdout)

    except subprocess.TimeoutExpired:
        print("Search timeout")
        return []
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return []


def analyze_prs_with_regex(prs: list[FetchedPR]) -> list[dict]:
    """Run regex detection on PRs."""
    results = []

    for pr in prs:
        text = f"{pr.title}\n\n{pr.body}"
        result = detect_ai_in_text(text)

        # Check for explicit signatures (high confidence)
        has_claude_code_sig = "generated with" in pr.body.lower() and "claude" in pr.body.lower()
        has_co_author = "co-authored-by:" in pr.body.lower() and any(
            ai in pr.body.lower() for ai in ["claude", "copilot", "cursor", "anthropic"]
        )

        results.append(
            {
                "repo": pr.repo,
                "number": pr.number,
                "title": pr.title[:80],
                "author": pr.author,
                "has_ai_disclosure": "ai disclosure" in pr.body.lower(),
                "has_explicit_signature": has_claude_code_sig or has_co_author,
                "regex_detected": result["is_ai_assisted"],
                "regex_tools": result["ai_tools"],
                "body_excerpt": pr.body[:300].replace("\n", " ").replace("\r", "") if pr.body else "",
            }
        )

    return results


def print_summary(results: list[dict], repo_name: str):
    """Print analysis summary."""
    total = len(results)
    if total == 0:
        print(f"\n{repo_name}: No PRs found")
        return

    detected = sum(1 for r in results if r["regex_detected"])
    has_disclosure = sum(1 for r in results if r["has_ai_disclosure"])
    has_explicit = sum(1 for r in results if r["has_explicit_signature"])

    print(f"\n{'=' * 60}")
    print(f"REPO: {repo_name}")
    print(f"{'=' * 60}")
    print(f"Total PRs analyzed: {total}")
    print(f"With AI Disclosure section: {has_disclosure} ({has_disclosure / total * 100:.1f}%)")
    print(f"With explicit AI signature: {has_explicit} ({has_explicit / total * 100:.1f}%)")
    print(f"Detected by regex: {detected} ({detected / total * 100:.1f}%)")

    # Tool breakdown
    tool_counts = {}
    for r in results:
        for tool in r["regex_tools"]:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    if tool_counts:
        print("\nTools detected:")
        for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            print(f"  {tool}: {count}")

    # High confidence detections (explicit signatures)
    explicit_prs = [r for r in results if r["has_explicit_signature"]][:5]
    if explicit_prs:
        print("\nHigh confidence detections (explicit signatures):")
        for r in explicit_prs:
            print(f"  #{r['number']}: {r['title'][:50]}...")

    # Potential false positives (detected but no explicit signature)
    potential_fp = [r for r in results if r["regex_detected"] and not r["has_explicit_signature"]][:3]
    if potential_fp:
        print(f"\nPotential false positives ({len(potential_fp)} detected, no explicit sig):")
        for r in potential_fp:
            print(f"  #{r['number']}: Tools={r['regex_tools']}")
            print(f"    {r['body_excerpt'][:80]}...")


def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(description="Fetch and analyze OSS PRs for AI detection")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3], help="Repo tier to analyze")
    parser.add_argument("--search", type=str, help="Search query for GitHub PR search")
    parser.add_argument("--limit", type=int, default=50, help="Limit per repo (default: 50)")
    args = parser.parse_args()

    all_results = []

    if args.search:
        print(f"\nSearching GitHub for: {args.search}")
        search_results = search_prs_with_gh(args.search, limit=args.limit)
        print(f"Found {len(search_results)} PRs")

        # Group by repository
        repos = {}
        for pr in search_results:
            repo = pr["repository"]["nameWithOwner"]
            if repo not in repos:
                repos[repo] = []
            repos[repo].append(pr)

        print(f"From {len(repos)} unique repositories")
        for repo, count in sorted(repos.items(), key=lambda x: -len(x[1]))[:10]:
            print(f"  {repo}: {len(count)} PRs")

    else:
        # Select tier
        if args.tier == 1:
            repos = TIER1_REPOS
        elif args.tier == 2:
            repos = TIER2_REPOS
        elif args.tier == 3:
            repos = TIER3_REPOS
        else:
            repos = TIER1_REPOS[:2]  # Default: first 2 repos

        for owner, repo in repos:
            print(f"\nFetching PRs from {owner}/{repo}...")
            try:
                prs = fetch_prs_with_gh(owner, repo, limit=args.limit)
                print(f"  Fetched {len(prs)} PRs")

                if prs:
                    results = analyze_prs_with_regex(prs)
                    print_summary(results, f"{owner}/{repo}")
                    all_results.extend(results)
            except Exception as e:
                print(f"  Error: {e}")

        # Save results
        output_path = Path(__file__).parent / "oss_pr_analysis.json"
        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to {output_path}")

        # Overall summary
        if all_results:
            print(f"\n{'=' * 60}")
            print("OVERALL SUMMARY")
            print(f"{'=' * 60}")
            print(f"Total PRs: {len(all_results)}")
            print(f"Detected by regex: {sum(1 for r in all_results if r['regex_detected'])}")
            print(f"With explicit signature: {sum(1 for r in all_results if r['has_explicit_signature'])}")
            print(f"With AI Disclosure: {sum(1 for r in all_results if r['has_ai_disclosure'])}")


if __name__ == "__main__":
    main()
