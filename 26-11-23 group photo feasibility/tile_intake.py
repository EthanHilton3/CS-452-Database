"""Tiling test: cut each photo into 2x2 overlapping tiles, list items per tile at high resolution, then merge.

Run:  py -3.13 tile_intake.py luna_tiled --model gpt-6-luna --photos IMG_1978 IMG_6527 IMG_6607 IMG_6608
      py -3.13 tile_intake.py sol_tiled  --model gpt-6-sol  --photos IMG_1978 IMG_6527 IMG_6607 IMG_6608
Each tile is 60% of the photo's width and height (20% overlap with its neighbours), sent at up to --size px.
A second, text-only call (same model) merges the four tile lists, dropping items seen twice in the overlap.
Writes results/items_<name>.jsonl in the same shape as group_intake.py, so review.py and score.py work on it.
"""
import argparse
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

import llm
from group_intake import SYSTEM, Scene

HERE = Path(__file__).parent
PHOTOS = HERE / 'photos' / 'jpg'
RESULTS = HERE / 'results'
FRAC = 0.6  # tile size as a fraction of the photo; 2 tiles per axis at offsets 0 and 0.4 -> 20% overlap

TILE_SYSTEM = SYSTEM + """

This image is ONE TILE (a crop) of a larger photo, so items at the tile's edges may be cut off. Identify an edge
item only if enough of it is visible. Give position relative to the tile (e.g. "top-left of tile")."""

MERGE_SYSTEM = """You merge item lists from four overlapping crops (tiles) of the SAME photo of a person's collection.
The tiles overlap by 20% of each side, so one real item can appear in two or more lists, often with slightly
different names. Produce ONE final list for the whole photo:
- Drop duplicates: the same physical item reported by more than one tile appears once. Keep the best-supported name,
  edition and details, and the highest confidence among the duplicates.
- A run of volumes cut by a tile edge is one entry (e.g. vols 1-4 in one tile and vols 5-7 in another is vols 1-7).
- Do NOT add items that are in no tile list, and do not rename items based on guesses. Keep text_read_on_item as
  quoted by the tile that saw the item best.
- position: describe where the item is in the whole photo (e.g. "bottom shelf, far left").
- visible_but_unidentifiable: your best count of distinct unidentified things in the whole photo, counting each once
  (do not just add the tiles' counts, since overlap double counts)."""


def tiles(path: Path, size: int) -> list[tuple[str, bytes]]:
    im = Image.open(path)
    w, h = im.size
    tw, th = int(w * FRAC), int(h * FRAC)
    out = []
    for r, y in enumerate((0, h - th)):
        for c, x in enumerate((0, w - tw)):
            t = im.crop((x, y, x + tw, y + th))
            if max(t.size) > size:
                t.thumbnail((size, size))
            buf = io.BytesIO()
            t.save(buf, 'JPEG', quality=88)
            out.append((f'{("top", "bottom")[r]}-{("left", "right")[c]}', buf.getvalue()))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--model', default='gpt-6-luna')
    ap.add_argument('--effort', default='low')
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--photos', nargs='+', required=True)
    ap.add_argument('--workers', type=int, default=4)
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    log = RESULTS / 'usage.jsonl'

    def call(system: str, user, tag: str):
        for attempt in range(3):
            try:
                return llm.parse(a.model, system, user, Scene, effort=a.effort, max_output_tokens=16000, log=log, tag=tag)
            except Exception as e:
                if attempt == 2:
                    raise RuntimeError(f'{tag}: {e!r}'[:300])

    def one(stem: str) -> dict:
        path = PHOTOS / f'{stem}.jpg'
        try:
            def per_tile(t):
                label, jpg = t
                parts = [{'type': 'input_text', 'text': f'Tile ({label}) of a photo of many things I own. List every distinct item.'},
                         llm.image_part(jpg, 'high')]
                scene, rec = call(TILE_SYSTEM, parts, f'tile:{a.name}:{stem}:{label}')
                return label, scene, rec
            with ThreadPoolExecutor(4) as ex:
                results = list(ex.map(per_tile, tiles(path, a.size)))
            payload = json.dumps({label: s.model_dump() for label, s, _ in results}, ensure_ascii=False)
            merged, mrec = call(MERGE_SYSTEM, [{'type': 'input_text', 'text': payload}], f'merge:{a.name}:{stem}')
            recs = [r for _, _, r in results] + [mrec]
            cost = sum(r['cost_usd'] for r in recs)
            latency = max(r['latency_ms'] for r in recs[:-1]) + mrec['latency_ms']  # tiles run in parallel
            n_tile_items = sum(len(s.items) for _, s, _ in results)
            print(f'{stem}: {n_tile_items} tile items -> {len(merged.items)} merged, '
                  f'{merged.visible_but_unidentifiable} unidentified (${cost:.4f}, {latency/1000:.0f}s)')
            return {'photo': stem, 'scene': merged.model_dump(), 'cost_usd': cost, 'latency_ms': latency,
                    'input_tokens': sum(r['input_tokens'] for r in recs),
                    'output_tokens': sum(r['output_tokens'] for r in recs),
                    'tiles': {label: s.model_dump() for label, s, _ in results}}
        except Exception as e:
            print(f'{stem}: ERROR {e!r}'[:250])
            return {'photo': stem, 'error': repr(e)[:300]}

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, a.photos))
    out = RESULTS / f'items_{a.name}.jsonl'
    out.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in [{'_meta': vars(a)}] + rows) + '\n', encoding='utf-8')
    ok = [r for r in rows if 'scene' in r]
    print(f'\n{len(ok)}/{len(rows)} photos, {sum(len(r["scene"]["items"]) for r in ok)} items, '
          f'${sum(r["cost_usd"] for r in ok):.4f} total -> {out.name}')


if __name__ == '__main__':
    main()
