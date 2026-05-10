#!/usr/bin/env bash
# Deploy services/medverse-ai/ to a Hugging Face Space.
#
# Usage:
#   HF_USERNAME=nivakaran HF_SPACE=MedVerse HF_TOKEN=hf_xxx ./scripts/deploy-hf.sh
#
# What it does:
#   1. Clone the HF Space's git remote into a tmp dir (with token auth
#      embedded only in the URL, never written to a config file you'd
#      keep around).
#   2. Mirror services/medverse-ai/ into that working tree (rsync-like
#      cp -r preserving the .pkl model weights handled by Git LFS on HF).
#   3. Commit + push.
#   4. Wipe the tmp dir so the embedded token doesn't linger in
#      .git/config on disk.
#
# Token rotation: don't reuse the same token across sessions. Generate
# a Write-scoped token at https://huggingface.co/settings/tokens, run
# this once, then revoke. The HF Space rebuilds automatically once
# the push completes (~3-5 min for code-only changes).

set -euo pipefail

: "${HF_USERNAME:?HF_USERNAME required (your Hugging Face username)}"
: "${HF_SPACE:?HF_SPACE required (Space repo name, e.g. MedVerse)}"
: "${HF_TOKEN:?HF_TOKEN required (Write-scoped token from https://huggingface.co/settings/tokens)}"

HF_EMAIL="${HF_EMAIL:-info@healplace.com}"
HF_NAME="${HF_NAME:-$HF_USERNAME}"
COMMIT_MSG="${COMMIT_MSG:-Sync services/medverse-ai/ from main repo ($(date -u +%Y-%m-%dT%H:%M:%SZ))}"

REPO_ROOT="$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)"
SRC_DIR="$REPO_ROOT/services/medverse-ai"
TMP_DIR="$(mktemp -d)"

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "[deploy-hf] Cloning huggingface.co/spaces/$HF_USERNAME/$HF_SPACE..."
git clone --quiet \
    "https://${HF_USERNAME}:${HF_TOKEN}@huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE}" \
    "$TMP_DIR"

echo "[deploy-hf] Mirroring $SRC_DIR -> Space..."
# Wipe the Space's existing tracked files except .git so deletes propagate.
find "$TMP_DIR" -mindepth 1 -maxdepth 1 \
    ! -name '.git' \
    ! -name '.gitattributes' \
    -exec rm -rf {} +
cp -r "$SRC_DIR"/. "$TMP_DIR"/

cd "$TMP_DIR"
git config user.email "$HF_EMAIL"
git config user.name "$HF_NAME"
# Track .pkl weights via LFS so HF stores them efficiently.
git lfs install --skip-repo >/dev/null 2>&1 || true
git lfs track "*.pkl" >/dev/null 2>&1 || true

git add .
if git diff --cached --quiet; then
    echo "[deploy-hf] No changes — skipping push."
    exit 0
fi
git commit -m "$COMMIT_MSG" >/dev/null
echo "[deploy-hf] Pushing..."
git push --quiet 2>&1 | sed "s/${HF_TOKEN}/***REDACTED***/g"

echo "[deploy-hf] Done. Watch https://huggingface.co/spaces/${HF_USERNAME}/${HF_SPACE} for the build to flip to Running."
