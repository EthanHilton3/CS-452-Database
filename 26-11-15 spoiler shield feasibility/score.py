"""Score every results/pred_*.jsonl against labels.csv and write results/SCORES.md.

The product question is: for a viewer who has watched up to episode p, is this comment hidden?
We simulate viewers at every position from S1E1 to S2E11 (none of them has seen Rogue One) and count, over all
(comment, viewer) pairs:
  caught      real spoilers that got hidden            (higher is better)
  false blur  safe comments that got hidden anyway      (lower is better)
Run: py -3.13 score.py
"""
import csv
import json
from collections import Counter

from llm import HERE

ORDER = {e['code']: e['order'] for e in json.loads((HERE / 'data' / 'episodes.json').read_text(encoding='utf-8'))['episodes']}
AFTER_SHOW = 25
POSITIONS = range(1, 24)  # watched through S1E1 ... S2E11
GENERAL = {n for n, l in enumerate((HERE / 'data' / 'comments.jsonl').read_text(encoding='utf-8').splitlines())
           if json.loads(l)['thread_kind'] == 'general'}


def order(reveals: str, rogue_one: bool) -> int:
    return AFTER_SHOW if rogue_one else ORDER.get(reveals, 0)


def load_labels():
    with open(HERE / 'labels.csv', encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    labels = {int(r['n']): order(r['label'], r['outside'].strip() == 'rogue_one') for r in rows}
    reviewed = sum(r['status'].strip().lower() == 'labeled' for r in rows)
    return labels, reviewed, len(rows)


def score(labels: dict[int, int], preds: dict[int, int]) -> dict:
    spoil = caught = safe = blur = 0
    for n, t in labels.items():
        p = preds[n]
        for pos in POSITIONS:
            if t > pos:
                spoil += 1
                caught += p > pos
            else:
                safe += 1
                blur += p > pos
    any_t = {n for n, t in labels.items() if t > 0}
    any_p = {n for n, p in preds.items() if p > 0}
    exact = sum(labels[n] == preds[n] for n in labels)
    near = sum(abs(labels[n] - preds[n]) <= 1 or (labels[n] == preds[n]) for n in labels)
    late = sum(preds[n] < labels[n] for n in labels)  # said it reveals less than it does: the dangerous direction
    return {'caught': caught / spoil, 'false_blur': blur / safe, 'pairs': spoil + safe,
            'flag_recall': len(any_t & any_p) / len(any_t), 'flag_precision': len(any_t & any_p) / max(len(any_p), 1),
            'exact': exact / len(labels), 'within_1': near / len(labels), 'under_called': late}


def main() -> None:
    labels, reviewed, total = load_labels()
    lines = ['# Spoiler classifier scores', '',
             f'Labels: {total} comments, **{reviewed} reviewed by Ethan**, {total - reviewed} still Claude drafts'
             + (' (PROVISIONAL)' if reviewed < total else ''), '',
             f'Simulated viewers at positions S1E1..S2E11 = {len(POSITIONS)} positions x {total} comments.', '',
             '| Run | Spoilers caught | Safe comments blurred | Spoiler/no-spoiler recall | precision | Exact episode | Within 1 ep | Under-called | Cost | Cost per 1k comments |',
             '|---|---|---|---|---|---|---|---|---|---|']
    misses = {}
    general_rows = []
    for path in sorted((HERE / 'results').glob('pred_*.jsonl')):
        raw = path.read_text(encoding='utf-8').splitlines()
        meta = json.loads(raw[0])['_meta']
        preds_raw = {p['n']: p for p in map(json.loads, raw[1:])}
        preds = {n: order(p['reveals'], p['rogue_one']) for n, p in preds_raw.items()}
        s = score(labels, preds)
        cost = meta.get('cost_usd', 0) or 0
        name = path.stem.removeprefix('pred_')
        lines.append(f'| {name} | {s["caught"]:.0%} | {s["false_blur"]:.0%} | {s["flag_recall"]:.0%} | {s["flag_precision"]:.0%} | '
                     f'{s["exact"]:.0%} | {s["within_1"]:.0%} | {s["under_called"]} | ${cost:.4f} | ${cost / total * 1000:.3f} |')
        g = score({n: labels[n] for n in GENERAL}, {n: preds[n] for n in GENERAL})
        general_rows.append(f'| {name} | {g["caught"]:.0%} | {g["false_blur"]:.0%} | {g["exact"]:.0%} | {g["under_called"]} |')
        misses[name] = [(n, labels[n], preds[n], preds_raw[n].get('evidence', '')) for n in labels
                        if preds[n] < labels[n]]
    lines += ['', f'## General threads only ({len(GENERAL)} comments)', '',
              'The realistic case: browsing r/andor (not an episode megathread) partway through the show.', '',
              '| Run | Spoilers caught | Safe comments blurred | Exact episode | Under-called |', '|---|---|---|---|---|']
    lines += general_rows
    lines += ['', 'Under-called = the model said the comment reveals an earlier episode than it does (or nothing), '
              'so some viewers would see a spoiler.', '']
    for name, m in misses.items():
        if not m:
            continue
        lines.append(f'<details><summary>{name}: {len(m)} under-called</summary>\n')
        lines += [f'- #{n}: label {t}, predicted {p} — {ev}' for n, t, p, ev in m]
        lines.append('\n</details>\n')
    (HERE / 'results' / 'SCORES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines[:8 + len(misses)]))


if __name__ == '__main__':
    main()
