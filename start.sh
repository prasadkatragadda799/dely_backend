#!/bin/bash
set -e

load_database_url_from_secrets_manager() {
    if [ -z "${DB_SECRET_ID:-}" ]; then
        return 0
    fi

    if ! command -v aws >/dev/null 2>&1; then
        echo "[ERROR] aws CLI is required when DB_SECRET_ID is set."
        exit 1
    fi

    local aws_region secret_string database_url
    aws_region="${AWS_REGION:-${AWS_DEFAULT_REGION:-ap-south-2}}"

    echo "Loading database credentials from Secrets Manager..."
    secret_string="$(aws secretsmanager get-secret-value \
        --secret-id "${DB_SECRET_ID}" \
        --region "${aws_region}" \
        --query SecretString \
        --output text)"

    database_url="$(SECRET_STRING="${secret_string}" python3 - <<'PY'
import json
import os
import sys
import urllib.parse

secret = json.loads(os.environ["SECRET_STRING"])
username = secret.get("username")
password = secret.get("password")
host = os.environ.get("DB_HOST") or secret.get("host")
port = os.environ.get("DB_PORT") or secret.get("port") or "5432"
dbname = os.environ.get("DB_NAME") or secret.get("dbname") or "postgres"
engine = os.environ.get("DB_ENGINE", "postgresql")
params = os.environ.get("DB_QUERY", "sslmode=require")

missing = [name for name, value in {
    "username": username,
    "password": password,
    "host": host,
}.items() if not value]

if missing:
    print(
        f"Secrets Manager secret is missing required keys: {', '.join(missing)}",
        file=sys.stderr,
    )
    sys.exit(1)

encoded_password = urllib.parse.quote(password, safe="")
url = f"{engine}://{username}:{encoded_password}@{host}:{port}/{dbname}"
if params:
    url = f"{url}?{params}"

print(url)
PY
)"

    export DATABASE_URL="${database_url}"
    echo "Loaded DATABASE_URL from Secrets Manager secret ${DB_SECRET_ID}."
}

load_database_url_from_secrets_manager

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
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
else
    echo "Skipping migrations (RUN_MIGRATIONS=false)"
fi

# Create admin user if credentials are provided and no admin exists
# Run with timeout to avoid blocking startup
if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Checking for admin user (with 10s timeout)..."
    timeout 10 python create_admin_from_env.py 2>/dev/null || echo "Admin creation skipped or timed out, continuing..."
fi

echo "Starting application..."

PORT="${PORT:-8000}"
WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
GUNICORN_TIMEOUT="${GUNICORN_TIMEOUT:-120}"
echo "Binding Gunicorn to 0.0.0.0:${PORT} with ${WEB_CONCURRENCY} workers"

exec gunicorn app.main:app \
  --bind "0.0.0.0:${PORT}" \
  --workers "${WEB_CONCURRENCY}" \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout "${GUNICORN_TIMEOUT}" \
  --keep-alive 5

