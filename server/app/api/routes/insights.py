from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.models.schemas import ApiResponse
from app.state import flight_store

router = APIRouter(tags=["insights"])


def _safe_avg(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


@router.get("/api/v1/flights/summary")
async def get_flights_summary() -> ApiResponse:
    flights = await flight_store.list_flights()

    altitudes = [item.altitude_ft for item in flights if item.altitude_ft is not None]
    speeds = [item.speed_kts for item in flights if item.speed_kts is not None]

    data = {
        "total": len(flights),
        "avg_altitude_ft": _safe_avg(altitudes),
        "min_altitude_ft": min(altitudes) if altitudes else None,
        "max_altitude_ft": max(altitudes) if altitudes else None,
        "avg_speed_kts": _safe_avg(speeds),
        "min_speed_kts": min(speeds) if speeds else None,
        "max_speed_kts": max(speeds) if speeds else None,
        "latest_updated_at": max((item.updated_at for item in flights), default=None),
        "lat_min": min((item.lat for item in flights), default=None),
        "lat_max": max((item.lat for item in flights), default=None),
        "lon_min": min((item.lon for item in flights), default=None),
        "lon_max": max((item.lon for item in flights), default=None),
    }
    return ApiResponse(data=data)


@router.get("/debug/flights-dashboard", response_class=HTMLResponse)
async def flights_dashboard(
    auto_refresh_ms: int = Query(default=5000, ge=1000, le=60000),
) -> HTMLResponse:
    html = DASHBOARD_HTML.replace("__AUTO_REFRESH_MS__", str(auto_refresh_ms))
    return HTMLResponse(content=html)


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sky-Trace Backend Data Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --text: #17233a;
      --muted: #5f6b7a;
      --line: #dde3ec;
      --accent: #0a7a5b;
      --accent-soft: #d8f3ea;
      --warn: #b45309;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", Tahoma, Arial, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 15% 10%, #e9f4ff 0, transparent 35%),
        radial-gradient(circle at 85% 0%, #eefbf5 0, transparent 30%),
        var(--bg);
      padding: 20px;
    }
    .wrap {
      max-width: 1280px;
      margin: 0 auto;
      display: grid;
      gap: 16px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
      padding: 14px;
    }
    h1 {
      margin: 0 0 4px 0;
      font-size: 24px;
    }
    .muted {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    .grid {
      display: grid;
      gap: 12px;
      grid-template-columns: repeat(6, minmax(120px, 1fr));
    }
    .card {
      border: 1px solid var(--line);
      border-radius: 10px;
      background: linear-gradient(180deg, #ffffff 0%, #f9fcff 100%);
      padding: 10px;
    }
    .card .k {
      color: var(--muted);
      font-size: 12px;
    }
    .card .v {
      margin-top: 6px;
      font-size: 22px;
      font-weight: 700;
      color: var(--accent);
    }
    .split {
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 12px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 8px 6px;
      vertical-align: top;
    }
    th {
      font-size: 12px;
      color: var(--muted);
      background: #fbfdff;
      position: sticky;
      top: 0;
    }
    .scroll {
      max-height: 330px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .btn {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      border-radius: 6px;
      padding: 4px 8px;
      cursor: pointer;
      font-size: 12px;
    }
    .btn:hover { background: var(--accent-soft); }
    .raw {
      margin: 0;
      max-height: 280px;
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #0f172a;
      color: #f8fafc;
      padding: 10px;
      font: 12px/1.4 Consolas, Monaco, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }
    canvas {
      width: 100%;
      height: 280px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: linear-gradient(180deg, #f7fbff 0%, #eef5ff 100%);
    }
    .warn {
      color: var(--warn);
      font-weight: 600;
    }
    @media (max-width: 1024px) {
      .grid { grid-template-columns: repeat(3, minmax(120px, 1fr)); }
      .split { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h1>Sky-Trace Backend Data Dashboard</h1>
      <div class="muted">
        This page helps inspect what backend APIs are returning and how the data can be used.
        It auto-refreshes every <span id="refreshLabel"></span> ms.
      </div>
    </section>

    <section class="panel grid" id="summaryCards"></section>

    <section class="panel split">
      <div>
        <h3>Current Flight Positions</h3>
        <canvas id="posCanvas" width="760" height="320"></canvas>
        <div class="muted">Scatter projection by lat/lon from /api/v1/flights</div>
      </div>
      <div>
        <h3>Current Flights</h3>
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Flight</th>
                <th>Callsign</th>
                <th>Lat</th>
                <th>Lon</th>
                <th>Alt(ft)</th>
                <th>Spd(kts)</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody id="flightRows"></tbody>
          </table>
        </div>
      </div>
    </section>

    <section class="panel split">
      <div>
        <h3>Selected Flight Detail</h3>
        <div class="muted">Data from /api/v1/flights/{flight_id} and /api/v1/flights/{flight_id}/track</div>
        <div class="scroll">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Lat</th>
                <th>Lon</th>
                <th>Alt(ft)</th>
                <th>Spd(kts)</th>
              </tr>
            </thead>
            <tbody id="trackRows"></tbody>
          </table>
        </div>
      </div>
      <div>
        <h3>Raw JSON Snapshot</h3>
        <div class="muted">Directly shows the exact payloads received from backend APIs.</div>
        <h4>/api/v1/flights</h4>
        <pre class="raw" id="rawFlights"></pre>
        <h4>/api/v1/flights/{flight_id}</h4>
        <pre class="raw" id="rawDetail"></pre>
      </div>
    </section>

    <section class="panel" id="fr24DetailSection" style="display:none">
      <h3>FR24 On-demand Details <span style="font-size:13px;font-weight:normal;color:#f97316">(GET /api/v1/flights/{flight_id}/fr24-details)</span></h3>
      <div class="muted">Click the <b>FR24详情</b> button in the flight table above to fetch aircraft age, full type name, trail, delay, and complete airport info.</div>
      <pre class="raw" id="rawFr24Detail"></pre>
    </section>

    <section class="panel">
      <div class="muted">
        Usage hints:
        1) Position fields (lat/lon/heading/speed/altitude) are used for map markers and movement rendering.
        2) flight_id and callsign are used for search and linking list/detail views.
        3) track_points are used for route playback and trend analysis.
      </div>
      <div id="status" class="muted"></div>
    </section>
  </div>

  <script>
    const REFRESH_MS = __AUTO_REFRESH_MS__;
    let selectedFlightId = null;
    let latestFlights = [];

    document.getElementById("refreshLabel").textContent = String(REFRESH_MS);

    function setStatus(text, isWarn = false) {
      const el = document.getElementById("status");
      el.textContent = text;
      el.className = isWarn ? "warn" : "muted";
    }

    function pretty(value) {
      return JSON.stringify(value, null, 2);
    }

    function setRaw(id, data) {
      document.getElementById(id).textContent = pretty(data);
    }

    async function apiGet(path) {
      const resp = await fetch(path);
      if (!resp.ok) {
        throw new Error("HTTP " + resp.status + " for " + path);
      }
      const payload = await resp.json();
      return payload.data;
    }

    function cardItem(name, value) {
      return '<div class="card"><div class="k">' + name + '</div><div class="v">' + value + '</div></div>';
    }

    function renderSummary(summary, stats) {
      const bySource = (stats && stats.by_source) || {};
      const fr24Count = bySource.fr24 ?? 0;
      const oskyCount = bySource.opensky ?? 0;
      const cards = [
        cardItem("Total flights", summary.total ?? "-"),
        cardItem("FR24 flights", fr24Count),
        cardItem("OpenSky flights", oskyCount),
        cardItem("Avg altitude ft", summary.avg_altitude_ft ?? "-"),
        cardItem("Avg speed kts", summary.avg_speed_kts ?? "-"),
        cardItem("Latest update", summary.latest_updated_at ? summary.latest_updated_at.replace("T", " ").slice(0, 19) + " UTC" : "-"),
      ];
      document.getElementById("summaryCards").innerHTML = cards.join("");
    }

    function renderFlights(items) {
      const rows = items.map((f) => {
        const isFr24 = (f.flight_id || "").startsWith("fr24-");
        const badge = isFr24
          ? '<span style="background:#f97316;color:#fff;border-radius:4px;padding:1px 5px;font-size:11px;margin-right:4px">FR24</span>'
          : '<span style="background:#0a7a5b;color:#fff;border-radius:4px;padding:1px 5px;font-size:11px;margin-right:4px">OpenSky</span>';
        const detailBtn = isFr24
          ? ' <button class="btn" data-fr24-id="' + f.flight_id + '" style="border-color:#f97316">FR24详情</button>'
          : "";
        return "<tr>"
          + "<td>" + badge + (f.flight_id ?? "") + "</td>"
          + "<td>" + (f.callsign ?? "") + "</td>"
          + "<td>" + (f.lat ?? "") + "</td>"
          + "<td>" + (f.lon ?? "") + "</td>"
          + "<td>" + (f.altitude_ft ?? "") + "</td>"
          + "<td>" + (f.speed_kts ?? "") + "</td>"
          + '<td><button class="btn" data-id="' + f.flight_id + '">基础</button>' + detailBtn + "</td>"
          + "</tr>";
      });
      document.getElementById("flightRows").innerHTML = rows.join("");

      for (const btn of document.querySelectorAll("button[data-id]")) {
        btn.addEventListener("click", async () => {
          selectedFlightId = btn.getAttribute("data-id");
          await loadDetail(selectedFlightId);
        });
      }
      for (const btn of document.querySelectorAll("button[data-fr24-id]")) {
        btn.addEventListener("click", async () => {
          const fid = btn.getAttribute("data-fr24-id");
          await loadFr24Detail(fid);
        });
      }
    }

    function renderTrackRows(points) {
      const rows = points.map((p) => {
        return "<tr>"
          + "<td>" + (p.ts ?? "") + "</td>"
          + "<td>" + (p.lat ?? "") + "</td>"
          + "<td>" + (p.lon ?? "") + "</td>"
          + "<td>" + (p.altitude_ft ?? "") + "</td>"
          + "<td>" + (p.speed_kts ?? "") + "</td>"
          + "</tr>";
      });
      document.getElementById("trackRows").innerHTML = rows.join("");
    }

    function drawScatter(items) {
      const canvas = document.getElementById("posCanvas");
      const ctx = canvas.getContext("2d");
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      ctx.fillStyle = "#f8fbff";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "#d6e2f1";
      ctx.strokeRect(0.5, 0.5, w - 1, h - 1);

      if (!items.length) {
        ctx.fillStyle = "#64748b";
        ctx.font = "14px Segoe UI";
        ctx.fillText("No flight positions yet", 16, 24);
        return;
      }

      const latMin = Math.min(...items.map((i) => i.lat));
      const latMax = Math.max(...items.map((i) => i.lat));
      const lonMin = Math.min(...items.map((i) => i.lon));
      const lonMax = Math.max(...items.map((i) => i.lon));

      const latSpan = Math.max(latMax - latMin, 0.00001);
      const lonSpan = Math.max(lonMax - lonMin, 0.00001);

      const pad = 26;
      for (const f of items) {
        const x = pad + ((f.lon - lonMin) / lonSpan) * (w - 2 * pad);
        const y = h - pad - ((f.lat - latMin) / latSpan) * (h - 2 * pad);
        const isFr24 = (f.flight_id || "").startsWith("fr24-");
        ctx.fillStyle = isFr24 ? "#f97316" : "#0a7a5b";
        ctx.beginPath();
        ctx.arc(x, y, isFr24 ? 3 : 4, 0, Math.PI * 2);
        ctx.fill();
      }

      // Legend
      ctx.fillStyle = "#0a7a5b";
      ctx.beginPath(); ctx.arc(w - 110, h - 16, 4, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#475569"; ctx.font = "11px Segoe UI";
      ctx.fillText("OpenSky", w - 102, h - 12);
      ctx.fillStyle = "#f97316";
      ctx.beginPath(); ctx.arc(w - 50, h - 16, 3, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#475569";
      ctx.fillText("FR24", w - 42, h - 12);

      ctx.fillStyle = "#475569";
      ctx.font = "12px Segoe UI";
      ctx.fillText("lon: " + lonMin.toFixed(4) + " to " + lonMax.toFixed(4), 8, h - 8);
      ctx.fillText("lat: " + latMin.toFixed(4) + " to " + latMax.toFixed(4), 8, 14);
    }

    async function loadDetail(flightId) {
      try {
        const detail = await apiGet("/api/v1/flights/" + encodeURIComponent(flightId));
        const track = await apiGet("/api/v1/flights/" + encodeURIComponent(flightId) + "/track");
        renderTrackRows(track || []);
        setRaw("rawDetail", detail || {});
      } catch (err) {
        setStatus(String(err), true);
      }
    }

    async function loadFr24Detail(flightId) {
      setStatus("Loading FR24 details for " + flightId + " ...");
      try {
        const detail = await apiGet("/api/v1/flights/" + encodeURIComponent(flightId) + "/fr24-details");
        setRaw("rawFr24Detail", detail || {});
        document.getElementById("fr24DetailSection").style.display = "";
        setStatus("FR24 details loaded for " + flightId);
      } catch (err) {
        setStatus("FR24 detail: " + String(err), true);
        setRaw("rawFr24Detail", { error: String(err) });
        document.getElementById("fr24DetailSection").style.display = "";
      }
    }

    async function refreshAll() {
      try {
        const summary = await apiGet("/api/v1/flights/summary");
        const stats = await apiGet("/api/v1/flights/summary/stats");
        const flightsPayload = await apiGet("/api/v1/flights?page=1&page_size=500");
        const items = (flightsPayload && flightsPayload.items) ? flightsPayload.items : [];
        latestFlights = items;

        renderSummary(summary || {}, stats || {});
        renderFlights(items);
        drawScatter(items);
        setRaw("rawFlights", flightsPayload || {});

        if (!selectedFlightId && items.length) {
          selectedFlightId = items[0].flight_id;
        }
        if (selectedFlightId) {
          await loadDetail(selectedFlightId);
        }
        setStatus("Last refresh: " + new Date().toLocaleString() + " | total=" + (stats && stats.total != null ? stats.total : (summary && summary.total != null ? summary.total : items.length)) + " (FR24: " + ((stats && stats.by_source && stats.by_source.fr24) || 0) + ", OpenSky: " + ((stats && stats.by_source && stats.by_source.opensky) || 0) + ")");
      } catch (err) {
        setStatus(String(err), true);
      }
    }

    refreshAll();
    setInterval(refreshAll, REFRESH_MS);
  </script>
</body>
</html>
"""
