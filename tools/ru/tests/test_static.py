"""Coverage and syntax gates for static Russian UI/teaching text."""
from pathlib import Path
import json
import re
import sys
import unittest
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/ru"))
from catalog import STATIC_FILES, DESCRIPTION_FILES, DATABASE_FILES, read_db, tokens


class StaticTranslationTests(unittest.TestCase):
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
