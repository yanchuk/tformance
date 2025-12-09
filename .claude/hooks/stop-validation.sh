#!/bin/bash
# Stop hook that validates code quality before allowing stop
# Runs ruff and optionally tests on affected apps

set -e

# Read input from stdin
read -r input 2>/dev/null || true

# Get project directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"

# Check if we have a cache of affected apps
CACHE_DIR="$PROJECT_DIR/.claude/cache"
SESSION_CACHE=$(find "$CACHE_DIR" -maxdepth 1 -type d -name "*" 2>/dev/null | head -1)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 CODE VALIDATION CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run ruff format check
echo "📝 Checking code formatting (ruff)..."
if ! make ruff-format 2>&1 | head -20; then
    echo ""
    echo "⚠️  Formatting issues found. Run 'make ruff-format' to fix."
    echo ""
fi

# Run ruff lint check
echo ""
echo "🔎 Checking code quality (ruff lint)..."
if ! make ruff-lint 2>&1 | head -20; then
    echo ""
    echo "⚠️  Linting issues found. Run 'make ruff-lint' to fix."
    echo ""
fi

# Check for missing migrations
echo ""
echo "🗃️  Checking for missing migrations..."
MIGRATION_CHECK=$(make manage ARGS='makemigrations --dry-run --check' 2>&1) || true
if echo "$MIGRATION_CHECK" | grep -q "No changes detected"; then
    echo "✅ No missing migrations"
else
    echo "⚠️  Missing migrations detected. Run 'make migrations' to create them."
    echo "$MIGRATION_CHECK" | head -10
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 TIP: Run 'make test' to verify tests pass"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Exit 0 to not block - just informational
exit 0
