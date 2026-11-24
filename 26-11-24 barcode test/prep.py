"""HEIC originals -> upright, metadata-stripped JPEGs in photos/jpg (full size). Run: py -3.13 -I prep.py"""
from pathlib import Path
from PIL import Image, ImageOps
import pillow_heif

pillow_heif.register_heif_opener()
HERE = Path(__file__).parent
SRC, OUT = HERE / 'photos' / 'originals', HERE / 'photos' / 'jpg'
OUT.mkdir(exist_ok=True)
for p in sorted(SRC.glob('*.HEIC')):
    im = ImageOps.exif_transpose(Image.open(p)).convert('RGB')   # apply rotation, then save with no EXIF/GPS
    im.save(OUT / f'{p.stem}.jpg', 'JPEG', quality=90)
    print(p.stem, im.size)
