"""Read Crawl text databases without changing their machine keys."""
from pathlib import Path
import hashlib
import json
import re
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
STATIC_FILES = (
    "ui", "input", "misc", "statuses", "abilities", "skills",
    "player-backgrounds", "player-species", "player-genus", "player-misc",
    "gods", "features", "features-counted", "dungeon", "annotations",
    "transforms", "hiscores", "shops", "mutations", "spells",
    "player-title-def", "player-title-plain", "monster-props",
    "verbs", "body-parts",
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
        if translation:
            # Match the game loader: quotes preserve spaces in fragments.
            value = "\n".join(
                line.strip()[1:-1] if line.strip().startswith('"') and line.strip().endswith('"')
                else line.strip()
                for line in value.split("\n"))
        if key in entries and entries[key] != value:
            raise ValueError(f"Duplicate key {key!r} in {path}")
        entries[key] = value
    return entries


def preserve_boundary_whitespace(source, target):
    """Keep layout/word separators which are part of a translation key."""
    leading = re.match(r"^\s*", source).group()
    trailing = re.search(r"\s*$", source).group()
    if leading:
        target = leading + target.lstrip()
    if trailing:
        target = target.rstrip() + trailing
    return target


def write_db(entries, comment):
    return "# " + comment + "\n" + "".join(
        "%%%%\n" + key + "\n\n" + value.rstrip() + "\n"
        for key, value in entries.items())


# These are engine syntax, never translatable prose. Lua may contain strings
# used as identifiers; preserve the whole expression rather than guessing.
TOKEN = re.compile(r"\{\{.*?\}\}|\$\w+\[[^\]]*\]|@[^@\n]+@|"
                   r"</?[A-Za-z][^<>\n]*>|\{[a-z_-]+\}|"
                   r"\$\d+|(?<![\w@])%(?:\d+\$)?[-+#0 ]*\d*(?:\.\d+)?[sdifuc]|"
                   r"https?://[^\s<>]+|\b[\w/-]+\.(?:txt|lua|rc)\b", re.S)


def tokens(text):
    return sorted(token.rstrip(",.;!?)") if token.startswith(("http://", "https://")) else token
                  for token in TOKEN.findall(text))


def message_syntax_matches(source, target):
    """Allow Russian case instructions; never lose arguments or engine markup."""
    original, translated = Counter(tokens(source)), Counter(tokens(target))
    grammatical = {"{nom}", "{gen}", "{dat}", "{acc}", "{ins}", "{prep}",
                   "{verb-inf}", "{verb-you}"}
    return not (original - translated) and all(t in grammatical for t in translated - original)


def translated_lua(source, replacements):
    """Translate explicitly reviewed string literals without changing Lua code.

    Selectors such as you.race() == "Djinni" remain byte-for-byte identical.
    The full rewritten Lua block is still a protected token during validation.
    """
    def translate_block(match):
        block = match.group()
        for english, russian in replacements.items():
            block = block.replace(json.dumps(english, ensure_ascii=False),
                                  json.dumps(russian, ensure_ascii=False))
        return block
    return re.sub(r"\{\{.*?\}\}", translate_block, source, flags=re.S)


def reviewed_descriptions():
    """Reject stale mechanics and damaged markup before writing game/wiki text."""
    data = json.loads((ROOT / "localization/ru/descriptions.json").read_text(encoding="utf8"))
    for filename, group in data.items():
        source = read_db(ROOT / f"crawl-ref/source/dat/descript/{filename}.txt")
        for key, entry in group.items():
            original = source[key]
            digest = hashlib.sha256(original.encode()).hexdigest()
            if digest != entry["source_sha256"]:
                raise ValueError(f"Recheck changed upstream mechanics: {filename}/{key}")
            expected = translated_lua(original, entry.get("lua_strings", {}))
            if tokens(expected) != tokens(entry["text"]):
                raise ValueError(f"Changed description syntax: {filename}/{key}")
            if re.findall(r"\[\[.*?\]\]", original) != re.findall(r"\[\[.*?\]\]", entry["text"]):
                raise ValueError(f"Changed description references: {filename}/{key}")
    return data


def reviewed_random_messages():
    """Keep random-message choices, weights, recursive references and Lua intact."""
    data = json.loads((ROOT / "localization/ru/random-messages.json").read_text(encoding="utf8"))
    for filename, entries in data.items():
        source = read_db(ROOT / f"crawl-ref/source/dat/database/{filename}.txt")
        for key, entry in entries.items():
            original = source[key]
            if hashlib.sha256(original.encode()).hexdigest() != entry["source_sha256"]:
                raise ValueError(f"Recheck changed random-message source: {filename}/{key}")
            expected = translated_lua(original, entry.get("lua_strings", {}))
            if tokens(expected) != tokens(entry["text"]):
                raise ValueError(f"Changed random-message syntax: {filename}/{key}")
            choices = original.split("\n\n")
            translated = entry["text"].split("\n\n")
            if len(choices) != len(translated):
                raise ValueError(f"Changed random-message choices: {filename}/{key}")
            for before, after in zip(choices, translated):
                if re.findall(r"^w:\d+$", before, re.M) != re.findall(r"^w:\d+$", after, re.M):
                    raise ValueError(f"Changed random-message weights: {filename}/{key}")
    return data
