#!/bin/bash
# ==============================================================================
# GIAMS — Backup PostgreSQL Database
# Uso: bash backup_db.sh
# Crea un dump compresso in backend/backups/ con timestamp.
# Mantiene gli ultimi 30 backup, elimina i piu' vecchi.
# ==============================================================================

set -euo pipefail

# Configurazione
DB_NAME="${GIAMS_DB_NAME:-giams_db}"
DB_USER="${GIAMS_DB_USER:-giams_user}"
DB_HOST="${GIAMS_DB_HOST:-localhost}"
DB_PORT="${GIAMS_DB_PORT:-5432}"
KEEP_LAST=30

# Directory backup
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/../backups"
mkdir -p "$BACKUP_DIR"

# Timestamp e nome file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="giams_backup_${TIMESTAMP}.sql.gz"
FILEPATH="$BACKUP_DIR/$FILENAME"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Avvio backup database $DB_NAME..."

# Esegui pg_dump
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --no-owner --no-privileges --format=plain \
  | gzip > "$FILEPATH"

SIZE=$(du -h "$FILEPATH" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup completato: $FILENAME ($SIZE)"

# Pulizia vecchi backup (mantieni solo ultimi N)
cd "$BACKUP_DIR"
NUM_FILES=$(ls -1 giams_backup_*.sql.gz 2>/dev/null | wc -l)
if [ "$NUM_FILES" -gt "$KEEP_LAST" ]; then
  REMOVE=$((NUM_FILES - KEEP_LAST))
  ls -1t giams_backup_*.sql.gz | tail -n "$REMOVE" | while read OLD; do
    echo "  Rimosso backup vecchio: $OLD"
    rm -f "$OLD"
  done
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup disponibili: $(ls -1 giams_backup_*.sql.gz 2>/dev/null | wc -l)/$KEEP_LAST"
echo "Percorso: $FILEPATH"
