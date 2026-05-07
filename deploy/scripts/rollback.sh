#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/qr-registros}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"

cd "$APP_DIR"

echo "Stopping current stack..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down

echo "Starting previous containers if available..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

echo "Rollback completed. Verify /health and logs before re-opening traffic."
