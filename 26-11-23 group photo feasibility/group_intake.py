"""Group-photo intake test: ONE photo of many items -> list of every distinct item the model can identify.

Run:  py -3.13 group_intake.py luna_1024 --model gpt-6-luna --effort low --size 1024
      py -3.13 group_intake.py luna_2048 --model gpt-6-luna --effort low --size 2048
      py -3.13 group_intake.py sol_2048  --model gpt-6-sol  --effort low --size 2048
Writes results/items_<name>.jsonl (one line per photo) and appends costs to results/usage.jsonl.
Photos come from photos/jpg (already upright and EXIF/GPS-stripped by prep.py).
"""
import argparse
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

from PIL import Image
from pydantic import BaseModel

import llm

HERE = Path(__file__).parent
PHOTOS = HERE / 'photos' / 'jpg'
RESULTS = HERE / 'results'

KINDS = ('novel or book', 'manga or comic volume', 'art book or guide', 'box set or slipcase set',
         'video game', 'movie or TV disc set', 'amiibo or figure', 'trading card or card product',
         'board game or puzzle', 'toy or building set', 'wall art or decor', 'electronics or accessory',
         'other')


class FoundItem(BaseModel):
    name: str                       # as it should appear in a collection
    creator_or_maker: str | None    # author, publisher, studio, brand
    kind: Literal[KINDS]            # type: ignore[valid-type]
    series_or_franchise: str | None
    volumes_or_count: str | None    # e.g. "vols 1-7", "3 books", "1"
    edition_or_format: str | None   # e.g. "Colossal Edition", "Blu-ray steelbook", "Deluxe Edition"
    text_read_on_item: str          # the words you can actually read on it (title, spine, box text)
    confidence: Literal['high', 'medium', 'low']
    position: str                   # coarse location in the photo, e.g. "bottom shelf, far left"
    sealed: bool | None             # visibly shrink-wrapped / sealed, else null


class Scene(BaseModel):
    items: list[FoundItem]
    visible_but_unidentifiable: int  # separate things you can see but cannot identify at all
    notes: str | None


SYSTEM = """You are the intake assistant for a personal collection tracker. The owner took ONE photo showing many
things they own at once (a shelf, a stack, a display). List every distinct item you can identify, so the owner can
confirm them in one pass.

- One entry per distinct product. A run of volumes of the same series and edition is ONE entry with volumes_or_count
  ("vols 1-7"). A box set or slipcase is one entry. Same series but a different edition or size is a separate entry.
- Name each item specifically (title + edition/format), as it should appear in the collection.
- text_read_on_item: quote the words you can really read on the item. If you cannot read it, say so.
- Only identify what is visible or what the visible text or art makes certain. Do not guess titles from a color or
  shape. If you can see something but cannot identify it, count it in visible_but_unidentifiable instead of inventing.
- Include partly hidden items if enough is visible to identify them. Ignore furniture, cables, bags and background.
- confidence is about the exact identification, not the general type.
- position: where it is in the photo (shelf, left/middle/right) so the owner can find it."""


def load_jpeg(path: Path, size: int) -> bytes:
    im = Image.open(path)
    if max(im.size) > size:
        im.thumbnail((size, size))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=88)
    return buf.getvalue()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('name')
    ap.add_argument('--model', default='gpt-6-luna')
    ap.add_argument('--effort', default='low')
    ap.add_argument('--size', type=int, default=2048)
    ap.add_argument('--detail', default='high')
    ap.add_argument('--workers', type=int, default=5)
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    photos = sorted(PHOTOS.glob('*.jpg'))

    def one(p: Path) -> dict:
        parts = [{'type': 'input_text', 'text': 'Photo of many things I own. List every distinct item.'},
                 llm.image_part(load_jpeg(p, a.size), a.detail)]
        for attempt in range(3):
            try:
                scene, rec = llm.parse(a.model, SYSTEM, parts, Scene, effort=a.effort, max_output_tokens=16000,
                                       log=RESULTS / 'usage.jsonl', tag=f'group:{a.name}:{p.stem}')
                break
            except Exception as e:
                if attempt == 2:
                    print(f'{p.stem}: ERROR {e!r}'[:200])
                    return {'photo': p.stem, 'error': repr(e)[:300]}
        print(f'{p.stem}: {len(scene.items)} items, {scene.visible_but_unidentifiable} unidentified '
              f'({rec["latency_ms"]/1000:.1f}s, ${rec["cost_usd"]:.4f})')
        return {'photo': p.stem, 'scene': scene.model_dump(), 'cost_usd': rec['cost_usd'],
                'latency_ms': rec['latency_ms'], 'input_tokens': rec['input_tokens'],
                'output_tokens': rec['output_tokens']}

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, photos))
    out = RESULTS / f'items_{a.name}.jsonl'
    out.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in [{'_meta': vars(a)}] + rows) + '\n',
                   encoding='utf-8')
    ok = [r for r in rows if 'scene' in r]
    print(f'\n{len(ok)}/{len(rows)} photos, {sum(len(r["scene"]["items"]) for r in ok)} items, '
          f'${sum(r["cost_usd"] for r in ok):.4f} total -> {out.name}')


if __name__ == '__main__':
    main()
