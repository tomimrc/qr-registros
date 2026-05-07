#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/qr-registros}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

cd "$APP_DIR"
mkdir -p "$BACKUP_DIR"

if [ -f "$ENV_FILE" ]; then
  echo "Using $ENV_FILE"
else
  echo "Missing $ENV_FILE"
  exit 1
fi

echo "Building and starting containers..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

echo "Initializing database schema..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm app python init_db.py

echo "Waiting for app health..."
for _ in $(seq 1 30); do
  if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T app python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" >/dev/null 2>&1; then
    echo "Health check passed"
    exit 0
  fi
  sleep 2
done

echo "Health check failed, rolling back to previous image state is manual"
exit 1
