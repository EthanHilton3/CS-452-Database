"""Build the test set: real r/andor comments from episode megathreads and general threads.

Source: the Arctic Shift Reddit archive (Reddit's own API returns 403 without auth).
Stores no usernames, only the comment ID, thread, score and text.
Run: py -3.13 collect/fetch_comments.py
"""
import json
import random

import time
from pathlib import Path

import httpx

HERE = Path(__file__).parent.parent
API = 'https://arctic-shift.photon-reddit.com/api'
UA = {'User-Agent': 'spoiler-feasibility-test/0.1 (personal class research)'}
SEED = 452
PER_EPISODE_THREAD = 6
PER_GENERAL_THREAD = 10

# Episode megathreads: the comment's "home" episode. order = position in data/episodes.json (S1E1 = 1, S2E1 = 13).
# Season 1 (2022): no archived official threads were found for E8 and E9; episodes 1-3 shared one thread.
SEASON1_THREADS = {
    'xkl6bz': 3, 'xrj4u3': 4, 'xwv6ay': 5, 'y1teyw': 6, 'y8dpg2': 7, 'yqo0bv': 10, 'ywnkum': 11, 'z2j8h6': 12,
}
SEASON2_THREADS = {
    '1k59ywo': 13, '1k59yx8': 14, '1k59yxp': 15, '1kax9lx': 16, '1kaxao9': 17, '1kaxc0m': 18,
    '1kfpvyf': 19, '1kfpwx5': 20, '1kfpxx3': 21, '1klzfqk': 22, '1klzjaw': 23, '1klzkkm': 24,
}
# General threads (no home episode): the realistic "browsing the sub mid-show" case.
GENERAL_THREADS = {
    '1km4z4b': 'Rogue One Rewatch Discussion Thead',
    '1m6thp8': 'Discussion: Does Kleya make it to Luthen if Heert does not pull Dedra?',
    '1kn0zrc': 'Discussion: Andor pulled off what The Last Jedi tried to',
    '1ix7men': 'Andor S2 Trailer Discussion Thread',
    '1kb6wai': 'Episodes 4 - 6 initial discussion',
}


def get(c: httpx.Client, path: str, **params) -> list[dict]:
    for attempt in range(6):
        r = c.get(f'{API}{path}', params=params)
        if r.status_code == 200 and r.json().get('data') is not None:
            return r.json()['data']
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'{path} {params} failed: {r.status_code} {r.text[:200]}')


def usable(body: str) -> bool:
    return (body not in ('[deleted]', '[removed]') and 25 <= len(body) <= 700
            and not body.lower().startswith(('i am a bot', 'this comment has been removed')))


def sample(c: httpx.Client, link_id: str, n: int, rng: random.Random) -> list[dict]:
    comments = [x for x in get(c, '/comments/search', link_id=link_id, limit=100)
                if x.get('author') != 'AutoModerator' and usable(x.get('body', ''))]
    rng.shuffle(comments)
    return comments[:n]


def main() -> None:
    rng = random.Random(SEED)
    rows = []
    with httpx.Client(headers=UA, timeout=40) as c:
        threads = [(tid, ep, None) for tid, ep in SEASON1_THREADS.items()]
        threads += [(tid, order, None) for tid, order in SEASON2_THREADS.items()]
        threads += [(tid, None, title) for tid, title in GENERAL_THREADS.items()]
        for tid, home, title in threads:
            n = PER_GENERAL_THREAD if home is None else PER_EPISODE_THREAD
            for x in sample(c, tid, n, rng):
                rows.append({
                    'comment_id': x['id'], 'thread_id': tid,
                    'thread_kind': 'general' if home is None else 'episode',
                    'home_order': home, 'thread_title': title, 'score': x.get('score'),
                    'is_reply': not str(x.get('parent_id', '')).startswith('t3_'),
                    'text': x['body'].strip(),
                })
            print(f'{tid}: home={home} -> {sum(r["thread_id"] == tid for r in rows)} comments')
            time.sleep(0.5)
    path = HERE / 'data' / 'comments.jsonl'
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    print(f'{len(rows)} comments -> {path.name}')


if __name__ == '__main__':
    main()
