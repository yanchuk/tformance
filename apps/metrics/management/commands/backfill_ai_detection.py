"""Management command to backfill AI detection for existing PRs."""

from django.core.management.base import BaseCommand

from apps.metrics.experiments.runner import detect_ai_with_litellm
from apps.metrics.models import PullRequest
from apps.metrics.services.ai_detector import detect_ai_in_text
from apps.teams.models import Team

# Default system prompt for LLM detection
DEFAULT_SYSTEM_PROMPT = """You are an AI detection system analyzing pull requests.
Your task is to identify if AI coding assistants were used.
You MUST respond with valid JSON only.

## Detection Rules

POSITIVE signals (AI was used):
1. Tool names: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine
2. In "AI Disclosure" section: Any usage statement like "Used for", "Used to", "Helped with"
3. Co-Authored-By with AI names or @anthropic.com/@cursor.sh emails
4. Phrases: "AI-generated", "AI-assisted", "generated with", "written by AI"

NEGATIVE signals (AI was NOT used):
1. Explicit denials: "No AI", "None", "Not used", "N/A"
2. AI as feature: "Add AI to dashboard" (building AI features ≠ using AI to code)
3. Past tense references: "Devin's previous PR" (referencing past work)

## Response Format

Return JSON with these fields:
- is_ai_assisted: boolean
- tools: list of lowercase tool names detected (e.g., ["cursor", "claude"])
- usage_category: "authored" | "assisted" | "reviewed" | "brainstorm" | null
- confidence: float 0.0-1.0
- reasoning: brief 1-sentence explanation"""


class Command(BaseCommand):
    """Backfill AI detection for existing PRs using regex or LLM."""

    help = "Backfill AI detection for existing PRs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            help="Team name to filter PRs",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving to database",
        )
        parser.add_argument(
            "--use-llm",
            action="store_true",
            help="Use Groq LLM for detection (requires GROQ_API_KEY)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum PRs to process (default: 100)",
        )
        parser.add_argument(
            "--only-undetected",
            action="store_true",
            help="Only process PRs not currently marked as AI-assisted",
        )
        parser.add_argument(
            "--model",
            type=str,
            default="groq/llama-3.3-70b-versatile",
            help="LiteLLM model string (default: groq/llama-3.3-70b-versatile)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Show detailed output for each PR",
        )

    def handle(self, *args, **options):
        team_name = options.get("team")
        dry_run = options["dry_run"]
        use_llm = options["use_llm"]
        limit = options["limit"]
        only_undetected = options["only_undetected"]
        model = options["model"]
        verbose = options["verbose"]

        # Get team if specified
        team = None
        if team_name:
            try:
                team = Team.objects.get(name=team_name)
                self.stdout.write(f"Filtering by team: {team.name}")
            except Team.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Team '{team_name}' not found"))
                return

        # Build queryset - intentionally unscoped, will filter by team below
        qs = PullRequest.objects.filter(  # noqa: TEAM001 - Admin command with team filter
            body__isnull=False,
        ).exclude(body="")

        if team:
            qs = qs.filter(team=team)

        if only_undetected:
            qs = qs.filter(is_ai_assisted=False)

        prs = list(qs[:limit])

        if not prs:
            self.stdout.write("No PRs to process")
            return

        self.stdout.write(f"\nProcessing {len(prs)} PRs...")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved\n"))
        if use_llm:
            self.stdout.write(f"Using LLM: {model}\n")

        # Track changes
        changes = []
        errors = []
        total = len(prs)

        for idx, pr in enumerate(prs, start=1):
            if verbose or idx % 10 == 0:
                self.stdout.write(f"Processing {idx}/{total}...")

            try:
                result = self._process_pr(pr, use_llm, model)
                if result:
                    changes.append(result)

                    if not dry_run:
                        self._save_pr(pr, result)

                    if verbose:
                        self._print_change(result)

            except Exception as e:
                errors.append({"pr_id": pr.id, "error": str(e)})
                if verbose:
                    self.stderr.write(f"  Error processing PR #{pr.github_pr_id}: {e}")

        # Summary
        self._print_summary(changes, errors, dry_run, use_llm)

    def _process_pr(self, pr, use_llm: bool, model: str) -> dict | None:
        """Process a single PR and return change dict if detection changed."""
        # Current state
        old_ai = pr.is_ai_assisted
        old_tools = pr.ai_tools_detected or []

        # New detection
        text = f"{pr.title}\n\n{pr.body}"

        if use_llm:
            llm_result = detect_ai_with_litellm(
                pr_body=pr.body or "",
                model=model,
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                temperature=0,
                max_tokens=500,
            )
            new_ai = llm_result.is_ai_assisted
            new_tools = llm_result.tools
            confidence = llm_result.confidence
            reasoning = llm_result.reasoning
        else:
            regex_result = detect_ai_in_text(text)
            new_ai = regex_result["is_ai_assisted"]
            new_tools = regex_result["ai_tools"]
            confidence = 1.0 if new_ai else 0.0
            reasoning = None

        # Check if changed
        if new_ai != old_ai or set(new_tools) != set(old_tools):
            return {
                "pr_id": pr.id,
                "pr_number": pr.github_pr_id,
                "repo": pr.github_repo,
                "old_ai": old_ai,
                "new_ai": new_ai,
                "old_tools": old_tools,
                "new_tools": new_tools,
                "confidence": confidence,
                "reasoning": reasoning,
                "body_preview": (pr.body or "")[:200],
            }

        return None

    def _save_pr(self, pr, result: dict):
        """Save updated detection to database."""
        pr.is_ai_assisted = result["new_ai"]
        pr.ai_tools_detected = result["new_tools"]
        pr.save(update_fields=["is_ai_assisted", "ai_tools_detected"])

    def _print_change(self, result: dict):
        """Print a single change."""
        status = "+" if result["new_ai"] else "-"
        self.stdout.write(
            f"  {status} PR #{result['pr_number']} ({result['repo']}): {result['old_ai']} → {result['new_ai']}"
        )
        if result["new_tools"]:
            self.stdout.write(f"    Tools: {result['new_tools']}")
        if result["reasoning"]:
            self.stdout.write(f"    Reason: {result['reasoning']}")

    def _print_summary(self, changes: list, errors: list, dry_run: bool, use_llm: bool):
        """Print summary of changes."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("SUMMARY") if not dry_run else self.style.WARNING("DRY RUN SUMMARY"))
        self.stdout.write("=" * 50)

        # Count changes by type
        new_detections = [c for c in changes if c["new_ai"] and not c["old_ai"]]
        removed_detections = [c for c in changes if not c["new_ai"] and c["old_ai"]]
        tool_changes = [c for c in changes if c["new_ai"] == c["old_ai"] and c["new_tools"] != c["old_tools"]]

        self.stdout.write(f"\nTotal PRs processed: {len(changes) + len(errors)}")
        self.stdout.write(f"Changes detected: {len(changes)}")
        self.stdout.write(f"  - New AI detections: {len(new_detections)}")
        self.stdout.write(f"  - Removed detections: {len(removed_detections)}")
        self.stdout.write(f"  - Tool changes only: {len(tool_changes)}")
        self.stdout.write(f"Errors: {len(errors)}")

        # Show new detections
        if new_detections:
            self.stdout.write(self.style.SUCCESS("\nNew AI Detections:"))
            for c in new_detections[:20]:
                tools = ", ".join(c["new_tools"]) if c["new_tools"] else "unknown"
                self.stdout.write(f"  PR #{c['pr_number']}: {tools}")
                if c["reasoning"]:
                    self.stdout.write(f"    → {c['reasoning']}")
            if len(new_detections) > 20:
                self.stdout.write(f"  ... and {len(new_detections) - 20} more")

        # Show removed detections (potential false positives being fixed)
        if removed_detections:
            self.stdout.write(self.style.WARNING("\nRemoved Detections (was false positive?):"))
            for c in removed_detections[:10]:
                old_tools = ", ".join(c["old_tools"]) if c["old_tools"] else "unknown"
                self.stdout.write(f"  PR #{c['pr_number']}: was [{old_tools}]")
            if len(removed_detections) > 10:
                self.stdout.write(f"  ... and {len(removed_detections) - 10} more")

        # Show errors
        if errors:
            self.stdout.write(self.style.ERROR("\nErrors:"))
            for e in errors[:5]:
                self.stdout.write(f"  PR {e['pr_id']}: {e['error']}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nNo changes saved (dry run mode)"))
            self.stdout.write("Run without --dry-run to apply changes")
