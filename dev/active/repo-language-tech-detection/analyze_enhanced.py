#!/usr/bin/env python
"""Analyze enhanced pattern detection using repo language stats.

This script compares:
1. Enhanced categorize_file_with_repo_context()
2. LLM tech.categories from llm_summary

Uses repo language stats to improve "javascript" classification.

Usage:
    python dev/active/repo-language-tech-detection/analyze_enhanced.py
    python dev/active/repo-language-tech-detection/analyze_enhanced.py --threshold 80
"""

import argparse
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

    tp: int = 0
    fp: int = 0
    fn: int = 0

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


def load_repo_languages():
    """Load cached repo language data."""
    path = Path(__file__).parent / "repo_languages.json"
    if not path.exists():
        raise FileNotFoundError(f"Run fetch_repo_languages.py first: {path}")
    with open(path) as f:
        return json.load(f)


def categorize_file_with_repo_context(
    filename: str, repo_languages: dict[str, int] | None = None, threshold: int = 70
) -> str:
    """Categorize file using extension + repo language distribution.

    Enhancement over base categorize_file():
    1. If base returns "javascript" (ambiguous), consult repo stats
    2. If repo is >threshold% backend languages, classify as backend
    3. If repo is >threshold% frontend languages, classify as frontend

    Args:
        filename: File path
        repo_languages: Dict of language -> bytes (from GitHub API)
        threshold: Percentage threshold for language dominance (0-100)

    Returns:
        Category string
    """
    base_category = PRFile.categorize_file(filename)

    # Only enhance ambiguous cases
    if base_category != "javascript" or not repo_languages:
        return base_category

    # Calculate language percentages
    total_bytes = sum(repo_languages.values())
    if total_bytes == 0:
        return base_category

    percentages = {lang: (bytes_ / total_bytes) * 100 for lang, bytes_ in repo_languages.items()}

    # Backend-dominant languages
    backend_langs = {
        "Python",
        "Go",
        "Ruby",
        "Java",
        "PHP",
        "Rust",
        "C#",
        "Kotlin",
        "C",
        "C++",
        "Scala",
        "Elixir",
        "Erlang",
        "Clojure",
        "Haskell",
        "Swift",
        "Objective-C",  # iOS backend/mobile
    }
    backend_pct = sum(percentages.get(l, 0) for l in backend_langs)

    # Frontend-dominant languages
    frontend_langs = {
        "TypeScript",
        "JavaScript",
        "CSS",
        "SCSS",
        "Sass",
        "Less",
        "Vue",
        "Svelte",
        "HTML",
        "MDX",
    }
    frontend_pct = sum(percentages.get(l, 0) for l in frontend_langs)

    # Apply threshold logic
    if backend_pct >= threshold and frontend_pct < threshold:
        # Backend-dominant repo: JS/TS is likely tooling/build scripts
        return "backend"

    if frontend_pct >= threshold and backend_pct < threshold:
        # Frontend-dominant repo: need path heuristics
        filename_lower = filename.lower()
        # Check for backend-specific paths even in frontend repos
        backend_paths = ["/api/", "/server/", "/backend/", "/services/"]
        if any(p in filename_lower for p in backend_paths):
            return "backend"
        return "frontend"

    # Mixed repo or below threshold: keep as ambiguous
    return "javascript"


def map_llm_to_file_category(llm_categories: list, filename: str) -> str:
    """Map LLM tech.categories to PRFile.CATEGORY_CHOICES."""
    if not llm_categories:
        return PRFile.categorize_file(filename)

    has_backend = "backend" in llm_categories
    has_frontend = "frontend" in llm_categories
    has_devops = "devops" in llm_categories

    if has_backend and not has_frontend:
        return "backend"
    if has_frontend and not has_backend:
        return "frontend"

    if has_devops and not has_backend and not has_frontend:
        if filename.lower().endswith((".yaml", ".yml", ".json", ".toml", ".ini")):
            return "config"
        return "backend"

    # Ambiguous: use extension
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    if ext in ("py", "go", "java", "rb", "php", "rs", "ex", "exs"):
        return "backend"
    if ext in ("jsx", "tsx", "vue", "svelte"):
        return "frontend"
    if ext in ("js", "ts", "mjs", "cjs"):
        return "javascript"

    return PRFile.categorize_file(filename)


def analyze_enhanced(threshold: int = 70):
    """Run enhanced analysis with repo language context."""
    print(f"=== Enhanced Analysis (threshold={threshold}%) ===\n")

    # Load repo languages
    repo_languages = load_repo_languages()
    print(f"Loaded language data for {len(repo_languages)} repos")

    # Get files with LLM data
    prs_with_tech = (
        PullRequest.objects.filter(llm_summary__isnull=False)
        .exclude(llm_summary__tech__isnull=True)
        .values_list("id", "github_repo")
    )

    pr_to_repo = {pr_id: repo for pr_id, repo in prs_with_tech}
    pr_ids = list(pr_to_repo.keys())

    files = PRFile.objects.filter(pull_request_id__in=pr_ids).select_related("pull_request")

    total_files = files.count()
    print(f"Total files to analyze: {total_files:,}")

    # Metrics
    baseline_metrics = defaultdict(CategoryMetrics)
    enhanced_metrics = defaultdict(CategoryMetrics)

    # Track javascript reclassifications
    js_reclassified = Counter()  # (baseline, enhanced, llm) -> count
    js_improvement = {"correct": 0, "incorrect": 0, "unchanged": 0}

    processed = 0
    for file in files.iterator(chunk_size=1000):
        processed += 1
        if processed % 20000 == 0:
            print(f"  Processed {processed:,} files...")

        repo = file.pull_request.github_repo
        languages = repo_languages.get(repo, {})

        # Baseline (no repo context)
        baseline_cat = file.file_category

        # Enhanced (with repo context)
        enhanced_cat = categorize_file_with_repo_context(file.filename, languages, threshold)

        # LLM ground truth
        llm_summary = file.pull_request.llm_summary or {}
        tech = llm_summary.get("tech", {})
        llm_categories = tech.get("categories", [])
        llm_cat = map_llm_to_file_category(llm_categories, file.filename)

        # Baseline metrics
        if baseline_cat == llm_cat:
            baseline_metrics[baseline_cat].tp += 1
        else:
            baseline_metrics[baseline_cat].fp += 1
            baseline_metrics[llm_cat].fn += 1

        # Enhanced metrics
        if enhanced_cat == llm_cat:
            enhanced_metrics[enhanced_cat].tp += 1
        else:
            enhanced_metrics[enhanced_cat].fp += 1
            enhanced_metrics[llm_cat].fn += 1

        # Track javascript reclassifications
        if baseline_cat == "javascript":
            js_reclassified[(baseline_cat, enhanced_cat, llm_cat)] += 1

            if baseline_cat != enhanced_cat:  # Was reclassified
                if enhanced_cat == llm_cat:
                    js_improvement["correct"] += 1
                else:
                    js_improvement["incorrect"] += 1
            else:
                js_improvement["unchanged"] += 1

    print(f"\nProcessed {processed:,} files total")

    # Calculate accuracies
    baseline_accuracy = sum(m.tp for m in baseline_metrics.values()) / total_files
    enhanced_accuracy = sum(m.tp for m in enhanced_metrics.values()) / total_files
    improvement = enhanced_accuracy - baseline_accuracy

    print(f"\n{'=' * 60}")
    print(f"RESULTS (threshold={threshold}%)")
    print(f"{'=' * 60}")
    print(f"Baseline accuracy:  {baseline_accuracy:.1%}")
    print(f"Enhanced accuracy:  {enhanced_accuracy:.1%}")
    print(f"Improvement:        {improvement:+.1%}")

    # Per-category comparison
    print(f"\n{'Category':<12} {'Baseline':>12} {'Enhanced':>12} {'Delta':>10}")
    print("-" * 48)
    for cat in ["frontend", "backend", "javascript", "test", "docs", "config", "other"]:
        b = baseline_metrics[cat]
        e = enhanced_metrics[cat]
        delta = e.precision - b.precision
        print(f"{cat:<12} {b.precision:>12.1%} {e.precision:>12.1%} {delta:>+10.1%}")

    # JavaScript reclassification analysis
    print("\n=== 'javascript' Reclassification Analysis ===")
    print(f"Total 'javascript' files: {sum(js_reclassified.values()):,}")
    print(f"Correctly reclassified: {js_improvement['correct']:,}")
    print(f"Incorrectly reclassified: {js_improvement['incorrect']:,}")
    print(f"Unchanged: {js_improvement['unchanged']:,}")

    if js_improvement["correct"] + js_improvement["incorrect"] > 0:
        reclassify_accuracy = js_improvement["correct"] / (js_improvement["correct"] + js_improvement["incorrect"])
        print(f"Reclassification accuracy: {reclassify_accuracy:.1%}")

    # Show reclassification breakdown
    print("\nReclassification breakdown (baseline -> enhanced, LLM says):")
    for (base, enh, llm), count in sorted(js_reclassified.items(), key=lambda x: -x[1])[:15]:
        if base != enh:
            correct = "✓" if enh == llm else "✗"
            print(f"  {base} -> {enh:<12} (LLM: {llm:<12}) : {count:>6} {correct}")

    # Save results
    results = {
        "threshold": threshold,
        "baseline_accuracy": baseline_accuracy,
        "enhanced_accuracy": enhanced_accuracy,
        "improvement": improvement,
        "js_improvement": js_improvement,
        "baseline_metrics": {
            cat: {"precision": m.precision, "recall": m.recall, "f1": m.f1} for cat, m in baseline_metrics.items()
        },
        "enhanced_metrics": {
            cat: {"precision": m.precision, "recall": m.recall, "f1": m.f1} for cat, m in enhanced_metrics.items()
        },
    }

    output_path = Path(__file__).parent / f"enhanced_results_t{threshold}.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")

    # Decision point
    print(f"\n{'=' * 60}")
    print("DECISION POINT")
    print(f"{'=' * 60}")
    if improvement >= 0.10:
        print(f"✓ Improvement ({improvement:+.1%}) >= 10% → PROCEED to Phase 3 (threshold tuning)")
    elif improvement >= 0.05:
        print(f"△ Improvement ({improvement:+.1%}) 5-10% → Consider cost/benefit")
    else:
        print(f"✗ Improvement ({improvement:+.1%}) < 5% → Enhancement may not be worth it")

    return results


def run_threshold_sweep():
    """Run analysis across multiple thresholds."""
    print("=== Threshold Sweep ===\n")

    results = {}
    for threshold in [50, 60, 70, 80, 90]:
        print(f"\n{'#' * 60}")
        r = analyze_enhanced(threshold)
        results[threshold] = r
        print()

    # Summary
    print("\n" + "=" * 60)
    print("THRESHOLD SWEEP SUMMARY")
    print("=" * 60)
    print(f"{'Threshold':>10} {'Baseline':>12} {'Enhanced':>12} {'Improve':>10} {'JS Correct':>12}")
    print("-" * 60)
    for t, r in sorted(results.items()):
        print(
            f"{t:>10}% {r['baseline_accuracy']:>12.1%} {r['enhanced_accuracy']:>12.1%} "
            f"{r['improvement']:>+10.1%} {r['js_improvement']['correct']:>12,}"
        )

    # Find best threshold
    best_t = max(results.keys(), key=lambda t: results[t]["improvement"])
    print(f"\nBest threshold: {best_t}% (improvement: {results[best_t]['improvement']:+.1%})")

    # Save sweep results
    output_path = Path(__file__).parent / "threshold_sweep_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Sweep results saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=70, help="Threshold percentage (default 70)")
    parser.add_argument("--sweep", action="store_true", help="Run threshold sweep (50-90%)")
    args = parser.parse_args()

    if args.sweep:
        run_threshold_sweep()
    else:
        analyze_enhanced(args.threshold)
