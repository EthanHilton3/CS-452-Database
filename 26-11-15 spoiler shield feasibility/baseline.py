"""Keyword baseline: what a non-AI spoiler blocker could do.

Every proper name in the Wookieepedia plot summaries (Kleya, Ghorman, Narkina...) is tagged with the episode it
first appears in. A comment "reveals" the latest first-appearance among the names it mentions. It can't see
events ("he dies"), only names, which is the point of comparing against it.
Run: py -3.13 baseline.py  -> results/pred_keyword.jsonl
"""
import json
import re
from collections import Counter

from llm import HERE

COMMON = {'The', 'A', 'An', 'He', 'She', 'They', 'His', 'Her', 'It', 'In', 'On', 'At', 'As', 'When', 'While', 'After',
          'Before', 'But', 'And', 'Then', 'Meanwhile', 'Later', 'With', 'Once', 'However', 'Back', 'Empire', 'Imperial',
          'Rebellion', 'Rebel', 'Star', 'Wars', 'Andor', 'Cassian', 'Senate', 'Senator', 'Captain', 'Lieutenant',
          'Major', 'Supervisor', 'Officer', 'Colonel', 'Emperor', 'Galactic', 'Force', 'Jedi', 'Imperials', 'Rogue', 'One'}


def main() -> None:
    raw = json.loads((HERE / 'data' / 'recaps_raw.json').read_text(encoding='utf-8'))
    first: dict[str, int] = {}
    counts: Counter = Counter()
    for ep in raw:
        for w in re.findall(r'(?<![.!?]\s)\b[A-Z][a-z]{3,}\b', ep['plot']):
            counts[w] += 1
            first.setdefault(w, ep['order'])
    terms = {w: o for w, o in first.items() if counts[w] >= 3 and w not in COMMON}
    rows = [json.loads(l) for l in (HERE / 'data' / 'comments.jsonl').read_text(encoding='utf-8').splitlines()]
    codes = {e['order']: e['code'] for e in raw}
    preds = []
    for n, r in enumerate(rows):
        hits = {w: o for w, o in terms.items() if re.search(rf'\b{w}\b', r['text'], re.I)}
        latest = max(hits.values(), default=0)
        preds.append({'n': n, 'reveals': codes.get(latest, 'none'), 'rogue_one': bool(re.search(r'rogue one|scarif|jyn', r['text'], re.I)),
                      'confidence': 1.0, 'evidence': ', '.join(w for w, o in hits.items() if o == latest)})
    meta = {'condition': 'keyword', 'model': None, 'terms': len(terms), 'cost_usd': 0}
    (HERE / 'results' / 'pred_keyword.jsonl').write_text(
        json.dumps({'_meta': meta}) + '\n' + ''.join(json.dumps(p) + '\n' for p in preds), encoding='utf-8')
    print(f'keyword baseline: {len(terms)} name terms, {sum(p["reveals"] != "none" for p in preds)} comments flagged')


if __name__ == '__main__':
    main()
