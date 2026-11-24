"""Step 2-3: look up every checksum-valid barcode on UPCitemdb's free trial endpoint (no key, ~100/day, ~6/min).
Run: .venv\\Scripts\\python.exe -I lookup.py

Every response is cached to cache/upcitemdb/<gtin13>.json, the way the app's catalog_cache table will work, so
re-running costs no quota. No key is used here; if a paid key ever exists, read it from the environment
(UPCITEMDB_KEY) or secrets.json, never from a committed file. Writes results/lookup.jsonl."""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import gtin

CACHE = HERE / 'cache' / 'upcitemdb'
URL = 'https://api.upcitemdb.com/prod/trial/lookup?upc='
GAP_SECONDS = 11  # trial limit is about 6 requests a minute
HEADERS = {'User-Agent': 'barcode-feasibility-test', 'Accept': 'application/json'}  # generic: nothing personal

FORMAT_RE = re.compile(r'\b(blu-?ray|dvd|4k|uhd|ultra hd|cd|vinyl|lp|cassette|hardcover|paperback|digital|disc)\b', re.I)
PLATFORM_RE = re.compile(r'\b(playstation ?\d?|ps ?[1-5]|xbox( one| 360| series [xs])?|nintendo (switch( 2)?|ds|3ds|wii u|64|gamecube)|switch( 2)?|'
                         r'wii( u)?|game ?cube|game ?boy( advance)?|gba|sega (genesis|saturn|dreamcast)|mega drive|pc game)\b', re.I)
EDITION_RE = re.compile(r"\b(steelbook|collector'?s|limited|special edition|extended|deluxe|ultimate|anniversary|remaster(ed)?|"
                        r"director'?s cut|unrated|criterion|game of the year|goty|edition)\b", re.I)


def fetch(gtin13: str, upc: str) -> dict:
    """Return the cache record for this code, calling the API only if it is not cached yet."""
    path = CACHE / f'{gtin13}.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8')) | {'from_cache': True}
    req = urllib.request.Request(URL + urllib.parse.quote(upc), headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status, body, hdr = r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        status, body, hdr = e.code, e.read(), e.headers
    rec = {'key': gtin13, 'queried_as': upc, 'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
           'http_status': status,
           'rate_headers': {k: v for k, v in hdr.items() if k.lower().startswith(('x-ratelimit', 'retry'))},
           'response': json.loads(body or b'{}')}
    if status == 200 or rec['response'].get('code') in ('OK', 'INVALID_UPC'):  # 429/5xx are not cached: retry later
        CACHE.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec, indent=1, ensure_ascii=False), encoding='utf-8')
    return rec | {'from_cache': False}


def fields_present(item: dict) -> dict:
    """Which of name / edition / format / platform could we fill from this hit? Heuristic text match, shown in the review."""
    text = ' '.join(str(item.get(k) or '') for k in ('title', 'brand', 'description', 'category', 'model'))
    text = re.sub(r'[^ -~]', ' ', text)  # the API returns stray non-ASCII like a broken (R) sign; do not let it break word matches
    m = {'name': item.get('title') or None, 'edition': EDITION_RE.search(text), 'format': FORMAT_RE.search(text),
         'platform': PLATFORM_RE.search(text)}
    return {k: (v if isinstance(v, str) or v is None else v.group(0)) for k, v in m.items()}


def main() -> None:
    decoded = [json.loads(l) for l in (HERE / 'results' / 'decode.jsonl').read_text(encoding='utf-8').splitlines()]
    rows, live = [], 0
    for d in decoded:
        row = {'photo': d['photo'], 'digits': d['digits'], 'looked_up': False}
        if d['digits'] and d['checksum_valid']:
            g = gtin.to_gtin13(d['digits'])
            if live and not CACHE.joinpath(f'{g}.json').exists():
                time.sleep(GAP_SECONDS)
            rec = fetch(g, d['digits'])
            live += 0 if rec['from_cache'] else 1
            resp = rec['response']
            items = resp.get('items') or []
            hit = rec['http_status'] == 200 and resp.get('code') == 'OK' and bool(items)
            it = items[0] if hit else {}
            row |= {'looked_up': True, 'gtin13': g, 'from_cache': rec['from_cache'], 'http_status': rec['http_status'],
                    'api_code': resp.get('code'), 'api_message': resp.get('message'), 'hit': hit, 'n_items': len(items),
                    'title': it.get('title'), 'brand': it.get('brand'), 'category': it.get('category'), 'model': it.get('model'),
                    'description': (it.get('description') or '')[:400], 'rate_headers': rec['rate_headers']}
            row['fields'] = fields_present(it) if hit else {}
            row['n_fields'] = sum(1 for v in row['fields'].values() if v)
            print(f"{d['photo']} {d['digits']} http={rec['http_status']} {'HIT ' if hit else 'MISS'} cache={rec['from_cache']} {it.get('title') or resp.get('message') or ''}")
            if rec['http_status'] == 429:
                print('Rate limited (429). Stopping; re-run later, cached codes cost nothing.', rec['rate_headers'])
                rows.append(row)
                break
        rows.append(row)
    (HERE / 'results' / 'lookup.jsonl').write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
