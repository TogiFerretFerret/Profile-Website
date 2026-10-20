#!/usr/bin/env bash
# deploy one built site (dist/<site>) as a Cloudflare Worker with static assets, then verify every page is live.
# usage: scripts/deploy-site.sh www|blog|projects        (called by the Makefile)
set -euo pipefail
cd "$(dirname "$0")/.."
site="${1:?usage: deploy-site.sh www|blog|projects [verify]}"
mode="${2:-deploy}"   # "verify" only checks the live pages, no upload
case "$site" in www) host=riverxia.sh ;; blog|projects) host="$site.riverxia.sh" ;; *) echo "unknown site: $site" >&2; exit 2 ;; esac

deploy() {
  npx -y wrangler@latest deploy --assets "dist/$site" --name "riverxia-$site" --compatibility-date 2026-10-01
}

# every page we built must answer 200 (after redirects). a partial asset upload once left every .html 404 for minutes.
verify() {
  local bad=0 f slug url code
  for f in dist/"$site"/*.html; do
    slug="$(basename "$f" .html)"
    [ "$slug" = 404 ] && continue
    if [ "$slug" = index ]; then url="https://$host/"; else url="https://$host/$slug"; fi
    code="$(curl -sL -m 15 -o /dev/null -w '%{http_code}' "$url" || true)"
    if [ "$code" != 200 ]; then echo "  MISSING ($code): $url" >&2; bad=1; fi
  done
  return $bad
}

if [ "$mode" = verify ]; then
  if verify; then echo "verified: $site"; exit 0; fi
  echo "VERIFY FAILED: $site" >&2; exit 1
fi

deploy
for attempt in 1 2 3; do
  sleep 4
  if verify; then echo "verified: $site"; exit 0; fi
  echo "verify failed for $site (attempt $attempt), re-uploading..." >&2
  deploy
done
echo "DEPLOY FAILED: $site still has missing pages" >&2
exit 1
