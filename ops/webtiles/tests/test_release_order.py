from pathlib import Path
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('retention_order', Path(__file__).resolve().parents[1] / 'retention.py')
retention = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retention)


class ReleaseOrderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name)
        self.repo = self.base / 'repository.git'
        subprocess.run(['git', 'init', '--bare', str(self.repo)], check=True, capture_output=True)
        self.git = ['git', '--git-dir', str(self.repo)]
        tree = subprocess.check_output(self.git + ['mktree'], input=b'').decode().strip()
        env = dict(os.environ, GIT_AUTHOR_NAME='Fixture', GIT_COMMITTER_NAME='Fixture',
                   GIT_AUTHOR_EMAIL='fixture@example.invalid', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.revisions = []
        for message in ('first', 'second', 'third'):
            args = self.git + ['commit-tree', tree]
            if self.revisions:
                args += ['-p', self.revisions[-1]]
            revision = subprocess.check_output(args, input=(message+'\n').encode(), env=env).decode().strip()
            self.revisions.append(revision)
        (self.base / 'current').mkdir()
        (self.base / 'current' / 'REVISION').write_text(self.revisions[1])

    def test_late_ancestor_cannot_roll_back_active_build(self):
        with self.assertRaisesRegex(ValueError, 'older'):
            retention.reject_stale_release(self.base, self.revisions[0])
        self.assertEqual((self.base / 'current' / 'REVISION').read_text(), self.revisions[1])

    def test_late_build_cannot_replace_a_newer_pending_build(self):
        pending = {'revision': self.revisions[2]}
        (self.base / 'pending.json').write_text(json.dumps(pending))
        with self.assertRaisesRegex(ValueError, 'older'):
            retention.reject_stale_release(self.base, self.revisions[1])
        self.assertEqual(json.loads((self.base / 'pending.json').read_text()), pending)

    def test_newer_and_same_revisions_are_allowed(self):
        retention.reject_stale_release(self.base, self.revisions[1])
        retention.reject_stale_release(self.base, self.revisions[2])


if __name__ == '__main__':
    unittest.main()
