#!/bin/sh
# Run as root with this directory uploaded to a temporary server directory.
set -eu
archive=$1
revision=$2
base=/srv/dcss-ru
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
test "$(id -u)" = 0
if test -d "$base" && ! test -e "$base/.managed-by-dcss-ru"; then
    echo 'Refusing to replace an unrelated /srv/dcss-ru installation' >&2
    exit 1
fi
id dcssru >/dev/null 2>&1 || useradd --system --user-group --home-dir "$base/shared" --shell /usr/sbin/nologin dcssru
id dcssdeploy >/dev/null 2>&1 || useradd --system --user-group --create-home --home-dir "$base/deploy-home" --shell /bin/sh dcssdeploy
install -d -m 0755 "$base" "$base/bin" "$base/releases"
touch "$base/.managed-by-dcss-ru"
install -d -m 0700 "$base/backups"
install -d -m 0700 -o dcssdeploy -g dcssdeploy "$base/incoming"
install -d -m 0700 -o dcssru -g dcssru "$base/shared"
for directory in rc saves morgues sockets running ttyrecs; do
    install -d -m 0700 -o dcssru -g dcssru "$base/shared/$directory"
done
install -m 0755 "$script_dir/init-player.py" "$base/bin/init-player.py"
install -m 0755 "$script_dir/receive-release.py" "$base/bin/receive-release.py"
install -m 0755 "$script_dir/activate-release.py" /usr/local/sbin/dcss-ru-activate
install -m 0644 "$script_dir/config.yml.in" "$base/config.yml.in"
for unit in dcss-ru.service dcss-ru-apply.service dcss-ru-apply.timer; do
    install -m 0644 "$script_dir/$unit" "/etc/systemd/system/$unit"
done
printf '%s\n' 'dcssdeploy ALL=(root) NOPASSWD: /usr/local/sbin/dcss-ru-activate' > /etc/sudoers.d/dcss-ru-deploy
chmod 0440 /etc/sudoers.d/dcss-ru-deploy
visudo -cf /etc/sudoers.d/dcss-ru-deploy
python3 -m venv "$base/venv"
# The initial package is from the same CI workflow used for future releases.
tar -xOf "$archive" dcss-ru-web/webserver/requirements/base.py3.txt > "$base/requirements.txt"
"$base/venv/bin/pip" install -r "$base/requirements.txt"
if ! test -d "$base/repository.git"; then
    git clone --bare https://github.com/Mr-Vivor/DCSS-RU.git "$base/repository.git"
else
    git -C "$base/repository.git" fetch origin ru-bootstrap
fi
systemctl daemon-reload
systemctl enable dcss-ru.service dcss-ru-apply.timer
install -m 0600 -o dcssdeploy -g dcssdeploy "$archive" "$base/incoming/bootstrap.tar.gz"
/usr/local/sbin/dcss-ru-activate --archive "$base/incoming/bootstrap.tar.gz" --revision "$revision"
systemctl start dcss-ru-apply.timer
