#!/usr/bin/env bash
# MedVerse one-command demo bring-up.
#
# Starts the FastAPI backend (port 8000) and the Next.js frontend (port 3000)
# in parallel. Ctrl+C tears both down.
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Kill all child processes on exit (Ctrl+C, error, normal exit).
trap 'jobs -p | xargs -r kill 2>/dev/null; exit' INT TERM EXIT

echo "[medverse] backend  → http://localhost:8000  (uvicorn via app.py)"
echo "[medverse] frontend → http://localhost:3000  (next dev)"
echo

( cd "$ROOT" && python app.py ) &
BACKEND_PID=$!

( cd "$ROOT/frontend" && npm run dev ) &
FRONTEND_PID=$!

wait $BACKEND_PID $FRONTEND_PID
