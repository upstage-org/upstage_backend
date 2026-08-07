#!/bin/sh
#
# Daily PostgreSQL + asset backup for UpStage.
#
# Runs as a long-lived sidecar beside the postgres service: one dump per day at
# BACKUP_AT_HOUR, verified before it is kept, with dumps older than
# BACKUP_KEEP_DAYS deleted. Only started when COMPOSE_PROFILES=backup, which
# run_docker_compose_prod.sh sets (dev starts no backup container).
#
# The uploads tree (assets) is copied straight into ASSETS_DIR in the same run:
# a plain overwriting copy, no dated archives and no rotation. The tree is
# multiple GB and mostly append-only, so one dump per day of it would fill the
# disk; nothing is ever deleted from the copy either, so a file removed from
# uploads survives here.
#
# Connection comes from the standard PG* variables set in the compose file.
#
set -eu

BACKUP_DIR=${BACKUP_DIR:-/backups}
BACKUP_KEEP_DAYS=${BACKUP_KEEP_DAYS:-14}
BACKUP_AT_HOUR=${BACKUP_AT_HOUR:-3}
SITE=${SITE:-prod}

# Both are mounts from the compose file: the source read-only, the destination
# writable. If the source is not mounted the asset step is skipped entirely.
ASSETS_SRC=${ASSETS_SRC:-/assets_src}
ASSETS_DIR=${ASSETS_DIR:-/assets_backup}

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

copy_assets() {
    if [ ! -d "$ASSETS_SRC" ]; then
        log "no assets mounted at ${ASSETS_SRC} - skipping"
        return
    fi

    # "$ASSETS_SRC/." copies the *contents* of uploads; without the trailing
    # dot the first run would fill ASSETS_DIR and every later one would nest
    # another copy inside it.
    if cp -rf "$ASSETS_SRC/." "$ASSETS_DIR/"; then
        size=$(du -sh "$ASSETS_DIR" | cut -f1)
        log "OK assets ${ASSETS_DIR} (${size})"
        echo "$(date '+%Y-%m-%d %H:%M:%S %Z') OK assets ${ASSETS_DIR} ${size}" \
            >> "${BACKUP_DIR}/status.txt"
    else
        log "FAILED to copy assets from ${ASSETS_SRC}"
        echo "$(date '+%Y-%m-%d %H:%M:%S %Z') FAIL assets ${ASSETS_SRC}" \
            >> "${BACKUP_DIR}/status.txt"
    fi
}

# status.txt holds one line per part: take_backup truncates it, copy_assets
# appends, so both results are always from the same run.
run_backup() {
    take_backup
    copy_assets
}

# Back up immediately unless today already has one, so that starting the
# container proves itself now instead of appearing to work until BACKUP_AT_HOUR.
if [ -z "$(find "$BACKUP_DIR" -maxdepth 1 -name "${PREFIX}$(date +%Y%m%d)_*.sql.gz" 2>/dev/null)" ]; then
    log "no backup yet today - taking one now"
    run_backup
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
    run_backup
done
