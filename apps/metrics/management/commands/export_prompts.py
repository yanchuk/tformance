"""Export prompts and promptfoo configuration.

Auto-generates promptfoo configuration from Python source of truth,
eliminating manual sync between code and test files.

Usage:
    python manage.py export_prompts
    python manage.py export_prompts --output /path/to/output
    python manage.py export_prompts --dry-run

The command generates:
    - prompts/v{VERSION}-system.txt - Current system prompt
    - promptfoo.yaml - Configuration with correct version reference
"""

from pathlib import Path

from django.core.management.base import BaseCommand

from apps.metrics.prompts.export import export_promptfoo_config
from apps.metrics.services.llm_prompts import PROMPT_VERSION


class Command(BaseCommand):
    help = "Export prompts and promptfoo configuration (auto-generated from Python source)"

    # Default output directory relative to project root
    DEFAULT_OUTPUT = "dev/active/ai-detection-pr-descriptions/experiments"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            "-o",
            type=str,
            default=self.DEFAULT_OUTPUT,
            help=f"Output directory (default: {self.DEFAULT_OUTPUT})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be generated without writing files",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output"])
        dry_run = options["dry_run"]

        self.stdout.write(f"Prompt version: {PROMPT_VERSION}")
        self.stdout.write(f"Output directory: {output_dir}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN ===\n"))
            self.stdout.write("Would generate:")
            self.stdout.write(f"  - {output_dir}/prompts/v{PROMPT_VERSION}-system.txt")
            self.stdout.write(f"  - {output_dir}/promptfoo.yaml")
            return

        # Export configuration
        result = export_promptfoo_config(output_dir)

        self.stdout.write(self.style.SUCCESS("\nGenerated files:"))
        self.stdout.write(f"  ✓ {result['prompt']}")
        self.stdout.write(f"  ✓ {result['config']}")

        self.stdout.write(self.style.SUCCESS(f"\nPromptfoo config ready for v{PROMPT_VERSION}"))
        self.stdout.write("\nNext steps:")
        self.stdout.write(f"  cd {output_dir}")
        self.stdout.write("  export GROQ_API_KEY='your-key'")
        self.stdout.write("  npx promptfoo eval")
        self.stdout.write("  npx promptfoo view")
