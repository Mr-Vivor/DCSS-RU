#!/usr/bin/python3
"""Forced SSH command: accept one archive, with no shell or forwarding."""
from pathlib import Path
import os
import re
import subprocess
import sys
import tempfile

match = re.fullmatch(r"deploy ([0-9a-f]{40})", os.environ.get("SSH_ORIGINAL_COMMAND", ""))
if not match:
    raise SystemExit("Only deploy <40-character revision> is allowed")
with tempfile.NamedTemporaryFile(dir="/srv/dcss-ru/incoming", suffix=".tar.gz", delete=False) as output:
    archive = Path(output.name)
    size = 0
    while block := sys.stdin.buffer.read(1024 * 1024):
        size += len(block)
        if size > 250 * 1024 * 1024:
            archive.unlink(missing_ok=True)
            raise SystemExit("Archive exceeds deployment limit")
        output.write(block)
try:
    subprocess.run(["sudo", "-n", "/usr/local/sbin/dcss-ru-activate", "--archive", str(archive), "--revision", match[1]], check=True)
finally:
    archive.unlink(missing_ok=True)
