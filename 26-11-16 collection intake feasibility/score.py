"""Score every results/cards_*.jsonl against answers.csv -> results/SCORES.md.

Deterministic checks: category, sealed/opened. A Sol "judge" compares each card to the answer for the fuzzy parts
(right item? how many fields to fix? invented details? right TMDB match?). Judgments are cached in
results/judgments.jsonl, so re-running only judges new cards or answers you changed.
Run: py -3.13 score.py
"""
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

import llm

HERE = Path(__file__).parent
RESULTS = HERE / 'results'
JUDGE_MODEL = 'gpt-6-sol'
ACCEPT = ('as is', '1 edit', 'more edits', 'wrong item')


class Judgment(BaseModel):
    identity: Literal['exact', 'close', 'wrong']
    fields_to_fix: int
    invented_details: list[str]
    tmdb_top_match: Literal['correct', 'wrong', 'n/a']
    accept: Literal[ACCEPT]  # type: ignore[valid-type]
    reason: str


JUDGE = """You grade an AI-proposed collection card against the owner's answer key for a photo of something they own.
- identity: exact = the specific product/edition the owner names (all must_have_details right);
  close = right thing but an edition/model/detail in must_have_details is missing or wrong; wrong = different thing.
- fields_to_fix: how many card fields (name, brand_or_maker, franchise_or_series, edition_or_model,
  platform_or_format, each wrong attribute, wrong bundle_contents) the owner would have to change. Ignore
  category, condition, catalog and ask_user (graded elsewhere). Missing optional info is not a fix; wrong info is.
- invented_details: details stated on the card that contradict the answer key or that the photo could not support
  (hallucinations). Empty if none.
- tmdb_top_match: if the card has tmdb matches, is the first one the right movie/show/collection? else n/a.
- accept: as is (0 fixes), 1 edit, more edits (2+), or wrong item.
- reason: one short sentence."""


# My own category names -> the tree path they mean. Anything else is matched by prefix
# ("Video Games" accepts any card under Video Games).
ALIASES = {
    'movies and tv': 'movies and tv > physical media',
    'fall home decor': 'home decor > seasonal',
    'movie or cinema memoribilia': 'collectibles and memorabilia',
    'movie or cinema memorabilia': 'collectibles and memorabilia',
}


def norm(c: str) -> str:
    c = ' '.join(c.lower().replace('&', 'and').split())
    return ALIASES.get(c, c)


def category_ok(card_cat: str, answer: str) -> bool:
    got = norm(card_cat)
    return any(got == a or got.startswith(a + ' >') for a in (norm(x) for x in answer.split('|') if x.strip()))


def load_answers() -> dict[str, dict]:
    with open(HERE / 'answers.csv', encoding='utf-8-sig') as f:
        return {r['photo']: {k: (v or '').strip() for k, v in r.items() if k} for r in csv.DictReader(f)
                if (r.get('name') or '').strip() and (r.get('condition') or '').strip()}


def load_runs() -> dict[str, list[dict]]:
    runs = {}
    for p in sorted(RESULTS.glob('cards_*.jsonl')):
        rows = [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
        runs[p.stem.removeprefix('cards_')] = [r for r in rows if '_meta' not in r]
    return runs


def key(run: str, row: dict, ans: dict) -> str:
    blob = json.dumps([run, row['photo'], row.get('card'), row.get('tmdb'), ans], sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()


def judge_all(runs, answers) -> dict[str, dict]:
    cache_path = RESULTS / 'judgments.jsonl'
    cache = {}
    if cache_path.exists():
        for l in cache_path.read_text(encoding='utf-8').splitlines():
            d = json.loads(l)
            cache[d['key']] = d['judgment']
    todo = [(run, r, answers[r['photo']]) for run, rows in runs.items() for r in rows
            if r['photo'] in answers and 'card' in r and key(run, r, answers[r['photo']]) not in cache]

    def one(t):
        run, r, ans = t
        user = json.dumps({'answer_key': ans, 'card': r['card'], 'tmdb_matches': r['tmdb']}, ensure_ascii=False)
        for attempt in range(3):
            try:
                j, _ = llm.parse(JUDGE_MODEL, JUDGE, user, Judgment, effort='low',
                                 log=RESULTS / 'usage.jsonl', tag=f'judge:{run}:{r["photo"]}')
                return key(run, r, ans), j.model_dump()
            except Exception:
                if attempt == 2:
                    raise

    if todo:
        print(f'judging {len(todo)} cards with {JUDGE_MODEL}...')
        with ThreadPoolExecutor(8) as ex, cache_path.open('a', encoding='utf-8') as f:
            for k, j in ex.map(one, todo):
                cache[k] = j
                f.write(json.dumps({'key': k, 'judgment': j}, ensure_ascii=False) + '\n')
    return cache


def pct(n, d):
    return f'{100 * n / d:.0f}%' if d else '-'


def main() -> None:
    answers = load_answers()
    if not answers:
        raise SystemExit('answers.csv has no filled-in rows yet (fill the name column).')
    runs = load_runs()
    cache = judge_all(runs, answers)
    lines = [f'# Intake scores ({len(answers)} of 26 photos have answers)', '',
             '| Run | Category right | Exact item | Exact or close | Accept as is | As is or 1 edit | '
             'Cards with invented details | Sealed/opened right | TMDB top match | Cost / 1,000 photos | Median latency |',
             '|' + '---|' * 11]
    per_photo = {}
    for run, rows in runs.items():
        rows = [r for r in rows if r['photo'] in answers and 'card' in r]
        js = [cache[key(run, r, answers[r['photo']])] for r in rows]
        n = len(rows)
        cat_scored = [(r, answers[r['photo']]) for r in rows if answers[r['photo']]['category'].strip()]
        cat_ok = sum(category_ok(r['card']['category'], a['category']) for r, a in cat_scored)
        cond_scored = [(r, answers[r['photo']]['condition'].strip().lower()) for r in rows
                       if answers[r['photo']]['condition'].strip()]
        cond_ok = sum(r['card']['condition'].startswith('sealed') == c.startswith('sealed') for r, c in cond_scored)
        tm = [j['tmdb_top_match'] for j in js if j['tmdb_top_match'] != 'n/a']
        lat = sorted(r['latency_ms'] for r in rows)
        cost = sum(r['cost_usd'] for r in rows) / n * 1000 if n else 0
        lines.append(
            f'| {run} | {pct(cat_ok, len(cat_scored))} | {pct(sum(j["identity"] == "exact" for j in js), n)} | '
            f'{pct(sum(j["identity"] != "wrong" for j in js), n)} | {pct(sum(j["accept"] == "as is" for j in js), n)} | '
            f'{pct(sum(j["accept"] in ("as is", "1 edit") for j in js), n)} | '
            f'{sum(bool(j["invented_details"]) for j in js)} of {n} | {pct(cond_ok, len(cond_scored))} | '
            f'{sum(t == "correct" for t in tm)} of {len(tm)} | ${cost:.2f} | {lat[len(lat) // 2] / 1000:.1f} s |')
        for r, j in zip(rows, js):
            per_photo.setdefault(r['photo'], {})[run] = (r, j)

    lines += ['', '## Every photo', '',
              'Per run: accept verdict, then the judge\'s reason. "cat" marks a category that differs from the answer key.', '']
    for photo, by_run in sorted(per_photo.items()):
        a = answers[photo]
        lines.append(f'### {photo}: {a["name"]}')
        lines.append(f'Answer: category `{a["category"]}`, must have `{a["must_have_details"]}`, {a["condition"]}')
        lines.append('')
        for run, (r, j) in by_run.items():
            c = r['card']
            cat_flag = '' if not a['category'].strip() or category_ok(c['category'], a['category']) \
                else f' **cat: {c["category"]}**'
            inv = f' Invented: {"; ".join(j["invented_details"])}.' if j['invented_details'] else ''
            lines.append(f'- **{run}**: {j["accept"]}. "{c["name"]}"{cat_flag}. {j["reason"]}{inv}')
        lines.append('')
    (RESULTS / 'SCORES.md').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines[:4 + len(runs)]))


if __name__ == '__main__':
    main()
