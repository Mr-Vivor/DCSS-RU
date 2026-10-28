"""Index upstream message templates by their real source section.

Authoring IDs are local to a source fingerprint; runtime dictionaries always
store the full English key. This avoids retyping long keys during review.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
from catalog import ROOT, read_db, preserve_boundary_whitespace, tokens, message_syntax_matches

SOURCE = ROOT / "crawl-ref/source/dat/translate/messages.txt"


def catalog():
    keys = read_db(SOURCE, True)
    contexts = {}
    section, expecting_key = "messages.txt", False
    for line in SOURCE.read_text(encoding="utf8").splitlines():
        heading = re.fullmatch(r"#\s+([\w-]+\.cc)\s*", line)
        if heading:
            section = heading.group(1)
        if line == "%%%%":
            expecting_key = True
        elif expecting_key and line.strip() and not line.startswith("#"):
            key = line.strip()
            if key.startswith('"') and key.endswith('"'):
                key = key[1:-1]
            contexts[key] = section
            expecting_key = False
    return [dict(id=i, source=k, context=contexts[k]) for i, k in enumerate(keys)]


def translations():
    result = {}
    for path in (ROOT / "crawl-ref/source/dat/translate/ru").glob("*.txt"):
        result.update(read_db(path, True))
    return result


def coverage(known):
    result = {"source": "crawl-ref/source/dat/translate/messages.txt",
              "source_sha256": hashlib.sha256(SOURCE.read_text(encoding="utf8").encode()).hexdigest(),
              "note": "Coverage of imported message templates, not a percentage of all current game text.",
              "total": 0, "translated": 0, "sections": {}}
    for entry in catalog():
        section = result["sections"].setdefault(entry["context"], {"total": 0, "translated": 0, "missing": []})
        result["total"] += 1
        section["total"] += 1
        if entry["source"] in known:
            result["translated"] += 1
            section["translated"] += 1
        else:
            section["missing"].append(entry["source"])
    result["missing"] = result["total"] - result["translated"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sections", nargs="*")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--apply", type=Path,
                        help="Reviewed UTF-8 lines: authoring ID | Russian text")
    args = parser.parse_args()
    entries = catalog()
    known = translations()
    if args.apply:
        path = ROOT / "localization/ru/system-messages.json"
        messages = json.loads(path.read_text(encoding="utf8"))
        review_path = ROOT / "localization/ru/context-review.json"
        review = json.loads(review_path.read_text(encoding="utf8"))
        fingerprint = hashlib.sha256(SOURCE.read_text(encoding="utf8").encode()).hexdigest()
        if review.get("message_source_sha256") != fingerprint:
            raise ValueError("Message authoring IDs changed: recheck the source fingerprint before applying translations")
        for line in args.apply.read_text(encoding="utf8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            index, value = line.split(" | ", 1)
            entry = entries[int(index)]
            key = entry["source"]
            value = preserve_boundary_whitespace(key, value)
            if not message_syntax_matches(key, value):
                raise ValueError((entry, tokens(key), tokens(value)))
            if key in known and known[key] != value:
                raise ValueError("Existing translation needs explicit review: " + key)
            messages[key] = value
            review["messages"][key] = dict(context=entry["context"],
                translation_sha256=hashlib.sha256(value.encode()).hexdigest())
        path.write_text(json.dumps(messages, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        print("System messages:", len(messages))
        return
    grouped = {}
    for entry in entries:
        grouped.setdefault(entry["context"], []).append(entry)
    print("UPSTREAM", len(entries), "PRESENT", sum(e["source"] in known for e in entries))
    for context, group in grouped.items():
        if args.sections and context not in args.sections:
            continue
        pending = [e for e in group if e["source"] not in known]
        print("\nSECTION", context, "MISSING", len(pending), "/", len(group))
        if not args.summary:
            for e in pending:
                print(e["id"], repr(e["source"]))


if __name__ == "__main__":
    main()
