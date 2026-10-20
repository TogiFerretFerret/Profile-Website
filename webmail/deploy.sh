#!/usr/bin/env bash
# push webmail/ to the VPS and (re)create the Roundcube container.
# usage: webmail/deploy.sh user@host   (needs ssh + rsync + docker on the host)
set -euo pipefail
HOST="${1:?usage: webmail/deploy.sh user@host}"
cd "$(dirname "$0")"
rsync -a --delete --exclude deploy.sh ./ "$HOST:/opt/roundcube/"
ssh "$HOST" 'bash /opt/roundcube/run.sh >/dev/null'
for i in $(seq 1 20); do
  code=$(ssh "$HOST" 'curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8110/' || true)
  [ "$code" = 200 ] && { echo "roundcube up"; exit 0; }
  sleep 2
done
echo "roundcube did not come up" >&2; exit 1
