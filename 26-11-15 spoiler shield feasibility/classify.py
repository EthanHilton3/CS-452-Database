"""Run the spoiler classifier over the test comments.

For each comment the model answers: what is the LATEST episode whose plot this comment reveals?
That answer doesn't depend on the viewer, so in the product one call serves every user; each user only
compares it to their own position.

Context conditions (what the model is told about the show):
  none    only the show's name, so the model relies on what it already knows
  tmdb    TMDB's one-line episode overviews (~13 words each)
  sheets  the condensed Wookieepedia reveal sheets (~200 words each), computed once per episode

Run:  py -3.13 classify.py sheets            (default model gpt-6-luna, batches of 10)
      py -3.13 classify.py tmdb --model gpt-6-sol --batch 10 --effort low
Writes results/pred_<condition>_<model>[_<effort>].jsonl and appends cost records to results/usage.jsonl.
"""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from typing import Literal

from pydantic import BaseModel, Field

from llm import HERE, parse

EPISODES = json.loads((HERE / 'data' / 'episodes.json').read_text(encoding='utf-8'))['episodes']
SHEETS = json.loads((HERE / 'data' / 'reveal_sheets.json').read_text(encoding='utf-8'))
CODES = [e['code'] for e in EPISODES]

SYSTEM = """You are the classifier inside a spoiler-blocking browser extension for the TV show Andor (Seasons 1-2).
For each Reddit comment, decide the LATEST episode of Andor whose plot the comment reveals.

What counts as revealing plot: deaths, injuries, captures, escapes, betrayals, identities, allegiances,
relationships, pregnancies, who survives, the outcome of a mission, a character's big decision, or quoting a
line in a way that gives away what happens. Naming a character only reveals the episode where they first
appear if the comment says something about what happens to them.
What does NOT count: praise or criticism, actors, music, props, sets, real-world politics, other Star Wars
works, jokes and questions that reveal nothing.

Answer "none" if it reveals no Andor plot. Set rogue_one=true if it spoils the film Rogue One (for example
how Cassian's story ends, or Jyn Erso's role), whether or not it also reveals an Andor episode.
If a comment reveals several episodes, give the latest one. Judge only the comment text; you don't know
which thread it came from. Episode codes: """ + ', '.join(CODES) + '.'


def context(condition: str) -> str:
    if condition == 'none':
        return 'Show: Andor (2022-2025), 24 episodes in two seasons.'
    if condition == 'tmdb':
        return 'Episode guide:\n' + '\n'.join(f'{e["code"]} "{e["title"]}": {e["overview"]}' for e in EPISODES)
    if condition == 'sheets':
        return 'What each episode reveals:\n\n' + '\n\n'.join(
            f'{s["code"]} "{s["title"]}"\n' + '\n'.join(f'- {f}' for f in s['facts']) for s in SHEETS)
    raise ValueError(condition)


class Verdict(BaseModel):
    n: int
    reveals: Literal[tuple(['none'] + CODES)]  # type: ignore[valid-type]
    rogue_one: bool
    confidence: float = Field(description='0 to 1')
    evidence: str = Field(description='the few words that give it away, or empty')


class Batch(BaseModel):
    verdicts: list[Verdict]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('condition', choices=['none', 'tmdb', 'sheets'])
    ap.add_argument('--model', default='gpt-6-luna')
    ap.add_argument('--batch', type=int, default=10)
    ap.add_argument('--effort', default=None)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--context', action='store_true',
                    help='also give each comment its thread title and parent comment, as the extension would see')
    a = ap.parse_args()

    rows = [json.loads(l) for l in (HERE / 'data' / 'comments.jsonl').read_text(encoding='utf-8').splitlines()]
    system = SYSTEM + '\n\n' + context(a.condition)  # stable prefix first, so repeated calls hit the prompt cache
    if a.context:
        system = system.replace("Judge only the comment text; you don't know\nwhich thread it came from.",
                                'Each comment comes with its thread title and, for replies, the comment it replies to. '
                                'Use them to understand what the comment refers to, but label only what the COMMENT '
                                'ITSELF reveals (a reply that only makes sense with its parent still reveals what it '
                                'refers to).')
    batches = [list(enumerate(rows))[i:i + a.batch] for i in range(0, len(rows), a.batch)]
    name = f'{a.condition}_{a.model}' + (f'_{a.effort}' if a.effort else '') + ('_ctx' if a.context else '')

    def show(n, r):
        text = f'[{n}] {" ".join(r["text"].split())}'
        if not a.context:
            return text
        parent = f'\n  (replying to: {" ".join(r["parent_text"].split())[:400]})' if r.get('parent_text') else ''
        return f'[{n}] thread: {r["thread_title"]}{parent}\n  comment: {" ".join(r["text"].split())}'
    log = HERE / 'results' / 'usage.jsonl'
    failures: list[int] = []  # malformed-output retries (their cost isn't logged: the failed call raised first)

    def run(batch):
        user = 'Comments:\n\n' + '\n\n'.join(show(n, r) for n, r in batch)
        for attempt in range(3):  # malformed JSON happens now and then; the product would retry too
            try:
                out, rec = parse(a.model, system, user, Batch, effort=a.effort, log=log,
                                 tag=f'classify {name} n={batch[0][0]}-{batch[-1][0]}')
                break
            except ValueError as e:  # pydantic ValidationError is a ValueError
                print(f'  batch {batch[0][0]}: bad output, retry {attempt + 1} ({str(e)[:80]})')
                failures.append(batch[0][0])
        else:
            raise RuntimeError(f'batch {batch[0][0]} failed 3 times')
        got = {v.n: v for v in out.verdicts}
        missing = [n for n, _ in batch if n not in got]
        return [dict(n=n, **got[n].model_dump(exclude={'n'})) if n in got else
                dict(n=n, reveals='none', rogue_one=False, confidence=0.0, evidence='', missing=True)
                for n, _ in batch], rec, missing

    with ThreadPoolExecutor(a.workers) as pool:
        results = list(pool.map(run, batches))
    preds = [p for r, _, _ in results for p in r]
    recs = [rec for _, rec, _ in results]
    missing = sum(len(m) for _, _, m in results)
    meta = {'condition': a.condition, 'model': a.model, 'effort': a.effort, 'batch': a.batch, 'calls': len(recs),
            'input_tokens': sum(r['input_tokens'] for r in recs), 'cached_tokens': sum(r['cached_tokens'] for r in recs),
            'output_tokens': sum(r['output_tokens'] for r in recs), 'cost_usd': round(sum(r['cost_usd'] for r in recs), 5),
            'latency_ms_per_call': sorted(r['latency_ms'] for r in recs), 'missing_verdicts': missing, 'malformed_retries': len(failures)}
    out = HERE / 'results' / f'pred_{name}.jsonl'
    out.write_text(json.dumps({'_meta': meta}) + '\n' + ''.join(json.dumps(p) + '\n' for p in preds), encoding='utf-8')
    lat = meta['latency_ms_per_call']
    print(f'{name}: {len(preds)} verdicts ({missing} missing) in {len(recs)} calls, ${meta["cost_usd"]:.4f}, '
          f'{meta["input_tokens"]} in ({meta["cached_tokens"]} cached) / {meta["output_tokens"]} out, '
          f'latency median {lat[len(lat) // 2]} ms, max {lat[-1]} ms')


if __name__ == '__main__':
    main()
