// Spoiler Shield feasibility probe (test 2). No network calls: it only checks the page side.
// 1. Find every comment on new Reddit (<shreddit-comment>) and old Reddit (.thing.comment), including ones that
//    load later (infinite scroll, "more replies"), using a MutationObserver.
// 2. Every comment starts blurred by blur.css. After a fake 400 ms "verdict", comments that mention a test word
//    stay blurred (click to reveal); the rest are revealed.
// 3. A panel in the corner reports counts and timings; "Copy report" puts a JSON summary on the clipboard.

const FAKE_VERDICT_MS = 400;
const TEST_WORDS = /\b(dies|died|dead|killed|kills|death|pregnant|luthen|kleya|syril)\b/i;
const seen = new Map(); // id -> {found, depth, chars, verdict}
const t0 = performance.now();
let firstFoundAt = null;

function readComment(el) {
  if (el.tagName === 'SHREDDIT-COMMENT') {
    const body = el.querySelector(':scope > [slot="comment"]');
    return body && { id: el.getAttribute('thingid'), depth: +el.getAttribute('depth') || 0, body, text: body.innerText };
  }
  const body = el.querySelector(':scope > .entry .usertext-body'); // old.reddit
  return body && { id: el.getAttribute('data-fullname'), depth: el.closest('.child') ? 1 : 0, body, text: body.innerText };
}

function handle(el) {
  const c = readComment(el);
  if (!c || !c.id || seen.has(c.id)) return;
  const found = performance.now();
  firstFoundAt ??= found;
  seen.set(c.id, { found: Math.round(found - t0), depth: c.depth, chars: c.text.length, verdict: 'pending' });
  setTimeout(() => {
    const spoiler = TEST_WORDS.test(c.text);
    seen.get(c.id).verdict = spoiler ? 'spoiler' : 'safe';
    if (spoiler) {
      c.body.classList.add('ss-spoiler');
      c.body.title = 'Spoiler Shield probe: click to reveal';
      c.body.addEventListener('click', () => c.body.classList.replace('ss-spoiler', 'ss-safe'), { once: true });
    } else {
      c.body.classList.add('ss-safe');
    }
    render();
  }, FAKE_VERDICT_MS);
  render();
}

function scan(root) {
  if (!(root instanceof Element)) return;
  if (root.matches('shreddit-comment, .thing.comment')) handle(root);
  root.querySelectorAll('shreddit-comment, .thing.comment').forEach(handle);
}

let panel;
function render() {
  if (!document.body) return;
  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'ss-probe';
    document.body.appendChild(panel);
  }
  const v = [...seen.values()];
  const count = (k) => v.filter((x) => x.verdict === k).length;
  panel.innerText = `Spoiler Shield probe (${location.host})
comments found: ${v.length} (replies: ${v.filter((x) => x.depth > 0).length})
pending ${count('pending')} · safe ${count('safe')} · test-word ${count('spoiler')}
first comment found at ${firstFoundAt ? Math.round(firstFoundAt - t0) : '-'} ms
latest found at ${v.length ? Math.max(...v.map((x) => x.found)) : '-'} ms (scroll to load more)`;
  const btn = document.createElement('button');
  btn.textContent = 'Copy report';
  btn.onclick = () => navigator.clipboard.writeText(JSON.stringify({
    url: location.href, host: location.host, found: v.length, replies: v.filter((x) => x.depth > 0).length,
    empty_text: v.filter((x) => x.chars === 0).length, first_found_ms: firstFoundAt && Math.round(firstFoundAt - t0),
    verdicts: { safe: count('safe'), spoiler: count('spoiler'), pending: count('pending') },
    userAgent: navigator.userAgent,
  }, null, 2));
  panel.appendChild(document.createElement('br'));
  panel.appendChild(btn);
}

new MutationObserver((muts) => muts.forEach((m) => m.addedNodes.forEach(scan)))
  .observe(document.documentElement, { childList: true, subtree: true });
document.addEventListener('DOMContentLoaded', () => { scan(document.documentElement); render(); });
