#!/bin/bash
# Q1-Q3 2025 OSS seeding script - Part 2 (remaining 14 projects)
# Run: ./scripts/seed_all_oss_part2.sh
#
# Fetches ALL PRs from Q1-Q3 2025 (Q4 already seeded)
# Expected: ~15,000+ PRs from 14 projects
# Time estimate: 4-8 hours depending on rate limits
#
# Run this AFTER seed_all_oss.sh completes

set -e

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Check for GitHub tokens
if [ -z "$GITHUB_SEEDING_TOKENS" ]; then
    echo "ERROR: GITHUB_SEEDING_TOKENS not set"
    echo "Export comma-separated GitHub PATs:"
    echo "  export GITHUB_SEEDING_TOKENS='token1,token2,token3'"
    exit 1
fi

# Date range for Q1-Q3 2025 (Q4 already seeded)
START_DATE="2025-01-01"
END_DATE="2025-09-30"

# Log file
LOG_FILE="seeding_part2_$(date +%Y%m%d_%H%M%S).log"
echo "Logging to: $LOG_FILE"

# Part 2: Remaining 14 projects
PROJECTS=(
    # Full parsing - smaller focused teams
    "antiwork"    # Gumroad, Flexile, Helper
    "polar"       # Polar platform + SDKs

    # Sampled - large active repos
    "posthog"     # Product analytics + SDKs
    "fastapi"     # Python web framework

    # AI-native companies
    "anthropic"   # Cookbook, SDKs, courses
    "langchain"   # LLM framework

    # Active OSS projects
    "calcom"      # Scheduling infrastructure
    "trigger"     # Background jobs platform

    # Tier 1: High AI Signal
    "vercel"      # AI SDK, Next.js, CLI
    "supabase"    # Firebase alternative
    "linear"      # Issue tracking

    # Tier 2: Varied Signal
    "resend"      # Email API
    "deno"        # JS/TS runtime
    "neon"        # Serverless Postgres
)

echo "==========================================="
echo "Q1-Q3 2025 OSS Data Import - Part 2"
echo "==========================================="
echo "Date range: $START_DATE to $END_DATE"
echo "Projects: ${#PROJECTS[@]}"
echo "Limits: No PR limit, No member limit"
echo "==========================================="
echo ""

# Seed each project
for project in "${PROJECTS[@]}"; do
    echo "========================================" | tee -a "$LOG_FILE"
    echo "$(date): Starting $project" | tee -a "$LOG_FILE"
    echo "========================================" | tee -a "$LOG_FILE"

    # Run seeding with full 2025 data (no limits)
    .venv/bin/python manage.py seed_real_projects \
        --project "$project" \
        --start-date "$START_DATE" \
        --end-date "$END_DATE" \
        --no-pr-limit \
        --no-member-limit \
        --no-check-runs \
        --refresh \
        2>&1 | tee -a "$LOG_FILE"

    echo "" | tee -a "$LOG_FILE"
    echo "$(date): Finished $project" | tee -a "$LOG_FILE"
    echo "" | tee -a "$LOG_FILE"

    # Small delay between projects to avoid rate limits
    sleep 5
done

echo ""
echo "========================================" | tee -a "$LOG_FILE"
echo "$(date): All Part 2 projects seeded!" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

# Run LLM batch analysis on new PRs
echo ""
echo "Now running LLM analysis on new PRs..."
if [ -n "$GROQ_API_KEY" ]; then
    .venv/bin/python manage.py run_llm_batch --limit 20000 2>&1 | tee -a "$LOG_FILE"

    echo ""
    echo "LLM batch submitted. Check status with:"
    echo "  GROQ_API_KEY=\$GROQ_API_KEY .venv/bin/python manage.py run_llm_batch --status <batch_id>"
else
    echo "GROQ_API_KEY not set - skipping LLM analysis"
    echo "Run manually after setting GROQ_API_KEY:"
    echo "  GROQ_API_KEY=\$GROQ_API_KEY .venv/bin/python manage.py run_llm_batch --limit 20000"
fi

echo ""
echo "Done! Check $LOG_FILE for details."
