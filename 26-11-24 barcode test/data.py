"""Shared loaders for review.py and score.py: decode + lookup rows joined per photo, and answers.json."""
import json
from pathlib import Path

HERE = Path(__file__).parent
ANSWERS = HERE / 'answers.json'
TYPES = ['movie', 'game', 'book', 'music', 'other']
VERDICTS = ['right', 'close', 'wrong', 'not_found']


def _jsonl(name: str) -> list[dict]:
    p = HERE / 'results' / name
    return [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()] if p.exists() else []


def rows() -> list[dict]:
    look = {r['photo']: r for r in _jsonl('lookup.jsonl')}
    return [d | {'lookup': look.get(d['photo'], {})} for d in _jsonl('decode.jsonl')]


def load_answers() -> dict:
    return json.loads(ANSWERS.read_text(encoding='utf-8')) if ANSWERS.exists() else {}


def looked_up(row: dict) -> bool:
    return bool(row['lookup'].get('looked_up'))


def is_done(row: dict, a: dict) -> bool:
    """A photo is judged when its type is set and, if there was a lookup, a verdict is set too."""
    return bool(a.get('type')) and (not looked_up(row) or bool(a.get('verdict')))
