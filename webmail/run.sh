#!/usr/bin/env bash
# (re)create the Roundcube container on the VPS. Run on the VPS from the directory holding custom.inc.php + geostyle/.
# Behind bifrost-caddy (mail.riverxia.sh -> 127.0.0.1:8110). IMAP/SMTP go to the host's Dovecot/Postfix over TLS.
set -euo pipefail
cd "$(dirname "$0")"
docker volume create roundcube_db >/dev/null
docker rm -f roundcube >/dev/null 2>&1 || true
docker run -d --name roundcube --restart unless-stopped -p 127.0.0.1:8110:80 \
  -v roundcube_db:/var/roundcube/db \
  -v "$PWD/custom.inc.php:/var/roundcube/config/custom.inc.php:ro" \
  -v "$PWD/geostyle:/var/www/html/plugins/geostyle:ro" \
  -e ROUNDCUBEMAIL_DB_TYPE=sqlite \
  -e ROUNDCUBEMAIL_DEFAULT_HOST=ssl://mail.riverxia.sh -e ROUNDCUBEMAIL_DEFAULT_PORT=993 \
  -e ROUNDCUBEMAIL_SMTP_SERVER=ssl://mail.riverxia.sh -e ROUNDCUBEMAIL_SMTP_PORT=465 \
  -e ROUNDCUBEMAIL_PLUGINS=archive,zipdownload,markasjunk,geostyle \
  -e ROUNDCUBEMAIL_SKIN=elastic \
  roundcube/roundcubemail:latest-apache
