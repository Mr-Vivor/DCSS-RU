"""Fetch attributed source revisions, without importing unscreened old mechanics."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request


def fetch(titles, output):
    records = {}
    for offset in range(0, len(titles), 20):
        params = dict(action="query", format="json", prop="revisions", redirects=1,
                      rvprop="ids|timestamp|content", titles="|".join(titles[offset:offset + 20]))
        url = "http://crawl.chaosforge.org/api.php?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": "DCSS-RU-wiki/1.0 (https://github.com/Mr-Vivor/DCSS-RU)"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=35) as response:
                    data = json.load(response)
                break
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(2)
        for page in data["query"]["pages"].values():
            if "missing" in page:
                continue
            revision = page["revisions"][0]
            text = revision["*"]
            records[page["title"]] = dict(title=page["title"], revision=revision["revid"],
                timestamp=revision["timestamp"], text=text,
                sha256=hashlib.sha256(text.encode()).hexdigest(),
                url="http://crawl.chaosforge.org/index.php?" + urllib.parse.urlencode({"title": page["title"], "oldid": revision["revid"]}))
        print("Fetched community sources:", min(offset + 20, len(titles)), "/", len(titles), flush=True)
        if offset + 20 < len(titles):
            time.sleep(0.5)
    output.write_text(json.dumps({"site": "CrawlWiki", "license": "GNU FDL", "pages": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("titles", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    fetch(json.loads(args.titles.read_text(encoding="utf8")), args.output)
