#!/bin/sh
set -eu
if [ "${RENEWED_LINEAGE:-}" = /etc/letsencrypt/live/dungeoncrawl.ru ]; then
    nginx -t
    systemctl reload nginx
fi
