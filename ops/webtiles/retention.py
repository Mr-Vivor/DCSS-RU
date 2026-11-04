#!/usr/bin/python3
"""Prune reproducible release directories, preserving live and pending versions."""
from pathlib import Path
import json
import re
import shutil

BASE = Path('/srv/dcss-ru')
REVISION = re.compile(r'[0-9a-f]{40}')


def protected_revisions(base, proc_root=Path('/proc')):
    releases = base / 'releases'
    protected = set()

    def protect(path):
        try:
            relative = path.resolve().relative_to(releases)
        except ValueError:
            return
        if relative.parts and REVISION.fullmatch(relative.parts[0]):
            protected.add(relative.parts[0])

    current = base / 'current'
    if current.exists() or current.is_symlink():
        target = current.resolve()
        if target.parent != releases or not REVISION.fullmatch(target.name):
            raise ValueError('Current release is outside the managed release directory')
        protect(target)
    pending = base / 'pending.json'
    if pending.exists():
        revision = json.loads(pending.read_text())['revision']
        if not isinstance(revision, str) or not REVISION.fullmatch(revision):
            raise ValueError('Invalid pending revision; refusing release cleanup')
        protected.add(revision)
    for process in proc_root.iterdir():
        if not process.name.isdigit():
            continue
        for name in ('exe', 'cwd'):
            try:
                protect(process / name)
            except (FileNotFoundError, ProcessLookupError):
                pass  # A process may exit while its links are inspected.
    return protected


def prune_releases(base=BASE, keep=5, proc_root=Path('/proc')):
    base = Path(base)
    if keep < 1 or base.resolve() != base or not (base / '.managed-by-dcss-ru').is_file():
        raise ValueError('Refusing cleanup outside a managed installation')
    releases = base / 'releases'
    if releases.resolve() != releases or not releases.is_dir():
        raise ValueError('Refusing a redirected release directory')
    protected = protected_revisions(base, proc_root)
    candidates = [path for path in releases.iterdir()
                  if REVISION.fullmatch(path.name) and not path.is_symlink() and path.is_dir()]
    candidates.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    protected.update(path.name for path in candidates[:keep])
    removed = []
    for path in candidates:
        if path.name in protected:
            continue
        # Recheck the target immediately before recursive removal. User data,
        # backups, incoming uploads and non-revision directories are excluded.
        if path.is_symlink() or path.resolve().parent != releases:
            raise ValueError('Release cleanup target changed')
        shutil.rmtree(path)
        removed.append(path.name)
    return removed


if __name__ == '__main__':
    import fcntl
    with (BASE / 'deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        print('Removed unused release directories:', len(prune_releases()))
