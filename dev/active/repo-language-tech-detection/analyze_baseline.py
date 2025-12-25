#!/usr/bin/env python
"""Analyze baseline pattern detection accuracy vs LLM ground truth.

This script compares:
1. Current PRFile.categorize_file() pattern-based detection
2. LLM tech.categories from llm_summary

Focus: "javascript" category files (ambiguous JS/TS)

Usage:
    python dev/active/repo-language-tech-detection/analyze_baseline.py
"""

import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")

import django

django.setup()

from apps.metrics.models import PRFile, PullRequest


@dataclass
class CategoryMetrics:
    """Metrics for a single category."""

    tp: int = 0  # True positives (pattern matches LLM)
    fp: int = 0  # False positives (pattern says X, LLM says something else)
    fn: int = 0  # False negatives (LLM says X, pattern says something else)

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) > 0 else 0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) > 0 else 0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0


def map_llm_to_file_category(llm_categories: list, filename: str) -> str:
    """Map LLM tech.categories to PRFile.CATEGORY_CHOICES.

    LLM outputs: ["backend", "frontend", "devops", "mobile", "data"]
    File categories: ["frontend", "backend", "javascript", "test", "docs", "config", "other"]

    Strategy:
    - If LLM says only "backend" -> "backend"
    - If LLM says only "frontend" -> "frontend"
    - If LLM says both or neither -> use file extension
    - If LLM says "devops" -> check if config file, else "backend"
    """
    if not llm_categories:
        # Fallback to extension-based
        return PRFile.categorize_file(filename)

    has_backend = "backend" in llm_categories
    has_frontend = "frontend" in llm_categories
    has_devops = "devops" in llm_categories

    # Clear cases
    if has_backend and not has_frontend:
        return "backend"
    if has_frontend and not has_backend:
        return "frontend"

    # DevOps often means config/infrastructure
    if has_devops and not has_backend and not has_frontend:
        if filename.lower().endswith((".yaml", ".yml", ".json", ".toml", ".ini")):
            return "config"
        return "backend"  # Infrastructure code is backend

    # Ambiguous: both or neither
    # Use extension as tiebreaker
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext in ("py", "go", "java", "rb", "php", "rs", "ex", "exs"):
        return "backend"
    if ext in ("jsx", "tsx", "vue", "svelte"):
        return "frontend"
    if ext in ("js", "ts", "mjs", "cjs"):
        return "javascript"  # Still ambiguous

    return PRFile.categorize_file(filename)


def get_files_with_llm_data():
    """Get all PRFiles where the PR has LLM tech data."""
    # Get PRs with LLM summary containing tech.categories
    prs_with_tech = (
        PullRequest.objects.filter(llm_summary__isnull=False)
        .exclude(llm_summary__tech__isnull=True)
        .values_list("id", flat=True)
    )

    files = PRFile.objects.filter(pull_request_id__in=prs_with_tech).select_related("pull_request")

    return files


def analyze_baseline():
    """Run baseline analysis comparing pattern vs LLM."""
    print("=== Baseline Analysis: Pattern vs LLM Tech Detection ===\n")

    files = get_files_with_llm_data()
    total_files = files.count()
    print(f"Total files with LLM tech data: {total_files:,}")

    # Category metrics
    metrics = defaultdict(CategoryMetrics)

    # Confusion matrix for javascript files
    js_confusion = Counter()  # (pattern_cat, llm_cat) -> count

    # Per-repo breakdown
    repo_stats = defaultdict(lambda: {"total": 0, "matches": 0, "js_files": 0})

    # Sample mismatches for analysis
    mismatches = []

    processed = 0
    for file in files.iterator(chunk_size=1000):
        processed += 1
        if processed % 10000 == 0:
            print(f"  Processed {processed:,} files...")

        # Get pattern prediction
        pattern_cat = file.file_category

        # Get LLM ground truth
        llm_summary = file.pull_request.llm_summary or {}
        tech = llm_summary.get("tech", {})
        llm_categories = tech.get("categories", [])
        llm_cat = map_llm_to_file_category(llm_categories, file.filename)

        repo = file.pull_request.github_repo
        repo_stats[repo]["total"] += 1

        # Track matches
        if pattern_cat == llm_cat:
            metrics[pattern_cat].tp += 1
            repo_stats[repo]["matches"] += 1
        else:
            metrics[pattern_cat].fp += 1
            metrics[llm_cat].fn += 1

            # Sample mismatches (limit to 100)
            if len(mismatches) < 100:
                mismatches.append(
                    {
                        "file": file.filename,
                        "pattern": pattern_cat,
                        "llm": llm_cat,
                        "llm_raw": llm_categories,
                        "repo": repo,
                    }
                )

        # Track javascript confusion
        if pattern_cat == "javascript":
            js_confusion[(pattern_cat, llm_cat)] += 1
            repo_stats[repo]["js_files"] += 1

    print(f"\nProcessed {processed:,} files total")

    # Calculate overall accuracy
    total_matches = sum(m.tp for m in metrics.values())
    overall_accuracy = total_matches / total_files if total_files > 0 else 0
    print(f"\n=== Overall Accuracy: {overall_accuracy:.1%} ===")

    # Per-category metrics
    print("\n=== Per-Category Metrics ===")
    print(f"{'Category':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>8} {'FP':>8} {'FN':>8}")
    print("-" * 70)
    for cat in ["frontend", "backend", "javascript", "test", "docs", "config", "other"]:
        m = metrics[cat]
        print(f"{cat:<12} {m.precision:>10.1%} {m.recall:>10.1%} {m.f1:>10.1%} {m.tp:>8} {m.fp:>8} {m.fn:>8}")

    # JavaScript confusion matrix
    print("\n=== 'javascript' Category Confusion ===")
    print("Pattern says 'javascript', LLM says:")
    js_total = sum(c for (p, l), c in js_confusion.items() if p == "javascript")
    for (pattern_cat, llm_cat), count in sorted(js_confusion.items(), key=lambda x: -x[1]):
        if pattern_cat == "javascript":
            pct = count / js_total * 100 if js_total > 0 else 0
            print(f"  {llm_cat:<12}: {count:>6} ({pct:.1f}%)")

    # Repos with most javascript files
    print("\n=== Repos with Most 'javascript' Files ===")
    js_repos = sorted(
        [(r, s["js_files"], s["total"]) for r, s in repo_stats.items() if s["js_files"] > 0], key=lambda x: -x[1]
    )[:15]
    for repo, js_count, total in js_repos:
        pct = js_count / total * 100 if total > 0 else 0
        print(f"  {repo}: {js_count:,} / {total:,} ({pct:.1f}%)")

    # Sample mismatches
    print("\n=== Sample Pattern != LLM Mismatches ===")
    for m in mismatches[:20]:
        print(f"  {m['file'][:50]:<50} pattern={m['pattern']:<12} llm={m['llm']:<12} raw={m['llm_raw']}")

    # Save detailed results
    results = {
        "overall_accuracy": overall_accuracy,
        "total_files": total_files,
        "category_metrics": {
            cat: {"precision": m.precision, "recall": m.recall, "f1": m.f1, "tp": m.tp, "fp": m.fp, "fn": m.fn}
            for cat, m in metrics.items()
        },
        "js_confusion": {f"{p}_{l}": c for (p, l), c in js_confusion.items()},
        "repo_stats": dict(repo_stats),
        "sample_mismatches": mismatches[:100],
    }

    output_path = Path(__file__).parent / "baseline_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nDetailed results saved to: {output_path}")

    # Key findings
    print("\n=== KEY FINDINGS ===")
    js_metrics = metrics["javascript"]
    js_accuracy = js_metrics.tp / (js_metrics.tp + js_metrics.fp) if (js_metrics.tp + js_metrics.fp) > 0 else 0
    print(f"1. Overall accuracy: {overall_accuracy:.1%}")
    print(f"2. 'javascript' category precision: {js_metrics.precision:.1%}")
    print(f"3. 'javascript' files total: {js_metrics.tp + js_metrics.fp:,}")
    print(f"4. 'javascript' correctly classified: {js_metrics.tp:,}")

    # Decision point
    print("\n=== DECISION POINT ===")
    if js_metrics.precision < 0.80:
        print(f"✓ 'javascript' precision ({js_metrics.precision:.1%}) < 80% → PROCEED to Phase 2")
    else:
        print(f"✗ 'javascript' precision ({js_metrics.precision:.1%}) >= 80% → Pattern already good")


if __name__ == "__main__":
    analyze_baseline()
