#!/bin/sh
# Run from the directory containing these files, as root, after bootstrap.sh.
set -eu
test "$(id -u)" = 0
test -f /srv/dcss-ru/.managed-by-dcss-ru
test -d /etc/nginx/sites-available
test -f /etc/letsencrypt/options-ssl-nginx.conf
test -f /etc/letsencrypt/ssl-dhparams.pem

site=/etc/nginx/sites-available/dungeoncrawl.ru
enabled=/etc/nginx/sites-enabled/dungeoncrawl.ru
if [ -e "$enabled" ] || [ -L "$enabled" ]; then
    test "$(readlink -f "$enabled")" = "$site"
fi

install -d -m 755 /var/www/dungeoncrawl.ru/acme
install -m 644 nginx-https.conf /srv/dcss-ru/nginx-https.conf
install -m 755 enable-https.py /srv/dcss-ru/bin/enable-https.py
install -m 644 dcss-ru-https.service /etc/systemd/system/dcss-ru-https.service
install -m 644 dcss-ru-https.timer /etc/systemd/system/dcss-ru-https.timer
install -m 755 renew-nginx.sh /etc/letsencrypt/renewal-hooks/deploy/dcss-ru-nginx

# Re-running installation preserves an already enabled HTTPS site.
if [ ! -e "$site" ]; then
    install -m 644 nginx-http.conf "$site"
fi
if [ ! -e "$enabled" ]; then
    ln -s "$site" "$enabled"
fi
nginx -t
systemctl reload nginx
systemctl daemon-reload
systemctl enable --now dcss-ru-https.timer
systemctl start dcss-ru-https.service
