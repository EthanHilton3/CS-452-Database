"""Judge page for the barcode test. Local only (127.0.0.1): photos never leave this machine.

Run: .venv\\Scripts\\python.exe review.py     -> opens http://127.0.0.1:8454
For each photo: (1) say what kind of item it is, (2) compare the photo with what the lookup returned and mark it
right / close / wrong / not found. Nothing is prefilled. Every click saves to answers.json; stop and come back any time.
Then run: .venv\\Scripts\\python.exe -I score.py
"""
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import data

PHOTOS = HERE / 'photos' / 'jpg'
PORT = 8454


def payload() -> dict:
    ans = data.load_answers()
    out = []
    for r in data.rows():
        lk = r['lookup']
        out.append({'photo': r['photo'], 'digits': r['digits'], 'method': r['method'], 'variant': r['variant'], 'kind': r['kind'],
                    'checksum_valid': r['checksum_valid'], 'model_note': r.get('model_note'), 'other_reads': [
                        f"{x['format']}: {x['text'] or '(unreadable)'}" for x in r['all_reads'] if x['format'] not in ('UPC-A', 'EAN-13')],
                    'looked_up': bool(lk.get('looked_up')), 'hit': lk.get('hit'), 'title': lk.get('title'), 'brand': lk.get('brand'),
                    'category': lk.get('category'), 'model': lk.get('model'), 'description': lk.get('description'),
                    'fields': lk.get('fields') or {}, 'answer': ans.get(r['photo'], {}), 'done': data.is_done(r, ans.get(r['photo'], {}))})
    return {'photos': out, 'types': data.TYPES}


def save(photo: str, patch: dict) -> None:
    ans = data.load_answers()
    ans.setdefault(photo, {}).update(patch)
    tmp = data.ANSWERS.with_suffix('.tmp')
    tmp.write_text(json.dumps(ans, indent=1, ensure_ascii=False), encoding='utf-8')
    tmp.replace(data.ANSWERS)


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Barcode judge</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#dcdad5;--acc:#2f6f5e;--right:#2f7d4f;--close:#b58a1d;--wrong:#b3412f;--nf:#6b6b9a}
@media (prefers-color-scheme:dark){:root{--bg:#18191b;--card:#232427;--ink:#ececee;--mute:#9a9aa1;--line:#3a3b3f;--acc:#6cc3a8;--right:#5bbf84;--close:#e0b34a;--wrong:#e07766;--nf:#9a9ad0}}
*{box-sizing:border-box}body{margin:0;font:14px/1.4 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{display:flex;gap:12px;align-items:center;padding:10px 16px;border-bottom:1px solid var(--line);flex-wrap:wrap}
header b{font-size:16px}#prog{color:var(--mute)}#strip{display:flex;gap:4px;flex-wrap:wrap;margin-left:auto}
#strip button{min-width:34px;height:26px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--mute);font-size:11px;cursor:pointer}
#strip button.done{background:var(--acc);color:#fff;border-color:var(--acc)}#strip button.cur{outline:2px solid var(--ink)}
main{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:14px;padding:14px;height:calc(100vh - 56px)}
@media (max-width:900px){main{grid-template-columns:1fr;height:auto}}
#view{overflow:auto;background:#000;border-radius:10px;position:relative;cursor:zoom-in}
#view.zoom{cursor:zoom-out}#img{display:block;width:100%}#view.zoom #img{width:260%;max-width:none}
#hint{position:absolute;left:8px;bottom:8px;background:#000a;color:#fff;font-size:12px;padding:3px 8px;border-radius:6px;pointer-events:none}
#side{display:flex;flex-direction:column;gap:10px;min-height:0;overflow:auto}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.box h3{margin:0 0 6px;font-size:12px;color:var(--mute);font-weight:600;text-transform:uppercase;letter-spacing:.04em}
.row{display:flex;gap:5px;flex-wrap:wrap}.row button{flex:1;min-width:70px;padding:7px 4px;border:1px solid var(--line);border-radius:7px;background:var(--bg);color:var(--ink);cursor:pointer;font-size:13px}
.row button.on{background:var(--ink);color:var(--bg)}.row .right.on{background:var(--right);color:#fff}.row .close.on{background:var(--close);color:#fff}
.row .wrong.on{background:var(--wrong);color:#fff}.row .not_found.on{background:var(--nf);color:#fff}
.digits{font:600 20px ui-monospace,Consolas,monospace;letter-spacing:.05em}.m{color:var(--mute);font-size:12px}.t{font-size:16px;font-weight:600}
.pill{display:inline-block;padding:1px 8px;border-radius:99px;font-size:12px;border:1px solid var(--line);margin-right:4px}
textarea{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:7px;padding:6px 8px;width:100%}
.help{font-size:12px;color:var(--mute)}
</style></head><body>
<header><b>Barcode judge</b><span id="prog"></span><div id="strip"></div></header>
<main>
<div id="view"><img id="img" alt=""><div id="hint">click to zoom</div></div>
<div id="side">
  <div class="box"><h3>1. What kind of item is this?</h3><div class="row" id="types"></div></div>
  <div class="box"><h3>Barcode read from the photo</h3><div id="read"></div></div>
  <div class="box" id="digitsbox" style="display:none"><h3>Model-read digits: do they match the barcode in the photo?</h3>
    <div class="row" id="digitsrow"></div></div>
  <div class="box" id="lookupbox"><h3>2. What the catalog lookup returned</h3><div id="lookup"></div><div class="row" id="verdicts" style="margin-top:8px"></div></div>
  <div class="box"><h3>Notes (optional)</h3><textarea id="note" rows="2"></textarea></div>
  <div class="help">Keys: <b>m</b> movie · <b>g</b> game · <b>b</b> book · <b>u</b> music · <b>o</b> other · <b>1</b> right · <b>2</b> close · <b>3</b> wrong · <b>4</b> not found · <b>y/x</b> digits match / don't · <b>n/p</b> next/prev. Right = the exact release I own (right edition and format). Close = right title, wrong edition/format/platform. Wrong = a different product. Not found = nothing useful came back.</div>
</div></main>
<script>
let D, pi = 0; const $ = id => document.getElementById(id);
const TK = {m:'movie', g:'game', b:'book', u:'music', o:'other'};
const VS = [['right','1 Right'],['close','2 Close'],['wrong','3 Wrong'],['not_found','4 Not found']];
const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const cur = () => D.photos[pi];
function firstOpen(){ const k = D.photos.findIndex(p => !p.done); return k < 0 ? 0 : k; }
function render(){
  const p = cur(), a = p.answer;
  const src = '/photo/' + p.photo + '.jpg'; if ($('img').getAttribute('src') !== src) { $('img').src = src; $('view').classList.remove('zoom'); $('hint').style.display = ''; }
  $('types').innerHTML = ''; D.types.forEach(t => { const b = document.createElement('button'); b.textContent = t; b.className = a.type === t ? 'on' : '';
    b.onclick = () => set({type: t}); $('types').appendChild(b); });
  let r = '';
  if (p.digits) r += '<div class="digits">' + esc(p.digits) + '</div><div class="m"><span class="pill">' + esc(p.method) + (p.variant && p.method === 'retry' ? ' · ' + esc(p.variant) : '') + '</span><span class="pill">' + esc(p.kind) + '</span><span class="pill">checksum ' + (p.checksum_valid ? 'valid' : 'INVALID') + '</span></div>';
  else r += '<div class="t">No digits could be read</div>';
  if (p.model_note) r += '<div class="m">Model note: ' + esc(p.model_note) + '</div>';
  if (p.other_reads.length) r += '<div class="m">Other codes seen: ' + p.other_reads.map(esc).join(' · ') + '</div>';
  $('read').innerHTML = r;
  $('digitsbox').style.display = p.method === 'model-read' && p.digits ? '' : 'none';
  $('digitsrow').innerHTML = ''; [['yes','y  Digits match'],['no','x  Digits do not match']].forEach(([k, l]) => { const b = document.createElement('button');
    b.textContent = l; b.className = a.digits_match === k ? 'on' : ''; b.onclick = () => set({digits_match: k}); $('digitsrow').appendChild(b); });
  const lb = $('lookupbox');
  if (!p.looked_up) { $('lookup').innerHTML = '<div class="m">' + (p.digits ? 'Checksum invalid, so no lookup was made.' : 'No valid barcode, so no lookup was made. This item would need the AI to read the box.') + '</div>'; $('verdicts').innerHTML = ''; }
  else {
    if (p.hit) $('lookup').innerHTML = '<div class="t">' + esc(p.title) + '</div><div class="m">Brand: ' + esc(p.brand || '—') + ' · Category: ' + esc(p.category || '—') + ' · Model: ' + esc(p.model || '—') + '</div><div class="m">' + esc(p.description || '') + '</div>';
    else $('lookup').innerHTML = '<div class="t">The API returned no match for this code.</div>';
    $('verdicts').innerHTML = ''; VS.forEach(([k, l]) => { const b = document.createElement('button'); b.textContent = l; b.className = k + (a.verdict === k ? ' on' : '');
      b.onclick = () => set({verdict: k}); $('verdicts').appendChild(b); });
  }
  if (document.activeElement !== $('note')) $('note').value = a.note || '';
  const st = $('strip'); st.innerHTML = '';
  D.photos.forEach((q, j) => { const b = document.createElement('button'); b.textContent = q.photo.slice(-2); b.title = q.photo;
    b.className = (q.done ? 'done ' : '') + (j === pi ? 'cur' : ''); b.onclick = () => { pi = j; render(); }; st.appendChild(b); });
  $('prog').textContent = D.photos.filter(q => q.done).length + ' / ' + D.photos.length + ' items done';
}
async function set(patch){ const p = cur(); Object.assign(p.answer, patch);
  p.done = !!p.answer.type && (!p.looked_up || !!p.answer.verdict); render();
  const r = await fetch('/api/answer', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({photo: p.photo, patch})});
  if (!r.ok) alert('Save failed: ' + r.status); }
$('note').addEventListener('change', () => set({note: $('note').value}));
$('view').addEventListener('click', e => { const v = $('view'), z = v.classList.toggle('zoom'); $('hint').style.display = z ? 'none' : '';
  if (z) { const r = $('img').getBoundingClientRect(); const fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
    requestAnimationFrame(() => { v.scrollLeft = fx * $('img').offsetWidth - v.clientWidth / 2; v.scrollTop = fy * $('img').offsetHeight - v.clientHeight / 2; }); } });
document.addEventListener('keydown', e => { if (e.target.tagName === 'TEXTAREA') return; const p = cur();
  if (TK[e.key]) set({type: TK[e.key]});
  else if (['1','2','3','4'].includes(e.key) && p.looked_up) set({verdict: VS[+e.key - 1][0]});
  else if (e.key === 'y' && p.method === 'model-read' && p.digits) set({digits_match: 'yes'});
  else if (e.key === 'x' && p.method === 'model-read' && p.digits) set({digits_match: 'no'});
  else if (e.key === 'n') { pi = Math.min(D.photos.length - 1, pi + 1); render(); }
  else if (e.key === 'p') { pi = Math.max(0, pi - 1); render(); } });
(async () => { D = await (await fetch('/api/data')).json(); pi = firstOpen(); render(); })();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == '/':
            self._send(200, PAGE.encode(), 'text/html; charset=utf-8')
        elif self.path == '/api/data':
            self._send(200, json.dumps(payload()).encode(), 'application/json')
        elif self.path.startswith('/photo/'):
            p = PHOTOS / Path(self.path.removeprefix('/photo/')).name  # .name blocks ../ paths
            if p.suffix == '.jpg' and p.exists():
                self._send(200, p.read_bytes(), 'image/jpeg')
            else:
                self._send(404, b'not found', 'text/plain')
        else:
            self._send(404, b'not found', 'text/plain')

    def do_POST(self) -> None:
        v = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        photo, patch = v.get('photo'), v.get('patch') or {}
        allowed = {'type': data.TYPES, 'verdict': data.VERDICTS, 'digits_match': ['yes', 'no']}
        ok = self.path == '/api/answer' and (PHOTOS / f'{photo}.jpg').exists() and set(patch) <= set(allowed) | {'note'}
        ok = ok and all(k == 'note' or patch[k] in allowed[k] for k in patch)
        if not ok:
            return self._send(400, b'bad request', 'text/plain')
        if 'note' in patch:
            patch['note'] = str(patch['note']).strip()
        save(photo, patch)
        self._send(200, b'{"ok":true}', 'application/json')

    def log_message(self, *args) -> None:
        pass


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'Judge page: http://127.0.0.1:{PORT}  (Ctrl+C to stop)')
    webbrowser.open(f'http://127.0.0.1:{PORT}')
    srv.serve_forever()
