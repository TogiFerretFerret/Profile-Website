#!/usr/bin/env bash
# build + deploy all three sites as Cloudflare Workers (static assets), then verify every page is really live.
# needs: CLOUDFLARE_ACCOUNT_ID, and either CLOUDFLARE_API_TOKEN or CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY (global key) in env.
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules/katex ] || npm install --no-audit --no-fund   # KaTeX renders blog math at build time
python3 build.py --prod

deploy() {
  npx -y wrangler@latest deploy --assets "dist/$1" --name "riverxia-$1" --compatibility-date 2026-10-01
}

host() { case "$1" in www) echo riverxia.sh;; *) echo "$1.riverxia.sh";; esac; }

# every page we built must answer 200 (after redirects). a partial asset upload once left every .html 404 for minutes.
verify() {
  local site="$1" bad=0 f slug code
  for f in dist/"$site"/*.html; do
    slug="$(basename "$f" .html)"
    [ "$slug" = index ] && url="https://$(host "$site")/" || url="https://$(host "$site")/$slug"
    [ "$slug" = 404 ] && continue
    code="$(curl -sL -m 15 -o /dev/null -w '%{http_code}' "$url" || true)"
    if [ "$code" != 200 ]; then echo "  MISSING ($code): $url" >&2; bad=1; fi
  done
  return $bad
}

for s in www blog projects; do
  deploy "$s"
  ok=0
  for attempt in 1 2 3; do
    sleep 4
    if verify "$s"; then ok=1; break; fi
    echo "verify failed for $s (attempt $attempt), re-uploading..." >&2
    deploy "$s"
  done
  [ "$ok" = 1 ] || { echo "DEPLOY FAILED: $s still has missing pages" >&2; exit 1; }
  echo "verified: $s"
done
