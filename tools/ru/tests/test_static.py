"""Coverage and syntax gates for static Russian UI/teaching text."""
from pathlib import Path
import json
import hashlib
import re
import sys
import unittest
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/ru"))
from catalog import STATIC_FILES, DESCRIPTION_FILES, DATABASE_FILES, TOKEN, read_db, tokens, reviewed_descriptions, reviewed_random_messages, message_syntax_matches
from message_catalog import SOURCE, catalog as message_catalog, coverage as message_coverage, translations


class StaticTranslationTests(unittest.TestCase):
    def test_random_messages_preserve_choices_weights_and_recursive_references(self):
        data = reviewed_random_messages()
        original = read_db(ROOT / "crawl-ref/source/dat/database/miscname.txt")
        self.assertEqual(set(data["miscname"]), set(original))
        for filename, entries in data.items():
            generated = read_db(ROOT / f"crawl-ref/source/dat/database/ru/{filename}.txt")
            for key, entry in entries.items():
                self.assertEqual(generated[key], entry["text"], key)
                for variant in entry["text"].split("\n\n"):
                    self.assertRegex(variant, r"[А-Яа-яЁё]", key)

    def test_context_review_marks_only_the_current_translations(self):
        review = json.loads((ROOT / "localization/ru/context-review.json").read_text(encoding="utf8"))
        data = json.loads((ROOT / "localization/ru/static.json").read_text(encoding="utf8"))
        messages = json.loads((ROOT / "localization/ru/system-messages.json").read_text(encoding="utf8"))
        for group, entry in review["catalogs"].items():
            self.assertEqual(len(data[group]), entry["entries"], group)
            actual = hashlib.sha256(json.dumps(data[group], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            self.assertEqual(actual, entry["translations_sha256"], group)
        for key, entry in review["messages"].items():
            self.assertEqual(hashlib.sha256(messages[key].encode()).hexdigest(), entry["translation_sha256"], key)
        duration_source = (ROOT / "crawl-ref/source/duration-data.h").read_text(encoding="utf8")
        self.assertEqual(hashlib.sha256(duration_source.encode()).hexdigest(), review["duration_source_sha256"],
                         "Recheck current status mechanics after upstream changes")
        self.assertEqual(hashlib.sha256(SOURCE.read_text(encoding="utf8").encode()).hexdigest(),
                         review["message_source_sha256"], "Recheck source sections and authoring IDs")

    def test_imported_message_catalog_has_no_remaining_gaps(self):
        entries = message_catalog()
        known = translations()
        self.assertGreater(len(entries), 6000)
        self.assertEqual(len({entry["source"] for entry in entries}), len(entries))
        for entry in entries:
            self.assertTrue(entry["context"].endswith(".cc"), entry)
            self.assertTrue(entry["source"] in known, entry)
        report = message_coverage(set(known))
        self.assertEqual(report["missing"], 0)
        self.assertEqual(report, json.loads((ROOT / "localization/ru/message-coverage.json").read_text(encoding="utf8")))

    def test_current_ability_labels_are_covered(self):
        # The imported catalog predates the chosen gameplay version.
        source = (ROOT / "crawl-ref/source/ability.cc").read_text(encoding="utf8")
        labels = re.findall(r'\{\s*ABIL_\w+,\s*"([^"\n]+)"', source)
        self.assertGreater(len(labels), 100)
        known = translations()
        for label in labels:
            self.assertTrue(label in known, label)
            self.assertRegex(known[label], r"[А-Яа-яЁё]", label)

    def test_case_instructions_do_not_relax_argument_or_markup_protection(self):
        self.assertTrue(message_syntax_matches("Roots grab @arg@.", "Корни хватают {acc}@arg@."))
        self.assertTrue(message_syntax_matches("You can @arg@.", "Вы можете {verb-inf}@arg@."))
        self.assertFalse(message_syntax_matches("You hit @arg@.", "Вы ударяете {acc}."))
        self.assertFalse(message_syntax_matches("<red>@arg@</red>", "{acc}@arg@"))
        self.assertFalse(message_syntax_matches("Hit @arg@.", "Удар {shop}@arg@."))
        self.assertFalse(message_syntax_matches("Hit @Arg@.", "Удар {acc}@arg@."))

    def test_current_duration_hud_labels_are_covered(self):
        # Check the current engine, not just the older imported English catalog.
        source = (ROOT / "crawl-ref/source/duration-data.h").read_text(encoding="utf8")
        labels = re.findall(r'\{\s*DUR_\w+,\s*[A-Z_]+,\s*"([^"\n]+)"', source)
        known = {}
        for path in (ROOT / "crawl-ref/source/dat/translate/ru").glob("*.txt"):
            known.update(read_db(path, True))
        self.assertGreater(len(labels), 70)
        for label in labels:
            translated = known.get("{status}" + label, known.get(label))
            self.assertIsNotNone(translated, label)
            self.assertRegex(translated, r"[А-Яа-яЁё]", label)

    def test_short_labels_do_not_contain_text_from_adjacent_records(self):
        data = json.loads((ROOT / "localization/ru/static.json").read_text(encoding="utf8"))
        for group, entries in data.items():
            for source, target in entries.items():
                if "\n" not in source:
                    self.assertNotIn("\n", target, (group, source))

    def test_ui_confirmation_keys_remain_real_engine_keys(self):
        data = json.loads((ROOT / "localization/ru/static.json").read_text(encoding="utf8"))
        for source, target in data["ui"].items():
            self.assertEqual(re.findall(r"\[[YyNnQq/]+\]", source),
                             re.findall(r"\[[YyNnQq/]+\]", target), source)

    def test_system_message_fragments_round_trip_with_spaces(self):
        messages = json.loads((ROOT / "localization/ru/system-messages.json").read_text(encoding="utf8"))
        generated = read_db(ROOT / "crawl-ref/source/dat/translate/ru/system.txt", True)
        self.assertEqual(generated, messages)
        self.assertEqual(generated[" Continue?"], " Продолжить?")
        self.assertEqual(generated["Cast: "], "Заклинание: ")

    def test_reviewed_mechanics_match_current_source_and_generated_text(self):
        data = reviewed_descriptions()  # Validates source hashes, references and Lua.
        self.assertEqual(set(data["skills"]), set(read_db(ROOT / "crawl-ref/source/dat/descript/skills.txt")))
        self.assertEqual(set(data["egos"]), set(read_db(ROOT / "crawl-ref/source/dat/descript/egos.txt")))
        for filename, group in data.items():
            generated = read_db(ROOT / f"crawl-ref/source/dat/descript/ru/{filename}.txt")
            for key, entry in group.items():
                self.assertEqual(generated[key], entry["text"], (filename, key))
        for filename in ("items", "skills", "spells", "ability"):
            wiki = json.loads((ROOT / "wiki/ru/reference/descriptions.json").read_text(encoding="utf8"))[filename]
            for key, entry in data[filename].items():
                self.assertEqual(wiki[key]["text"], entry["text"], key)
                if wiki[key]["title"]:
                    page = (ROOT / "wiki/ru/reference" / filename / (key.lower().replace(" ", "-") + ".md")).read_text(encoding="utf8")
                    self.assertIn(entry.get("wiki_text", entry["text"]), page, key)

    def test_token_protection_distinguishes_contexts_and_natural_percentages(self):
        self.assertEqual(tokens("{menu-state}manual"), ["{menu-state}"])
        self.assertEqual(tokens("{adj-e}Human"), ["{adj-e}"])
        self.assertEqual(tokens("20% chance, 30% faster"), [])
        self.assertEqual(tokens("chance: %4.1f; %+d; %c"), ["%+d", "%4.1f", "%c"])

    def test_fragment_whitespace_survives_the_generated_database(self):
        data = json.loads((ROOT / "localization/ru/static.json").read_text(encoding="utf8"))
        generated = read_db(ROOT / "crawl-ref/source/dat/translate/ru/static.txt", True)
        for group in data.values():
            for source, target in group.items():
                leading = re.match(r"^\s*", source).group()
                trailing = re.search(r"\s*$", source).group()
                for value in (target, generated.get(source, target)):
                    if leading:
                        self.assertTrue(value.startswith(leading), repr(source))
                    if trailing:
                        self.assertTrue(value.endswith(trailing), repr(source))
        self.assertEqual(generated[" and "], " и ")
        self.assertEqual(generated[", and "], " и ")

    def test_system_messages_preserve_substitutions(self):
        messages = json.loads((ROOT / "localization/ru/system-messages.json").read_text(encoding="utf8"))
        for source, target in messages.items():
            self.assertTrue(message_syntax_matches(source, target), source)
            # Some translations consist solely of substituted names and
            # punctuation ("@Arg1@: @arg2@") or coordinate/key hints.
            prose = re.sub(r"\b(?:Enter|Esc|Space|Shift|Ctrl|Alt|Tab|Backspace|R-Click|L-Click)\b", "", TOKEN.sub("", target), flags=re.I)
            if re.search(r"[A-Za-z]{2}", prose):
                self.assertRegex(target, r"[А-Яа-яЁё]", source)

    def test_web_controls_keep_protocol_values_and_hotkeys(self):
        class Controls(HTMLParser):
            def __init__(self):
                super().__init__()
                self.controls = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag not in ("input", "button", "label"):
                    return
                keys = ["id", "name", "type", "for", "data-hotkey", "data-sync-id"]
                if tag == "input" and attrs.get("type") not in ("submit", "button"):
                    keys.append("value")
                self.controls.append([tag, {k: attrs[k] for k in keys if k in attrs}])

        fixtures = json.loads((ROOT / "localization/ru/web-controls.json").read_text(encoding="utf8"))
        for filename, expected in fixtures.items():
            parser = Controls()
            parser.feed((ROOT / "crawl-ref/source/webserver" / filename).read_text(encoding="utf8"))
            self.assertEqual(parser.controls, expected, filename)

    def test_catalog_covers_every_selected_upstream_key(self):
        data = json.loads((ROOT / "localization/ru/static.json").read_text(encoding="utf8"))
        for filename in STATIC_FILES:
            source = read_db(ROOT / f"crawl-ref/source/dat/translate/{filename}.txt", True)
            self.assertFalse(set(source) - set(data[filename]), filename)
            for key in source:
                value = data[filename][key]
                self.assertTrue(value.strip(), (filename, key))
                self.assertEqual(tokens(key), tokens(value), (filename, key))
                self.assertNotRegex(value, r"ZX[PQ]\d{4}[PQ]XZ", (filename, key))

    def test_descriptions_preserve_all_commands_and_markup(self):
        for directory, files in (("descript", DESCRIPTION_FILES), ("database", DATABASE_FILES)):
            for filename in files:
                source = read_db(ROOT / f"crawl-ref/source/dat/{directory}/{filename}.txt")
                target = read_db(ROOT / f"crawl-ref/source/dat/{directory}/ru/{filename}.txt")
                self.assertFalse(set(source) - set(target), filename)
                for key, value in source.items():
                    self.assertTrue(target[key].strip(), (filename, key))
                    self.assertEqual(tokens(value), tokens(target[key]), (filename, key))
                    self.assertNotRegex(target[key], r"ZX[PQ]\d{4}[PQ]XZ", (filename, key))

    def test_all_five_tutorials_have_translated_prose(self):
        target = read_db(ROOT / "crawl-ref/source/dat/descript/ru/tutorial.txt")
        for lesson in range(1, 6):
            prefix = f"tutorial{lesson} "
            entries = [value for key, value in target.items() if key.startswith(prefix)]
            self.assertGreater(len(entries), 5)
            for value in entries:
                self.assertRegex(value, r"[А-Яа-яЁё]")

    def test_literal_tutorial_script_messages_are_translated(self):
        messages = read_db(ROOT / "crawl-ref/source/dat/translate/ru/messages.txt", True)
        for path in (ROOT / "crawl-ref/source/dat/des/tutorial").glob("lesson*.des"):
            for literal in re.findall(r'crawl\.mpr\("([^"\n]+)"\)', path.read_text(encoding="utf8")):
                self.assertIn(literal, messages, str(path))
                self.assertRegex(messages[literal], r"[А-Яа-яЁё]")

    def test_canonical_transliterations_and_wiki_descriptions(self):
        terms = json.loads((ROOT / "localization/ru/terms.json").read_text(encoding="utf8"))
        self.assertEqual(terms["species"]["Spriggan"], "Спригган")
        self.assertEqual(terms["species"]["Gnoll"], "Гнолл")
        self.assertEqual(terms["species"]["Barachi"], "Барачи")
        for category, filename in (("species", "species"), ("background", "backgrounds"), ("gods", "gods")):
            descriptions = read_db(ROOT / f"crawl-ref/source/dat/descript/ru/{filename}.txt")
            for english, russian in terms[category].items():
                slug = english.lower().replace(" ", "-")
                page = (ROOT / f"wiki/ru/characters/{category}/{slug}.md").read_text(encoding="utf8")
                self.assertTrue(page.startswith("# " + russian + "\n"))
                self.assertIn(descriptions[english], page)


if __name__ == "__main__":
    unittest.main()
