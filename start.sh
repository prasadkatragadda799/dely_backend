#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head || echo "Migration failed, continuing..."

echo "Starting application..."
exec gunicorn app.main:app --bind 0.0.0.0:$PORT --workers 4 --worker-class uvicorn.workers.UvicornWorker

