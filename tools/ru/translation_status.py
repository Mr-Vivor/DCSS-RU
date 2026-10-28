"""Measure Russian text availability, without treating it as gameplay completion.

Source prose word counts weight entries by size. Inherited translations may be
stale; Russian text being present is not an assertion that it was reviewed.
Source C++/Lua/JS assembly sites and frequency of gameplay messages are outside
this inventory, so the combined percentage is not a whole-game completion rate.
"""
from pathlib import Path
import argparse
import json
import re

from catalog import ROOT, STATIC_FILES, read_db
from message_catalog import catalog as message_catalog, translations

FLAVOUR = ('monspeak', 'monspell', 'monflee', 'godspeak', 'miscname',
           'decorlines', 'shout', 'insult', 'wpnnoise', 'miscast', 'gizmo', 'graffiti')


def database(path):
    """Database source loader uses the last definition of a duplicate key."""
    if not path.exists():
        return {}
    result = {}
    for block in path.read_text(encoding='utf8').split('%%%%')[1:]:
        lines = [line for line in block.splitlines() if not line.startswith('#')]
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines:
            result[lines[0].strip()] = '\n'.join(lines[1:]).strip()
    return result


def prose_words(value):
    value = re.sub(r'\{\{.*?\}\}|\[\[.*?\]\]|@[^@]+@|<[^>]+>|\{[^}]+\}', '', value, flags=re.S)
    value = re.sub(r'^w:\d+\s*$', '', value, flags=re.M)
    return len(re.findall(r"[A-Za-z]+(?:['-][A-Za-z]+)*", value))


def has_russian(value):
    return bool(re.search('[А-Яа-яЁё]', value))


def measure(source, russian, reviewed=None):
    reviewed = reviewed or {}
    rows = [(key, value, prose_words(value)) for key, value in source.items()]
    rows = [(key, value, words) for key, value, words in rows if words]
    present = [(key, value, words) for key, value, words in rows if has_russian(russian.get(key, ''))]
    checked = [(key, value, words) for key, value, words in rows if key in reviewed]
    all_words = sum(row[2] for row in rows)
    translated_words = sum(row[2] for row in present)
    return dict(entries=len(rows), with_russian=len(present),
                entry_percent=round(100*len(present)/len(rows), 1) if rows else None,
                source_prose_words=all_words, source_words_with_russian=translated_words,
                word_percent=round(100*translated_words/all_words, 1) if all_words else None,
                fingerprinted_description_entries=len(checked),
                fingerprinted_description_words=sum(row[2] for row in checked))


def report():
    dat = ROOT / 'crawl-ref/source/dat'
    reviewed = json.loads((ROOT / 'localization/ru/descriptions.json').read_text(encoding='utf8'))
    descriptions = {}
    for path in sorted((dat / 'descript').glob('*.txt')):
        descriptions[path.stem] = measure(database(path), database(path.parent / 'ru' / path.name), reviewed.get(path.stem))
    flavour = {name: measure(database(dat / 'database' / (name+'.txt')),
                             database(dat / 'database/ru' / (name+'.txt')))
               for name in FLAVOUR}
    known = translations()
    keys = {entry['source'] for entry in message_catalog()}
    for name in STATIC_FILES:
        keys.update(read_db(dat / 'translate' / (name+'.txt'), True))
    keys = {key for key in keys if not key.startswith(('GENERATE:', 'PREGENERATE:'))}
    system = measure({key:key for key in keys}, known)
    # These categories partition the files; do not count key names as prose.
    def total(rows):
        sums = {field:sum(row[field] for row in rows) for field in
                ('entries','with_russian','source_prose_words','source_words_with_russian',
                 'fingerprinted_description_entries','fingerprinted_description_words')}
        sums['entry_percent'] = round(100*sums['with_russian']/sums['entries'],1)
        sums['word_percent'] = round(100*sums['source_words_with_russian']/sums['source_prose_words'],1)
        return sums
    return dict(
        note='Availability of Russian text in explicitly inventoried files; includes inherited/draft translations. Not whole-game completion or runtime coverage.',
        method='Unique entries, weighted by English source prose words; code, markup and references excluded. Random-name pools, source-code assembly and gameplay frequency are not measured.',
        selected_system_catalogs=system, descriptions=descriptions, flavour_databases=flavour,
        description_total=total(list(descriptions.values())),
        flavour_total=total(list(flavour.values())),
        tracked_corpus_total=total([system,*descriptions.values(),*flavour.values()]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()
    result = report()
    if args.json:
        args.json.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    for name in ('selected_system_catalogs','description_total','flavour_total','tracked_corpus_total'):
        print(name, result[name])
    for name,row in result['descriptions'].items():
        print(name, f"{row['with_russian']}/{row['entries']}", f"words {row['word_percent']}%",
              f"fingerprinted descriptions {row['fingerprinted_description_entries']}")


if __name__=='__main__':
    main()
