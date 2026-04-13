from __future__ import annotations

import httpx

from clients.common import ApiTestResult


def run_test(_settings: object | None = None) -> ApiTestResult:
    # CesiumJS is a JS library, so we check registry availability and latest version.
    url = "https://registry.npmjs.org/cesium"
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url)
        payload = resp.json()
        preview = {
            "package": payload.get("name"),
            "latest": (payload.get("dist-tags") or {}).get("latest"),
            "description": payload.get("description"),
        }
        return ApiTestResult(
            name="CesiumJS (library check)",
            ok=resp.status_code == 200,
            status_code=resp.status_code,
            message="请求完成",
            preview=preview,
        )
    except Exception as exc:
        return ApiTestResult(
            name="CesiumJS (library check)",
            ok=False,
            status_code=None,
            message=f"请求异常: {exc}",
        )


if __name__ == "__main__":
    print(run_test())
