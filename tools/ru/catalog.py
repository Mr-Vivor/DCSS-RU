"""Read Crawl text databases without changing their machine keys."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
STATIC_FILES = (
    "ui", "input", "misc", "statuses", "abilities", "skills",
    "player-backgrounds", "player-species", "player-genus", "player-misc",
    "gods", "features", "features-counted", "dungeon", "annotations",
    "transforms", "hiscores", "shops", "mutations", "spells",
    "player-title-def", "player-title-plain", "monster-props",
)
DESCRIPTION_FILES = ("species", "backgrounds", "gods", "tutorial", "hints", "commands")
DATABASE_FILES = ("help", "FAQ")


def read_db(path, translation=False):
    entries = {}
    for block in Path(path).read_text(encoding="utf8").split("%%%%")[1:]:
        lines = [line for line in block.splitlines() if not line.startswith("#")]
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            continue
        key = lines.pop(0).strip()
        if translation and key.startswith('"') and key.endswith('"'):
            key = key[1:-1]
        value = "\n".join(lines).strip("\n")
        if key in entries and entries[key] != value:
            raise ValueError(f"Duplicate key {key!r} in {path}")
        entries[key] = value
    return entries


def write_db(entries, comment):
    return "# " + comment + "\n" + "".join(
        "%%%%\n" + key + "\n\n" + value.rstrip() + "\n"
        for key, value in entries.items())


# These are engine syntax, never translatable prose. Lua may contain strings
# used as identifiers; preserve the whole expression rather than guessing.
TOKEN = re.compile(r"\{\{.*?\}\}|\$\w+\[[^\]]*\]|@[^@\n]+@|"
                   r"</?[A-Za-z][^<>\n]*>|\{[a-z_]+\}|"
                   r"\$\d+|%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[sdifuc]|"
                   r"https?://[^\s<>]+|\b[\w/-]+\.(?:txt|lua|rc)\b", re.S)


def tokens(text):
    return sorted(token.rstrip(",.;!?)") if token.startswith(("http://", "https://")) else token
                  for token in TOKEN.findall(text))
