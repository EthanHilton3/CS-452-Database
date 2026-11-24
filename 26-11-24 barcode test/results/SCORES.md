# Barcode scores (15 of 15 photos fully judged)

## 1. Reading the barcode from the photo

| Measure | Result |
|---|---|
| Decoder on the full photo | 6/15 (40%) |
| Decoder after retries (contrast, resize, crops) | 1/15 (7%) |
| Model read the digits (gpt-6-luna) | 4/15 (27%) |
| No digits at all | 4/15 (27%) |
| **Decode rate, decoder only** (full + retry) | 7/15 (47%) |
| **Decode rate, with model fallback** | 11/15 (73%) |
| **Checksum-valid** (of all photos) | 10/15 (67%) |
| Checksum-valid (of photos that produced digits) | 10/11 (91%) |
| Model-read digits that match the photo (my check) | 3/4 (75%) of 4 read; 0 unchecked |

Photos by how the barcode was obtained: 9420 model-read, 9421 retry, 9422 decoder, 9423 none, 9424 decoder, 9425 decoder, 9426 model-read, 9427 model-read (bad checksum), 9428 decoder, 9429 decoder, 9430 decoder, 9431 model-read, 9432 none, 9433 none, 9435 none

## 2. Catalog lookup (UPCitemdb free trial endpoint)

| Measure | Result |
|---|---|
| Looked up (valid checksum only) | 10 of 15 |
| **Lookup hit rate** (of looked up) | 8/10 (80%) |
| Hit rate counting every photo | 8/15 (53%) |
| Hits judged right | 7/8 (88%) |
| Hits judged close | 1/8 (12%) |
| Hits judged wrong or not found | 0/8 (0%) |
| **Hits that are right or close** | 8/8 (100%) |
| **End to end** (right or close, of all 15 photos) | 8/15 (53%) |

## 3. By item type (my labels)

| Type | Photos | Decoded & valid | Looked up | Hits | Hit rate | Right | Close | Wrong / not found | Right or close (of hits) | End to end (of photos) |
|---|---|---|---|---|---|---|---|---|---|---|
| movie | 7 | 6 | 6 | 6 | 6/6 (100%) | 6 | 0 | 0 | 6/6 (100%) | 6/7 (86%) |
| game | 3 | 2 | 2 | 2 | 2/2 (100%) | 1 | 1 | 0 | 2/2 (100%) | 2/3 (67%) |
| other | 5 | 2 | 2 | 0 | 0/2 (0%) | 0 | 0 | 0 | 0/0 (n/a) | 0/5 (0%) |

## 4. Fields the API gave us (hits only)

Heuristic text match on title, brand, description and category (see lookup.py). "name" is the API title; edition, format and platform are only counted when a keyword appears.

| Photo | Type | name | edition | format | platform | Useful fields |
|---|---|---|---|---|---|---|
| 9420 | movie | yes | Extended | 4K | n/a | 3/3 |
| 9421 | movie | yes | Ultimate | Blu-ray | n/a | 3/3 |
| 9422 | movie | yes | Limited | Blu-ray | n/a | 3/3 |
| 9424 | movie | yes | - | Blu-ray | n/a | 2/3 |
| 9425 | movie | yes | - | Blu-ray | n/a | 2/3 |
| 9426 | game | yes | - | - | Nintendo GameCube | 2/4 |
| 9428 | game | yes | - | - | Nintendo Switch 2 | 2/4 |
| 9431 | movie | yes | - | Blu-ray | n/a | 2/3 |

Across all hits: 19/26 (73%) of the fields we need were present (platform counted for games only).

## 5. Which items would have needed the AI fallback

An item needs the fallback (the AI reads the box) when the barcode path did not end in a right-or-close release.

| Photo | Type | Why |
|---|---|---|
| 9423 | movie | no readable barcode |
| 9426 | game | (close: the barcode path works but a detail needs the AI or a question) |
| 9427 | game | digits read but checksum invalid |
| 9429 | other | lookup miss |
| 9430 | other | lookup miss |
| 9432 | other | no readable barcode |
| 9433 | other | no readable barcode |
| 9435 | other | no readable barcode |

**Needed the AI fallback: 7/15 (47%)** (8/15 (53%) if "close" results also count as needing the AI for the missing detail).
- The zxing decoder failed on 8 photos. The model read a valid code on 3 of them, and 3 of those were right or close.
- End to end **without** the model fallback (decoder + lookup only): 5/15 (33%) right or close. With it: 8/15 (53%).

## 6. Cost and free-tier limits

- OpenAI: 8 calls, $0.0035 total (results/usage.jsonl).
- UPCitemdb: 10 lookups, cached to cache/upcitemdb/. The trial endpoint reported a limit of 100 per day; remaining after the run: 90. Requests were spaced 11 s apart to stay under the per-minute cap.
