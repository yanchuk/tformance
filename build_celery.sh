#!/usr/bin/env bash
# Build script for Render Celery worker
# This runs during the build phase for the worker service
#
# Note: Migrations are NOT run here (only in web service build.sh)

set -o errexit  # Exit on error

echo "=== Running build_celery.sh ==="
echo "Celery worker build complete (no additional steps needed)"
echo "=== Build complete ==="
