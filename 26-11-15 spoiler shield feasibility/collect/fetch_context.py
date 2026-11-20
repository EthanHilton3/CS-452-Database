"""Add what the extension would see around each comment: the thread title and, for replies, the parent comment.
Run: py -3.13 collect/fetch_context.py   (updates data/comments.jsonl in place)
"""
import json
import time
from pathlib import Path

import httpx

HERE = Path(__file__).parent.parent
API = 'https://arctic-shift.photon-reddit.com/api'
UA = {'User-Agent': 'spoiler-feasibility-test/0.1 (personal class research)'}


def get(c, path, **params):
    for attempt in range(6):
        r = c.get(f'{API}{path}', params=params)
        if r.status_code == 200 and r.json().get('data') is not None:
            return r.json()['data']
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f'{path} failed: {r.status_code}')


def main():
    path = HERE / 'data' / 'comments.jsonl'
    rows = [json.loads(l) for l in path.read_text(encoding='utf-8').splitlines()]
    with httpx.Client(headers=UA, timeout=40) as c:
        threads = {p['id']: p['title'] for p in get(c, '/posts/ids', ids=','.join({r['thread_id'] for r in rows}))}
        need = [r['comment_id'] for r in rows if r['is_reply']]
        full = {}
        for i in range(0, len(need), 50):
            for x in get(c, '/comments/ids', ids=','.join(need[i:i + 50])):
                full[x['id']] = x['parent_id']
        parents = {}
        pids = [p[3:] for p in full.values() if p.startswith('t1_')]
        for i in range(0, len(pids), 50):
            for x in get(c, '/comments/ids', ids=','.join(pids[i:i + 50])):
                parents[x['id']] = x.get('body', '')
    for r in rows:
        r['thread_title'] = threads.get(r['thread_id'], r.get('thread_title'))
        pid = full.get(r['comment_id'], '')
        r['parent_text'] = parents.get(pid[3:]) if pid.startswith('t1_') else None
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    print(f'{len(threads)} thread titles, {sum(r["parent_text"] is not None for r in rows)} parent comments')


if __name__ == '__main__':
    main()
