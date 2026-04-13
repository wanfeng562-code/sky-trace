# API Interface Test Report (20260413_052927)

## Run Metadata

- started_at_utc: 2026-04-13T05:29:27.908770+00:00
- ended_at_utc: 2026-04-13T05:29:41.460737+00:00
- duration_seconds: 13.552
- python: 3.12.4
- platform: Windows-11-10.0.22631-SP0
- source_doc: ../docs/API搜索与记录.md
- test_code_dir: ./clients

## Summary

- total: 7
- passed: 7
- failed: 0

| API | Result | HTTP Status | Duration(ms) | Message |
|---|---|---:|---:|---|
| OpenSky | PASS | 200 | 2203.7 | 请求完成 |
| AeroDataBox | PASS | 200 | 2857.8 | 请求完成 |
| Aviationstack | PASS | 200 | 1752.7 | 请求完成 |
| Leaflet (library check) | PASS | 200 | 1897.1 | 请求完成 |
| CesiumJS (library check) | PASS | 200 | 1728.5 | 请求完成 |
| AntV L7 (library check) | PASS | 200 | 1872.9 | 请求完成 |
| OpenWeatherMap | PASS | 200 | 1232.3 | 请求完成 |

## Details

### OpenSky
- result: PASS
- status_code: 200
- duration_ms: 2203.6900999955833
- message: 请求完成
- preview:
```json
{
  "time": 1776058169,
  "state_count": 103,
  "sample_state": [
    "801622",
    "IGO1721 ",
    "India",
    1776057950,
    1776057958,
    113.5424,
    22.0151,
    5791.2,
    false,
    159.28,
    162.33,
    -0.33,
    null,
    6134.1,
    null,
    false,
    0
  ]
}
```

### AeroDataBox
- result: PASS
- status_code: 200
- duration_ms: 2857.8293998725712
- message: 请求完成
- preview:
```json
{
  "keys": [
    "departures",
    "arrivals"
  ],
  "arrivals_count": 498,
  "departures_count": 704
}
```

### Aviationstack
- result: PASS
- status_code: 200
- duration_ms: 1752.6891001034528
- message: 请求完成
- preview:
```json
{
  "pagination": {
    "limit": 5,
    "offset": 0,
    "count": 5,
    "total": 372146
  },
  "item_count": 5,
  "sample": {
    "flight_date": "2026-04-13",
    "flight_status": "scheduled",
    "departure": {
      "airport": "Montgomery Co",
      "timezone": "America/Chicago",
      "iata": "CXO",
      "icao": "KCXO",
      "terminal": null,
      "gate": null,
      "delay": null,
      "scheduled": "2026-04-13T06:15:00+00:00",
      "estimated": "2026-04-13T06:15:00+00:00",
      "actual": null,
      "estimated_runway": null,
      "actual_runway": null
    },
    "arrival": {
      "airport": "Easterwood Field",
      "timezone": "America/Chicago",
      "iata": "CLL",
      "icao": "KCLL",
      "terminal": null,
      "gate": null,
      "baggage": null,
      "scheduled": "2026-04-13T06:40:00+00:00",
      "delay": null,
      "estimated": null,
      "actual": null,
      "estimated_runway": null,
      "actual_runway": null
    },
    "airline": {
      "name": "Japan Airlines",
      "iata": "JL",
      "icao": "JTL"
    },
    "flight": {
      "number": "939",
      "iata": "JL939",
      "icao": "JTL939",
      "codeshared": null
    },
    "aircraft": null,
    "live": null
  }
}
```

### Leaflet (library check)
- result: PASS
- status_code: 200
- duration_ms: 1897.0973999239504
- message: 请求完成
- preview:
```json
{
  "package": "leaflet",
  "latest": "1.9.4",
  "description": "JavaScript library for mobile-friendly interactive maps"
}
```

### CesiumJS (library check)
- result: PASS
- status_code: 200
- duration_ms: 1728.5231999121606
- message: 请求完成
- preview:
```json
{
  "package": "cesium",
  "latest": "1.140.0",
  "description": "CesiumJS is a JavaScript library for creating 3D globes and 2D maps in a web browser without a plugin."
}
```

### AntV L7 (library check)
- result: PASS
- status_code: 200
- duration_ms: 1872.945399954915
- message: 请求完成
- preview:
```json
{
  "package": "@antv/l7",
  "latest": "2.25.4",
  "description": "A Large-scale WebGL-powered Geospatial Data Visualization"
}
```

### OpenWeatherMap
- result: PASS
- status_code: 200
- duration_ms: 1232.2992000263184
- message: 请求完成
- preview:
```json
{
  "city": "Guangzhou",
  "weather": "Clear",
  "temperature_c": 30.74,
  "wind": {
    "speed": 4.44,
    "deg": 180,
    "gust": 5.88
  }
}
```

## Course Report Usage

- 将本文件中的 Summary 表格粘贴到课程报告“接口测试结果”章节。
- 将 Details 中关键样例作为“接口返回样本证据”。
- 与 docs/API搜索与记录.md 共同构成“搜索 -> 实现 -> 验证”闭环。
