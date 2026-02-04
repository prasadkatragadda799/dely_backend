#!/bin/bash
set -e

echo "Running database migrations..."
# Retry migrations up to 3 times with 5 second delays
for i in {1..3}; do
    echo "Migration attempt $i of 3..."
    if alembic upgrade head; then
        echo "Migrations completed successfully!"
        break
    else
        if [ $i -eq 3 ]; then
            echo "[ERROR] Migrations failed after 3 attempts!"
            echo "[ERROR] Please check database connection and migration files."
            exit 1
        fi
        echo "Migration failed, retrying in 5 seconds..."
        sleep 5
    fi
done

# Create admin user if credentials are provided and no admin exists
# Run with timeout to avoid blocking startup
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Checking for admin user (with 10s timeout)..."
    timeout 10 python create_admin_from_env.py 2>/dev/null || echo "Admin creation skipped or timed out, continuing..."
fi

echo "Starting application..."

# Render (and most PaaS) expose the app on a single port.
# Default to 10000 if PORT is not explicitly set so the container
# always binds to a known port for health checks/port scanning.
PORT="${PORT:-10000}"
echo "Binding Gunicorn to 0.0.0.0:${PORT}"

exec gunicorn app.main:app \
  --bind "0.0.0.0:${PORT}" \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --keep-alive 5

