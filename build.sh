#!/usr/bin/env bash
# Build script for Render deployment
# This runs during the build phase for the web service
#
# Reference: https://docs.render.com/deploy-django

set -o errexit  # Exit on error

echo "=== Running build.sh ==="

# Run database migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create cache table (if using database cache)
echo "Creating cache table..."
python manage.py createcachetable --dry-run || python manage.py createcachetable

# Compile translation messages (if using i18n)
if [ -d "locale" ]; then
    echo "Compiling messages..."
    python manage.py compilemessages || true
fi

# Bootstrap Stripe subscriptions (if using Stripe)
# Uncomment if you have Stripe products set up
# echo "Syncing Stripe..."
# python manage.py djstripe_sync_models Product Price

echo "=== Build complete ==="
