#!/usr/bin/env bash
# deploy one built site (dist/<site>) as a Cloudflare Worker with static assets, then verify every page is live.
# usage: scripts/deploy-site.sh www|blog|projects|uses|dots|paste|guestbook  (called by the Makefile)
set -euo pipefail
cd "$(dirname "$0")/.."
site="${1:?usage: deploy-site.sh www|blog|projects|uses|dots|paste|guestbook [verify]}"
mode="${2:-deploy}"   # "verify" only checks the live pages, no upload
case "$site" in www) host=riverxia.sh ;; blog|projects|uses|dots|paste|guestbook) host="$site.riverxia.sh" ;; *) echo "unknown site: $site" >&2; exit 2 ;; esac

deploy() {
  # one wrangler config per site (generated: dist/ is rebuilt on every build).
  #   www/dots: worker/front.js on "/" serves the bash script to curl/wget (env.SCRIPT)
  #   paste:    worker/paste.js on a SQLite Durable Object
  #   guestbook: worker/guestbook.js on a SQLite Durable Object
  python3 - "$site" > "dist/$site.wrangler.jsonc" <<'PY'
import json, sys
site = sys.argv[1]
cfg = {"name": f"riverxia-{site}", "compatibility_date": "2026-10-01", "assets": {"directory": f"./{site}", "not_found_handling": "404-page"}}
if site in ("www", "dots"):
    cfg.update(main="../worker/front.js", vars={"SCRIPT": "/riverxia.sh" if site == "www" else "/dots.sh"})
    cfg["assets"].update(binding="ASSETS", run_worker_first=["/"])
elif site == "paste":
    cfg.update(main="../worker/paste.js", durable_objects={"bindings": [{"name": "PASTES", "class_name": "PasteStore"}]}, migrations=[{"tag": "v1", "new_sqlite_classes": ["PasteStore"]}])
    cfg["assets"].update(binding="ASSETS", run_worker_first=True)
elif site == "guestbook":
    cfg.update(main="../worker/guestbook.js", durable_objects={"bindings": [{"name": "GB", "class_name": "Guestbook"}]}, migrations=[{"tag": "v1", "new_sqlite_classes": ["Guestbook"]}])
    cfg["assets"].update(binding="ASSETS", run_worker_first=True)
print(json.dumps(cfg, indent=1))
PY
  npx -y wrangler@latest deploy --config "dist/$site.wrangler.jsonc"
  ensure_domain
}

cf_auth() {
  if [ -n "${CLOUDFLARE_API_TOKEN:-}" ]; then printf '%s\n' -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
  else printf '%s\n' -H "X-Auth-Email: $CLOUDFLARE_EMAIL" -H "X-Auth-Key: $CLOUDFLARE_API_KEY"; fi
}


# attach $host to the worker as a custom domain (creates the dns record + cert). no-op when it is already attached.
ensure_domain() {
  local api=https://api.cloudflare.com/client/v4 auth zone have
  mapfile -t auth < <(cf_auth)
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
