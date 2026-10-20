#!/usr/bin/env bash
# build + deploy all three sites as Cloudflare Workers (static assets).
# needs: CLOUDFLARE_ACCOUNT_ID, and either CLOUDFLARE_API_TOKEN or CLOUDFLARE_EMAIL + CLOUDFLARE_API_KEY (global key) in env.
set -euo pipefail
cd "$(dirname "$0")"
[ -d node_modules/katex ] || npm install --no-audit --no-fund   # KaTeX renders blog math at build time
python3 build.py --prod
for s in www blog projects; do
  npx -y wrangler@latest deploy --assets "dist/$s" --name "riverxia-$s" --compatibility-date 2026-10-01
done
