#!/usr/bin/env bash
# Push cron env vars to Railway from local .env files.
# Prereqs: npx @railway/cli login && railway link (select daily-digest service)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BOT_ENV="$ROOT/../stock-news-bot/.env"
LOCAL_ENV="$ROOT/.env.local"

if ! command -v railway >/dev/null 2>&1; then
  RAILWAY="npx --yes @railway/cli@latest"
else
  RAILWAY="railway"
fi

load_env() {
  local file="$1"
  [[ -f "$file" ]] || return 0
  set -a
  # shellcheck disable=SC1090
  source "$file"
  set +a
}

load_env "$BOT_ENV"
load_env "$LOCAL_ENV"

: "${FINNHUB_API_KEY:?Missing FINNHUB_API_KEY}"
: "${BREVO_API_KEY:?Missing BREVO_API_KEY}"
: "${BREVO_LIST_ID:?Missing BREVO_LIST_ID}"
: "${EMAIL_FROM:?Missing EMAIL_FROM (set in stock-news-bot/.env)}"
: "${DIGEST_SIGNING_SECRET:?Missing DIGEST_SIGNING_SECRET}"
: "${SITE_URL:?Missing SITE_URL}"

EMAIL_FROM_NAME="${EMAIL_FROM_NAME:-Tickr Digest}"
TZ="${TZ:-America/New_York}"

echo "Setting Railway variables (service must be linked)..."

set_var() {
  local key="$1"
  local value="$2"
  echo "  $key"
  printf '%s' "$value" | $RAILWAY variable set "$key" --stdin --skip-deploys
}

set_var FINNHUB_API_KEY "$FINNHUB_API_KEY"
set_var BREVO_API_KEY "$BREVO_API_KEY"
set_var BREVO_LIST_ID "$BREVO_LIST_ID"
set_var BREVO_TICKERS_ATTRIBUTE "${BREVO_TICKERS_ATTRIBUTE:-US_TICKERS}"
set_var EMAIL_FROM "$EMAIL_FROM"
set_var EMAIL_FROM_NAME "$EMAIL_FROM_NAME"
set_var DIGEST_SIGNING_SECRET "$DIGEST_SIGNING_SECRET"
set_var SITE_URL "$SITE_URL"
set_var TZ "$TZ"

echo "Done. Redeploy the service in Railway to pick up variables."
