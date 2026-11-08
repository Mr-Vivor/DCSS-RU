#!/usr/bin/env python3
"""Update the wiki from the exact, already activated game commit, without secrets."""
from pathlib import Path
import fcntl
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request

BASE=Path('/srv/dcss-wiki')
MIRROR=Path('/srv/dcss-ru/repository.git')
PATHS=['tools/wiki','tools/ru','wiki/site','wiki/ru/reference/descriptions.json',
       'localization/ru','crawl-ref/source/rltiles','crawl-ref/source/dat/mons',
       'crawl-ref/source/dat/species','crawl-ref/source/dat/jobs',
       'crawl-ref/source/dat/descript/ru','crawl-ref/source/spl-data.h','crawl-ref/source/art-data.txt',
       'crawl-ref/source/branch-data.h','crawl-ref/source/item-prop.cc','crawl-ref/source/book-data.h',
       'crawl-ref/source/ability.cc','crawl-ref/source/tilepick.cc','crawl-ref/source/mon-spell.h']


def run(args,**kwargs):
    result=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kwargs)
    if result.returncode:
        raise RuntimeError('Command failed: '+str(args[0])+'\n'+'\n'.join(result.stdout.splitlines()[-15:]))
    return result.stdout


def main():
    os.umask(0o022)
    shared=BASE/'shared'
    with (shared/'sync.lock').open('w') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return
        sha=Path('/srv/dcss-ru/current/REVISION').read_text().strip()
        if not re.fullmatch('[0-9a-f]{40}',sha):raise RuntimeError('Invalid active game revision')
        cursor=shared/'sync-revision'
        if cursor.exists() and cursor.read_text().strip()==sha:return
        git=['git','-c','safe.directory='+str(MIRROR),'--git-dir='+str(MIRROR)]
        exists=subprocess.run(git+['cat-file','-e',sha+':tools/wiki/build.py'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if exists.returncode:
            print('Active game commit predates the wiki builder; leaving the wiki unchanged.')
            return
        staging=shared/'sync-work'
        staging.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='build-',dir=staging) as scratch:
            scratch=Path(scratch);source=scratch/'source';source.mkdir()
            archive=scratch/'source.tar'
            with archive.open('wb') as stream:
                subprocess.run(git+['archive','--format=tar',sha,'--']+PATHS,stdout=stream,check=True)
            with tarfile.open(archive) as bundle:
                for member in bundle.getmembers():
                    if not (member.isfile() or member.isdir()):raise RuntimeError('Unexpected link in wiki source archive')
                bundle.extractall(source,filter='data')
            output=scratch/'output'
            run(['python3',str(source/'tools/wiki/build.py'),'--output',str(output),'--revision',sha])
            # Main article text is updated before new file metadata is uploaded.
            summary=run(['php',str(BASE/'bin/update-content.php'),'--memory-limit=512M',str(output/'pages.json')])
            print(summary.splitlines()[-1])
            images=run(['php','maintenance/run.php','importImages',str(output/'sprites'),
                '--user=Vivor','--comment=Спрайты активной версии русского форка','--memory-limit=512M'],cwd=BASE/'current')
            print('\n'.join(images.splitlines()[-2:]))
            for name in ('wiki-logo.svg','favicon.png','theme.css'):
                shutil.copyfile(output/name,shared/'resources'/name)
            shutil.copyfile(output/'report.json',shared/'build-report.json')
            shutil.copyfile(output/'search-extracts.json',shared/'search-extracts.json')
            data=urllib.parse.urlencode(dict(action='purge',format='json',titles='Заглавная страница|Виды|Предыстории|Боги|Заклинания|Существа|Предметы|Навыки|Артефакты')).encode()
            request=urllib.request.Request('https://wiki.dungeoncrawl.ru/api.php',data=data,headers={'User-Agent':'DCSS-RU-wiki-sync/1.0'})
            with urllib.request.urlopen(request,timeout=30) as response:json.load(response)
            cursor.write_text(sha+'\n')
            print('Wiki synchronized with active game:',sha)


if __name__=='__main__':main()
