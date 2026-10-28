#!/usr/bin/python3
"""Install a CI package and defer activation until existing games have ended."""
from pathlib import Path, PurePosixPath
import argparse
import datetime
import fcntl
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import urllib.request

BASE = Path("/srv/dcss-ru")

def unpack(archive, revision):
    if not re.fullmatch(r"[0-9a-f]{40}", revision or ""):
        raise ValueError("Invalid revision")
    archive = Path(archive).resolve(strict=True)
    if archive.parent != BASE / "incoming" or not archive.is_file():
        raise ValueError("Only an incoming archive may be installed")
    release = BASE / "releases" / revision
    if release.exists():
        raise ValueError("Release already exists; use --pending to activate it")
    subprocess.run(["git", "--git-dir", str(BASE / "repository.git"), "fetch", "--no-tags", "origin", "ru-bootstrap"], check=True, timeout=90)
    subprocess.run(["git", "--git-dir", str(BASE / "repository.git"), "cat-file", "-e", revision + "^{commit}"], check=True)
    with tempfile.TemporaryDirectory(dir=BASE / "releases", prefix=".unpack-") as stage:
        with tarfile.open(archive, "r:gz") as package:
            members = package.getmembers()
            if len(members) > 20000 or sum(member.size for member in members) > 1024 * 1024 * 1024:
                raise ValueError("Unpacked release exceeds deployment limits")
            for member in members:
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or not path.parts or path.parts[0] != "dcss-ru-web":
                    raise ValueError("Invalid archive path")
                if not (member.isfile() or member.isdir()):
                    raise ValueError("Links and special files are not permitted")
            package.extractall(stage, filter="data")
        directory = Path(stage) / "dcss-ru-web"
        with (directory / "crawl").open("rb") as binary:
            magic = binary.read(4)
        if magic != b"\x7fELF":
            raise ValueError("The package must contain a Linux engine")
        template = (BASE / "config.yml.in").read_text()
        (directory / "webserver/config.yml").write_text(template.replace("@RELEASE@", str(release)))
        (directory / "REVISION").write_text(revision + "\n")
        (directory / "crawl").chmod(0o755)
        os.replace(directory, release)
    (BASE / "pending.json").write_text(json.dumps({"revision": revision}) + "\n")
    return release

def backup():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = BASE / "backups" / stamp
    destination.mkdir(mode=0o700)
    for source in (BASE / "shared").glob("*.db3"):
        with sqlite3.connect(source) as live, sqlite3.connect(destination / source.name) as saved:
            live.backup(saved)
    for group in ("saves", "rc", "morgues"):
        shutil.copytree(BASE / "shared" / group, destination / group, symlinks=True)
    current = BASE / "current"
    if current.exists():
        (destination / "previous-release").write_text(str(current.resolve()) + "\n")

def health():
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8088/", timeout=2) as response:
                if response.status == 200:
                    return True
        except OSError:
            time.sleep(1)
    return False

def activate():
    pending = BASE / "pending.json"
    if not pending.exists():
        return
    # Includes players currently in character selection, not just saved games.
    if subprocess.run(["pgrep", "-u", "dcssru", "-x", "crawl"], stdout=subprocess.DEVNULL).returncode == 0:
        print("Release staged; activation waits for players to finish.")
        return
    revision = json.loads(pending.read_text())["revision"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Invalid pending revision")
    target = BASE / "releases" / revision
    if not target.is_dir() or target.resolve().parent != BASE / "releases":
        raise ValueError("Invalid release directory")
    current = BASE / "current"
    previous = current.resolve() if current.exists() else None
    subprocess.run(["systemctl", "stop", "dcss-ru.service"], check=True)
    try:
        backup()
        link = BASE / "current.next"
        link.unlink(missing_ok=True)
        link.symlink_to(target, target_is_directory=True)
        os.replace(link, current)
        subprocess.run(["systemctl", "start", "dcss-ru.service"], check=True)
        if not health():
            raise RuntimeError("New release failed its HTTP health check")
    except Exception:
        if previous:
            current.unlink(missing_ok=True)
            current.symlink_to(previous, target_is_directory=True)
            subprocess.run(["systemctl", "restart", "dcss-ru.service"], check=True)
        raise
    pending.unlink()
    print("Active DCSS-RU release:", revision)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive")
    parser.add_argument("--revision")
    parser.add_argument("--pending", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit("Activation must run via the restricted sudo command")
    with (BASE / "deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.archive:
            unpack(args.archive, args.revision)
        activate()
