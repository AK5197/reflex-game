from flask import Flask, render_template_string, Response, jsonify, request
from flask_sock import Sock
from flasgger import Swagger
from dotenv import load_dotenv
import os
import json, sqlite3, time, logging, threading
import paho.mqtt.client as mqtt

# ----------------- Konfiguration aus .env -----------------
load_dotenv()

DB         = os.getenv("DB", "scores.db")
TOPIC      = os.getenv("TOPIC", "spiel/reflex/score")
MQTT_HOST  = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT  = int(os.getenv("MQTT_PORT", "1883"))
WEB_PORT   = int(os.getenv("PORT", "8080"))
DEBUG      = bool(int(os.getenv("DEBUG", "0")))
MS_MIN     = int(os.getenv("MS_MIN", "20"))
MS_MAX     = int(os.getenv("MS_MAX", "20000"))
HIST_LIMIT_DEFAULT = int(os.getenv("HIST_LIMIT_DEFAULT", "1000"))
HIST_LIMIT_MAX     = int(os.getenv("HIST_LIMIT_MAX", "5000"))

# ----------------- Logging -----------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("reflex")

# ----------------- DB Helper -----------------
def init_db():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS scores(ts INTEGER, player TEXT, ms INTEGER)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_ms ON scores(ms)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scores_ts ON scores(ts)")
    con.commit()
    con.close()

def with_db(query, args=(), fetch=False, many=False):
    con = sqlite3.connect(DB)
    cur = con.cursor()
    if many:
        cur.executemany(query, args)
    else:
        cur.execute(query, args)
    rows = cur.fetchall() if fetch else None
    con.commit()
    con.close()
    return rows

init_db()

# ----------------- Web (Flask + Swagger + Sock) -----------------
app = Flask(__name__)
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "Reflex Game API",
        "description": "REST API für Highscores & Historie des Reflex-Games",
        "version": "1.0.0"
    },
    "basePath": "/",
    "schemes": ["http"],
})
sock = Sock(app)

# WebSocket-Clientverwaltung (thread-safe)
_ws_clients = set()
_ws_lock = threading.Lock()

def ws_broadcast(obj: dict):
    data = json.dumps(obj)
    dead = []
    with _ws_lock:
        for ws in list(_ws_clients):
            try:
                ws.send(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _ws_clients.discard(ws)

# ----------------- MQTT -> DB -> WS -----------------
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        player = str(data.get("player", "unknown")).strip()[:16] or "unknown"
        ms = int(data.get("ms"))
        if not (MS_MIN <= ms <= MS_MAX):
            log.warning("Drop invalid ms=%s from player=%s", ms, player)
            return
    except Exception as e:
        log.exception("Bad MQTT payload: %s", e)
        return

    ts = int(time.time())
    with_db("INSERT INTO scores VALUES(?,?,?)", (ts, player, ms))
    log.info("Saved score: player=%s ms=%s", player, ms)

    # Push an Browser
    ws_broadcast({
        "type": "score",
        "ts": ts,
        "player": player,
        "ms": ms,
        "dt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    })

mclient = mqtt.Client()
mclient.on_message = on_message
mclient.connect(MQTT_HOST, MQTT_PORT, 60)
mclient.subscribe(TOPIC, qos=1)
mclient.loop_start()

# ----------------- HTML (mit WS + REST) -----------------
HTML = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"/>
<title>Reflex Highscore</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  body { font-family: system-ui, sans-serif; margin:0; background:#0f172a; color:#e5e7eb; }
  header { background:#111827; padding:10px 20px; position:sticky; top:0; z-index:2; }
  h1 { margin:0; font-size:20px; }
  .wrap { display:flex; gap:20px; padding:20px; max-width:1400px; margin:0 auto; }
  .left { flex:2; min-width:0; }
  .right { flex:1; display:flex; flex-direction:column; gap:20px; min-width:320px; }
  .card { background:#1f2937; border-radius:10px; overflow:hidden; border:1px solid #263143; }
  .card h2 { margin:0; padding:10px; background:#0b1220; font-size:16px; }
  table { width:100%; border-collapse:collapse; font-size:14px; }
  th, td { padding:8px 10px; border-bottom:1px solid #263143; text-align:left; }
  th { background:#0b1220; position:sticky; top:0; z-index:1; }
  tbody tr:nth-child(odd){ background:#0e1626; }
  tbody tr:hover { background:#0b1220; }
  .scroll { max-height:70vh; overflow-y:auto; }
  .rank { color:#22d3ee; }
  .pill { background:#111827; border-radius:12px; padding:2px 6px; font-size:12px; border:1px solid #263143; }
  td.num { text-align:right; font-variant-numeric: tabular-nums; }
  .toolbar{ display:flex; gap:8px; padding:8px 10px; background:#0b1220; border-bottom:1px solid #263143; }
  .chip{ padding:.25rem .6rem; border:1px solid #334155; border-radius:999px; cursor:pointer; font-size:12px }
  .chip.active{ background:#0f172a }
  footer { text-align:center; padding:12px; color:#94a3b8; font-size:12px; }
  .links { position: absolute; right: 20px; top: 10px; font-size: 12px; }
  .links a { color:#e5e7eb; text-decoration:none; margin-left:10px; border:1px solid #263143; padding:3px 6px; border-radius:8px; }
</style>
</head>
<body>
<header>
  <h1>Reflex Highscore</h1>
  <div class="links">
    <a href="/apidocs/">API-Doku</a>
    <a href="/export.csv">CSV Export</a>
  </div>
  <div style="font-size:12px;color:#94a3b8">Links: Historie · Rechts: Top-10 (Overall, P1, P2)</div>
</header>

<div class="wrap">
  <div class="left card">
    <h2>Historie (neueste zuerst)</h2>
    <div class="toolbar">
      <span class="chip active" data-filter="ALL">Alle</span>
      <span class="chip" data-filter="P1">P1</span>
      <span class="chip" data-filter="P2">P2</span>
    </div>
    <div class="scroll">
      <table>
        <thead><tr><th>#</th><th>Zeit</th><th>Spieler</th><th>ms</th></tr></thead>
        <tbody id="tbody-history"></tbody>
      </table>
    </div>
  </div>

  <div class="right">
    <div class="card">
      <h2>Top 10 Overall</h2>
      <table>
        <thead><tr><th>#</th><th>Spieler</th><th>ms</th><th>Zeit</th></tr></thead>
        <tbody id="tbody-top-all"></tbody>
      </table>
    </div>
    <div class="card">
      <h2>Top 10 P1</h2>
      <table>
        <thead><tr><th>#</th><th>ms</th><th>Zeit</th></tr></thead>
        <tbody id="tbody-top-p1"></tbody>
      </table>
    </div>
    <div class="card">
      <h2>Top 10 P2</h2>
      <table>
        <thead><tr><th>#</th><th>ms</th><th>Zeit</th></tr></thead>
        <tbody id="tbody-top-p2"></tbody>
      </table>
    </div>
  </div>
</div>

<footer>&copy; {{ year }} · Reflex-Game · MQTT Topic: {{ topic }}</footer>

<script>
let filter = 'ALL';
const H  = document.getElementById('tbody-history');
const TA = document.getElementById('tbody-top-all');
const TP1= document.getElementById('tbody-top-p1');
const TP2= document.getElementById('tbody-top-p2');

function fmtMs(n){ return Number(n).toLocaleString('de-DE'); }
function rowHistory(i, r){ return `<tr><td class="rank">${i}</td><td>${r.dt}</td><td><span class="pill">${r.player}</span></td><td class="num">${fmtMs(r.ms)}</td></tr>`; }
function rowTop(i, r){ return `<tr><td class="rank">${i}</td><td><span class="pill">${r.player}</span></td><td class="num">${fmtMs(r.ms)}</td><td>${r.dt}</td></tr>`; }
function rowTopSimple(i, r){ return `<tr><td class="rank">${i}</td><td class="num">${fmtMs(r.ms)}</td><td>${r.dt}</td></tr>`; }

async function loadAll(){
  const limit = 1000;
  const [hist, topAll, topP1, topP2] = await Promise.all([
    fetch(`/api/scores?limit=${limit}`).then(r=>r.json()),
    fetch(`/api/top?limit=10`).then(r=>r.json()),
    fetch(`/api/top?player=P1&limit=10`).then(r=>r.json()),
    fetch(`/api/top?player=P2&limit=10`).then(r=>r.json()),
  ]);
  renderHistory(hist);
  TA.innerHTML = topAll.map((r,i)=>rowTop(i+1,r)).join('');
  TP1.innerHTML= topP1.map((r,i)=>rowTopSimple(i+1,r)).join('');
  TP2.innerHTML= topP2.map((r,i)=>rowTopSimple(i+1,r)).join('');
}

function renderHistory(hist){
  const f = hist.filter(r => filter==='ALL' ? true : r.player===filter);
  H.innerHTML  = f.map((r,i)=>rowHistory(i+1,r)).join('');
}

function connectWS(){
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onmessage = (ev)=>{
    const msg = JSON.parse(ev.data);
    if(msg.type === 'score'){
      if(filter==='ALL' || filter===msg.player){
        const row = { dt: msg.dt, player: msg.player, ms: msg.ms };
        H.insertAdjacentHTML('afterbegin', rowHistory(1, row));
        let i=1; H.querySelectorAll('tr td.rank').forEach(td=> td.textContent = i++);
      }
      loadTopLists();
    }
  };
  ws.onclose = ()=> setTimeout(connectWS, 2000);
}

async function loadTopLists(){
  const [topAll, topP1, topP2] = await Promise.all([
    fetch(`/api/top?limit=10`).then(r=>r.json()),
    fetch(`/api/top?player=P1&limit=10`).then(r=>r.json()),
    fetch(`/api/top?player=P2&limit=10`).then(r=>r.json()),
  ]);
  TA.innerHTML = topAll.map((r,i)=>rowTop(i+1,r)).join('');
  TP1.innerHTML= topP1.map((r,i)=>rowTopSimple(i+1,r)).join('');
  TP2.innerHTML= topP2.map((r,i)=>rowTopSimple(i+1,r)).join('');
}

document.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('.chip').forEach(c=>{
    c.addEventListener('click', ()=>{
      document.querySelectorAll('.chip').forEach(x=>x.classList.remove('active'));
      c.classList.add('active'); filter = c.dataset.filter; loadAll();
    });
  });
  loadAll();
  connectWS();
});
</script>
</body>
</html>
"""

# ---------- UI ----------
@app.route("/")
def index():
    return render_template_string(HTML, year=time.strftime("%Y"), topic=TOPIC)

# ---------- REST: Scores ----------
@app.get("/api/scores")
def api_scores():
    """
    Scores History
    ---
    tags:
      - Scores
    parameters:
      - name: player
        in: query
        type: string
        required: false
        description: Filter nach Spieler (z.B. "P1")
      - name: limit
        in: query
        type: integer
        required: false
        description: Anzahl der Einträge (max. 5000, default 1000)
    responses:
      200:
        description: Liste von Scores (neueste zuerst)
        schema:
          type: array
          items:
            type: object
            properties:
              ts: {type: integer}
              dt: {type: string}
              player: {type: string}
              ms: {type: integer}
    """
    player = request.args.get("player")
    try:
        limit = int(request.args.get("limit", HIST_LIMIT_DEFAULT))
    except ValueError:
        limit = HIST_LIMIT_DEFAULT
    limit = max(1, min(limit, HIST_LIMIT_MAX))

    if player:
        rows = with_db(
            "SELECT ts, player, ms FROM scores WHERE player=? ORDER BY ts DESC LIMIT ?",
            (player, limit), fetch=True
        )
    else:
        rows = with_db(
            "SELECT ts, player, ms FROM scores ORDER BY ts DESC LIMIT ?",
            (limit,), fetch=True
        )

    data = [
        {"ts": ts,
         "dt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
         "player": pl, "ms": int(ms)}
        for ts, pl, ms in rows
    ]
    return jsonify(data)

# ---------- REST: Top ----------
@app.get("/api/top")
def api_top():
    """
    Top Scores
    ---
    tags:
      - Scores
    parameters:
      - name: player
        in: query
        type: string
        required: false
        description: Filter (z.B. "P1" oder "P2")
      - name: limit
        in: query
        type: integer
        required: false
        description: Anzahl (default 10, max 100)
    responses:
      200:
        description: Topliste (aufsteigend nach ms)
        schema:
          type: array
          items:
            type: object
            properties:
              ts: {type: integer}
              dt: {type: string}
              player: {type: string}
              ms: {type: integer}
    """
    player = request.args.get("player")
    try:
        limit = int(request.args.get("limit", 10))
    except ValueError:
        limit = 10
    limit = max(1, min(limit, 100))

    if player:
        rows = with_db(
            "SELECT ts, player, ms FROM scores WHERE player=? ORDER BY ms ASC, ts ASC LIMIT ?",
            (player, limit), fetch=True
        )
    else:
        rows = with_db(
            "SELECT ts, player, ms FROM scores ORDER BY ms ASC, ts ASC LIMIT ?",
            (limit,), fetch=True
        )

    data = [
        {"ts": ts,
         "dt": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
         "player": pl, "ms": int(ms)}
        for ts, pl, ms in rows
    ]
    return jsonify(data)

# ---------- CSV ----------
@app.route("/export.csv")
def export_csv():
    """
    Export Scores als CSV
    ---
    tags:
      - Export
    produces:
      - text/csv
    responses:
      200:
        description: CSV-Datei mit allen Scores
    """
    rows = with_db("SELECT ts, player, ms FROM scores ORDER BY ts DESC", fetch=True)
    lines = ["timestamp,datetime_local,player,ms"]
    for ts, player, ms in rows:
        dt = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
        lines.append(f"{ts},{dt},{player},{ms}")
    return Response("\n".join(lines), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=scores.csv"})

# ---------- Favicon ----------
@app.route("/favicon.ico")
def favicon():
    return Response(status=204)

# ---------- WebSocket ----------
@sock.route("/ws")
def ws(ws):
    with _ws_lock:
        _ws_clients.add(ws)
    try:
        while ws.receive() is not None:
            pass
    finally:
        with _ws_lock:
            _ws_clients.discard(ws)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=WEB_PORT, debug=DEBUG)
