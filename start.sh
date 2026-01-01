#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head || echo "Migration failed, continuing..."

# Create admin user if credentials are provided and no admin exists
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Checking for admin user..."
    python create_admin_from_env.py || echo "Admin creation skipped or failed, continuing..."
fi

echo "Starting application..."
exec gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker

