"""Untrusted zip -> photos/originals (flat, only *.HEIC, size-capped). Run: py -3.13 -I extract.py <zip path>"""
import sys
import zipfile
from pathlib import Path, PurePosixPath

OUT = Path(__file__).parent / 'photos' / 'originals'
MAX_BYTES = 50_000_000  # per file; the real ones are ~1-2 MB

if any(OUT.iterdir()):
    sys.exit('photos/originals is not empty; refusing to extract into it')
with zipfile.ZipFile(sys.argv[1]) as z:
    for info in z.infolist():
        name = PurePosixPath(info.filename).name  # drop folders and any ../ tricks
        if info.is_dir() or not name.upper().endswith('.HEIC') or info.file_size > MAX_BYTES:
            print('skipped', info.filename)
            continue
        (OUT / name).write_bytes(z.read(info))
        print('extracted', name, info.file_size)
