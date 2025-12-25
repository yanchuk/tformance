#!/bin/bash
# Q1-Q3 2025 OSS seeding script - All data from product-focused projects
# Run: ./scripts/seed_all_oss.sh
#
# Fetches ALL PRs from Q1-Q3 2025 (Q4 already seeded)
# Expected: ~15,000+ PRs from 11 product companies
# Time estimate: 4-8 hours depending on rate limits
#
# Run seed_all_oss_part2.sh after this for remaining 14 projects

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
LOG_FILE="seeding_$(date +%Y%m%d_%H%M%S).log"
echo "Logging to: $LOG_FILE"

# Part 1: 11 product-focused projects (Part 2 has remaining 14)
PROJECTS=(
    # Tier 3: Large Product Teams (100+ contributors)
    "twenty"      # Salesforce alternative (561 contributors)
    "novu"        # Notification infra (447 contributors)
    "hoppscotch"  # Postman alternative (314 contributors)
    "plane"       # Jira alternative (151 contributors)
    "documenso"   # DocuSign alternative (142 contributors)

    # Tier 4: Self-Hosting & DevTools
    "coolify"     # Heroku alternative (48.7k stars)
    "infisical"   # Secrets management (24.3k stars)
    "dub"         # Link platform (88 contributors)

    # Tier 5: Billing & Surveys
    "lago"        # Usage billing (YC backed)
    "formbricks"  # Qualtrics alternative

    # Tier 6: AI-Native Startups
    "compai"      # AI compliance (trycomp.ai)
)

echo "==========================================="
echo "Q1-Q3 2025 OSS Data Import"
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
echo "$(date): All projects seeded!" | tee -a "$LOG_FILE"
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
