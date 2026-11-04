from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('retention', Path(__file__).resolve().parents[1] / 'retention.py')
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        (self.base / '.managed-by-dcss-ru').touch()
        (self.base / 'releases').mkdir()
        self.revisions = [f'{i:040x}' for i in range(8)]
        for i, revision in enumerate(self.revisions):
            directory = self.base / 'releases' / revision
            directory.mkdir()
            (directory / 'crawl').write_bytes(b'cached build')
            os.utime(directory, (100 + i, 100 + i))

    def test_prunes_only_old_unused_builds_and_keeps_user_data(self):
        for group in ('shared', 'backups', 'incoming'):
            (self.base / group).mkdir()
            (self.base / group / 'important').write_bytes(b'keep')
        (self.base / 'releases' / 'not-a-release').mkdir()
        protected = set(self.revisions[:3])  # Current, pending and active process.
        with patch.object(retention, 'protected_revisions', return_value=protected):
            removed = retention.prune_releases(self.base, keep=2)
        self.assertEqual(set(removed), set(self.revisions[3:6]))
        for revision in (*self.revisions[:3], *self.revisions[-2:]):
            self.assertTrue((self.base / 'releases' / revision / 'crawl').is_file())
        for group in ('shared', 'backups', 'incoming'):
            self.assertEqual((self.base / group / 'important').read_bytes(), b'keep')
        self.assertTrue((self.base / 'releases' / 'not-a-release').is_dir())

    @unittest.skipIf(os.name == 'nt', 'POSIX process and installation links')
    def test_current_pending_executable_and_working_directory_are_protected(self):
        releases = self.base / 'releases'
        (self.base / 'current').symlink_to(releases / self.revisions[0])
        (self.base / 'pending.json').write_text(json.dumps({'revision': self.revisions[1]}))
        proc = self.base / 'proc'
        (proc / '123').mkdir(parents=True)
        (proc / '123' / 'exe').symlink_to(releases / self.revisions[2] / 'crawl')
        (proc / '123' / 'cwd').symlink_to(releases / self.revisions[3])
        self.assertEqual(retention.protected_revisions(self.base, proc), set(self.revisions[:4]))
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'important').write_bytes(b'keep')
        (releases / ('f' * 40)).symlink_to(outside)
        retention.prune_releases(self.base, keep=1, proc_root=proc)
        self.assertEqual((outside / 'important').read_bytes(), b'keep')
        self.assertTrue((releases / ('f' * 40)).is_symlink())

    def test_unmanaged_installation_is_not_modified(self):
        (self.base / '.managed-by-dcss-ru').unlink()
        with self.assertRaises(ValueError):
            retention.prune_releases(self.base)
        self.assertEqual(len(list((self.base / 'releases').iterdir())), 8)


if __name__ == '__main__':
    unittest.main()
