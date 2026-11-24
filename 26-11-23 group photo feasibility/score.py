"""Scores the three setups against answers.json (made with review.py) -> results/SCORES.md.   py -3.13 score.py"""
import scoring

res, ans = scoring.load_results(), scoring.load_answers()
tab, prog = scoring.summarize(res, ans), scoring.progress(res, ans)
L = scoring.LABELS
lines = [f'# Group photo scores ({prog["done"]} of {prog["total"]} photos fully judged)\n',
         '| Setup | Photos | Items listed | Right | Close | Wrong | Duplicate | Precision (right+close) | '
         'Strict precision | Recall | Strict recall | Hallucination rate | Cost / photo | Avg time |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
for s in scoring.SETUP_FILES:
    t = tab[s]
    n = t['photos'] or 1
    lines.append(f'| {L[s]} | {t["photos"]} | {t["listed"]} | {t["right"]} | {t["close"]} | {t["wrong"]} | {t["dup"]} | '
                 f'{t["precision"]:.0%} | {t["strict_precision"]:.0%} | {t["recall"]:.0%} | {t["strict_recall"]:.0%} | '
                 f'{t["hallucination"]:.0%} | ${t["cost"]/n:.4f} | {t["avg_latency"]:.0f}s |')
lines += ['', '- **Right**: the item and the details I care about are correct. **Close**: right item, but a detail is wrong or missing.',
          '- **Recall** = (right + close) / number of entries a perfect list would have (my count per photo).',
          '- **Duplicate** items are real but listed twice; they count against precision, not as hallucinations.', '']
missed = [(p, a['missed']) for p, a in sorted(ans.items()) if a.get('missed')]
if missed:
    lines.append('## What was missed (my notes)\n')
    lines += [f'- **{p}**: {m}' for p, m in missed]
(scoring.RESULTS / 'SCORES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))
