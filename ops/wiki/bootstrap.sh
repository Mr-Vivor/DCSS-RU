#!/bin/sh
# Run as root on the existing Ubuntu VPS, from the uploaded ops/wiki directory.
set -eu
test "$(id -u)" = 0
base=/srv/dcss-wiki
version=1.43.11
release="$base/releases/mediawiki-$version"
install -d -m 0755 "$base" "$base/releases" "$base/incoming"
if ! id dcsswiki >/dev/null 2>&1; then
    useradd --system --home-dir "$base" --shell /usr/sbin/nologin dcsswiki
fi
install -d -m 0750 -o root -g dcsswiki /etc/dcss-wiki
install -d -m 0755 -o dcsswiki -g dcsswiki "$base/shared"
install -d -m 0750 -o dcsswiki -g dcsswiki "$base/shared/data" "$base/shared/cache"
install -d -m 0755 -o dcsswiki -g dcsswiki "$base/shared/images"
install -d -m 0755 -o dcsswiki -g dcsswiki "$base/shared/resources"
if ! php -m | grep -qx gd; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y --no-install-recommends php8.3-gd php-apcu
fi
if ! python3 -c 'import yaml' >/dev/null 2>&1; then
    apt-get install -y --no-install-recommends python3-yaml
fi
if ! test -d "$release"; then
    # The detached signature is verified against keys published by MediaWiki.
    install -d -m 0700 "$base/incoming/gnupg"
    curl -fLsS --retry 2 "https://releases.wikimedia.org/mediawiki/1.43/mediawiki-$version.tar.gz.sig" -o "$base/incoming/mediawiki-$version.tar.gz.sig"
    curl -fLsS --retry 2 https://www.mediawiki.org/keys/keys.txt -o "$base/incoming/mediawiki-signing-keys.txt"
    gpg --batch --homedir "$base/incoming/gnupg" --import "$base/incoming/mediawiki-signing-keys.txt" 2>"$base/incoming/key-import.log"
    gpg --batch --homedir "$base/incoming/gnupg" --verify "$base/incoming/mediawiki-$version.tar.gz.sig" "$base/incoming/mediawiki-$version.tar.gz"
    tar -xzf "$base/incoming/mediawiki-$version.tar.gz" -C "$base/releases"
fi
if ! test -e "$base/current"; then ln -s "$release" "$base/current"; fi
test "$(readlink -f "$base/current")" = "$release"
if ! test -f /etc/dcss-wiki/LocalSettings.php; then
    python3 -c 'import secrets; print(secrets.token_urlsafe(30))' > /etc/dcss-wiki/admin-password
    chmod 0600 /etc/dcss-wiki/admin-password
    cd "$release"
    php maintenance/run.php install --dbtype sqlite --dbpath "$base/shared/data" \
        --dbname dcsswiki --lang ru --server https://wiki.dungeoncrawl.ru \
        --scriptpath '' --skins Vector --passfile /etc/dcss-wiki/admin-password \
        'Dungeon Crawl — русская вики' Vivor
    install -m 0640 -o root -g dcsswiki LocalSettings.php /etc/dcss-wiki/LocalSettings.php
    # Replace only the installer output just copied to its persistent location.
    mv LocalSettings.php /etc/dcss-wiki/LocalSettings.installer.php
    chmod 0600 /etc/dcss-wiki/LocalSettings.installer.php
    ln -s /etc/dcss-wiki/LocalSettings.php LocalSettings.php
    printf "\nrequire_once '/etc/dcss-wiki/ProjectSettings.php';\n" >> /etc/dcss-wiki/LocalSettings.php
    chown -R dcsswiki:dcsswiki "$base/shared/data"
    chmod 0750 "$base/shared/data"
fi
install -m 0640 -o root -g dcsswiki /tmp/dcss-wiki-ops/LocalSettings.extra.php /etc/dcss-wiki/ProjectSettings.php
# Preserve existing editor uploads; use the initially empty installer directory as a fallback.
if ! test -L "$release/images"; then
    mv "$release/images" "$release/images.distribution"
    ln -s "$base/shared/images" "$release/images"
fi
if ! test -e "$release/resources/dcss"; then
    ln -s "$base/shared/resources" "$release/resources/dcss"
fi
install -m 0644 /tmp/dcss-wiki-ops/php-fpm.conf /etc/php/8.3/fpm/pool.d/dcss-wiki.conf
install -m 0644 /tmp/dcss-wiki-ops/nginx-https.conf /etc/dcss-wiki/nginx-https.conf
install -m 0755 /tmp/dcss-wiki-ops/enable-https.sh /usr/local/sbin/dcss-wiki-enable-https
if ! test -e /etc/nginx/sites-enabled/wiki.dungeoncrawl.ru; then
    install -d -m 0755 /var/www/wiki.dungeoncrawl.ru/acme
    install -m 0644 /tmp/dcss-wiki-ops/nginx-http.conf /etc/nginx/sites-available/wiki.dungeoncrawl.ru
    ln -s /etc/nginx/sites-available/wiki.dungeoncrawl.ru /etc/nginx/sites-enabled/wiki.dungeoncrawl.ru
fi
php-fpm8.3 -t
nginx -t
systemctl reload php8.3-fpm
systemctl reload nginx
install -m 0644 /tmp/dcss-wiki-ops/dcss-wiki-https.service /etc/systemd/system/dcss-wiki-https.service
install -m 0644 /tmp/dcss-wiki-ops/dcss-wiki-https.timer /etc/systemd/system/dcss-wiki-https.timer
install -m 0755 /tmp/dcss-wiki-ops/backup.py /usr/local/sbin/dcss-wiki-backup.py
install -m 0755 /tmp/dcss-wiki-ops/sync.py /usr/local/sbin/dcss-wiki-sync.py
install -d -m 0755 "$base/bin"
install -m 0644 /tmp/dcss-wiki-ops/update-content.php "$base/bin/update-content.php"
for unit in dcss-wiki-backup.service dcss-wiki-backup.timer dcss-wiki-jobs.service dcss-wiki-jobs.timer dcss-wiki-sync.service dcss-wiki-sync.timer; do
    install -m 0644 "/tmp/dcss-wiki-ops/$unit" "/etc/systemd/system/$unit"
done
systemctl daemon-reload
systemctl enable --now dcss-wiki-https.timer
systemctl enable --now dcss-wiki-backup.timer dcss-wiki-jobs.timer dcss-wiki-sync.timer
/usr/local/sbin/dcss-wiki-enable-https
