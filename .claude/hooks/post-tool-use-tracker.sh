#!/bin/bash
set -e

# Post-tool-use hook that tracks edited files for Django projects
# This runs after Edit, MultiEdit, or Write tools complete successfully

# Read tool information from stdin
tool_info=$(cat)

# Extract relevant data
tool_name=$(echo "$tool_info" | jq -r '.tool_name // empty')
file_path=$(echo "$tool_info" | jq -r '.tool_input.file_path // empty')
session_id=$(echo "$tool_info" | jq -r '.session_id // empty')

# Skip if not an edit tool or no file path
if [[ ! "$tool_name" =~ ^(Edit|MultiEdit|Write)$ ]] || [[ -z "$file_path" ]]; then
    exit 0
fi

# Skip markdown files and cache files
if [[ "$file_path" =~ \.(md|markdown)$ ]] || [[ "$file_path" =~ __pycache__ ]]; then
    exit 0
fi

# Create cache directory in project
cache_dir="$CLAUDE_PROJECT_DIR/.claude/cache/${session_id:-default}"
mkdir -p "$cache_dir"

# Function to detect Django app from file path
detect_app() {
    local file="$1"
    local project_root="$CLAUDE_PROJECT_DIR"

    # Remove project root from path
    local relative_path="${file#$project_root/}"

    # Extract first directory component
    local first_dir=$(echo "$relative_path" | cut -d'/' -f1)

    # Django app patterns
    case "$first_dir" in
        # Django apps directory
        apps)
            local app_name=$(echo "$relative_path" | cut -d'/' -f2)
            if [[ -n "$app_name" ]]; then
                echo "apps/$app_name"
            else
                echo "apps"
            fi
            ;;
        # Templates
        templates)
            echo "templates"
            ;;
        # Static assets
        assets|static)
            echo "$first_dir"
            ;;
        # Project config
        tformance)
            echo "tformance"
            ;;
        # Pegasus apps
        pegasus)
            local pegasus_app=$(echo "$relative_path" | cut -d'/' -f3)
            if [[ -n "$pegasus_app" ]]; then
                echo "pegasus/$pegasus_app"
            else
                echo "pegasus"
            fi
            ;;
        # Root files
        *)
            if [[ ! "$relative_path" =~ / ]]; then
                echo "root"
            else
                echo "$first_dir"
            fi
            ;;
    esac
}

# Function to get test command for app
get_test_command() {
    local app="$1"
    local project_root="$CLAUDE_PROJECT_DIR"

    case "$app" in
        apps/*)
            # Django app test
            local app_module="${app//\//.}"
            echo "make test ARGS='$app_module'"
            ;;
        *)
            # Default: run all tests
            echo "make test"
            ;;
    esac
}

# Detect app
app=$(detect_app "$file_path")

# Skip if unknown
if [[ -z "$app" ]]; then
    exit 0
fi

# Log edited file
echo "$(date +%s):$file_path:$app" >> "$cache_dir/edited-files.log"

# Update affected apps list
if ! grep -q "^$app$" "$cache_dir/affected-apps.txt" 2>/dev/null; then
    echo "$app" >> "$cache_dir/affected-apps.txt"
fi

# Store test commands
test_cmd=$(get_test_command "$app")

if [[ -n "$test_cmd" ]]; then
    echo "$app:test:$test_cmd" >> "$cache_dir/commands.txt.tmp"
fi

# Remove duplicates from commands
if [[ -f "$cache_dir/commands.txt.tmp" ]]; then
    sort -u "$cache_dir/commands.txt.tmp" > "$cache_dir/commands.txt"
    rm -f "$cache_dir/commands.txt.tmp"
fi

# Exit cleanly
exit 0
