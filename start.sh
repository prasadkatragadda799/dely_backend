#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head || echo "Migration failed, continuing..."

# Create admin user if credentials are provided and no admin exists
# Run with timeout to avoid blocking startup
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Checking for admin user (with 10s timeout)..."
    timeout 10 python create_admin_from_env.py 2>/dev/null || echo "Admin creation skipped or timed out, continuing..."
fi

echo "Starting application..."
exec gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 2 --worker-class uvicorn.workers.UvicornWorker --timeout 120 --keep-alive 5

