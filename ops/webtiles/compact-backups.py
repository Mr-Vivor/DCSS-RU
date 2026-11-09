#!/usr/bin/python3
"""Losslessly archive old game snapshots; never expire backup history."""
from pathlib import Path
import fcntl
import os
import re
import shutil
import subprocess
import tempfile

BASE = Path('/srv/dcss-ru')
STAMP = re.compile(r'\d{8}T\d{6}Z')


def compact_snapshots(base=BASE, keep=10):
    base = Path(base)
    root = base / 'backups'
    if (keep < 1 or base.resolve() != base
            or not (base / '.managed-by-dcss-ru').is_file()
            or root.resolve() != root or not root.is_dir()):
        raise ValueError('Refusing backup compression outside a managed installation')
    # A snapshot must be finished before archiving it. Activation writes
    # previous-release last, and uses this same lock during the complete backup.
    with (base / 'deploy.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        snapshots = sorted(path for path in root.iterdir()
                           if STAMP.fullmatch(path.name) and path.is_dir()
                           and not path.is_symlink()
                           and (path / 'previous-release').is_file())
        compacted = []
        for source in snapshots[:-keep]:
            if source.resolve().parent != root or source.is_symlink():
                raise ValueError('Backup path changed')
            archive = root / (source.name + '.tar.gz')
            if archive.is_symlink():
                raise ValueError('Refusing a redirected backup archive')
            # Leave both versions untouched after an interrupted earlier run.
            # tar --compare alone cannot prove an existing archive is complete.
            if archive.exists():
                continue
            size = sum(path.stat().st_size for path in source.rglob('*')
                       if path.is_file() and not path.is_symlink())
            if shutil.disk_usage(root).free < size + 8 * 1024**2:
                raise RuntimeError('Insufficient workspace for a verified archive')
            fd, name = tempfile.mkstemp(prefix='.compress-', suffix='.tar.gz', dir=root)
            os.close(fd)
            temporary = Path(name)
            try:
                temporary.chmod(0o600)
                subprocess.run(['tar', '--create', '-I', 'gzip -1', '--file',
                                str(temporary), '--directory', str(root), source.name],
                               check=True)
                # Checks file bytes, ownership, modes, timestamps and symlinks
                # against the original complete snapshot before any replacement.
                subprocess.run(['tar', '--compare', '--gzip', '--file',
                                str(temporary), '--directory', str(root)], check=True)
                if temporary.stat().st_size >= size:
                    continue
                with temporary.open('rb') as stream:
                    os.fsync(stream.fileno())
                os.replace(temporary, archive)
                directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
                if source.resolve().parent != root or source.is_symlink():
                    raise ValueError('Backup path changed after verification')
                shutil.rmtree(source)
                compacted.append(source.name)
                print('Verified and archived snapshot:', source.name, flush=True)
            finally:
                temporary.unlink(missing_ok=True)
        return compacted


if __name__ == '__main__':
    os.umask(0o077)
    print('Snapshots archived:', len(compact_snapshots()))
