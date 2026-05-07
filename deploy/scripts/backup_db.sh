#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/qr-registros}"
BACKUP_DIR="${BACKUP_DIR:-$APP_DIR/backups}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-qr_registros_db}"
POSTGRES_DB="${POSTGRES_DB:-attendance_db}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/${POSTGRES_DB}_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

echo "Creating database backup at $BACKUP_FILE"
docker exec -t "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_FILE"

echo "Backup saved to $BACKUP_FILE"
