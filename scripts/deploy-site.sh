#!/usr/bin/env bash
# deploy one built site (dist/<site>) as a Cloudflare Worker with static assets, then verify every page is live.
# usage: scripts/deploy-site.sh www|blog|projects|uses  (called by the Makefile)
set -euo pipefail
cd "$(dirname "$0")/.."
site="${1:?usage: deploy-site.sh www|blog|projects|uses [verify]}"
mode="${2:-deploy}"   # "verify" only checks the live pages, no upload
case "$site" in www) host=riverxia.sh ;; blog|projects|uses) host="$site.riverxia.sh" ;; *) echo "unknown site: $site" >&2; exit 2 ;; esac

deploy() {
  # one wrangler config per site (generated: dist/ is rebuilt on every build). www also runs worker/www.js on "/" for the wget/curl trick.
  local main="" rwf=""
  if [ "$site" = www ]; then main='"main": "../worker/www.js",'; rwf='"binding": "ASSETS", "run_worker_first": ["/"],'; fi
  cat > "dist/$site.wrangler.jsonc" <<EOF
{ "name": "riverxia-$site", "compatibility_date": "2026-10-01", $main
  "assets": { "directory": "./$site", $rwf "not_found_handling": "404-page" } }
EOF
  npx -y wrangler@latest deploy --config "dist/$site.wrangler.jsonc"
  ensure_domain
}

# attach $host to the worker as a custom domain (creates the dns record + cert). no-op when it is already attached.
ensure_domain() {
  local api=https://api.cloudflare.com/client/v4 auth zone have
  if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then auth=(-H "Authorization: Bearer $CLOUDFLARE_API_TOKEN")
  else auth=(-H "X-Auth-Email: $CLOUDFLARE_EMAIL" -H "X-Auth-Key: $CLOUDFLARE_API_KEY"); fi
  have="$(curl -fsS "${auth[@]}" "$api/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/domains?hostname=$host" | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["result"]))')"
  [ "$have" != 0 ] && return 0
  zone="$(curl -fsS "${auth[@]}" "$api/zones?name=riverxia.sh" | python3 -c 'import sys,json;print(json.load(sys.stdin)["result"][0]["id"])')"
  echo "attaching $host to riverxia-$site"
  curl -fsS -X PUT "${auth[@]}" -H 'Content-Type: application/json' "$api/accounts/$CLOUDFLARE_ACCOUNT_ID/workers/domains" \
    --data "{\"hostname\":\"$host\",\"service\":\"riverxia-$site\",\"zone_id\":\"$zone\",\"environment\":\"production\"}" >/dev/null
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
