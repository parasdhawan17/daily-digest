#!/usr/bin/env bash
# Copy env vars from stock-news-bot .env into Vercel (production).
# Run after: npx vercel login && npx vercel link
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_ENV="${STOCK_NEWS_BOT_ENV:-$ROOT/../stock-news-bot/.env}"

if [[ ! -f "$SOURCE_ENV" ]]; then
  echo "Missing $SOURCE_ENV — set STOCK_NEWS_BOT_ENV to your .env path"
  exit 1
fi

# shellcheck disable=SC1090
set -a
source "$SOURCE_ENV"
set +a

if [[ -z "${DIGEST_SIGNING_SECRET:-}" ]]; then
  DIGEST_SIGNING_SECRET="$(openssl rand -hex 32)"
  echo "Generated new DIGEST_SIGNING_SECRET (save for stock-news-bot later)"
fi

if [[ -z "${SITE_URL:-}" ]]; then
  echo "SITE_URL not set — pass after first deploy, e.g.:"
  echo "  SITE_URL=https://daily-digest.vercel.app ./scripts/setup_vercel_env.sh"
fi

cd "$ROOT"

add_env() {
  local name="$1"
  local value="$2"
  if [[ -z "$value" ]]; then
    echo "Skip $name (empty)"
    return
  fi
  printf '%s' "$value" | npx vercel@latest env add "$name" production --force
  echo "Set $name"
}

add_env FINNHUB_API_KEY "${FINNHUB_API_KEY:-}"
add_env DIGEST_SIGNING_SECRET "${DIGEST_SIGNING_SECRET:-}"
add_env BREVO_SUBSCRIBE_FORM_URL "${BREVO_SUBSCRIBE_FORM_URL:-}"
add_env SITE_URL "${SITE_URL:-}"

echo "Done. Redeploy: npx vercel --prod"
