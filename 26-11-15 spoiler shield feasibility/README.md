# Spoiler Shield feasibility test

Before committing my CS 452 final project to Spoiler Shield (a Chrome extension that hides Reddit comments spoiling
episodes I haven't watched yet), this checks the two riskiest parts:

1. **Can an LLM tell how far into a show a comment spoils?** Tested on 170 real r/andor comments.
2. **Can an extension find and blur Reddit comments before you read them?** A probe extension, which I still need to run.

Claude built the test harness and drafted the labels. All results are provisional until I review the labels.

## Results so far (labels not yet reviewed)

Viewers are simulated at every point from S1E1 to S2E11. "Caught" means a real spoiler got hidden, and "blurred"
means a safe comment got hidden anyway.

**General threads** are the realistic case: browsing r/andor partway through the show. There are 50 comments, about 15 of them spoilers.

| Approach | Spoilers caught | Safe comments blurred | Cost per 1,000 comments | Latency per batch of 10 |
|---|---|---|---|---|
| Keyword blocker (no AI) | 39% | 15% | $0 | instant |
| Luna, no show info (its own knowledge) | 77% | 4% | $0.14 | ~27 s |
| Luna + TMDB one-line overviews | 86% | 2% | $0.13 | ~24 s |
| **Luna (low effort) + reveal sheets** | **91%** | **4%** | **$0.05** | **~7 s** |
| Sol (low effort) + reveal sheets | 99% | 7% | $0.75 | ~5 s |

On all 170 comments, the best Luna setup caught 76% of spoilers and blurred 3% of safe comments. Most of the misses
are short replies like "Dead is dead" or "he sleeps with the sarlaccs", which only make sense in context.
The full tables and every miss are in [results/SCORES.md](results/SCORES.md).

## What it means for the design

- **The AI is clearly needed.** A keyword blocker catches 39% and blurs 15% of safe comments. Spoilers are usually
  about events ("she's the loose end, she dies"), not names.
- **Reveal sheets are the key data.** TMDB overviews average 13 words per episode, which is too thin. Condensing each
  Wookieepedia plot summary into about 200 words of "what this episode reveals" cost $0.03 once for the whole show.
  In the product that's a `units.reveal_sheet` column computed once per episode, never per comment.
- **Label each comment once.** The model answers "the latest episode this comment reveals", which is the same for
  everyone. One call serves every viewer, and each viewer only compares that number to their own progress. That's
  what makes a shared Redis cache work.
- **Use Luna at low effort.** It's as accurate as default effort at half the cost and less than half the latency.
  `none` effort is faster but noticeably worse and returns broken JSON now and then (2 retries in 34 calls), so
  retries are needed either way. Sol isn't worth 15× the cost here.
- **Don't feed the model the thread title.** With "[S2 EP9 SPOILERS] Megathread" in view, it starts tagging harmless
  praise as an E9 spoiler, and false blurs on general threads went from 4% to 15%. Megathreads are better handled
  by a plain rule: hide the whole thread from anyone who hasn't reached that episode.
- **7 seconds is too slow to wait on.** Comments stay blurred until a verdict arrives (CSS blurs them before the page
  paints), so the cache does the heavy lifting: the first viewer of a thread waits, everyone after gets instant
  verdicts. Popular threads could be classified ahead of time.
- **Cost at scale:** $0.05 per 1,000 new comments. Even 100k new comments a day is about $5/day, no matter how many
  people use it, because verdicts are shared.

## What I still need to do

1. **Review the labels** in [labels.csv](labels.csv), about 30–45 minutes:
   - Each row has Claude's draft `label`: the latest episode the comment reveals (`S2E10`), or `none`. `outside` is
     `rogue_one` when it spoils the movie.
   - Start with the 33 rows where `claude_confidence` is `low`.
   - Fix the label if it's wrong, then change `status` from `needs Ethan's label` to `labeled`.
   - Then run `py -3.13 score.py`. The header says how many labels are reviewed.
   - Claude already got 5 wrong (#130–135 are S2E10, not E11), and every model caught it, so expect more.
2. **Run the extension probe** (test 2, about 5 minutes):
   - Go to `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, and pick the `extension_probe` folder.
   - Open a big r/andor thread, for example the S2E12 megathread, and scroll for a bit.
   - Check: are comments blurred the instant they appear, with no flash of text first? Do comments with test words
     ("dies", "Luthen", "Kleya"...) stay blurred until clicked? Does the corner panel's count keep growing as you scroll?
   - Click **Copy report** and paste it to Claude. Try old.reddit.com too.
   - Remove the extension afterwards.
3. **Decide what to commit.** `data/comments.jsonl` and `labels.csv` contain public Reddit comment text (no usernames).
   `data/recaps_raw.json` is Wookieepedia text (CC BY-SA). Consider keeping those out of a public repo.

## How the pieces fit together

| File | What it does |
|---|---|
| `fetch_episodes.py` | Pulls Andor's 24 episodes and overviews from TMDB (key from `continuity/.env`) → `data/episodes.json` |
| `fetch_recaps.py` | Pulls each episode's Wookieepedia plot summary → `data/recaps_raw.json` |
| `condense_recaps.py` | One-time Luna job: each plot summary → a reveal sheet → `data/reveal_sheets.json` |
| `collect/fetch_comments.py` | Samples 170 comments from 20 episode megathreads and 5 general threads (Arctic Shift archive, because Reddit's API blocks unauthenticated access) → `data/comments.jsonl` |
| `collect/fetch_context.py` | Adds each comment's thread title and parent comment (for the `--context` runs) |
| `labels.csv` | The answer key: Claude's draft labels, for me to review |
| `baseline.py` | The no-AI keyword blocker |
| `classify.py` | The classifier. `py -3.13 classify.py sheets --effort low [--model gpt-6-sol] [--context]` |
| `llm.py` | Shared OpenAI call, structured output and cost logging (prices from Continuity's `usage.py`) |
| `score.py` | Scores every `results/pred_*.jsonl` → `results/SCORES.md` |
| `extension_probe/` | Manifest V3 test extension: blur-first CSS, a MutationObserver to find comments, a fake verdict after 400 ms |

Total API spend for everything above: about **$0.25** (class OpenAI key).

## Limitations

- One show, and a famous one. Luna already knew Andor well enough to catch 77% of spoilers with no show info, so a
  less-known show will lean much harder on reveal sheets.
- 170 comments, only 50 from general threads, so treat the percentages as ±10 points.
- The labels are Claude's drafts, and the models being tested are also LLMs, which can inflate agreement.
  The numbers count only once I've reviewed them.
- Comments came from an archive, not the live page, so whether real pages behave is what the probe checks.
