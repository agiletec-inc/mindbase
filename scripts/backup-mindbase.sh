#!/usr/bin/env bash
# Multi-tier backup of the canonical MindBase postgres (the conversation store).
#
#   Tier 1 — Docker named volume (mindbase_postgres_data_dev): automatic, survives
#            container restarts. Nothing to do here.
#   Tier 2 — pg_dump custom-format archive on the Mac, generation-retained.
#   Tier 3 — upload to an rclone remote (Cloudflare R2).
#
# Runs host-native on the Mac. Secrets are NOT in this script or in env: the R2
# credentials live in rclone's own config (set up once via `rclone config`), and
# we only reference the remote by name.
#
# Config (env, all optional except the cloud tier needs BACKUP_REMOTE):
#   PG_CONTAINER   default mindbase-postgres-canon
#   PG_USER        default mindbase
#   PG_DB          default mindbase_dev
#   BACKUP_DIR     default ~/mindbase-backups
#   KEEP           default 7   (generations kept locally and remotely)
#   BACKUP_REMOTE  e.g. "r2:mindbase-backups"  (unset => Tier 3 skipped, loudly)
set -euo pipefail

PG_CONTAINER="${PG_CONTAINER:-mindbase-postgres-canon}"
PG_USER="${PG_USER:-mindbase}"
PG_DB="${PG_DB:-mindbase_dev}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/mindbase-backups}"
KEEP="${KEEP:-7}"
BACKUP_REMOTE="${BACKUP_REMOTE:-}"

ts="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
out="$BACKUP_DIR/${PG_DB}_${ts}.dump"

# --- Tier 2: local pg_dump (custom format = compressed, pg_restore-able) ---
echo "[backup] pg_dump ${PG_DB} -> ${out}"
docker exec "$PG_CONTAINER" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc > "$out"

# Validate the archive is real and restorable before trusting it (read its TOC).
test -s "$out"
docker exec -i "$PG_CONTAINER" pg_restore -l < "$out" >/dev/null
echo "[backup] local dump OK ($(du -h "$out" | cut -f1))"

# Prune old local generations (keep newest $KEEP).
ls -1t "$BACKUP_DIR"/${PG_DB}_*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | while read -r old; do
  echo "[backup] prune local ${old}"
  rm -f "$old"
done

# --- Tier 3: cloud (Cloudflare R2 via rclone) ---
if [ -z "$BACKUP_REMOTE" ]; then
  echo "[backup] WARNING: BACKUP_REMOTE unset — R2 tier SKIPPED. Configure an R2" >&2
  echo "[backup]          remote (rclone config) and set BACKUP_REMOTE=r2:<bucket>." >&2
  exit 0
fi

echo "[backup] rclone copy -> ${BACKUP_REMOTE}/"
rclone copy "$out" "${BACKUP_REMOTE}/" --no-traverse

# Prune old remote generations (keep newest $KEEP).
rclone lsf "${BACKUP_REMOTE}/" --include "${PG_DB}_*.dump" 2>/dev/null | sort -r | tail -n +"$((KEEP + 1))" | while read -r rf; do
  echo "[backup] prune remote ${rf}"
  rclone deletefile "${BACKUP_REMOTE}/${rf}"
done

echo "[backup] done — local: ${out}, remote: ${BACKUP_REMOTE}/$(basename "$out")"
