# Collection tracker: AI intake feasibility test

The riskiest part of the "track anything" collection app is **AI intake**: I photograph something I own, and the app
proposes a card (category, name, brand, edition, platform, useful attributes, sealed or opened, a catalog match) for
me to confirm. If I have to rewrite most cards, intake is not worth building. This test measures how often the card
is right, using 26 photos of real things I own.

Claude built the harness. The answer key is mine: I wrote 13 rows by hand and corrected the other 13 from Luna's
prefilled cards (see the caveat below).

## Verdict: AI intake works, use Luna

| Setup | Category right | Right item (exact or close) | Exact item | Accept as is | **As is or 1 edit** | Cost per 1,000 photos | Median time |
|---|---|---|---|---|---|---|---|
| Luna, 2048 px | 92% | 100% | 46% | 38% | 73% | $0.52 | 4.4 s |
| **Luna, 768 px** | 96% | 100% | 42% | 38% | **85%** | **$0.27** | 4.3 s |
| Sol, 2048 px | 96% | 92% | 42% | 35% | 73% | $9.53 | 3.0 s |
| Sol, 768 px | 96% | 96% | 38% | 35% | 81% | $4.89 | 3.2 s |

Sealed vs opened was right 25 of 26 times in every setup (all four missed the sealed LEGO set). Full per-photo
judgments: [results/SCORES.md](results/SCORES.md).

- **Luna always recognized the item.** All 26, from the Hyrule Edition 3DS XL to a Russell M. Nelson quote print and
  a "Mr. & Mrs." pumpkin. Sol was no better and twice confidently wrong (the popcorn tin as a "wastebasket", the
  blanket as a "pillow cover"), at 18x the cost. Intake costs well under a tenth of a cent per photo.
- **Most fixes are details a single photo can't show:** steelbook, Deluxe or XL editions, capacity, "for the New
  3DS XL", the four film titles in a box set, sealed or not. For about 8 of Luna's 12 one-edit cards, its
  follow-up question asked for exactly the missing detail ("Blu-ray or DVD?", "what is this case designed to
  carry?", "which Spider-Man movie is this tin from?"). So in the product, `ask_user` should be a one-tap question
  on the confirmation card, not a hidden field.
- **New releases are a blind spot.** The Ocarina of Time Switch 2 remake and the "I Play Rocky" cup are newer than
  the model's knowledge, so it fell back to the old game and the Rocky franchise. A catalog lookup (IGDB, UPC,
  TMDB) is what fixes recency, not a bigger model.
- **Image size: 768 px is enough, with one exception.** It scored as well as full size at half the cost, but it read
  the DBZ Blu-ray set as DVD, because the format logo got too small. The product should send roughly 1024 px, or a
  full-size crop of the label when the format matters. Either way the cost is negligible.
- **Catalog lookups need code-side fallbacks.** Only 2-3 movie cards got a TMDB hit. Luna's search text included
  extras ("Princess Mononoke (1997)", "...Motion Picture Trilogy") that TMDB's search doesn't match. The fix fits
  Continuity's pattern, "the model proposes, the code decides": have the model return a clean title, year and kind,
  then let code search with fallbacks (title only, then movie instead of collection).
- **My answers changed the data model.** Almost every row has a condition grade (CIB, like new, very good), where
  I got it (eBay, Right Stuf, Orem Cinemark, a wedding registry gift from a named person) and an approximate date
  ("2021 or 2022"). Those should be real columns (`condition_grade`, `acquired_from`, `gift_from`,
  `acquired_on` + `date_is_approximate`, as in Continuity), not notes.

### Caveats

- 26 photos, so treat every percentage as roughly +/-15 points. The Luna-vs-Sol and 768-vs-2048 gaps are within
  that noise. The clear results are "Luna is enough" and "most fixes need info that isn't in the photo".
- 13 answers were corrected from Luna's prefilled card, which can flatter Luna slightly.
- The judge (Sol) is strict. It counts any detail missing from my answer key as "invented" (a candle's scent notes,
  a digital-code deadline printed on the box), so the "invented details" counts in SCORES.md are an upper bound.
  The real hallucinations were few: the Sol wastebasket and pillow cover, a CREAMi "Scoop & Swirl", and DVD vs Blu-ray.
- One photo per item, good light, plain background.

Total API spend: about $0.67 (intake $0.38, judging $0.28) on the class OpenAI key.

## How the answer key was made

The fast way: run **`py -3.13 review.py`**. It opens a local page (127.0.0.1 only) with each photo next to a form.
Rows I've already written load as they are; empty fields are prefilled from Luna's card. I fix what's wrong and press
Enter, and it saves to `answers.csv` straight away. The `edited` column records which prefilled fields I changed.
Caveat: seeing Luna's guess first may make me accept it more readily, which slightly flatters Luna. The first 13
rows were written by hand without it.

The columns, if editing `answers.csv` directly:

| Column | What to write | Example |
|---|---|---|
| `name` | What it actually is, named the way I'd want it in the app | `New Nintendo 3DS XL Hyrule Edition` |
| `category` | Where I'd look for it, from the list below. If more than one is fine, separate them with `\|` | `Kitchen > Drinkware & Dishes \| Collectibles & Memorabilia` |
| `must_have_details` | What a card must get right to count as exactly right (edition, format, model). Blank if the name is enough | `4K UHD`, `steelbook`, `Hyrule Edition` |
| `condition` | `sealed`, or a grade like `open / like new` or `very good`. Only "sealed" is scored | `sealed` |
| `notes` | Where and when I got it, anything else (optional) | `bought at the theater` |

Broad categories are fine: "Video Games" accepts any card under Video Games. My own names ("Fall Home Decor",
"Movie or Cinema Memoribilia") are mapped to the tree in `score.py` (`ALIASES`).

Categories (the starter tree from the design: brands and platforms are attributes, not categories):
Video Games > Games / Consoles / Controllers / Accessories · Movies & TV > Physical media ·
Books > Novels / Manga & Comics / Other · Board Games & Puzzles · Toys & Building Sets ·
Music > Instruments / Albums & Vinyl · Collectibles & Memorabilia ·
Home Decor > Wall art & Frames / Seasonal / Candles & Fragrance / Other ·
Kitchen > Appliances / Drinkware & Dishes · Bags & Cases · Clothing & Textiles ·
Tools > Tool sets / Hand & Power tools · Electronics > Other · Other

Then run `py -3.13 score.py`. Rows I leave blank are skipped, so it also works on a partly filled key.

## How it's scored

- **Category right** and **sealed/opened right** are checked by code, directly against my answers.
- A Sol judge compares each card to my answer and reports:
  - **Exact / close / wrong:** "close" means the right thing but a must-have detail is missing or wrong.
  - **Fields to fix:** how many fields I'd have to change. This gives the headline number, **"as is or 1 edit"**: the share of
    cards I'd accept almost immediately.
  - **Invented details:** claims that contradict my answer or that the photo can't support. Hallucinations are
    worse than gaps, since a gap gets a follow-up question instead.
  - **TMDB top match:** for movie and TV items, whether the first search result is the right title.
- Every judgment and its one-line reason are in `results/SCORES.md`, so I can overrule the judge.

## Files

| File | What it does |
|---|---|
| `intake.py` | Photo → proposed card (structured output, fixed category list), plus a TMDB search for movies and TV. `py -3.13 intake.py <name> --model gpt-6-luna --effort low --size 2048` |
| `review.py` | Local review page for the answer key: photo + form prefilled from Luna, saves to `answers.csv` |
| `score.py` | Scores every `results/cards_*.jsonl` against `answers.csv` → `results/SCORES.md`. Judgments are cached in `results/judgments.jsonl` |
| `llm.py` | Shared OpenAI call with image input and cost logging (prices from Continuity's `usage.py`) |
| `answers.csv` | The answer key I fill in |
| `results/cards_*.jsonl` | The 26 proposed cards for each setup |
| `results/usage.jsonl` | Tokens, cost and latency for every call |
| `photos/` | HEIC originals, stripped JPEGs and a contact sheet. **Gitignored**: photos of my home stay off GitHub |

## Limitations

- 26 photos, one photo per item, in good light on a plain background. Real intake will include shelves, bad
  angles and several items in one photo.
- Catalog matching is only tested for movies and TV (TMDB). IGDB (games and consoles) needs a Twitch developer
  account, and BoardGameGeek and Rebrickable (LEGO) need registration, so for those the test only checks
  identification, not the catalog lookup.
- The judge is also an LLM. The per-photo reasons are there so I can check it.
