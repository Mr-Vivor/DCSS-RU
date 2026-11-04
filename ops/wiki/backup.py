#!/usr/bin/env python3
"""Consistent SQLite snapshot plus uploads/settings; retain seven managed backups."""
from datetime import datetime, timezone
from pathlib import Path
import fcntl
import os
import re
import sqlite3
import tarfile
import tempfile

BASE = Path('/srv/dcss-wiki')


def main():
    os.umask(0o077)
    backup_dir = BASE / 'backups'
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    if backup_dir.resolve() != Path('/srv/dcss-wiki/backups') or backup_dir.is_symlink():
        raise RuntimeError('Unexpected backup path')
    with (backup_dir / '.lock').open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        target = backup_dir / ('dcss-wiki-' + stamp + '.tar.gz')
        database = BASE / 'shared/data/dcsswiki.sqlite'
        if not database.is_file() or database.is_symlink():
            raise RuntimeError('The wiki content database is missing or is a symlink')
        with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=backup_dir) as scratch:
            snapshot = Path(scratch) / 'dcsswiki.sqlite'
            with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(snapshot) as dest:
                source.backup(dest)
                if dest.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('SQLite snapshot integrity check failed')
            partial = target.with_suffix('.gz.partial')
            with tarfile.open(partial, 'w:gz') as archive:
                archive.add(snapshot, arcname='data/dcsswiki.sqlite')
                archive.add(BASE / 'shared/images', arcname='images')
                for name in ('LocalSettings.php', 'ProjectSettings.php'):
                    archive.add(Path('/etc/dcss-wiki') / name, arcname='settings/' + name)
                for name in ('import-state.json', 'import-conflicts.json'):
                    path = BASE / 'shared' / name
                    if path.exists():
                        archive.add(path, arcname=name)
            partial.replace(target)
        managed = sorted(p for p in backup_dir.iterdir()
                         if re.fullmatch(r'dcss-wiki-\d{8}T\d{6}Z\.tar\.gz', p.name)
                         and p.is_file() and not p.is_symlink() and p.resolve().parent == backup_dir)
        for old in managed[:-7]:
            old.unlink()
        print('Wiki backup:', target.name, 'bytes:', target.stat().st_size)


if __name__ == '__main__':
    main()
