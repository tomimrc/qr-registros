#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: restore_db.sh /path/to/backup.sql"
  exit 1
fi

BACKUP_FILE="$1"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-qr_registros_db}"
POSTGRES_DB="${POSTGRES_DB:-attendance_db}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

echo "Restoring database from $BACKUP_FILE"
cat "$BACKUP_FILE" | docker exec -i "$POSTGRES_CONTAINER" psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "Restore completed"
