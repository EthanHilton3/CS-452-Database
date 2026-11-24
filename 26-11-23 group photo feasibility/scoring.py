"""Shared by review.py (live summary) and score.py (SCORES.md). Reads results/items_*.jsonl and answers.json."""
import json
import random
from pathlib import Path

HERE = Path(__file__).parent
RESULTS = HERE / 'results'
ANSWERS = HERE / 'answers.json'
WHOLE = ['luna_1024', 'luna_2048', 'sol_2048']
TILED = ['luna_tiled', 'sol_tiled']
SETUP_FILES = WHOLE + TILED
LABELS = {'luna_1024': 'Luna 1024 px', 'luna_2048': 'Luna 2048 px', 'sol_2048': 'Sol 2048 px',
          'luna_tiled': 'Luna 2x2 tiles', 'sol_tiled': 'Sol 2x2 tiles'}
VERDICTS = {'right': 'Right', 'close': 'Close', 'wrong': 'Wrong / not there', 'dup': 'Duplicate'}


def blind_order() -> list[str]:
    """Fixed shuffle so tabs A/B/C don't reveal which model is which while judging."""
    first, second = WHOLE[:], TILED[:]
    random.Random(452).shuffle(first)   # same A/B/C as before the tiling test was added
    random.Random(453).shuffle(second)  # D/E
    return first + second


def load_results() -> dict[str, dict[str, dict]]:
    """{setup: {photo: row}}"""
    out = {}
    for s in SETUP_FILES:
        p = RESULTS / f'items_{s}.jsonl'
        out[s] = {}
        if not p.exists():
            continue
        for line in p.read_text(encoding='utf-8').splitlines():
            r = json.loads(line)
            if 'photo' in r:
                out[s][r['photo']] = r
    return out


def load_answers() -> dict:
    return json.loads(ANSWERS.read_text(encoding='utf-8')) if ANSWERS.exists() else {}


def summarize(results: dict, answers: dict, setups=None, photos=None) -> dict:
    """Per setup totals over photos where all of that setup's items are judged (optionally only `photos`)."""
    table = {}
    for s in setups or SETUP_FILES:
        t = dict(photos=0, listed=0, right=0, close=0, wrong=0, dup=0, key=0, unidentified=0, cost=0.0, latency=0.0)
        for photo, row in results[s].items():
            if 'scene' not in row or (photos is not None and photo not in photos):
                continue
            a = answers.get(photo, {})
            v = a.get('verdicts', {}).get(s, {})
            n = len(row['scene']['items'])
            if n == 0 or len(v) < n or a.get('key_total') in (None, ''):
                continue
            t['photos'] += 1
            t['listed'] += n
            for i in range(n):
                t[v[str(i)]] += 1
            t['key'] += int(a['key_total'])
            t['unidentified'] += row['scene']['visible_but_unidentifiable']
            t['cost'] += row['cost_usd']
            t['latency'] += row['latency_ms'] / 1000
        L = t['listed'] or 1
        t['precision'] = (t['right'] + t['close']) / L
        t['strict_precision'] = t['right'] / L
        t['hallucination'] = t['wrong'] / L
        t['recall'] = min(1.0, (t['right'] + t['close']) / t['key']) if t['key'] else 0.0
        t['strict_recall'] = min(1.0, t['right'] / t['key']) if t['key'] else 0.0
        t['avg_latency'] = t['latency'] / t['photos'] if t['photos'] else 0.0
        table[s] = t
    return table


def progress(results: dict, answers: dict) -> dict:
    """How many photos are fully judged for the three setups."""
    done = 0
    photos = sorted(results[SETUP_FILES[0]])
    for photo in photos:
        a = answers.get(photo, {})
        ok = a.get('key_total') not in (None, '')
        for s in SETUP_FILES:
            row = results[s].get(photo)
            if row is None:
                continue
            n = len(row.get('scene', {}).get('items', []))
            ok = ok and len(a.get('verdicts', {}).get(s, {})) >= n
        done += ok
    return {'done': done, 'total': len(photos)}
