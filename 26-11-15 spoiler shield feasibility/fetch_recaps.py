"""Fetch each Andor episode's "Plot summary" from Wookieepedia into data/recaps_raw.json.

Wookieepedia text is CC BY-SA; it's used here only as local test context.
Run: py -3.13 fetch_recaps.py
"""
import html
import json
import re
import time
from pathlib import Path

import httpx

HERE = Path(__file__).parent
API = 'https://starwars.fandom.com/api.php'
UA = {'User-Agent': 'spoiler-feasibility-test/0.1 (personal class research)'}


def page_for(c: httpx.Client, title: str) -> str | None:
    """The episode's page name: 'Title (episode)' if it exists, else 'Title'."""
    for name in (f'{title} (episode)', title):
        r = c.get(API, params={'action': 'parse', 'page': name, 'prop': 'sections', 'format': 'json',
                               'redirects': 1}).json()
        if 'parse' in r and any(s['line'] == 'Plot summary' for s in r['parse']['sections']):
            return r['parse']['title']
    return None


def plot_text(c: httpx.Client, page: str) -> str:
    sections = c.get(API, params={'action': 'parse', 'page': page, 'prop': 'sections', 'format': 'json'}).json()
    sections = sections['parse']['sections']
    start = next(s for s in sections if s['line'] == 'Plot summary')
    # The plot summary plus its level-3 subsections, up to the next level-2 heading.
    idxs = [start['index']]
    for s in sections[sections.index(start) + 1:]:
        if int(s['level']) <= int(start['level']):
            break
        idxs.append(s['index'])
    parts = []
    for i in idxs:
        h = c.get(API, params={'action': 'parse', 'page': page, 'prop': 'text', 'section': i,
                               'format': 'json', 'disablelimitreport': 1}).json()['parse']['text']['*']
        h = re.sub(r'<sup.*?</sup>', '', h, flags=re.S)           # reference markers
        h = re.sub(r'<h\d.*?</h\d>', '\n', h, flags=re.S)          # headings
        text = html.unescape(re.sub(r'<[^>]+>', '', h))
        parts.append(re.sub(r'\n{2,}', '\n', text).strip())
        time.sleep(0.3)
    return '\n'.join(p for p in parts if p)


def main() -> None:
    eps = json.loads((HERE / 'data' / 'episodes.json').read_text(encoding='utf-8'))['episodes']
    out = []
    with httpx.Client(headers=UA, timeout=30) as c:
        for e in eps:
            page = page_for(c, e['title'])
            text = plot_text(c, page) if page else ''
            out.append({'order': e['order'], 'code': e['code'], 'title': e['title'], 'page': page, 'plot': text})
            print(f'{e["code"]:6} {e["title"]:28} -> {page!s:34} {len(text.split()):5} words')
    (HERE / 'data' / 'recaps_raw.json').write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
