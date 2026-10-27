from pathlib import Path
import importlib.util
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("ru_generate", ROOT / "tools/ru/generate.py")
generate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate)


class SharedRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entities = generate.load_entities()
        cls.entries = generate.game_entries(cls.entities)
        cls.by_name = {entity["en"]: entity for entity in cls.entities}

    def test_dragon_forms_are_linguistically_correct(self):
        self.assertEqual(self.by_name["ice dragon"]["forms"]["singular"], {
            "nom": "ледяной дракон", "gen": "ледяного дракона", "dat": "ледяному дракону",
            "acc": "ледяного дракона", "ins": "ледяным драконом", "prep": "ледяном драконе"})

    def test_dependent_genitive_does_not_change(self):
        self.assertEqual(self.by_name["potion of curing"]["forms"]["singular"]["ins"],
                         "зельем исцеления")

    def test_feminine_adjective_uses_accusative(self):
        self.assertEqual(self.by_name["bat"]["forms"]["singular"]["acc"], "летучую мышь")

    def test_wiki_and_game_use_the_same_canonical_name(self):
        wiki = json.loads((ROOT / "wiki/ru/entities.json").read_text(encoding="utf8"))
        for entity in self.entities:
            title = wiki[entity["id"]]["title"]
            value = re.sub(r"^\{[^}]*\}", "", self.entries[entity["en"]])
            self.assertEqual(title, value.capitalize())

    def test_count_classes_do_not_omit_twenty_one(self):
        key = "@num@ scrolls of teleportation"
        self.assertEqual(self.entries["{one}" + key], "@num@ свиток телепортации")
        self.assertEqual(self.entries["{few}" + key], "@num@ свитка телепортации")
        self.assertEqual(self.entries["{many}" + key], "@num@ свитков телепортации")

    def test_every_generated_file_is_current(self):
        for path, content in generate.outputs(self.entities).items():
            self.assertEqual(path.read_text(encoding="utf8"), content, str(path))

    def test_message_parameters_are_preserved(self):
        path = ROOT / "crawl-ref/source/dat/translate/ru/messages.txt"
        for block in path.read_text(encoding="utf8").split("%%%%"):
            rows = [row for row in block.splitlines() if row and not row.startswith("#")]
            if len(rows) < 2:
                continue
            # Initial capitalisation controls rendered sentence case, not identity.
            source = sorted(p.lower() for p in re.findall(r"@([^@]+)@", rows[0]))
            target = sorted(p.lower() for p in re.findall(r"@([^@]+)@", "\n".join(rows[1:])))
            self.assertEqual(source, target, rows[0])


if __name__ == "__main__":
    unittest.main()
