"""Optional authoring aid: cache protected machine drafts of public game text.

Requires requests. Never called by the game, generator or CI. Existing entries
are not overwritten; edit static.json / description databases to review drafts.
"""
from pathlib import Path
import json
import re
import time
import requests
import argparse
from catalog import ROOT, STATIC_FILES, DESCRIPTION_FILES, DATABASE_FILES, TOKEN, read_db, write_db, tokens

CACHE = ROOT / "localization/ru/static.json"
terms = json.loads((ROOT / "localization/ru/terms.json").read_text(encoding="utf8"))
names = {en: ru for group in terms.values() for en, ru in group.items()}
# Names from DCSS lore are transliterated, never semantically reinvented.
names.update(json.loads((ROOT / "localization/ru/proper-names.json").read_text(encoding="utf8")))
name_re = re.compile(r"(?<![\w])(?:" + "|".join(re.escape(s) for s in sorted(names, key=len, reverse=True)) + r")(?![\w])")


def protect(text):
    saved = []
    def hold(value):
        saved.append(value)
        return f" ZXP{len(saved)-1:04d}PXZ "
    text = TOKEN.sub(lambda m: hold(m.group()), text)
    text = name_re.sub(lambda m: hold(names[m.group()]), text)
    if ":nowrap" not in text:
        paragraphs = text.split("\n\n")
        text = "\n\n".join(
            paragraph if any(line.startswith("  ") for line in paragraph.splitlines())
            else " ".join(line.strip() for line in paragraph.splitlines())
            for paragraph in paragraphs)
    # Preserve indented diagrams and input keys. Paragraphs may be reflowed.
    text = re.sub(r"(?m)^ {2,}[^\n]*[\\|][^\n]*$",
                  lambda m: m.group() if "ZXP" in m.group() else hold(m.group()), text)
    return text, saved


def translate_batch(batch):
    protected = [protect(text) for text in batch]
    query = "\n".join(f"ZXQ{i:04d}QXZ {text}" for i, (text, _) in enumerate(protected))
    for attempt in range(4):
        try:
            response = requests.get("https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "en", "tl": "ru", "dt": "t", "q": query}, timeout=40)
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
            continue
        if response.status_code == 200:
            break
        if response.status_code in (429, 503):
            time.sleep(10 * (attempt + 1))
        else:
            response.raise_for_status()
    response.raise_for_status()
    result = "".join(part[0] or "" for part in response.json()[0])
    chunks = re.split(r"ZXQ\s*(\d{4})\s*QXZ\s*", result)
    found = {int(chunks[i]): chunks[i+1].strip() for i in range(1, len(chunks)-1, 2)}
    if len(found) != len(batch):
        if len(batch) > 1:
            return [translate_batch([text])[0] for text in batch]
        raise ValueError("Translation damaged record separators")
    out = []
    for i, (original, (_, saved)) in enumerate(zip(batch, protected)):
        value = found[i]
        for n, token in enumerate(saved):
            pattern = rf"ZXP\s*{n:04d}\s*PXZ"
            value, count = re.subn(pattern, lambda m: token, value)
            if count != 1:
                if len(batch) > 1:
                    return [translate_batch([text])[0] for text in batch]
                # Dense help tables can make a translator discard opaque tags.
                # Translate only the prose between them, then rebuild locally.
                parts = re.split(r"(ZXP\d{4}PXZ)", protected[0][0])
                indexes = [j for j, part in enumerate(parts)
                           if j % 2 == 0 and re.search(r"[A-Za-z]{2}", part)]
                prose = translate_batch([parts[j].strip() for j in indexes])
                for j, translated in zip(indexes, prose):
                    parts[j] = " " + translated + " "
                for j in range(1, len(parts), 2):
                    parts[j] = saved[int(parts[j][3:7])]
                value = "".join(parts).strip()
                break
        if tokens(original) != tokens(value):
            from collections import Counter
            raise ValueError(f"Token mismatch: {original[:90]}\nMissing: {Counter(tokens(original))-Counter(tokens(value))}\nAdded: {Counter(tokens(value))-Counter(tokens(original))}")
        if not value.strip():
            if len(batch) > 1:
                return [translate_batch([text])[0] for text in batch]
            raise ValueError("Empty draft: " + original)
        out.append(value.strip())
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", nargs="*", choices=DESCRIPTION_FILES, default=[],
                        help="Explicitly replace selected description drafts")
    args = parser.parse_args()
    data = json.loads(CACHE.read_text(encoding="utf8")) if CACHE.exists() else {}
    targets = []
    for filename in STATIC_FILES:
        group = data.setdefault(filename, {})
        for key in read_db(ROOT / f"crawl-ref/source/dat/translate/{filename}.txt", True):
            if key not in group:
                # Leading/trailing whitespace is significant for translation keys.
                if not re.search(r"[A-Za-z]{2}", TOKEN.sub("", key)):
                    group[key] = key
                else:
                    targets.append((group, key, key))
    descriptions = {}
    databases = {}
    for filename in DESCRIPTION_FILES:
        path = ROOT / f"crawl-ref/source/dat/descript/ru/{filename}.txt"
        group = descriptions[filename] = read_db(path) if path.exists() else {}
        if filename in args.refresh:
            group.clear()
        # Existing tutorial prose is already edited; retain it and validate below.
        # Species/backgrounds are rewritten separately against current upstream.
        for key, value in read_db(ROOT / f"crawl-ref/source/dat/descript/{filename}.txt").items():
            if key not in group or tokens(value) != tokens(group[key]):
                if key == "HINT_THROWABLE":
                    group[key] = "$1 можно метнуть командой <w>$cmd[CMD_FIRE]</w> без метательного оружия."
                    continue
                if key == "HINT_DESCRIBE_JEWELLERY":
                    group[key] = "Украшение можно надеть командой <w>$cmd[CMD_WEAR_JEWELLERY]</w> и снять командой <w>$cmd[CMD_REMOVE_JEWELLERY]</w><tiles>; в графическом режиме обе команды также доступны щелчком по предмету в инвентаре</tiles>."
                    continue
                if key == "HINT_JEWELLERY_HAS_ABILITY":
                    group[key] = "Некоторые украшения, в том числе это, дают особые способности, пока надеты. Их можно применить командой <w>$cmd[CMD_USE_ABILITY]</w>."
                    continue
                targets.append((group, key, value))
    for filename in DATABASE_FILES:
        path = ROOT / f"crawl-ref/source/dat/database/ru/{filename}.txt"
        group = databases[filename] = read_db(path) if path.exists() else {}
        for key, value in read_db(ROOT / f"crawl-ref/source/dat/database/{filename}.txt").items():
            if key not in group or tokens(value) != tokens(group[key]):
                targets.append((group, key, value))

    def save():
        CACHE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8", newline="\n")
        for filename, group in descriptions.items():
            path = ROOT / f"crawl-ref/source/dat/descript/ru/{filename}.txt"
            path.write_text(write_db(group, "Russian text; draft additions checked for engine placeholders."), encoding="utf8", newline="\n")
        for filename, group in databases.items():
            path = ROOT / f"crawl-ref/source/dat/database/ru/{filename}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(write_db(group, "Russian help; draft additions checked for engine placeholders."), encoding="utf8", newline="\n")

    batch, count = [], 0
    for target in targets + [None]:
        if batch and (target is None or sum(len(t[2]) + 25 for t in batch) + len(target[2]) > 3200):
            translated = translate_batch([t[2] for t in batch])
            for (group, key, _), value in zip(batch, translated):
                group[key] = value
            count += len(batch)
            save()
            print(f"Drafted {count}/{len(targets)} records", flush=True)
            batch = []
        if target is not None:
            batch.append(target)
    save()


if __name__ == "__main__":
    main()
