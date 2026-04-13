from __future__ import annotations

import json
import platform
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from config import load_settings
from clients.common import ApiTestResult, format_preview
from clients.test_aerodatabox import run_test as run_aerodatabox
from clients.test_aviationstack import run_test as run_aviationstack
from clients.test_cesium import run_test as run_cesium
from clients.test_l7 import run_test as run_l7
from clients.test_leaflet import run_test as run_leaflet
from clients.test_openweather import run_test as run_openweather
from clients.test_opensky import run_test as run_opensky


BASE_DIR = Path(__file__).resolve().parent
RESULT_DIR = BASE_DIR / "results"


def _ensure_result_dir() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)


def _to_markdown(
    *,
    run_id: str,
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    results: list[ApiTestResult],
) -> str:
    failed = sum(1 for item in results if not item.ok)
    passed = len(results) - failed

    lines: list[str] = []
    lines.append(f"# API Interface Test Report ({run_id})")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append(f"- started_at_utc: {started_at}")
    lines.append(f"- ended_at_utc: {ended_at}")
    lines.append(f"- duration_seconds: {duration_seconds:.3f}")
    lines.append(f"- python: {sys.version.split()[0]}")
    lines.append(f"- platform: {platform.platform()}")
    lines.append("- source_doc: ../docs/API搜索与记录.md")
    lines.append("- test_code_dir: ./clients")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- total: {len(results)}")
    lines.append(f"- passed: {passed}")
    lines.append(f"- failed: {failed}")
    lines.append("")
    lines.append("| API | Result | HTTP Status | Duration(ms) | Message |")
    lines.append("|---|---|---:|---:|---|")
    for item in results:
        flag = "PASS" if item.ok else "FAIL"
        status = item.status_code if item.status_code is not None else "-"
        duration = f"{item.duration_ms:.1f}" if item.duration_ms is not None else "-"
        lines.append(f"| {item.name} | {flag} | {status} | {duration} | {item.message} |")

    lines.append("")
    lines.append("## Details")
    for item in results:
        lines.append("")
        lines.append(f"### {item.name}")
        lines.append(f"- result: {'PASS' if item.ok else 'FAIL'}")
        lines.append(f"- status_code: {item.status_code}")
        lines.append(f"- duration_ms: {item.duration_ms}")
        lines.append(f"- message: {item.message}")
        if item.preview is not None:
            lines.append("- preview:")
            lines.append("```json")
            lines.append(format_preview(item.preview))
            lines.append("```")

    lines.append("")
    lines.append("## Course Report Usage")
    lines.append("")
    lines.append("- 将本文件中的 Summary 表格粘贴到课程报告“接口测试结果”章节。")
    lines.append("- 将 Details 中关键样例作为“接口返回样本证据”。")
    lines.append("- 与 docs/API搜索与记录.md 共同构成“搜索 -> 实现 -> 验证”闭环。")
    lines.append("")

    return "\n".join(lines)


def _save_reports(
    *,
    run_id: str,
    started_at: str,
    ended_at: str,
    duration_seconds: float,
    results: list[ApiTestResult],
) -> tuple[Path, Path, Path, Path]:
    _ensure_result_dir()

    json_path = RESULT_DIR / f"api_test_report_{run_id}.json"
    md_path = RESULT_DIR / f"api_test_report_{run_id}.md"
    latest_json_path = RESULT_DIR / "latest.json"
    latest_md_path = RESULT_DIR / "latest.md"

    payload = {
        "run_id": run_id,
        "started_at_utc": started_at,
        "ended_at_utc": ended_at,
        "duration_seconds": duration_seconds,
        "python": sys.version,
        "platform": platform.platform(),
        "source_doc": "../docs/API搜索与记录.md",
        "results": [asdict(item) for item in results],
        "summary": {
            "total": len(results),
            "failed": sum(1 for item in results if not item.ok),
            "passed": sum(1 for item in results if item.ok),
        },
    }

    markdown = _to_markdown(
        run_id=run_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        results=results,
    )

    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")

    latest_json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_md_path.write_text(markdown, encoding="utf-8")

    return json_path, md_path, latest_json_path, latest_md_path


def _print_result(result: ApiTestResult) -> None:
    flag = "PASS" if result.ok else "FAIL"
    duration = f" | duration={result.duration_ms:.1f}ms" if result.duration_ms is not None else ""
    print(f"[{flag}] {result.name} | status={result.status_code} | {result.message}{duration}")
    if result.preview is not None:
        print(format_preview(result.preview))
        print("-" * 80)


def main() -> int:
    settings = load_settings()
    tests: list[tuple[str, str, Callable[..., ApiTestResult]]] = [
        ("OpenSky", "flight_data_api", run_opensky),
        ("AeroDataBox", "flight_data_api", run_aerodatabox),
        ("Aviationstack", "flight_data_api", run_aviationstack),
        ("Leaflet", "frontend_map_library", run_leaflet),
        ("CesiumJS", "frontend_map_library", run_cesium),
        ("AntV L7", "frontend_map_library", run_l7),
        ("OpenWeatherMap", "weather_api", run_openweather),
    ]

    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    results: list[ApiTestResult] = []

    for _name, category, test in tests:
        t_case = time.perf_counter()
        result = test(settings)
        result.duration_ms = (time.perf_counter() - t_case) * 1000
        result.category = category
        _print_result(result)
        results.append(result)

    ended = datetime.now(timezone.utc)
    total_duration = time.perf_counter() - t0
    failed = sum(1 for item in results if not item.ok)

    run_id = started.strftime("%Y%m%d_%H%M%S")
    json_path, md_path, latest_json_path, latest_md_path = _save_reports(
        run_id=run_id,
        started_at=started.isoformat(),
        ended_at=ended.isoformat(),
        duration_seconds=total_duration,
        results=results,
    )

    print(f"Summary: total={len(results)} failed={failed} passed={len(results) - failed}")
    print(f"Saved JSON report: {json_path}")
    print(f"Saved Markdown report: {md_path}")
    print(f"Updated latest JSON: {latest_json_path}")
    print(f"Updated latest Markdown: {latest_md_path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
