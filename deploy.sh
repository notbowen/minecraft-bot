#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-beesnuts}"
REMOTE_DIR="${REMOTE_DIR:-/home/bowen/minecraft-bot}"

if command -v rsync >/dev/null 2>&1 && ssh "${REMOTE}" 'command -v rsync >/dev/null 2>&1'; then
  rsync -az --delete \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '.env' \
    --exclude '.pytest_cache' \
    --exclude '*.egg-info' \
    --exclude '__pycache__' \
    --exclude '*/__pycache__' \
    --exclude 'data' \
    ./ "${REMOTE}:${REMOTE_DIR}/"
else
  ssh "${REMOTE}" "mkdir -p '${REMOTE_DIR}' && find '${REMOTE_DIR}' -mindepth 1 -maxdepth 1 ! -name '.env' ! -name 'data' -exec rm -rf {} +"
  tar \
    --exclude './.git' \
    --exclude './.venv' \
    --exclude './.env' \
    --exclude './.pytest_cache' \
    --exclude './*.egg-info' \
    --exclude './__pycache__' \
    --exclude './*/__pycache__' \
    --exclude './data' \
    -czf - . | ssh "${REMOTE}" "tar -xzf - -C '${REMOTE_DIR}'"
fi

ssh "${REMOTE}" "cd '${REMOTE_DIR}' && bash scripts/remote-deploy.sh"
