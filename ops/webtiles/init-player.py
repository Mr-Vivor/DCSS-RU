#!/usr/bin/python3
"""Create only the validated player's persistent directories."""
from pathlib import Path
import re
import sys

if len(sys.argv) != 2 or not re.fullmatch(r"[A-Za-z0-9]{3,20}", sys.argv[1]):
    raise SystemExit("Invalid player name")
for group in ("saves", "morgues", "ttyrecs"):
    (Path("/srv/dcss-ru/shared") / group / sys.argv[1]).mkdir(mode=0o700, parents=True, exist_ok=True)
