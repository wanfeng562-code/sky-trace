"""API usage monitoring dashboard.

Exposes a machine-readable JSON endpoint plus an operator-facing HTML dashboard
that visualises per-source call counts, daily quota consumption, health status
and error history in real-time.

Endpoints
---------
GET /api/v1/api-monitor          → JSON snapshot (for programmatic consumption)
GET /debug/api-monitor           → HTML dashboard (auto-refreshes every 10 s)
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse

from app.models.schemas import ApiResponse
from app.state import unified_pipeline

router = APIRouter(tags=["api-monitor"])


@router.get("/api/v1/api-monitor")
async def get_api_monitor_snapshot() -> ApiResponse:
    """Return a combined snapshot of quota usage and pipeline health."""
    status = await unified_pipeline.get_status()
    quota = await unified_pipeline.get_quota()
    return ApiResponse(data={"status": status, "quota": quota})


@router.get("/debug/api-monitor", response_class=HTMLResponse)
async def api_monitor_dashboard(
    auto_refresh_ms: int = Query(default=10000, ge=2000, le=120000),
) -> HTMLResponse:
    html = _MONITOR_HTML.replace("__AUTO_REFRESH_MS__", str(auto_refresh_ms))
    return HTMLResponse(content=html)


# ---------------------------------------------------------------------------
# Inline HTML dashboard
# ---------------------------------------------------------------------------

_MONITOR_HTML = """<!doctype html>
<html lang="zh-cn">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Sky-Trace · API 用量监控</title>
  <style>
    :root {
      --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#e6edf3;
      --muted:#8b949e; --green:#3fb950; --yellow:#d29922; --red:#f85149;
      --blue:#58a6ff; --purple:#bc8cff; --accent:#238636;
    }
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:var(--bg);color:var(--text);font-family:"Segoe UI",sans-serif;padding:20px}
    h1{font-size:22px;margin-bottom:4px;color:var(--blue)}
    .sub{color:var(--muted);font-size:13px;margin-bottom:20px}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin-bottom:20px}
    .panel{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:14px}
    .panel h2{font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;margin-bottom:12px}
    .stat{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
    .stat .label{font-size:13px;color:var(--muted)}
    .stat .value{font-size:16px;font-weight:700}
    .ok{color:var(--green)} .warn{color:var(--yellow)} .err{color:var(--red)} .info{color:var(--blue)}
    .bar-wrap{background:#21262d;border-radius:4px;height:8px;margin-top:6px;overflow:hidden}
    .bar{height:8px;border-radius:4px;transition:width .4s}
    .bar.ok{background:var(--green)} .bar.warn{background:var(--yellow)} .bar.err{background:var(--red)}
    .source-card{border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:10px}
    .source-card .name{font-weight:700;font-size:14px;margin-bottom:6px}
    .kv{font-size:12px;color:var(--muted);line-height:1.8}
    .kv span{color:var(--text)}
    .badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600}
    .badge.ok{background:#1a3a2a;color:var(--green)}
    .badge.warn{background:#3a2e00;color:var(--yellow)}
    .badge.err{background:#3a1a1a;color:var(--red)}
    .badge.idle{background:#1c2128;color:var(--muted)}
    #ts{color:var(--muted);font-size:12px;margin-top:16px}
  </style>
</head>
<body>
  <h1>Sky-Trace · API 用量监控</h1>
  <p class="sub">实时显示各数据源调用次数、配额消耗及健康状态 · 自动刷新间隔 <span id="interval"></span> 秒</p>

  <div class="grid" id="quota-grid"></div>
  <div class="grid" id="status-grid"></div>
  <div id="ts"></div>

  <script>
    const REFRESH = __AUTO_REFRESH_MS__;
    document.getElementById('interval').textContent = (REFRESH/1000).toFixed(0);

    const QUOTA_CONFIG = {
      opensky:    { label:'OpenSky Network', budget:4000, unit:'调用/日', note:'OAuth2 = 4000点/日' },
      openweather:{ label:'OpenWeatherMap',  budget:1000, unit:'调用/日', note:'Free = 1000次/日' },
      airlabs:    { label:'AirLabs v9',      budget:1000, unit:'调用/月', note:'Free = 1000次/月' },
    };

    const TILE_CONFIG = {
      maptiler: { label:'MapTiler Cloud', note:'Free = 100,000 tile loads/月' },
      stadia:   { label:'Stadia Maps',    note:'免费非商业用途，月额度 429 时切换' },
    };

    const SOURCE_LABELS = {
      realtime:    { icon:'✈️', label:'实时位置层',   source:'OpenSky / FR24' },
      environment: { icon:'🌤', label:'气象环境层',   source:'OpenWeatherMap' },
      commercial:  { icon:'🏷️', label:'商业富集层',   source:'AirLabs v9' },
    };

    function statusBadge(entry) {
      if (!entry.last_success_at && !entry.last_error_at) return '<span class="badge idle">待机</span>';
      if (entry.failure_count > 0 && entry.last_error_at > (entry.last_success_at||'')) return '<span class="badge err">异常</span>';
      return '<span class="badge ok">正常</span>';
    }

    function barClass(pct) {
      if (pct >= 90) return 'err';
      if (pct >= 70) return 'warn';
      return 'ok';
    }

    function fmt(v) { return v ?? '--'; }
    function fmtDt(iso) {
      if (!iso) return '--';
      const d = new Date(iso);
      return d.toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
    }

    async function refresh() {
      try {
        const r = await fetch('/api/v1/api-monitor');
        const json = await r.json();
        const {status, quota} = json.data;

        // ── Quota cards ──
        let qHtml = '';
        for (const [key, cfg] of Object.entries(QUOTA_CONFIG)) {
          const q = quota[key] || {};
          const calls = q.today_calls ?? 0;
          const budget = q.daily_budget ?? cfg.budget;
          const pct = budget > 0 ? Math.min(100, Math.round(calls/budget*100)) : 0;
          const cls = barClass(pct);
          qHtml += `
            <div class="panel">
              <h2>${cfg.label}</h2>
              <div class="stat">
                <span class="label">今日调用</span>
                <span class="value ${cls}">${calls.toLocaleString()} / ${budget.toLocaleString()}</span>
              </div>
              <div class="stat">
                <span class="label">配额消耗</span>
                <span class="value ${cls}">${pct}%</span>
              </div>
              <div class="bar-wrap"><div class="bar ${cls}" style="width:${pct}%"></div></div>
              <div style="margin-top:8px;font-size:11px;color:var(--muted)">${cfg.note}</div>
            </div>`;
        }

        // FR24 status card (no quota tracking, show current/configured source)
        const fr24Active = (status.realtime?.source||'').toLowerCase().includes('fr24');
        const defaultSrc = status.profile?.default_realtime_source || '--';
        const curSrc = status.realtime?.source || '--';
        qHtml += `
          <div class="panel">
            <h2>FlightRadar24 (CF Worker)</h2>
            <div class="stat">
              <span class="label">当前数据源</span>
              <span class="value ${fr24Active ? 'ok' : 'info'}">${curSrc}</span>
            </div>
            <div class="stat">
              <span class="label">配置默认源</span>
              <span class="value info">${defaultSrc}</span>
            </div>
            <div class="stat">
              <span class="label">失败次数</span>
              <span class="value ${(status.realtime?.failure_count||0)>0 ? 'err' : 'ok'}">
                ${status.realtime?.failure_count ?? 0}
              </span>
            </div>
            <div style="margin-top:8px;font-size:11px;color:var(--muted)">Cloudflare Worker免费层 = 100k次/日</div>
          </div>`;

        // ── Tile proxy stats ──
        try {
          const tileR = await fetch('/api/v1/tiles/stats');
          const tileJson = await tileR.json();
          const td = tileJson.data || {};
          let tileHtml = '';
          for (const [k, cfg] of Object.entries(TILE_CONFIG)) {
            const cnt = td[k] ?? 0;
            tileHtml += `
              <div class="panel">
                <h2>${cfg.label} — 底图代理</h2>
                <div class="stat">
                  <span class="label">本次启动请求总数</span>
                  <span class="value info">${cnt.toLocaleString()}</span>
                </div>
                <div style="margin-top:8px;font-size:11px;color:var(--muted)">${cfg.note}</div>
              </div>`;
          }
          qHtml += tileHtml;
        } catch(e) { /* tile stats endpoint optional */ }

        document.getElementById('quota-grid').innerHTML = qHtml;

        // ── Status cards ──
        let sHtml = '';
        for (const [key, meta] of Object.entries(SOURCE_LABELS)) {
          const e = status[key] || {};
          const total = (e.success_count||0) + (e.failure_count||0);
          const errRate = total > 0 ? Math.round((e.failure_count||0)/total*100) : 0;
          sHtml += `
            <div class="panel">
              <h2>${meta.icon} ${meta.label}</h2>
              <div class="source-card">
                <div class="name">${meta.source} ${statusBadge(e)}</div>
                <div class="kv">
                  上次成功：<span>${fmtDt(e.last_success_at)}</span><br>
                  上次失败：<span>${fmtDt(e.last_error_at)}</span><br>
                  最新错误：<span class="${e.last_error ? 'warn' : ''}">${e.last_error||'无'}</span><br>
                  成功次数：<span>${fmt(e.success_count)}</span><br>
                  失败次数：<span class="${e.failure_count>0?'err':''}">${fmt(e.failure_count)}</span><br>
                  错误率：<span class="${errRate>20?'err':errRate>5?'warn':'ok'}">${errRate}%</span><br>
                  上次数量：<span>${fmt(e.last_count)}</span>
                </div>
              </div>
            </div>`;
        }
        document.getElementById('status-grid').innerHTML = sHtml;
        document.getElementById('ts').textContent = '最后更新: ' + new Date().toLocaleTimeString('zh-CN');
      } catch(err) {
        console.error('Monitor refresh error', err);
      }
    }

    refresh();
    setInterval(refresh, REFRESH);
  </script>
</body>
</html>"""
