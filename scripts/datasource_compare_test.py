"""
datasource_compare_test.py
==========================
One-shot test script that fetches real-time flight data from three sources:
  1. OpenSky Network  (OAuth2 or anonymous)
  2. AirLabs /flights (API Key, single global call)
  3. FlightRadar24    (via unofficial FlightRadarAPI SDK, no key needed)

Then analyses:
  - Region coverage (lat/lon bucket count)
  - Field availability per source
  - Unique aircraft overlap between sources

Output:
  - Summary printed to console
  - Raw JSON saved to  scripts/compare_results/  directory
  - Markdown report saved to docs/数据源对比测试报告.md

Run from repo root or server/ directory:
    python scripts/datasource_compare_test.py

Dependencies (in server venv):
    pip install aiohttp python-dotenv FlightRadarAPI
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── path setup ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_ROOT = REPO_ROOT / "server"
sys.path.insert(0, str(SERVER_ROOT))

# ── load .env  ──────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(SERVER_ROOT / ".env", override=True)
except ImportError:
    pass  # dotenv optional; fall back to real env vars

OPENSKY_CLIENT_ID     = os.getenv("OPENSKY_CLIENT_ID", "")
OPENSKY_CLIENT_SECRET = os.getenv("OPENSKY_CLIENT_SECRET", "")
OPENSKY_USERNAME      = os.getenv("OPENSKY_USERNAME", "")
OPENSKY_PASSWORD      = os.getenv("OPENSKY_PASSWORD", "")
AIRLABS_API_KEY       = os.getenv("AIRLABS_API_KEY", "")
HTTP_PROXY            = os.getenv("HTTP_PROXY", "") or None

OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
OPENSKY_API_URL   = "https://opensky-network.org/api/states/all"
AIRLABS_API_URL   = "https://airlabs.co/api/v9/flights"

# ── region definitions (lat_min, lat_max, lon_min, lon_max) ─────────────────
REGIONS: dict[str, tuple[float, float, float, float]] = {
    "中国大陆":         ( 18.0,  55.0,  73.0, 135.0),
    "东南亚":           ( -5.0,  25.0,  95.0, 140.0),
    "东亚(日韩)":       ( 25.0,  45.0, 120.0, 150.0),
    "南亚":             (  5.0,  35.0,  60.0,  95.0),
    "中东":             ( 12.0,  40.0,  35.0,  65.0),
    "欧洲":             ( 35.0,  72.0, -12.0,  45.0),
    "北美洲":           ( 15.0,  75.0,-170.0, -50.0),
    "南美洲":           (-60.0,  15.0, -85.0, -30.0),
    "非洲":             (-40.0,  38.0, -20.0,  55.0),
    "大洋洲":           (-50.0, -10.0, 110.0, 180.0),
    "北极/南极及其他":  None,  # type: ignore[assignment]  # catch-all
}


def classify_region(lat: float, lon: float) -> str:
    for name, bbox in REGIONS.items():
        if bbox is None:
            continue
        lat_min, lat_max, lon_min, lon_max = bbox
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return "北极/南极及其他"


# ── OpenSky ──────────────────────────────────────────────────────────────────
async def fetch_opensky(session) -> dict[str, Any]:
    """Return raw OpenSky payload + token metadata."""
    result: dict[str, Any] = {"auth_method": "anonymous", "raw": None, "error": None, "elapsed_s": None}
    headers: dict[str, str] = {}
    auth = None

    # OAuth2
    if OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET:
        try:
            t0 = time.monotonic()
            async with session.post(
                OPENSKY_TOKEN_URL,
                data={"grant_type": "client_credentials",
                      "client_id": OPENSKY_CLIENT_ID,
                      "client_secret": OPENSKY_CLIENT_SECRET},
                proxy=HTTP_PROXY,
            ) as resp:
                if resp.status == 200:
                    token_data = await resp.json(content_type=None)
                    token = token_data.get("access_token", "")
                    headers["Authorization"] = f"Bearer {token}"
                    result["auth_method"] = "oauth2"
                    print(f"  [OpenSky] OAuth2 token acquired ({time.monotonic()-t0:.1f}s)")
                else:
                    txt = await resp.text()
                    result["error"] = f"OAuth2 token failed: HTTP {resp.status} {txt[:100]}"
                    print(f"  [OpenSky] OAuth2 FAILED: {result['error']}")
        except Exception as exc:
            result["error"] = f"OAuth2 exception: {exc}"
            print(f"  [OpenSky] OAuth2 exception: {exc}")
    elif OPENSKY_USERNAME and OPENSKY_PASSWORD:
        import aiohttp
        auth = aiohttp.BasicAuth(OPENSKY_USERNAME, OPENSKY_PASSWORD)
        result["auth_method"] = "basic"

    t0 = time.monotonic()
    try:
        async with session.get(
            OPENSKY_API_URL,
            params={"extended": 1},
            headers=headers or None,
            auth=auth,
            proxy=HTTP_PROXY,
        ) as resp:
            result["elapsed_s"] = round(time.monotonic() - t0, 2)
            result["http_status"] = resp.status
            remaining = resp.headers.get("X-Rate-Limit-Remaining")
            if remaining:
                result["credits_remaining"] = remaining
            if resp.status == 200:
                result["raw"] = await resp.json(content_type=None)
                print(f"  [OpenSky] HTTP 200 — {len(result['raw'].get('states') or [])} states "
                      f"({result['elapsed_s']}s)")
            else:
                txt = await resp.text()
                result["error"] = f"HTTP {resp.status}: {txt[:200]}"
                print(f"  [OpenSky] Error: {result['error']}")
    except Exception as exc:
        result["elapsed_s"] = round(time.monotonic() - t0, 2)
        result["error"] = str(exc)
        print(f"  [OpenSky] Exception: {exc}")

    return result


def parse_opensky(raw: dict | None) -> list[dict]:
    """Convert OpenSky states array to normalized dicts."""
    if not raw:
        return []
    flights = []
    for row in (raw.get("states") or []):
        if not isinstance(row, list) or len(row) < 11:
            continue
        lon = row[5]
        lat = row[6]
        if lon is None or lat is None:
            continue
        speed_ms  = row[9]
        alt_m     = row[7]
        heading   = row[10]
        speed_kts = round(speed_ms * 1.943844) if speed_ms else None
        alt_ft    = round(alt_m   * 3.28084)   if alt_m    else None
        icao24    = str(row[0]).strip().lower() if row[0] else None
        callsign  = str(row[1]).strip()         if row[1] else None
        on_ground = bool(row[8])
        category  = row[17] if len(row) >= 18 else None

        flights.append({
            "source":       "opensky",
            "icao24":       icao24,
            "callsign":     callsign,
            "lat":          float(lat),
            "lon":          float(lon),
            "altitude_ft":  alt_ft,
            "speed_kts":    speed_kts,
            "heading":      round(heading) % 360 if heading else None,
            "on_ground":    on_ground,
            "category":     category,
            # not available from this endpoint:
            "reg_number":   None,
            "dep_iata":     None,
            "arr_iata":     None,
            "aircraft_type":None,
            "airline_icao": None,
            "status":       "on-ground" if on_ground else "en-route",
            "squawk":       row[14] if len(row) > 14 else None,
        })
    return flights


# ── AirLabs ──────────────────────────────────────────────────────────────────
async def fetch_airlabs(session) -> dict[str, Any]:
    """Fetch all flights from AirLabs /flights (single global call, no bbox)."""
    result: dict[str, Any] = {"raw": None, "error": None, "elapsed_s": None}
    if not AIRLABS_API_KEY:
        result["error"] = "AIRLABS_API_KEY not set"
        print("  [AirLabs] AIRLABS_API_KEY not set — skipping")
        return result

    t0 = time.monotonic()
    try:
        async with session.get(
            AIRLABS_API_URL,
            params={"api_key": AIRLABS_API_KEY},
            proxy=HTTP_PROXY,
        ) as resp:
            result["elapsed_s"] = round(time.monotonic() - t0, 2)
            result["http_status"] = resp.status
            if resp.status == 200:
                payload = await resp.json(content_type=None)
                # Free plan: {"request":{...}, "response":[...]}
                if isinstance(payload, list):
                    result["raw"] = payload
                elif isinstance(payload, dict) and isinstance(payload.get("response"), list):
                    result["raw"] = payload["response"]
                    result["request_meta"] = payload.get("request", {})
                else:
                    result["error"] = f"Unexpected shape: {list(payload.keys()) if isinstance(payload, dict) else type(payload)}"
                    result["raw"] = []
                count = len(result["raw"] or [])
                print(f"  [AirLabs] HTTP 200 — {count} flights ({result['elapsed_s']}s)")
            else:
                txt = await resp.text()
                result["error"] = f"HTTP {resp.status}: {txt[:200]}"
                print(f"  [AirLabs] Error: {result['error']}")
    except Exception as exc:
        result["elapsed_s"] = round(time.monotonic() - t0, 2)
        result["error"] = str(exc)
        print(f"  [AirLabs] Exception: {exc}")

    return result


def parse_airlabs(raw: list | None) -> list[dict]:
    """Normalize AirLabs flight list."""
    if not raw:
        return []
    flights = []
    for f in raw:
        lat = f.get("lat")
        lng = f.get("lng")  # Note: AirLabs uses 'lng'
        if lat is None or lng is None:
            continue
        alt_m     = f.get("alt")
        speed_kmh = f.get("speed")
        alt_ft    = round(alt_m   * 3.28084)   if alt_m    is not None else None
        speed_kts = round(speed_kmh * 0.539957) if speed_kmh is not None else None
        dir_raw   = f.get("dir")
        heading   = round(dir_raw) % 360 if dir_raw is not None else None

        flights.append({
            "source":        "airlabs",
            "icao24":        str(f.get("hex", "")).strip().lower() or None,
            "callsign":      f.get("flight_icao") or f.get("flight_iata"),
            "lat":           float(lat),
            "lon":           float(lng),
            "altitude_ft":   alt_ft,
            "speed_kts":     speed_kts,
            "heading":       heading,
            "on_ground":     None,  # not directly provided
            "category":      None,
            "reg_number":    f.get("reg_number"),
            "dep_iata":      f.get("dep_iata") or f.get("dep_icao"),
            "arr_iata":      f.get("arr_iata") or f.get("arr_icao"),
            "aircraft_type": f.get("aircraft_icao"),
            "airline_icao":  f.get("airline_icao") or f.get("airline_iata"),
            "status":        f.get("status"),
            "squawk":        f.get("squawk"),
            "v_speed":       f.get("v_speed"),
            "flag":          f.get("flag"),
        })
    return flights


# ── FlightRadar24 ─────────────────────────────────────────────────────────────
def fetch_flightradar_sync() -> dict[str, Any]:
    """Synchronous FlightRadar24 fetch (run in executor by caller)."""
    result: dict[str, Any] = {"raw": [], "error": None, "elapsed_s": None}
    try:
        from FlightRadar24 import FlightRadar24API  # type: ignore[import]
    except ImportError:
        result["error"] = "FlightRadarAPI not installed; run: pip install FlightRadarAPI"
        print(f"  [FR24] {result['error']}")
        return result

    t0 = time.monotonic()
    try:
        fr = FlightRadar24API()
        flights = fr.get_flights()
        result["elapsed_s"] = round(time.monotonic() - t0, 2)
        result["raw"] = flights
        print(f"  [FR24] {len(flights)} flights ({result['elapsed_s']}s)")
    except Exception as exc:
        result["elapsed_s"] = round(time.monotonic() - t0, 2)
        result["error"] = str(exc)
        print(f"  [FR24] Exception: {exc}")

    return result


def parse_flightradar(raw: list) -> list[dict]:
    """Normalize FlightRadarAPI Flight objects."""
    flights = []
    for f in (raw or []):
        lat = getattr(f, "latitude", None)
        lon = getattr(f, "longitude", None)
        if lat is None or lon is None:
            continue
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            continue

        alt_raw   = getattr(f, "altitude",     None)
        spd_raw   = getattr(f, "ground_speed",  None)
        hdg_raw   = getattr(f, "heading",       None)
        icao24    = str(getattr(f, "icao_24bit", "") or "").strip().lower() or None
        callsign  = str(getattr(f, "callsign",   "") or "").strip() or None
        reg       = str(getattr(f, "registration","") or "").strip() or None
        ac_type   = str(getattr(f, "aircraft_code","")or "").strip() or None
        airline   = str(getattr(f, "airline_icao", "")or "").strip() or None
        dep       = str(getattr(f, "origin_airport_iata","")or "").strip() or None
        arr       = str(getattr(f, "destination_airport_iata","")or "").strip() or None
        on_ground = bool(getattr(f, "on_ground", False))

        flights.append({
            "source":        "flightradar24",
            "icao24":        icao24,
            "callsign":      callsign,
            "lat":           lat,
            "lon":           lon,
            "altitude_ft":   round(float(alt_raw)) if alt_raw else None,
            "speed_kts":     round(float(spd_raw)) if spd_raw else None,
            "heading":       round(float(hdg_raw)) % 360 if hdg_raw else None,
            "on_ground":     on_ground,
            "category":      None,
            "reg_number":    reg,
            "dep_iata":      dep if dep else None,
            "arr_iata":      arr if arr else None,
            "aircraft_type": ac_type,
            "airline_icao":  airline,
            "status":        "on-ground" if on_ground else "en-route",
            "squawk":        str(getattr(f, "squawk", "") or "").strip() or None,
            "v_speed":       None,
            "flag":          None,
        })
    return flights


# ── Analysis ──────────────────────────────────────────────────────────────────
def analyse_regions(flights: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {r: 0 for r in REGIONS}
    for f in flights:
        region = classify_region(f["lat"], f["lon"])
        counts[region] = counts.get(region, 0) + 1
    return counts


def field_fill_rate(flights: list[dict], fields: list[str]) -> dict[str, str]:
    """Return field → 'N/total (pct%)' for each field."""
    total = len(flights)
    if total == 0:
        return {f: "N/A" for f in fields}
    result = {}
    for field in fields:
        non_null = sum(1 for fl in flights if fl.get(field) is not None)
        pct = round(non_null / total * 100)
        result[field] = f"{non_null}/{total} ({pct}%)"
    return result


COMPARE_FIELDS = [
    "icao24", "callsign", "lat", "lon",
    "altitude_ft", "speed_kts", "heading", "on_ground",
    "reg_number", "dep_iata", "arr_iata",
    "aircraft_type", "airline_icao", "status", "squawk",
]


def compute_overlap(
    a: list[dict], b: list[dict], source_a: str, source_b: str
) -> dict[str, Any]:
    """Count overlapping ICAO24 hex codes between two sources."""
    set_a = {f["icao24"] for f in a if f.get("icao24")}
    set_b = {f["icao24"] for f in b if f.get("icao24")}
    common = set_a & set_b
    return {
        "source_a": source_a, "source_b": source_b,
        "count_a": len(set_a), "count_b": len(set_b),
        "common": len(common),
        "overlap_pct_a": round(len(common) / len(set_a) * 100, 1) if set_a else 0,
        "overlap_pct_b": round(len(common) / len(set_b) * 100, 1) if set_b else 0,
    }


# ── Markdown report builder ───────────────────────────────────────────────────
def build_markdown(
    fetch_meta: dict[str, dict],
    parsed: dict[str, list[dict]],
    regions: dict[str, dict[str, int]],
    overlap_pairs: list[dict],
) -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 数据源对比测试报告",
        "",
        f"> 测试时间：{now_str}",
        "",
        "## 1. 测试概览",
        "",
        "| 数据源 | 认证方式 | HTTP状态 | 总航班数 | 耗时(s) | 备注 |",
        "| ------ | -------- | -------- | -------- | ------- | ---- |",
    ]

    source_labels = {
        "opensky":       "OpenSky Network",
        "airlabs":       "AirLabs /flights",
        "flightradar24": "FlightRadar24 (SDK)",
    }
    for key, label in source_labels.items():
        meta = fetch_meta.get(key, {})
        total = len(parsed.get(key, []))
        status = meta.get("http_status", "—")
        elapsed = meta.get("elapsed_s", "—")
        auth = meta.get("auth_method", "sdk/无需")
        error = meta.get("error") or ""
        note = f"⚠ {error[:60]}" if error else "OK"
        lines.append(f"| {label} | {auth} | {status} | **{total}** | {elapsed} | {note} |")

    lines += [
        "",
        "## 2. 区域覆盖分布",
        "",
        "| 区域 | OpenSky | AirLabs | FlightRadar24 |",
        "| ---- | ------: | ------: | ------------: |",
    ]
    all_regions = list(REGIONS.keys())
    for region in all_regions:
        os_cnt  = regions.get("opensky", {}).get(region, 0)
        al_cnt  = regions.get("airlabs", {}).get(region, 0)
        fr_cnt  = regions.get("flightradar24", {}).get(region, 0)
        lines.append(f"| {region} | {os_cnt} | {al_cnt} | {fr_cnt} |")

    os_total  = len(parsed.get("opensky", []))
    al_total  = len(parsed.get("airlabs", []))
    fr_total  = len(parsed.get("flightradar24", []))
    lines.append(f"| **合计** | **{os_total}** | **{al_total}** | **{fr_total}** |")

    lines += [
        "",
        "## 3. 字段填充率",
        "",
        "| 字段 | OpenSky | AirLabs | FlightRadar24 |",
        "| ---- | :-----: | :-----: | :-----------: |",
    ]
    for field in COMPARE_FIELDS:
        os_f  = field_fill_rate(parsed.get("opensky", []),       [field]).get(field, "N/A")
        al_f  = field_fill_rate(parsed.get("airlabs", []),       [field]).get(field, "N/A")
        fr_f  = field_fill_rate(parsed.get("flightradar24", []), [field]).get(field, "N/A")
        lines.append(f"| `{field}` | {os_f} | {al_f} | {fr_f} |")

    lines += [
        "",
        "## 4. ICAO24 重叠分析",
        "",
        "| 对比组 | 源A航班数 | 源B航班数 | 共同ICAO24 | 在A中占比 | 在B中占比 |",
        "| ------ | --------: | --------: | ---------: | --------: | --------: |",
    ]
    for ov in overlap_pairs:
        la = source_labels.get(ov["source_a"], ov["source_a"])
        lb = source_labels.get(ov["source_b"], ov["source_b"])
        lines.append(
            f"| {la} ↔ {lb} | {ov['count_a']} | {ov['count_b']} | "
            f"{ov['common']} | {ov['overlap_pct_a']}% | {ov['overlap_pct_b']}% |"
        )

    lines += [
        "",
        "## 5. 字段对比说明",
        "",
        "| 字段 | OpenSky 说明 | AirLabs 说明 | FlightRadar24 说明 |",
        "| ---- | ------------ | ------------ | ------------------ |",
        "| `icao24` | 24bit ICAO hex（索引0） | `hex` 字段 | `icao_24bit` 属性 |",
        "| `callsign` | 索引1，原始ATC呼号 | `flight_icao`/`flight_iata` | `callsign` 属性 |",
        "| `lat/lon` | 索引6/5，WGS84 | `lat`/`lng`（注意lng） | `latitude`/`longitude` |",
        "| `altitude_ft` | 索引7（米）×3.28084 | `alt`（米）×3.28084 | `altitude`（英尺，直接） |",
        "| `speed_kts` | 索引9（m/s）×1.9438 | `speed`（km/h）×0.5400 | `ground_speed`（节，直接） |",
        "| `heading` | 索引10（度） | `dir`（度） | `heading`（度） |",
        "| `on_ground` | 索引8（bool） | 不直接提供 | `on_ground`（bool） |",
        "| `reg_number` | 不提供 | `reg_number` | `registration` |",
        "| `dep_iata` | 不提供 | `dep_iata`/`dep_icao` | `origin_airport_iata` |",
        "| `arr_iata` | 不提供 | `arr_iata`/`arr_icao` | `destination_airport_iata` |",
        "| `aircraft_type` | `category`（数字分类） | `aircraft_icao`（机型代码） | `aircraft_code`（机型代码） |",
        "| `airline_icao` | 不提供 | `airline_icao`/`airline_iata` | `airline_icao` |",
        "| `squawk` | 索引14 | `squawk` | `squawk` |",
        "| `v_speed` | 不提供 | `v_speed`（km/h） | 不提供 |",
        "| `flag` | 不提供 | `flag`（国家ISO2） | 不提供 |",
        "",
        "## 6. 数据源定性对比",
        "",
        "| 维度 | OpenSky | AirLabs | FlightRadar24 |",
        "| ---- | ------- | ------- | ------------- |",
        "| 数据来源 | 全球ADS-B接收器网络 | 多源聚合（含ADS-B） | FR24专有接收器网络 |",
        "| 认证方式 | OAuth2 Client Credentials | API Key | 无需（非官方SDK） |",
        "| 免费额度 | 4000积分/天（OAuth2） | 1000次/月 | 无限制（存在封IP风险） |",
        "| 全球覆盖 | ✅ 全球 | ✅ 全球 | ✅ 全球 |",
        "| 位置精度 | ADS-B原始数据 | 同等 | FR24处理后数据 |",
        "| 位置字段 | lat/lon/alt/speed/heading | lat/lng/alt/speed/dir | latitude/longitude/altitude/ground_speed/heading |",
        "| 起降机场 | ❌ 不提供 | ✅ dep/arr IATA | ✅ origin/destination IATA |",
        "| 机型信息 | ⚠ 仅category分类（数字） | ✅ aircraft_icao | ✅ aircraft_code |",
        "| 航司信息 | ❌ 不提供 | ✅ airline_icao/iata | ✅ airline_icao |",
        "| 注册号 | ❌ 不提供 | ✅ reg_number | ✅ registration |",
        "| 垂直速度 | ❌ 不提供 | ✅ v_speed | ❌ 不提供 |",
        "| 国家标志 | ❌ 不提供 | ✅ flag | ❌ 不提供 |",
        "| 接入风险 | 低（官方API） | 低（官方API） | 高（非官方爬取，存在封IP风险） |",
        "| 适用场景 | P0实时位置主力 | P1补充富集字段 | 补充覆盖/备援 |",
        "",
        "## 7. 结论与建议",
        "",
        "### 互补策略",
        "",
        "```",
        "OpenSky   →  主力实时位置（icao24/lat/lon/alt/speed/heading）",
        "AirLabs   →  富集层（dep/arr/aircraft_type/airline/reg_number），单次调用覆盖所有航班",
        "FR24 SDK  →  备援补充（OpenSky离线/429时切换），但应控制频率防止封IP",
        "```",
        "",
        "### AirLabs 额度优化建议",
        "",
        "- 一次 `/flights` 调用（不带bbox）可获取全球所有可见航班，同时获得位置+富集数据",
        "- 额度：1000次/月 ≈ 33次/天，配合24h刷新间隔仅需1次/天",
        "- 若改为实时位置补充（90s一次）则需 960次/天 × 30天 = 28800次/月，超出免费额度",
        "- **推荐**：保持24h一次的商业层富集，不用于实时位置",
        "",
        "### FlightRadar24 使用注意",
        "",
        "- 非官方SDK，无SLA保证，FR24可能随时更新接口格式导致解析失败",
        "- 高频调用（<30s）可能触发IP封禁",
        "- 数据格式相对稳定，字段最丰富（直接提供英尺/节单位，无需换算）",
        "- 建议作为 OpenSky 完全失败时的备援，轮询间隔 ≥ 60s",
    ]

    return "\n".join(lines) + "\n"


# ── main ──────────────────────────────────────────────────────────────────────
async def main() -> None:
    import aiohttp

    out_dir = REPO_ROOT / "scripts" / "compare_results"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n=== Sky-Trace 数据源对比测试 ===")
    print(f"时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"HTTP_PROXY: {HTTP_PROXY or '(无)'}\n")

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:

        print(">> 请求 OpenSky ...")
        os_meta = await fetch_opensky(session)

        print(">> 请求 AirLabs ...")
        al_meta = await fetch_airlabs(session)

    print(">> 请求 FlightRadar24 (sync in thread) ...")
    loop = asyncio.get_event_loop()
    fr_meta = await loop.run_in_executor(None, fetch_flightradar_sync)

    # ── Parse ────────────────────────────────────────────────────────────────
    os_flights  = parse_opensky(os_meta.get("raw"))
    al_flights  = parse_airlabs(al_meta.get("raw"))
    fr_flights  = parse_flightradar(fr_meta.get("raw") or [])

    parsed = {
        "opensky":       os_flights,
        "airlabs":       al_flights,
        "flightradar24": fr_flights,
    }

    print(f"\n>> 解析结果: OpenSky={len(os_flights)} / AirLabs={len(al_flights)} / FR24={len(fr_flights)}")

    # ── Region analysis ───────────────────────────────────────────────────────
    regions = {
        src: analyse_regions(flights)
        for src, flights in parsed.items()
    }

    # ── Overlap ───────────────────────────────────────────────────────────────
    overlap_pairs = [
        compute_overlap(os_flights,  al_flights,  "opensky",  "airlabs"),
        compute_overlap(os_flights,  fr_flights,  "opensky",  "flightradar24"),
        compute_overlap(al_flights,  fr_flights,  "airlabs",  "flightradar24"),
    ]

    # ── Save raw JSON ─────────────────────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def _json_serializable(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Not serializable: {type(obj)}")

    for src, flights in parsed.items():
        out_path = out_dir / f"{ts}_{src}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(flights[:200], f, ensure_ascii=False, indent=2, default=_json_serializable)
        print(f"  Raw JSON (first 200): {out_path.relative_to(REPO_ROOT)}")

    # ── Build and save Markdown report ────────────────────────────────────────
    fetch_meta = {
        "opensky":       os_meta,
        "airlabs":       al_meta,
        "flightradar24": fr_meta,
    }
    md = build_markdown(fetch_meta, parsed, regions, overlap_pairs)
    report_path = REPO_ROOT / "docs" / "数据源对比测试报告.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"\n>> Markdown报告: {report_path.relative_to(REPO_ROOT)}")

    # ── Console summary ───────────────────────────────────────────────────────
    print("\n=== 区域覆盖摘要 ===")
    print(f"{'区域':<18} {'OpenSky':>8} {'AirLabs':>8} {'FR24':>8}")
    print("-" * 46)
    for region in REGIONS:
        os_c  = regions["opensky"].get(region, 0)
        al_c  = regions["airlabs"].get(region, 0)
        fr_c  = regions["flightradar24"].get(region, 0)
        print(f"{region:<18} {os_c:>8} {al_c:>8} {fr_c:>8}")
    print("-" * 46)
    print(f"{'合计':<18} {len(os_flights):>8} {len(al_flights):>8} {len(fr_flights):>8}")

    print("\n=== ICAO24 重叠 ===")
    for ov in overlap_pairs:
        print(
            f"  {ov['source_a']} ↔ {ov['source_b']}: "
            f"共同 {ov['common']} "
            f"(在A中 {ov['overlap_pct_a']}%, 在B中 {ov['overlap_pct_b']}%)"
        )

    print("\n完成。\n")


if __name__ == "__main__":
    asyncio.run(main())
