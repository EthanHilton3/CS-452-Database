"""AI intake test: photo -> proposed collection card (+ TMDB lookup for movies/TV).

Run:  py -3.13 intake.py luna_full  --model gpt-6-luna --effort low --size 2048
      py -3.13 intake.py luna_small --model gpt-6-luna --effort low --size 768
Writes results/cards_<name>.jsonl (one line per photo) and appends costs to results/usage.jsonl.
Photos come from photos/jpg (already EXIF/GPS-stripped). The TMDB key is read from continuity/.env, never printed.
"""
import argparse
import io
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Literal

import httpx
from PIL import Image
from pydantic import BaseModel

import llm

HERE = Path(__file__).parent
PHOTOS = HERE / 'photos' / 'jpg'
RESULTS = HERE / 'results'
ENV = HERE.parent.parent / 'continuity' / '.env'

# The starter category tree from the design discussion (brands/platforms are attributes, not categories).
CATEGORIES = (
    'Video Games > Games', 'Video Games > Consoles', 'Video Games > Controllers', 'Video Games > Accessories',
    'Movies & TV > Physical media',
    'Books > Novels', 'Books > Manga & Comics', 'Books > Other',
    'Board Games & Puzzles',
    'Toys & Building Sets',
    'Music > Instruments', 'Music > Albums & Vinyl',
    'Collectibles & Memorabilia',
    'Home Decor > Wall art & Frames', 'Home Decor > Seasonal', 'Home Decor > Candles & Fragrance',
    'Home Decor > Other',
    'Kitchen > Appliances', 'Kitchen > Drinkware & Dishes',
    'Bags & Cases',
    'Clothing & Textiles',
    'Tools > Tool sets', 'Tools > Hand & Power tools',
    'Electronics > Other',
    'Other',
)


class Attr(BaseModel):
    key: str
    value: str


class Card(BaseModel):
    item_count: int
    category: Literal[CATEGORIES]  # type: ignore[valid-type]
    name: str
    brand_or_maker: str | None
    franchise_or_series: str | None
    edition_or_model: str | None
    platform_or_format: str | None
    attributes: list[Attr]
    condition: Literal['sealed / new in box', 'opened / used', 'cannot tell']
    bundle_contents: list[str]
    catalog: Literal['tmdb_movie', 'tmdb_tv', 'tmdb_collection', 'igdb_game', 'igdb_platform', 'open_library',
                     'boardgamegeek', 'lego_set', 'upc_lookup', 'none']
    catalog_query: str
    confidence: Literal['high', 'medium', 'low']
    ask_user: str | None


SYSTEM = """You are the intake assistant for a personal collection tracker where people catalog anything they own:
games, consoles, movies, board games, decor, kitchen gear, art, tools. The owner took a photo of one thing they own.
Propose the card that gets saved for it. The owner confirms or edits it, so be accurate and specific.

- item_count: how many separate owned items the photo shows (a sealed bundle or a boxed set counts as 1).
- category: the one category from the list the owner would most likely browse this under.
- name: the name as it should appear in the collection, specific enough to tell it apart from similar things
  (e.g. "New Nintendo 3DS XL - Hyrule Edition", not "Nintendo 3DS").
- brand_or_maker, franchise_or_series, edition_or_model, platform_or_format (console, 4K UHD / Blu-ray / DVD,
  steelbook...): null when not applicable or not visible.
- attributes: the few extra fields worth keeping for this kind of thing (color, size, material, scent, set number,
  disc count, player count...). Only what you can see or are confident about.
- condition: sealed / new in box only if packaging is visibly unopened (shrink wrap, seals); otherwise opened or
  cannot tell.
- bundle_contents: if it is a bundle, box set or kit, what it includes; else empty.
- catalog + catalog_query: which public catalog could hold an entry for this exact product, and the search text
  to find it there. 'none' for unique or generic items.
- confidence: how sure you are of the exact identification (not just the general type).
- ask_user: the single most useful question to finish the card (e.g. which edition, what scent), or null.
Never invent details you cannot see or reasonably know; ask instead."""


def tmdb_key() -> str:
    for line in ENV.read_text(encoding='utf-8').splitlines():
        if line.startswith('TMDB_API_KEY='):
            return line.split('=', 1)[1].strip().strip('"')
    raise SystemExit('TMDB_API_KEY not found in continuity/.env')


def tmdb_lookup(http: httpx.Client, card: Card) -> list[dict]:
    kind = {'tmdb_movie': 'movie', 'tmdb_tv': 'tv', 'tmdb_collection': 'collection'}.get(card.catalog)
    if not kind:
        return []
    res = http.get(f'/search/{kind}', params={'query': card.catalog_query}).raise_for_status().json()['results']
    return [{'kind': kind, 'id': r['id'], 'title': r.get('title') or r.get('name'),
             'year': (r.get('release_date') or r.get('first_air_date') or '')[:4]} for r in res[:3]]


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
    ap.add_argument('--workers', type=int, default=6)
    a = ap.parse_args()
    RESULTS.mkdir(exist_ok=True)
    photos = sorted(PHOTOS.glob('*.jpg'))
    http = httpx.Client(base_url='https://api.themoviedb.org/3', params={'api_key': tmdb_key()}, timeout=20)

    def one(p: Path) -> dict:
        parts = [{'type': 'input_text', 'text': 'Photo of something I own. Propose its card.'},
                 llm.image_part(load_jpeg(p, a.size), a.detail)]
        for attempt in range(3):
            try:
                card, rec = llm.parse(a.model, SYSTEM, parts, Card, effort=a.effort,
                                      log=RESULTS / 'usage.jsonl', tag=f'intake:{a.name}:{p.stem}')
                break
            except Exception as e:  # malformed output / transient API error
                if attempt == 2:
                    return {'photo': p.stem, 'error': repr(e)[:300]}
        try:
            matches = tmdb_lookup(http, card)
        except httpx.HTTPError as e:
            matches = [{'error': repr(e)[:200]}]
        print(f'{p.stem}: {card.category} | {card.name} ({card.confidence}, {rec["latency_ms"]/1000:.1f}s)')
        return {'photo': p.stem, 'card': card.model_dump(), 'tmdb': matches, 'cost_usd': rec['cost_usd'],
                'latency_ms': rec['latency_ms'], 'input_tokens': rec['input_tokens'],
                'output_tokens': rec['output_tokens']}

    with ThreadPoolExecutor(a.workers) as ex:
        rows = list(ex.map(one, photos))
    meta = {'_meta': vars(a)}
    out = RESULTS / f'cards_{a.name}.jsonl'
    out.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in [meta] + rows) + '\n', encoding='utf-8')
    ok = [r for r in rows if 'card' in r]
    lat = sorted(r['latency_ms'] for r in ok)
    print(f'\n{len(ok)}/{len(rows)} cards, ${sum(r["cost_usd"] for r in ok):.4f} total, '
          f'median {lat[len(lat)//2]/1000:.1f}s, avg {sum(r["input_tokens"] for r in ok)/len(ok):.0f} input tokens '
          f'-> {out.name}')


if __name__ == '__main__':
    main()
