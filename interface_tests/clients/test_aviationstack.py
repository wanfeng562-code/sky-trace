from __future__ import annotations

import httpx

from config import Settings, load_settings
from clients.common import ApiTestResult


def run_test(settings: Settings) -> ApiTestResult:
    if not settings.aviationstack_access_key:
        return ApiTestResult(
            name="Aviationstack",
            ok=False,
            status_code=None,
            message="缺少 AVIATIONSTACK_ACCESS_KEY",
        )

    url = f"{settings.aviationstack_base_url.rstrip('/')}/flights"
    params = {"access_key": settings.aviationstack_access_key, "limit": 5}

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, params=params)
        payload = resp.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        preview = {
            "pagination": payload.get("pagination") if isinstance(payload, dict) else None,
            "item_count": len(data) if isinstance(data, list) else None,
            "sample": data[0] if isinstance(data, list) and data else None,
        }
        return ApiTestResult(
            name="Aviationstack",
            ok=resp.status_code == 200,
            status_code=resp.status_code,
            message="请求完成",
            preview=preview,
        )
    except Exception as exc:
        return ApiTestResult(
            name="Aviationstack",
            ok=False,
            status_code=None,
            message=f"请求异常: {exc}",
        )


if __name__ == "__main__":
    result = run_test(load_settings())
    print(result)
