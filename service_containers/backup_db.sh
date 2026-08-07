#!/bin/sh
#
# Daily PostgreSQL backup for UpStage.
#
# Runs as a long-lived sidecar beside the postgres service: one dump per day at
# BACKUP_AT_HOUR, verified before it is kept, with dumps older than
# BACKUP_KEEP_DAYS deleted. Only started when COMPOSE_PROFILES=backup, which
# run_docker_compose_prod.sh sets (dev starts no backup container).
#
# Connection comes from the standard PG* variables set in the compose file.
#
set -eu

BACKUP_DIR=${BACKUP_DIR:-/backups}
BACKUP_KEEP_DAYS=${BACKUP_KEEP_DAYS:-14}
BACKUP_AT_HOUR=${BACKUP_AT_HOUR:-3}
SITE=${SITE:-prod}

PREFIX="upstage_${SITE}_"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*"
}

take_backup() {
    stamp=$(date +%Y%m%d_%H%M%S)
    out="${BACKUP_DIR}/${PREFIX}${stamp}.sql.gz"

    # pg_dump compresses the file itself rather than "pg_dump | gzip": /bin/sh
    # has no pipefail, so a failing dump in a pipeline would leave a truncated
    # archive behind a zero exit status.
    if pg_dump --compress=gzip:6 -f "${out}.part" && gzip -t "${out}.part"; then
        mv "${out}.part" "$out"
        size=$(du -h "$out" | cut -f1)
        log "OK ${out} (${size})"
        echo "$(date '+%Y-%m-%d %H:%M:%S %Z') OK ${out} ${size}" > "${BACKUP_DIR}/status.txt"

        # Scoped to this site's own filenames, so anything else living in the
        # backup directory is never touched.
        find "$BACKUP_DIR" -maxdepth 1 -name "${PREFIX}*.sql.gz" \
            -mtime "+${BACKUP_KEEP_DAYS}" -delete
    else
        rm -f "${out}.part"
        log "FAILED to back up ${PGDATABASE:-?} at ${stamp}"
        echo "$(date '+%Y-%m-%d %H:%M:%S %Z') FAIL ${PGDATABASE:-?}" > "${BACKUP_DIR}/status.txt"
    fi
}

# Back up immediately unless today already has one, so that starting the
# container proves itself now instead of appearing to work until BACKUP_AT_HOUR.
if [ -z "$(find "$BACKUP_DIR" -maxdepth 1 -name "${PREFIX}$(date +%Y%m%d)_*.sql.gz" 2>/dev/null)" ]; then
    log "no backup yet today - taking one now"
    take_backup
else
    log "today already has a backup - waiting for the next scheduled run"
fi

while true; do
    now=$(date +%s)
    next=$(date -d "today ${BACKUP_AT_HOUR}:00:00" +%s)
    if [ "$next" -le "$now" ]; then
        next=$(date -d "tomorrow ${BACKUP_AT_HOUR}:00:00" +%s)
    fi
    log "next backup at $(date -d "@${next}" '+%Y-%m-%d %H:%M:%S %Z')"
    sleep $((next - now))
    take_backup
done
