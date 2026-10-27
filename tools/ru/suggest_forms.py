"""One-time authoring helper: propose explicit forms from seed.tsv.

Requires pymorphy3; the game and normal generation do not depend on it.
Generated forms are drafts and are intended for manual correction in entities.json.
"""
from pathlib import Path
import json
import re
import pymorphy3

ROOT = Path(__file__).resolve().parents[2]
MORPH = pymorphy3.MorphAnalyzer()
CASES = dict(nom="nomn", gen="gent", dat="datv", acc="accs", ins="ablt", prep="loct")


def parse_word(word):
    candidates = MORPH.parse(word)
    # Preserve the supplied lemma; avoid reading "крыса" as genitive of "крыс".
    nominal = [p for p in candidates if p.tag.POS in {"NOUN", "ADJF", "PRTF"}
               and "nomn" in p.tag and "sing" in p.tag]
    return nominal[0] if nominal else candidates[0]


def propose(name, indices, animate):
    words = name.split()
    parses = {i: parse_word(words[i]) for i in indices}
    noun = next((p for p in reversed(list(parses.values())) if p.tag.POS == "NOUN"),
                list(parses.values())[-1])
    gender = {"masc": "m", "femn": "f", "neut": "n"}.get(noun.tag.gender, "n")
    forms = {}
    for number, gram_number in [("singular", "sing"), ("plural", "plur")]:
        forms[number] = {}
        for case, gram_case in CASES.items():
            result = words.copy()
            for i, parsed in parses.items():
                tags = {gram_case, gram_number}
                if case == "acc" and (number == "plural" or gender == "m"):
                    if parsed.tag.POS == "NOUN":
                        # Noun lexemes cannot change lexical animacy. Choose
                        # the equivalent genitive/nominative form explicitly.
                        tags.discard("accs")
                        tags.add("gent" if animate else "nomn")
                    else:
                        tags.add("anim" if animate else "inan")
                if parsed.tag.POS in {"ADJF", "PRTF"} and number == "singular":
                    tags.add({"m": "masc", "f": "femn", "n": "neut"}[gender])
                inflected = parsed.inflect(tags)
                result[i] = inflected.word if inflected else words[i]
            forms[number][case] = " ".join(result)
    return gender, forms


def main():
    output = []
    for line in (ROOT / "localization/ru/seed.tsv").read_text(encoding="utf8").splitlines():
        if not line or line.startswith("#"):
            continue
        kind, english, plural, russian, indices, animate = line.split("|")
        gender, forms = propose(russian, [int(i) for i in indices.split(",")], animate == "1")
        output.append(dict(id=kind + "." + re.sub(r"[^a-z0-9]+", "_", english).strip("_"),
                           kind=kind, en=english, en_plural=plural, gender=gender,
                           animate=animate == "1", forms=forms, review="draft"))
    path = ROOT / "localization/ru/entities.json"
    if path.exists():
        raise SystemExit("entities.json already exists; edit it directly to preserve corrections")
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"Proposed forms for {len(output)} entities")


if __name__ == "__main__":
    main()
