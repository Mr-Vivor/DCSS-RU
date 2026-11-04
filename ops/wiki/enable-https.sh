#!/bin/sh
set -eu
exec 9>/run/lock/dcss-wiki-https.lock
flock -n 9 || exit 0
domain=wiki.dungeoncrawl.ru
if ! dig +short @1.1.1.1 "$domain" A | grep -qx '193.104.33.59'; then
    echo 'Wiki DNS is not ready yet; the timer will retry.'
    exit 0
fi
certbot certonly --webroot -w /var/www/wiki.dungeoncrawl.ru/acme \
    --cert-name "$domain" -d "$domain" --non-interactive --agree-tos \
    --register-unsafely-without-email --keep-until-expiring \
    --deploy-hook 'nginx -t && systemctl reload nginx'
install -m 0644 /etc/dcss-wiki/nginx-https.conf /etc/nginx/sites-available/wiki.dungeoncrawl.ru
nginx -t
systemctl reload nginx
systemctl disable --now dcss-wiki-https.timer
echo 'Wiki HTTPS is enabled.'
