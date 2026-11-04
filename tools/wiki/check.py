"""One fast publication check for links, sprite files and runtime placeholders."""
from pathlib import Path
import json
import re
import sys


def check(output):
    payload=json.loads((output/'pages.json').read_text(encoding='utf8'))
    pages=payload['pages'];assets=payload['assets'];problems=[]
    if sum(payload['counts'].values())<2500:problems.append('Unexpectedly small wiki catalogue')
    for title,row in pages.items():
        for target in re.findall(r'\[\[([^\]|#]+)',row['text']):
            if target.startswith(('Категория:','Служебная:')):continue
            if target.startswith('Файл:'):
                if target[5:] not in assets:problems.append((title,'missing sprite',target))
            elif target not in pages:problems.append((title,'missing link',target))
        if re.search(r'@[^@\n]+@|#Lua#|\{\{',row['text']):problems.append((title,'unrendered runtime substitution'))
        if row['kind']=='article' and not re.search('[А-Яа-яЁё]',title):problems.append((title,'untranslated title'))
    for name in assets:
        if not (output/'sprites'/name).is_file():problems.append(('missing bundled image',name))
    if problems:
        raise SystemExit(json.dumps(problems[:30],ensure_ascii=False,indent=2))
    print('Wiki bundle OK:',len(pages),'pages,',len(assets),'sprite files; internal links and runtime text checked.')


if __name__=='__main__':check(Path(sys.argv[1]))
