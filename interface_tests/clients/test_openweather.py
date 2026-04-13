from __future__ import annotations

import httpx

from config import Settings, load_settings
from clients.common import ApiTestResult


def run_test(settings: Settings) -> ApiTestResult:
    if not settings.openweather_api_key:
        return ApiTestResult(
            name="OpenWeatherMap",
            ok=False,
            status_code=None,
            message="缺少 OPENWEATHER_API_KEY",
        )

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": settings.openweather_city,
        "appid": settings.openweather_api_key,
        "units": "metric",
    }

    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(url, params=params)
        payload = resp.json()
        weather = payload.get("weather", []) if isinstance(payload, dict) else []
        main = payload.get("main", {}) if isinstance(payload, dict) else {}
        preview = {
            "city": payload.get("name") if isinstance(payload, dict) else None,
            "weather": weather[0].get("main") if weather else None,
            "temperature_c": main.get("temp"),
            "wind": payload.get("wind") if isinstance(payload, dict) else None,
        }
        return ApiTestResult(
            name="OpenWeatherMap",
            ok=resp.status_code == 200,
            status_code=resp.status_code,
            message="请求完成",
            preview=preview,
        )
    except Exception as exc:
        return ApiTestResult(
            name="OpenWeatherMap",
            ok=False,
            status_code=None,
            message=f"请求异常: {exc}",
        )


if __name__ == "__main__":
    result = run_test(load_settings())
    print(result)
