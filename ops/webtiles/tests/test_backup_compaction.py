from pathlib import Path
import importlib.util
import os
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch

if os.name == 'posix':
    spec = importlib.util.spec_from_file_location(
        'backup_compaction', Path(__file__).resolve().parents[1] / 'compact-backups.py')
    compact = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(compact)


@unittest.skipUnless(os.name == 'posix', 'Server backup compression uses GNU tar and flock')
class BackupCompactionTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.base = Path(self.workspace.name) / 'server'
        self.root = self.base / 'backups'
        self.root.mkdir(parents=True)
        (self.base / '.managed-by-dcss-ru').touch()
        self.old = self.snapshot('20261101T010000Z')
        self.latest = self.snapshot('20261109T010000Z')

    def snapshot(self, stamp):
        path = self.root / stamp
        (path / 'saves').mkdir(parents=True)
        (path / 'previous-release').write_text('/srv/dcss-ru/releases/old\n')
        (path / 'saves' / 'player.cs').write_bytes(b'save-data\0' * 10000)
        (path / 'saves' / 'player.cs').chmod(0o640)
        return path

    def test_archive_restores_bytes_modes_links_and_keeps_latest(self):
        (self.old / 'saves' / 'current').symlink_to('player.cs')
        expected = (self.old / 'saves' / 'player.cs').read_bytes()
        self.assertEqual(compact.compact_snapshots(self.base, keep=1), [self.old.name])
        self.assertFalse(self.old.exists())
        self.assertTrue(self.latest.is_dir())
        archive = self.root / (self.old.name + '.tar.gz')
        self.assertEqual(archive.stat().st_mode & 0o777, 0o600)
        with tarfile.open(archive) as bundle:
            member = bundle.getmember(self.old.name + '/saves/player.cs')
            self.assertEqual(bundle.extractfile(member).read(), expected)
            self.assertEqual(member.mode, 0o640)
            self.assertEqual(bundle.getmember(self.old.name + '/saves/current').linkname,
                             'player.cs')

    def test_redirected_backup_root_is_rejected(self):
        external = self.base / 'other'
        self.root.rename(external)
        self.root.symlink_to(external, target_is_directory=True)
        with self.assertRaises(ValueError):
            compact.compact_snapshots(self.base, keep=1)
        self.assertTrue((external / self.old.name / 'saves/player.cs').is_file())

    def test_failed_comparison_preserves_original_and_removes_partial_archive(self):
        run = subprocess.run
        def reject_comparison(args, **kwargs):
            if '--compare' in args:
                raise subprocess.CalledProcessError(1, args)
            return run(args, **kwargs)
        with patch.object(compact.subprocess, 'run', side_effect=reject_comparison):
            with self.assertRaises(subprocess.CalledProcessError):
                compact.compact_snapshots(self.base, keep=1)
        self.assertTrue((self.old / 'saves/player.cs').is_file())
        self.assertFalse(list(self.root.glob('*.tar.gz')))

    def test_preexisting_archive_never_replaces_original_blindly(self):
        (self.root / (self.old.name + '.tar.gz')).write_bytes(b'incomplete archive')
        self.assertEqual(compact.compact_snapshots(self.base, keep=1), [])
        self.assertTrue((self.old / 'saves/player.cs').is_file())


if __name__ == '__main__':
    unittest.main()
