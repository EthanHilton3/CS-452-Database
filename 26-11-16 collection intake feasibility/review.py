"""Answer-key review page: each photo next to a form prefilled from Luna's card. Fix what's wrong, press Enter.

Run: py -3.13 review.py   -> opens http://127.0.0.1:8452 (local only; photos never leave this machine)
Every save rewrites answers.csv. Rows already in answers.csv load as they are, so you can stop and come back.
The `edited` column records which prefilled fields you changed (a direct measure of Luna's card quality).
"""
import csv
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from intake import CATEGORIES

HERE = Path(__file__).parent
PHOTOS = HERE / 'photos' / 'jpg'
ANSWERS = HERE / 'answers.csv'
PREFILL_RUN = HERE / 'results' / 'cards_luna_full.jsonl'
FIELDS = ['photo', 'name', 'category', 'must_have_details', 'condition', 'notes', 'edited']
PORT = 8452


def read_answers() -> dict[str, dict]:
    if not ANSWERS.exists():
        return {}
    with ANSWERS.open(encoding='utf-8-sig') as f:
        return {r['photo']: r for r in csv.DictReader(f)}


def write_answers(rows: dict[str, dict]) -> None:
    with ANSWERS.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, FIELDS, extrasaction='ignore')
        w.writeheader()
        for p in sorted(rows):
            w.writerow({k: rows[p].get(k, '') for k in FIELDS})


def prefill() -> dict[str, dict]:
    out = {}
    for line in PREFILL_RUN.read_text(encoding='utf-8').splitlines():
        r = json.loads(line)
        if 'card' not in r:
            continue
        c = r['card']
        details = ', '.join(x for x in (c['edition_or_model'], c['platform_or_format']) if x)
        cond = {'sealed / new in box': 'sealed', 'opened / used': 'opened'}.get(c['condition'], '')
        out[r['photo']] = {'name': c['name'], 'category': c['category'], 'must_have_details': details,
                           'condition': cond, 'notes': ''}
    return out


def data() -> dict:
    saved, pre = read_answers(), prefill()
    items = []
    for p in sorted(x.stem for x in PHOTOS.glob('*.jpg')):
        s = {k: (v or '').strip() for k, v in saved.get(p, {}).items() if k}
        done = all(s.get(k) for k in ('name', 'category', 'condition'))
        # Anything I already typed wins; Luna's card only fills the empty fields.
        values = {**pre.get(p, {}), **{k: v for k, v in s.items() if v}, 'photo': p}
        items.append({'photo': p, 'done': done, 'prefill': pre.get(p, {}), 'values': values})
    mine = sorted({c.strip() for r in saved.values() for c in (r.get('category') or '').split('|') if c.strip()})
    conds = sorted({(r.get('condition') or '').strip() for r in saved.values()} - {''})
    return {'items': items, 'categories': mine + [c for c in CATEGORIES if c not in mine],
            'conditions': ['sealed'] + [c for c in conds if c != 'sealed'] + ['opened']}


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Intake answer key</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#dcdad5;--acc:#2f6f5e;--warn:#b5651d}
@media (prefers-color-scheme:dark){:root{--bg:#18191b;--card:#232427;--ink:#ececee;--mute:#9a9aa1;--line:#3a3b3f;--acc:#6cc3a8;--warn:#e0a060}}
*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,sans-serif;background:var(--bg);color:var(--ink)}
header{display:flex;gap:12px;align-items:center;padding:12px 20px;border-bottom:1px solid var(--line)}
header b{font-size:16px}#prog{color:var(--mute)}#strip{display:flex;gap:4px;flex-wrap:wrap;margin-left:auto}
#strip button{width:26px;height:26px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--mute);font-size:11px;cursor:pointer}
#strip button.done{background:var(--acc);color:#fff;border-color:var(--acc)}#strip button.cur{outline:2px solid var(--ink)}
main{display:grid;grid-template-columns:minmax(0,1fr) 420px;gap:20px;padding:20px;height:calc(100vh - 60px)}
@media (max-width:800px){main{grid-template-columns:1fr;height:auto}}
#img{width:100%;height:100%;object-fit:contain;background:#000;border-radius:10px;min-height:300px}
form{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;display:flex;flex-direction:column;gap:12px;overflow:auto}
label{display:flex;flex-direction:column;gap:4px;font-size:13px;color:var(--mute)}
input,select,textarea{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:7px;padding:8px}
input.changed,select.changed,textarea.changed{border-color:var(--warn)}
.row{display:flex;gap:14px}.row label{flex-direction:row;align-items:center;gap:6px;color:var(--ink)}
.hint{font-size:12px;color:var(--mute)}button.save{margin-top:auto;padding:10px;border:0;border-radius:8px;background:var(--acc);color:#fff;font:600 15px system-ui;cursor:pointer}
#msg{font-size:12px;color:var(--acc);min-height:16px}
</style></head><body>
<header><b>Intake answer key</b><span id="prog"></span><div id="strip"></div></header>
<main><img id="img" alt="">
<form id="f" autocomplete="off">
  <div class="hint">Prefilled from Luna's card. Fix anything wrong. Changed fields turn orange. Enter saves and moves to the next photo.</div>
  <label>Name (what it actually is)<input name="name" required></label>
  <label>Category (type your own or pick a suggestion)<input name="category" list="cats" required></label>
  <label>Also acceptable category (optional)<input name="category2" list="cats"></label>
  <label>Must-have details (edition, format, model that a card must get right)<input name="must_have_details"></label>
  <label>Condition (sealed, open / like new, very good...)<input name="condition" list="conds" required></label>
  <label>Notes: where and when you got it, anything else (optional)<textarea name="notes" rows="3"></textarea></label>
  <datalist id="cats"></datalist><datalist id="conds"></datalist>
  <div id="msg"></div>
  <button class="save">Save &amp; next (Enter)</button>
</form></main>
<script>
let D, i = 0;
const f = document.getElementById('f'), F = f.elements;
async function load(){ D = await (await fetch('/api/data')).json();
  for (const c of D.categories) document.getElementById('cats').append(new Option(c));
  for (const c of D.conditions) document.getElementById('conds').append(new Option(c));
  i = Math.max(0, D.items.findIndex(x => !x.done)); show(); }
function show(){
  const it = D.items[i], v = it.values, cats = (v.category||'').split('|').map(s=>s.trim());
  document.getElementById('img').src = '/photo/' + it.photo + '.jpg';
  F.name.value = v.name||''; F.category.value = cats[0]||''; F.category2.value = cats[1]||'';
  F.must_have_details.value = v.must_have_details||''; F.notes.value = v.notes||''; F.condition.value = v.condition||'';
  document.getElementById('msg').textContent = it.done ? 'Saved earlier.' : (v.condition ? '' : 'Luna couldn’t tell the condition: fill it in.');
  mark(); strip(); F.name.focus(); }
function mark(){ const p = D.items[i].prefill;
  for (const k of ['name','category','must_have_details','condition']) F[k].classList.toggle('changed', (F[k].value||'') !== (p[k]||'')); }
function strip(){ const s = document.getElementById('strip'); s.innerHTML='';
  D.items.forEach((it, j) => { const b = document.createElement('button'); b.type='button'; b.textContent = it.photo.slice(-2);
    b.title = it.photo; b.className = (it.done?'done ':'') + (j===i?'cur':''); b.onclick = () => { i=j; show(); }; s.appendChild(b); });
  document.getElementById('prog').textContent = D.items.filter(x=>x.done).length + ' / ' + D.items.length + ' done'; }
f.addEventListener('input', mark);
f.addEventListener('submit', async e => { e.preventDefault();
  const it = D.items[i], p = it.prefill;
  const v = { photo: it.photo, name: F.name.value.trim(),
    category: [F.category.value.trim(), F.category2.value.trim()].filter(Boolean).join(' | '),
    must_have_details: F.must_have_details.value.trim(), condition: F.condition.value.trim(), notes: F.notes.value.trim() };
  v.edited = ['name','category','must_have_details','condition'].filter(k => k==='category'
    ? F.category.value.trim() !== p.category : (v[k]||'') !== (p[k]||'')).join(' ');
  const r = await fetch('/api/save', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(v)});
  if (!r.ok) { document.getElementById('msg').textContent = 'Save failed: ' + r.status; return; }
  it.values = v; it.done = true;
  const next = D.items.findIndex((x, j) => j > i && !x.done);
  i = next >= 0 ? next : (D.items.findIndex(x => !x.done) >= 0 ? D.items.findIndex(x => !x.done) : i);
  show();
  if (D.items.every(x => x.done)) document.getElementById('msg').textContent = 'All 26 done. Close this tab and run: py -3.13 score.py';
});
load();
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
            self._send(200, json.dumps(data()).encode(), 'application/json')
        elif self.path.startswith('/photo/'):
            p = PHOTOS / Path(self.path.removeprefix('/photo/')).name  # .name blocks ../ paths
            if p.suffix == '.jpg' and p.exists():
                self._send(200, p.read_bytes(), 'image/jpeg')
            else:
                self._send(404, b'not found', 'text/plain')
        else:
            self._send(404, b'not found', 'text/plain')

    def do_POST(self) -> None:
        if self.path != '/api/save':
            return self._send(404, b'not found', 'text/plain')
        v = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        if not (PHOTOS / f"{v.get('photo')}.jpg").exists():
            return self._send(400, b'unknown photo', 'text/plain')
        rows = read_answers()
        rows[v['photo']] = v
        write_answers(rows)
        self._send(200, b'{"ok":true}', 'application/json')

    def log_message(self, *args) -> None:  # keep the terminal quiet
        pass


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'Review page: http://127.0.0.1:{PORT}  (Ctrl+C to stop)')
    webbrowser.open(f'http://127.0.0.1:{PORT}')
    srv.serve_forever()
