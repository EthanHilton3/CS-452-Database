"""Copy your earlier verdicts onto tiled-setup items that make an IDENTICAL claim (same name, volumes, edition) as an
item you already judged in the same photo. Anything else is left for you to judge. Marks copies in answers.json under
'auto' so review.py can badge them.   py -3.13 carry.py
"""
import json
import re
import scoring


def norm(s) -> str:
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def key(it: dict) -> tuple:
    return norm(it['name']), norm(it['volumes_or_count']), norm(it['edition_or_format'])


res, ans = scoring.load_results(), scoring.load_answers()
copied = todo = conflicts = 0
for photo, a in ans.items():
    known: dict[tuple, set] = {}
    for s in scoring.WHOLE:
        items = res[s].get(photo, {}).get('scene', {}).get('items', [])
        for i, v in a.get('verdicts', {}).get(s, {}).items():
            if v != 'dup':   # a duplicate verdict depends on the list it sits in
                known.setdefault(key(items[int(i)]), set()).add(v)
    for s in scoring.TILED:
        row = res[s].get(photo)
        if not row or 'scene' not in row:
            continue
        verd = a.setdefault('verdicts', {}).setdefault(s, {})
        for i, it in enumerate(row['scene']['items']):
            if str(i) in verd:
                continue
            vs = known.get(key(it), set())
            if len(vs) == 1:
                verd[str(i)] = next(iter(vs))
                a.setdefault('auto', {}).setdefault(s, []).append(i)
                copied += 1
            else:
                conflicts += len(vs) > 1
                todo += 1
scoring.ANSWERS.write_text(json.dumps(ans, indent=1, ensure_ascii=False), encoding='utf-8')
print(f'copied {copied} verdicts from identical judged items; {todo} items still need you ({conflicts} had conflicting earlier verdicts)')
for photo in sorted(ans):
    for s in scoring.TILED:
        row = res[s].get(photo)
        if row and 'scene' in row:
            n = len(row['scene']['items']); d = len(ans[photo]['verdicts'].get(s, {}))
            print(f'  {photo} {s}: {n} items, {n - d} to judge')
