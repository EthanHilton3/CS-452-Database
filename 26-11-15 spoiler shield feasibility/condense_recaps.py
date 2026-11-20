"""One-time job: turn each long Wookieepedia plot summary into a short "reveal sheet".

A reveal sheet lists what a viewer learns in that episode that would spoil it for someone who hasn't seen it:
deaths, betrayals, identities, who survives, new characters or places, major plot turns.
In the product this runs once per episode and is stored (units.reveal_sheet), never per comment.
Run: py -3.13 condense_recaps.py
"""
import json
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from llm import HERE, parse

MODEL = 'gpt-6-luna'
SYSTEM = """You write spoiler reference sheets for a TV show, used by a spoiler filter.
Given one episode's full plot summary, list the facts a viewer learns in THIS episode that would spoil it
for someone who hasn't watched it yet. Prioritise: deaths, injuries, captures, escapes, betrayals, reveals of
identity or allegiance, relationships, big decisions, how storylines end, and the first appearance of
characters, places, ships or objects that later get discussed. Use the names fans would use.
Each fact is one short sentence. 8 to 15 facts. No praise, no analysis."""


class Sheet(BaseModel):
    facts: list[str]
    new_names: list[str]  # characters/places/things that first matter in this episode


def condense(ep: dict, log) -> dict:
    sheet, _ = parse(MODEL, SYSTEM, f'Episode {ep["code"]} "{ep["title"]}"\n\n{ep["plot"]}', Sheet,
                     log=log, tag=f'condense {ep["code"]}')
    return {'order': ep['order'], 'code': ep['code'], 'title': ep['title'],
            'facts': sheet.facts, 'new_names': sheet.new_names}


def main() -> None:
    raw = json.loads((HERE / 'data' / 'recaps_raw.json').read_text(encoding='utf-8'))
    log = HERE / 'results' / 'usage_condense.jsonl'
    log.unlink(missing_ok=True)
    with ThreadPoolExecutor(6) as pool:
        sheets = list(pool.map(lambda e: condense(e, log), raw))
    (HERE / 'data' / 'reveal_sheets.json').write_text(json.dumps(sheets, indent=2, ensure_ascii=False),
                                                      encoding='utf-8')
    recs = [json.loads(l) for l in log.read_text().splitlines()]
    words = [len(' '.join(s['facts']).split()) for s in sheets]
    print(f'{len(sheets)} sheets, {sum(words) // len(words)} words avg; '
          f'{sum(r["input_tokens"] for r in recs)} in / {sum(r["output_tokens"] for r in recs)} out tokens, '
          f'${sum(r["cost_usd"] for r in recs):.4f}')


if __name__ == '__main__':
    main()
