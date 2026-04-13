from __future__ import annotations

import httpx

from config import Settings, load_settings
from clients.common import ApiTestResult


def run_test(settings: Settings) -> ApiTestResult:
    if not settings.aerodatabox_api_key:
        return ApiTestResult(
            name="AeroDataBox",
            ok=False,
            status_code=None,
            message="缺少 AERODATABOX_API_KEY",
        )

    path = settings.aerodatabox_test_path.lstrip("/")
    url = f"{settings.aerodatabox_base_url.rstrip('/')}/{path}"

    headers = {
        "x-rapidapi-key": settings.aerodatabox_api_key,
        "x-rapidapi-host": settings.aerodatabox_api_host,
    }
    params = {"withLeg": str(settings.aerodatabox_with_leg).lower()}

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, headers=headers, params=params)
        payload = resp.json()
        preview = {
            "keys": list(payload.keys()) if isinstance(payload, dict) else None,
            "arrivals_count": len(payload.get("arrivals", [])) if isinstance(payload, dict) else None,
            "departures_count": len(payload.get("departures", [])) if isinstance(payload, dict) else None,
        }
        return ApiTestResult(
            name="AeroDataBox",
            ok=resp.status_code == 200,
            status_code=resp.status_code,
            message="请求完成",
            preview=preview,
        )
    except Exception as exc:
        return ApiTestResult(
            name="AeroDataBox",
            ok=False,
            status_code=None,
            message=f"请求异常: {exc}",
        )


if __name__ == "__main__":
    result = run_test(load_settings())
    print(result)
