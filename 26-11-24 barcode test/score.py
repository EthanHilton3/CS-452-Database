"""Step 5: score the barcode test. Run: .venv\\Scripts\\python.exe -I score.py [answers.json path]  -> results/SCORES.md"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import data

N_FIELDS_PER_TYPE = {'game': ('name', 'edition', 'format', 'platform')}  # platform only makes sense for games
DEFAULT_FIELDS = ('name', 'edition', 'format')


def pct(a: int, b: int) -> str:
    return f'{a}/{b} ({round(100 * a / b)}%)' if b else f'{a}/0 (n/a)'


def main() -> None:
    ans = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')) if len(sys.argv) > 1 else data.load_answers()
    rows = data.rows()
    n = len(rows)
    judged = [r for r in rows if data.is_done(r, ans.get(r['photo'], {}))]
    L = [f'# Barcode scores ({len(judged)} of {n} photos fully judged)', '']

    # 1. reading
    by_method = defaultdict(int)
    for r in rows:
        by_method[r['method'] if r['digits'] else 'unreadable'] += 1
    valid = [r for r in rows if r['digits'] and r['checksum_valid']]
    non_ai = [r for r in rows if r['method'] in ('decoder', 'retry')]
    L += ['## 1. Reading the barcode from the photo', '',
          '| Measure | Result |', '|---|---|',
          f"| Decoder on the full photo | {pct(by_method['decoder'], n)} |",
          f"| Decoder after retries (contrast, resize, crops) | {pct(by_method['retry'], n)} |",
          f"| Model read the digits (gpt-6-luna) | {pct(by_method['model-read'], n)} |",
          f"| No digits at all | {pct(by_method['unreadable'], n)} |",
          f"| **Decode rate, decoder only** (full + retry) | {pct(len(non_ai), n)} |",
          f"| **Decode rate, with model fallback** | {pct(sum(1 for r in rows if r['digits']), n)} |",
          f"| **Checksum-valid** (of all photos) | {pct(len(valid), n)} |",
          f"| Checksum-valid (of photos that produced digits) | {pct(len(valid), sum(1 for r in rows if r['digits']))} |"]
    mr = [r for r in rows if r['method'] == 'model-read' and r['digits']]
    if mr:
        yes = sum(1 for r in mr if ans.get(r['photo'], {}).get('digits_match') == 'yes')
        no = sum(1 for r in mr if ans.get(r['photo'], {}).get('digits_match') == 'no')
        L.append(f"| Model-read digits that match the photo (my check) | {pct(yes, yes + no)} of {len(mr)} read; {len(mr) - yes - no} unchecked |")
    L.append('')
    L.append('Photos by how the barcode was obtained: ' + ', '.join(
        f"{r['photo'][-4:]} {r['method'] if r['digits'] else 'none'}{'' if not r['digits'] or r['checksum_valid'] else ' (bad checksum)'}" for r in rows))
    L.append('')

    # 2. lookup
    looked = [r for r in rows if data.looked_up(r)]
    hits = [r for r in looked if r['lookup'].get('hit')]
    L += ['## 2. Catalog lookup (UPCitemdb free trial endpoint)', '',
          '| Measure | Result |', '|---|---|',
          f"| Looked up (valid checksum only) | {len(looked)} of {n} |",
          f"| **Lookup hit rate** (of looked up) | {pct(len(hits), len(looked))} |",
          f"| Hit rate counting every photo | {pct(len(hits), n)} |"]
    verd = defaultdict(int)
    for r in hits:
        verd[ans.get(r['photo'], {}).get('verdict') or 'unjudged'] += 1
    good = verd['right'] + verd['close']
    L += [f"| Hits judged right | {pct(verd['right'], len(hits))} |", f"| Hits judged close | {pct(verd['close'], len(hits))} |",
          f"| Hits judged wrong or not found | {pct(verd['wrong'] + verd['not_found'], len(hits))} |",
          f"| **Hits that are right or close** | {pct(good, len(hits))} |",
          f"| **End to end** (right or close, of all {n} photos) | {pct(good, n)} |"]
    if verd['unjudged']:
        L.append(f"| Hits not judged yet | {verd['unjudged']} |")
    L.append('')

    # 3. by type
    L += ['## 3. By item type (my labels)', '',
          '| Type | Photos | Decoded & valid | Looked up | Hits | Hit rate | Right | Close | Wrong / not found | Right or close (of hits) | End to end (of photos) |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    types = data.TYPES + ['unlabeled']
    for t in types:
        rs = [r for r in rows if (ans.get(r['photo'], {}).get('type') or 'unlabeled') == t]
        if not rs:
            continue
        lk = [r for r in rs if data.looked_up(r)]
        ht = [r for r in lk if r['lookup'].get('hit')]
        v = [ans.get(r['photo'], {}).get('verdict') for r in ht]
        rt, cl = v.count('right'), v.count('close')
        L.append(f"| {t} | {len(rs)} | {sum(1 for r in rs if r['digits'] and r['checksum_valid'])} | {len(lk)} | {len(ht)} | {pct(len(ht), len(lk))} | "
                 f"{rt} | {cl} | {v.count('wrong') + v.count('not_found')} | {pct(rt + cl, len(ht))} | {pct(rt + cl, len(rs))} |")
    L.append('')

    # 4. fields
    L += ['## 4. Fields the API gave us (hits only)', '',
          'Heuristic text match on title, brand, description and category (see lookup.py). "name" is the API title; edition, format and platform are only counted when a keyword appears.', '',
          '| Photo | Type | name | edition | format | platform | Useful fields |', '|---|---|---|---|---|---|---|']
    tot_have = tot_need = 0
    for r in hits:
        t = ans.get(r['photo'], {}).get('type') or 'unlabeled'
        need = N_FIELDS_PER_TYPE.get(t, DEFAULT_FIELDS)
        f = r['lookup']['fields']
        have = sum(1 for k in need if f.get(k))
        tot_have, tot_need = tot_have + have, tot_need + len(need)
        cell = lambda k: (f.get(k) or '-') if k in need else 'n/a'
        L.append(f"| {r['photo'][-4:]} | {t} | {'yes' if f.get('name') else '-'} | {cell('edition')} | {cell('format')} | {cell('platform')} | {have}/{len(need)} |")
    L += ['', f'Across all hits: {pct(tot_have, tot_need)} of the fields we need were present (platform counted for games only).', '']

    # 5. AI fallback
    L += ['## 5. Which items would have needed the AI fallback', '',
          'An item needs the fallback (the AI reads the box) when the barcode path did not end in a right-or-close release.', '',
          '| Photo | Type | Why |', '|---|---|---|']
    need_ai = 0
    for r in rows:
        a = ans.get(r['photo'], {})
        t = a.get('type') or 'unlabeled'
        why = None
        if not r['digits']:
            why = 'no readable barcode'
        elif not r['checksum_valid']:
            why = 'digits read but checksum invalid'
        elif not r['lookup'].get('hit'):
            why = 'lookup miss'
        elif a.get('verdict') in ('wrong', 'not_found'):
            why = 'lookup hit was wrong'
        elif not a.get('verdict'):
            why = None
            L.append(f"| {r['photo'][-4:]} | {t} | not judged yet |")
            continue
        elif a.get('verdict') == 'close':
            L.append(f"| {r['photo'][-4:]} | {t} | (close: the barcode path works but a detail needs the AI or a question) |")
            continue
        if why:
            need_ai += 1
            extra = ' (decoder failed, model read it)' if r['method'] == 'model-read' and r['checksum_valid'] and why != 'no readable barcode' else ''
            L.append(f"| {r['photo'][-4:]} | {t} | {why}{extra} |")
    close_n = sum(1 for r in rows if ans.get(r['photo'], {}).get('verdict') == 'close')
    rescued = [r for r in rows if r['method'] == 'model-read' and r['checksum_valid']]
    rescued_good = sum(1 for r in rescued if ans.get(r['photo'], {}).get('verdict') in ('right', 'close'))
    no_model = sum(1 for r in rows if r['method'] in ('decoder', 'retry') and ans.get(r['photo'], {}).get('verdict') in ('right', 'close'))
    L += ['', f'**Needed the AI fallback: {pct(need_ai, n)}** ({pct(need_ai + close_n, n)} if "close" results also count as needing the AI for the missing detail).',
          f'- The zxing decoder failed on {sum(1 for r in rows if r["method"] not in ("decoder", "retry"))} photos. The model read a valid code on {len(rescued)} of them, and {rescued_good} of those were right or close.',
          f'- End to end **without** the model fallback (decoder + lookup only): {pct(no_model, n)} right or close. With it: {pct(good, n)}.', '']

    # 6. cost + limits
    usage = [json.loads(l) for l in (HERE / 'results' / 'usage.jsonl').read_text(encoding='utf-8').splitlines()] if (HERE / 'results' / 'usage.jsonl').exists() else []
    live = sum(1 for r in looked if not r['lookup'].get('from_cache'))
    rem = [r['lookup']['rate_headers'].get('X-RateLimit-Remaining') for r in looked if r['lookup'].get('rate_headers')]
    L += ['## 6. Cost and free-tier limits', '',
          f"- OpenAI: {len(usage)} calls, ${sum(u['cost_usd'] for u in usage):.4f} total (results/usage.jsonl).",
          f"- UPCitemdb: {len(looked)} lookups, cached to cache/upcitemdb/. The trial endpoint reported a limit of {looked[0]['lookup']['rate_headers'].get('X-RateLimit-Limit', '?') if looked else '?'} per day; "
          f"remaining after the run: {rem[-1] if rem else '?'}. Requests were spaced 11 s apart to stay under the per-minute cap.", '']
    out = HERE / 'results' / ('SCORES.md' if len(sys.argv) == 1 else 'SCORES.test.md')
    out.write_text('\n'.join(L), encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
