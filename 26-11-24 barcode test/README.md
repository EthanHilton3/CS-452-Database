# Barcode feasibility test (Provenance S2)

**Question:** for items I own, can we (1) read the barcode out of a phone photo, and (2) look it up in a free catalog API and get the right release? This decides how much S11 (barcode scan, lookup, `catalog_cache`) can carry versus falling back to the AI reading the box.

## Setup

- 15 phone photos (HEIC) of items with barcodes: 7 movies, 3 games, 5 other. Photos stay local and are gitignored.
- **Reading:** zxing-cpp on the full photo, then retries (contrast, resize, 3x3 enlarged crops, denoise), then `gpt-6-luna` (low effort, high detail) reads the printed digits and is marked "model-read". Every result gets a UPC-A / EAN-13 check-digit test.
- **Lookup:** UPCitemdb free trial endpoint (no key, 100 a day), only for checksum-valid codes, spaced 11 s apart, every response cached to `cache/upcitemdb/` (the future `catalog_cache`).
- **Judging:** `review.py` (local, 127.0.0.1). I labeled each item's type and marked the lookup right / close / wrong / not found, with nothing prefilled. Scores are in [results/SCORES.md](results/SCORES.md).
- Run order: `extract.py`, `prep.py`, `decode.py`, `lookup.py`, `review.py`, `score.py` (all with `.venv\Scripts\python.exe -I`).

## Results

| Measure | Result |
|---|---|
| Decoded by zxing (full photo + retries) | 7/15 (47%): 6 full photo, 1 after resize |
| Decoded with the model fallback | 11/15 (73%) |
| Checksum-valid | 10/15 (67%) |
| Lookup hit rate (valid codes) | 8/10 (80%): movies 6/6, games 2/2, other 0/2 |
| Hits that are right or close | 8/8: 7 right, 1 close |
| End to end, right or close | 8/15 (53%); 5/15 (33%) without the model fallback |
| Needed the AI to read the box | 7/15 (47%) |
| Cost | OpenAI $0.0035 (8 calls); UPC lookups free (10 of 100 daily) |

By type, end to end (right or close, of photos): movies 6/7, games 2/3, other 0/5.

What I saw:

- **When the API has the code, it is right.** All 8 hits were the right product. The one "close" was Smash Bros Melee, titled "Restored Super Smash Bros Melee" (right game and platform, wrong edition name).
- **The misses were not media.** Both lookup misses were Nintendo Switch 2 controllers. The other 3 unreadable-by-everything photos were an Xbox (barcode too blurry), a ceramic ocarina with only an Amazon SKU sticker, and a laptop with no product barcode. All five "other" items failed.
- **The checksum earned its keep.** The model misread IMG_9427 by one digit (`...600397` instead of `...900397`). The check digit flagged it, so no wrong lookup was made. My corrected digits pass the checksum. Model-read digits matched the photo 3 of 4 times, so they must always be checksum-gated.
- **Missing fields:** the API returns a title, brand, category and description only. A keyword match on that text found 19 of the 26 fields we need (73%). Movie titles often carry the format ("[Blu-ray]") and sometimes the edition ("Limited Edition Steelbook"). Games lack format, and the Zelda Switch 2 title has no sign of the foil-cover limited edition I own. The edition question stays a one-tap follow-up.
- **Blurry photos are the main decode failure.** Two close-up barcodes were too soft for the decoder and the model. In the app the browser reads the barcode live from the camera, so the user can refocus; this test used single photos, so it is the harder case.
- **Free-tier limits:** no limit was hit. The API reports 100 lookups a day (90 left after this run), and I never found out where the per-minute cap bites because I paced calls 11 s apart.

## Conclusion for S11

**Use UPCitemdb first for movies, TV and games, but plan for it to be only part of the path.** For items that have a retail barcode in the catalog it was always right (8/8) and it is cheap, so S11 should check `releases` by barcode, then `catalog_cache`, then UPCitemdb, with no AI call. It will not carry the whole intake: only 53% of this mixed set ended in a right or close release (86% of movies, 67% of games, 0% of "other"). Items with unlisted barcodes, no barcode or a blurry one fall back to the AI reading the box, and that is nearly half the items. Gate every barcode behind the check-digit test, treat model-read digits as unverified until it passes, and expect the edition to be a follow-up question. A second source (Open Library for ISBNs, plus a games source such as IGDB) is worth testing before S12, because this set had no books and the lookup said little about game format and edition.
