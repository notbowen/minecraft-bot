#!/usr/bin/env bash
set -euo pipefail

mkdir -p data

if [[ ! -f .env ]]; then
  cp .env.example .env
fi

ensure_env_key() {
  local key="$1"
  local value="${2:-}"
  if ! grep -Eq "^${key}=" .env; then
    printf '%s=%s\n' "${key}" "${value}" >> .env
  fi
}

ensure_env_key ROLE_ID

if ! grep -Eq '^MC_RCON_PASSWORD=.+$' .env; then
  password="$(
    awk -F= 'tolower($1) == "password" { print $2 }' \
      /home/bowen/services/minecraft/data/.rcon-cli.env 2>/dev/null || true
  )"
  if [[ -n "${password}" ]]; then
    tmp="$(mktemp)"
    awk -v password="${password}" '
      BEGIN { written = 0 }
      /^MC_RCON_PASSWORD=/ {
        print "MC_RCON_PASSWORD=" password
        written = 1
        next
      }
      { print }
      END {
        if (!written) {
          print "MC_RCON_PASSWORD=" password
        }
      }
    ' .env > "${tmp}"
    mv "${tmp}" .env
  fi
fi

docker compose build

if grep -Eq '^DISCORD_TOKEN=.+$' .env; then
  docker compose up -d
else
  echo "DISCORD_TOKEN is not set in ${PWD}/.env; built image but did not start the bot."
fi
