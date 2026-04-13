from __future__ import annotations

import httpx

from config import Settings, load_settings
from clients.common import ApiTestResult


def run_test(settings: Settings) -> ApiTestResult:
    url = "https://opensky-network.org/api/states/all"
    params: dict[str, float] = {}

    if settings.opensky_bbox:
        try:
            lamin, lamax, lomin, lomax = [float(v.strip()) for v in settings.opensky_bbox.split(",")]
            params = {"lamin": lamin, "lamax": lamax, "lomin": lomin, "lomax": lomax}
        except ValueError:
            return ApiTestResult(
                name="OpenSky",
                ok=False,
                status_code=None,
                message="OPENSKY_BBOX 解析失败，格式应为: lat_min,lat_max,lon_min,lon_max",
            )

    auth = None
    if settings.opensky_username and settings.opensky_password:
        auth = (settings.opensky_username, settings.opensky_password)

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, params=params or None, auth=auth)
        payload = resp.json()
        states = payload.get("states") or []
        preview = {
            "time": payload.get("time"),
            "state_count": len(states),
            "sample_state": states[0] if states else None,
        }
        return ApiTestResult(
            name="OpenSky",
            ok=resp.status_code == 200,
            status_code=resp.status_code,
            message="请求完成",
            preview=preview,
        )
    except Exception as exc:
        return ApiTestResult(
            name="OpenSky",
            ok=False,
            status_code=None,
            message=f"请求异常: {exc}",
        )


if __name__ == "__main__":
    result = run_test(load_settings())
    print(result)
