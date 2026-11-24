"""Step 1: read the barcode out of each photo. Run: .venv\\Scripts\\python.exe -I decode.py [--no-model]

Ladder per photo: (1) zxing-cpp on the full photo ("decoder"), (2) retries on contrast-boosted, resized and cropped
versions ("retry"), (3) the vision model reads the printed digits ("model-read", gpt-6-luna, low effort, high detail).
Writes results/decode.jsonl, one row per photo. Model reads are reused from the last run so you never pay twice."""
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))  # -I drops the script folder from sys.path; this is our own code, not the photos folder

import zxingcpp
from PIL import Image, ImageFilter, ImageOps
from pydantic import BaseModel

import gtin
import llm

PHOTOS = HERE / 'photos' / 'jpg'
OUT = HERE / 'results' / 'decode.jsonl'
USAGE = HERE / 'results' / 'usage.jsonl'
MODEL, EFFORT = 'gpt-6-luna', 'low'
PRODUCT_FORMATS = {'EAN-13', 'EAN-8', 'UPC-A', 'UPC-E'}  # zxing's names (str(b.format))


class BarcodeRead(BaseModel):
    barcode_visible: bool
    digits: str
    note: str


SYSTEM = ('You read product barcodes from photos of collectibles (movies, games, books, music, other goods). '
          'Transcribe the digit string printed beneath the main product barcode (UPC-A, EAN-13, ISBN-13). '
          'Digits only, no spaces. Ignore SKU stickers, prices and other numbers. If you cannot read every digit with '
          'confidence, return an empty string for digits. Never guess or complete digits.')


def scan(im: Image.Image, **kw) -> list:
    return zxingcpp.read_barcodes(im, return_errors=True, **kw)


def upscale_to(im: Image.Image, long_side: int) -> Image.Image:
    s = long_side / max(im.size)
    return im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)


def variants(full: Image.Image):
    """Cheap-to-expensive retries. Yields (name, image, extra read_barcodes kwargs)."""
    gray = ImageOps.autocontrast(full.convert('L'), cutoff=1)
    yield 'gray+autocontrast', gray, {}
    for side in (2000, 1200):
        yield f'downscale-{side}', upscale_to(gray, side), {}
    yield 'sharpen+contrast', gray.filter(ImageFilter.UnsharpMask(radius=3, percent=250, threshold=2)), {}
    yield 'denoise', gray, {'try_denoise': True}
    yield 'global-binarizer', gray, {'binarizer': zxingcpp.Binarizer.GlobalHistogram}
    w, h = full.size                      # 3x3 overlapping crops, each half the photo's size, then enlarged
    for r in range(3):
        for c in range(3):
            box = (round(c * w * .25), round(r * h * .25), round(c * w * .25 + w * .5), round(r * h * .25 + h * .5))
            tile = ImageOps.autocontrast(full.crop(box).convert('L'), cutoff=1)
            yield f'crop r{r}c{c} x2', upscale_to(tile, 2400), {}


def summarize(found: list) -> dict:
    """Pick the primary product barcode: valid checksum, biggest on the page."""
    rows = []
    for b in found:
        fmt = str(b.format)
        text = b.text
        if fmt == 'EAN-13' and text.startswith('0'):  # zxing reports every UPC-A as EAN-13 with a leading 0
            fmt, text = 'UPC-A', text[1:]
        xs, ys = [b.position.top_left.x, b.position.bottom_right.x], [b.position.top_left.y, b.position.bottom_right.y]
        rows.append({'format': fmt, 'text': text, 'zxing_error': str(b.error) if b.error else None,
                     'area': abs(xs[1] - xs[0]) * abs(ys[1] - ys[0])})
    good = [r for r in rows if r['format'] in PRODUCT_FORMATS and not r['zxing_error'] and gtin.checksum_valid(r['text'])]
    good.sort(key=lambda r: -r['area'])
    return {'primary': good[0] if good else None, 'all_reads': [{k: v for k, v in r.items() if k != 'area'} for r in rows]}


def decode_photo(path: Path) -> dict:
    full = Image.open(path).convert('RGB')
    row = {'photo': path.stem, 'digits': None, 'method': None, 'variant': None, 'format': None, 'kind': None,
           'checksum_valid': False, 'all_reads': []}
    found = scan(full)
    s = summarize(found)
    row['all_reads'] = s['all_reads']
    if s['primary']:
        return row | {'digits': s['primary']['text'], 'method': 'decoder', 'variant': 'full photo',
                      'format': s['primary']['format']}
    for name, im, kw in variants(full):
        s = summarize(scan(im, **kw))
        if s['primary']:
            return row | {'digits': s['primary']['text'], 'method': 'retry', 'variant': name,
                          'format': s['primary']['format'], 'all_reads': row['all_reads'] + s['all_reads']}
    return row


def model_read(path: Path) -> dict:
    im = upscale_to(Image.open(path).convert('RGB'), 2048)
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=90)
    user = [{'type': 'input_text', 'text': 'Read the barcode digits in this photo.'}, llm.image_part(buf.getvalue(), 'high')]
    out, rec = llm.parse(MODEL, SYSTEM, user, BarcodeRead, effort=EFFORT, log=USAGE, tag=f'barcode:{path.stem}')
    digits = ''.join(ch for ch in out.digits if ch.isdigit())
    return {'digits': digits or None, 'model_note': out.note, 'barcode_visible': out.barcode_visible, 'cost_usd': rec['cost_usd']}


def main() -> None:
    use_model = '--no-model' not in sys.argv
    prev = {}
    if OUT.exists():
        prev = {r['photo']: r for r in map(json.loads, OUT.read_text(encoding='utf-8').splitlines())}
    rows = []
    for p in sorted(PHOTOS.glob('*.jpg')):
        row = decode_photo(p)
        if row['digits'] is None and use_model:
            old = prev.get(p.stem)
            m = old if old and old['method'] == 'model-read' else None
            if m is None:
                r = model_read(p)
                row |= {'method': 'model-read', 'digits': r['digits'], 'model_note': r['model_note'],
                        'model_barcode_visible': r['barcode_visible'], 'model_cost_usd': r['cost_usd']}
            else:
                row |= {k: m.get(k) for k in ('method', 'digits', 'model_note', 'model_barcode_visible', 'model_cost_usd')}
        elif row['digits'] is None:
            row['method'] = 'failed'
        if row['digits']:
            row['kind'] = gtin.kind(row['digits'])
            row['checksum_valid'] = gtin.checksum_valid(row['digits'])
        rows.append(row)
        print(f"{p.stem}  {row['method'] or 'FAILED':10} {row['variant'] or '':20} {row['digits'] or '-':15} "
              f"{row['kind'] or '-':8} checksum={'ok' if row['checksum_valid'] else 'BAD' if row['digits'] else '-'}")
    OUT.write_text('\n'.join(json.dumps(r) for r in rows) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
