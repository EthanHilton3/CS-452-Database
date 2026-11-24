"""Judge page for the group-photo test. Local only (127.0.0.1): photos never leave this machine.

Run: py -3.13 review.py     -> opens http://127.0.0.1:8453
For each photo: (1) type how many entries a perfect list would have, (2) mark every item each setup listed
(1 right, 2 close, 3 wrong / not there, 4 duplicate), (3) note anything they missed. Setups are labelled A, B, C... so
you don't judge by model name. Every click saves to answers.json; stop and come back any time.
Then run: py -3.13 score.py
"""
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import scoring

HERE = Path(__file__).parent
PHOTOS = HERE / 'photos' / 'jpg'
PORT = 8453


def data() -> dict:
    res, ans = scoring.load_results(), scoring.load_answers()
    order = scoring.blind_order()
    photos = []
    for ph in sorted(res[order[0]]):
        a = ans.get(ph, {})
        setups = []
        for letter, s in zip('ABCDE', order):
            if ph not in res[s]:
                continue
            row = res[s][ph]
            sc = row.get('scene', {'items': [], 'visible_but_unidentifiable': 0})
            setups.append({'id': s, 'letter': letter, 'items': sc['items'], 'unid': sc['visible_but_unidentifiable'],
                           'error': row.get('error'), 'verdicts': a.get('verdicts', {}).get(s, {}),
                           'auto': a.get('auto', {}).get(s, [])})
        photos.append({'photo': ph, 'key_total': a.get('key_total'), 'missed': a.get('missed', ''), 'setups': setups})
    return {'photos': photos, 'progress': scoring.progress(res, ans)}


def save_answers(ans: dict) -> None:
    tmp = scoring.ANSWERS.with_suffix('.tmp')
    tmp.write_text(json.dumps(ans, indent=1, ensure_ascii=False), encoding='utf-8')
    tmp.replace(scoring.ANSWERS)


PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><title>Group photo judge</title>
<style>
:root{--bg:#f6f5f2;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#dcdad5;--acc:#2f6f5e;--right:#2f7d4f;--close:#b58a1d;--wrong:#b3412f;--dup:#6b6b9a}
@media (prefers-color-scheme:dark){:root{--bg:#18191b;--card:#232427;--ink:#ececee;--mute:#9a9aa1;--line:#3a3b3f;--acc:#6cc3a8;--right:#5bbf84;--close:#e0b34a;--wrong:#e07766;--dup:#9a9ad0}}
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
#side{display:flex;flex-direction:column;gap:10px;min-height:0}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.box label{display:block;font-size:12px;color:var(--mute);margin-bottom:3px}
input,textarea{font:inherit;color:var(--ink);background:var(--bg);border:1px solid var(--line);border-radius:7px;padding:6px 8px;width:100%}
#tabs{display:flex;gap:6px}#tabs button{flex:1;padding:8px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);cursor:pointer;font:600 14px system-ui}
#tabs button.cur{background:var(--ink);color:var(--bg)}#tabs small{font-weight:400;color:inherit;opacity:.7}
#items{overflow:auto;display:flex;flex-direction:column;gap:6px;min-height:0;flex:1;padding-right:4px}
.it{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:8px;padding:8px 10px}
.it.cur{outline:2px solid var(--ink)}.it.right{border-left-color:var(--right)}.it.close{border-left-color:var(--close)}.it.wrong{border-left-color:var(--wrong)}.it.dup{border-left-color:var(--dup)}
.it .n{font-weight:600}.it .m{color:var(--mute);font-size:12px}.it .q{font-size:12px;font-style:italic;color:var(--mute)}
.btns{display:flex;gap:5px;margin-top:6px}.btns button{flex:1;padding:5px 2px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);cursor:pointer;font-size:12px}
.btns button.on{color:#fff;border-color:transparent}.btns .right.on{background:var(--right)}.btns .close.on{background:var(--close)}.btns .wrong.on{background:var(--wrong)}.btns .dup.on{background:var(--dup)}
.help{font-size:12px;color:var(--mute)}
</style></head><body>
<header><b>Group photo judge</b><span id="prog"></span><div id="strip"></div></header>
<main>
<div id="view"><img id="img" alt=""><div id="hint">click to zoom</div></div>
<div id="side">
  <div class="box"><label>How many entries would a perfect list have for this photo? (a run of volumes = 1, a box set = 1)</label>
    <input id="key" type="number" min="0" placeholder="count the separate things you would list">
    <label style="margin-top:8px">What did all of them miss? (optional)</label><textarea id="missed" rows="2"></textarea></div>
  <div id="tabs"></div>
  <div class="help" id="info"></div>
  <div id="items"></div>
  <div class="help">Keys: <b>1</b> right · <b>2</b> close · <b>3</b> wrong/not there · <b>4</b> duplicate · <b>j/k</b> next/prev item · <b>[ ]</b> switch setups · <b>n/p</b> next/prev photo. Right = item and details correct. Close = right item, a detail wrong or missing.</div>
</div></main>
<script>
let D, pi = 0, si = 0, ii = 0; const $ = id => document.getElementById(id);
const V = [['right','1 Right'],['close','2 Close'],['wrong','3 Wrong'],['dup','4 Dup']];
const photoDone = p => p.key_total !== null && p.key_total !== '' && p.setups.every(s => s.items.every((_, k) => s.verdicts[k]));
const esc = t => String(t ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function firstOpen(){ const s = D.photos[pi].setups[si]; const k = s.items.findIndex((_, j) => !s.verdicts[j]); return k < 0 ? 0 : k; }
function render(){
  const p = D.photos[pi], s = p.setups[si];
  const src = '/photo/' + p.photo + '.jpg'; if ($('img').getAttribute('src') !== src) { $('img').src = src; $('view').classList.remove('zoom'); $('hint').style.display = ''; }
  if (document.activeElement !== $('key')) $('key').value = p.key_total ?? '';
  if (document.activeElement !== $('missed')) $('missed').value = p.missed || '';
  $('tabs').innerHTML = ''; p.setups.forEach((t, j) => { const b = document.createElement('button');
    b.innerHTML = 'Setup ' + t.letter + ' <small>' + Object.keys(t.verdicts).length + '/' + t.items.length + '</small>';
    b.className = j === si ? 'cur' : ''; b.onclick = () => { si = j; ii = firstOpen(); render(); }; $('tabs').appendChild(b); });
  $('info').textContent = s.error ? 'This setup failed on this photo.' : s.items.length + ' items listed · ' + s.unid + ' things it said it could not identify';
  const box = $('items'); box.innerHTML = '';
  s.items.forEach((it, k) => { const d = document.createElement('div'); const v = s.verdicts[k];
    d.className = 'it ' + (v || '') + (k === ii ? ' cur' : '');
    const bits = [it.volumes_or_count, it.edition_or_format, it.creator_or_maker, it.confidence + ' confidence', it.sealed ? 'sealed' : ''].filter(Boolean).join(' · ');
    d.innerHTML = '<div class="n">' + esc(it.name) + (s.auto.includes(k) ? ' <span class="m">(filled from your earlier judgement of an identical item; change it if wrong)</span>' : '') + '</div><div class="m">' + esc(bits) + '</div><div class="m">' + esc(it.position) + '</div><div class="q">“' + esc(it.text_read_on_item) + '”</div>';
    const bt = document.createElement('div'); bt.className = 'btns';
    V.forEach(([key, label]) => { const b = document.createElement('button'); b.textContent = label; b.className = key + (v === key ? ' on' : '');
      b.onclick = e => { e.stopPropagation(); judge(k, key, false); }; bt.appendChild(b); });
    d.appendChild(bt); d.onclick = () => { ii = k; render(); }; box.appendChild(d); });
  const cur = box.children[ii]; if (cur) cur.scrollIntoView({block:'nearest'});
  const st = $('strip'); st.innerHTML = '';
  D.photos.forEach((q, j) => { const b = document.createElement('button'); b.textContent = q.photo.slice(-4); b.title = q.photo;
    b.className = (photoDone(q) ? 'done ' : '') + (j === pi ? 'cur' : ''); b.onclick = () => { pi = j; si = 0; ii = firstOpen(); render(); }; st.appendChild(b); });
  $('prog').textContent = D.photos.filter(photoDone).length + ' / ' + D.photos.length + ' photos done';
}
async function post(url, body){ const r = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)}); if (!r.ok) alert('Save failed: ' + r.status); }
async function judge(k, verdict, advance){ const p = D.photos[pi], s = p.setups[si]; s.verdicts[k] = verdict; ii = k;
  if (advance && k + 1 < s.items.length) ii = k + 1; render();
  await post('/api/verdict', {photo: p.photo, setup: s.id, idx: k, verdict}); }
async function saveMeta(){ const p = D.photos[pi]; p.key_total = $('key').value === '' ? null : parseInt($('key').value, 10); p.missed = $('missed').value;
  await post('/api/meta', {photo: p.photo, key_total: p.key_total, missed: p.missed}); render(); }
$('key').addEventListener('change', saveMeta); $('missed').addEventListener('change', saveMeta);
$('view').addEventListener('click', e => { const v = $('view'), z = v.classList.toggle('zoom'); $('hint').style.display = z ? 'none' : '';
  if (z) { const r = $('img').getBoundingClientRect(); const fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
    requestAnimationFrame(() => { v.scrollLeft = fx * $('img').offsetWidth - v.clientWidth / 2; v.scrollTop = fy * $('img').offsetHeight - v.clientHeight / 2; }); } });
document.addEventListener('keydown', e => { if (['INPUT','TEXTAREA'].includes(e.target.tagName)) return;
  const s = D.photos[pi].setups[si];
  if (['1','2','3','4'].includes(e.key)) judge(ii, V[+e.key - 1][0], true);
  else if (e.key === 'j') { ii = Math.min(s.items.length - 1, ii + 1); render(); } else if (e.key === 'k') { ii = Math.max(0, ii - 1); render(); }
  else if (e.key === ']') { si = (si + 1) % D.photos[pi].setups.length; ii = firstOpen(); render(); } else if (e.key === '[') { si = (si + D.photos[pi].setups.length - 1) % D.photos[pi].setups.length; ii = firstOpen(); render(); }
  else if (e.key === 'n') { pi = Math.min(D.photos.length - 1, pi + 1); si = 0; ii = firstOpen(); render(); }
  else if (e.key === 'p') { pi = Math.max(0, pi - 1); si = 0; ii = firstOpen(); render(); } });
(async () => { D = await (await fetch('/api/data')).json(); pi = Math.max(0, D.photos.findIndex(p => !photoDone(p))); ii = firstOpen(); render(); })();
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
        v = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        photo = v.get('photo')
        if self.path not in ('/api/verdict', '/api/meta') or not (PHOTOS / f'{photo}.jpg').exists():
            return self._send(400, b'bad request', 'text/plain')
        ans = scoring.load_answers()
        a = ans.setdefault(photo, {})
        if self.path == '/api/verdict':
            if v.get('setup') not in scoring.SETUP_FILES or v.get('verdict') not in scoring.VERDICTS:
                return self._send(400, b'bad verdict', 'text/plain')
            a.setdefault('verdicts', {}).setdefault(v['setup'], {})[str(int(v['idx']))] = v['verdict']
        else:
            a['key_total'], a['missed'] = v.get('key_total'), (v.get('missed') or '').strip()
        save_answers(ans)
        self._send(200, b'{"ok":true}', 'application/json')

    def log_message(self, *args) -> None:
        pass


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'Judge page: http://127.0.0.1:{PORT}  (Ctrl+C to stop)')
    webbrowser.open(f'http://127.0.0.1:{PORT}')
    srv.serve_forever()
