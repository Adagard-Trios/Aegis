#!/bin/sh
# MedVerse container entrypoint.
#
# Render mounts the persistent disk as root:root, so the non-root
# `medverse` user can't write Chroma / uploads / SQLite without help.
# This script runs as root, prepares + chowns every storage path the
# app expects, then drops privileges via gosu and execs the app.
#
# Idempotent: chown is fine to re-run on every boot.

set -e

PATHS=""

# SQLITE path is a file — chown its parent dir.
if [ -n "$MEDVERSE_SQLITE_PATH" ]; then
    PATHS="$PATHS $(dirname "$MEDVERSE_SQLITE_PATH")"
fi

# Directory env vars — append directly.
for VAR in MEDVERSE_UPLOADS_DIR CHROMA_PERSIST_DIR MEDVERSE_MODELS_DIR; do
    eval "VAL=\$$VAR"
    if [ -n "$VAL" ]; then
        PATHS="$PATHS $VAL"
    fi
done

for P in $PATHS; do
    mkdir -p "$P" 2>/dev/null || true
    chown -R medverse:medverse "$P" 2>/dev/null || true
done

# Run migrations + start the app as the unprivileged user.
exec gosu medverse sh -c "alembic upgrade head && exec python app.py"
