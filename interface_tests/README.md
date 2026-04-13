# Interface Tests

This folder contains per-API smoke tests for external map and geo-visualization related services.

## Covered APIs
- OpenSky Network
- AeroDataBox (RapidAPI)
- Aviationstack
- OpenWeatherMap
- Leaflet (library availability check)
- CesiumJS (library availability check)
- AntV L7 (library availability check)

Excluded from automated tests:
- Mapbox (cannot complete registration under current IP constraints)

## Note about frontend map libraries
Leaflet, CesiumJS, and AntV L7 are frontend visualization libraries rather than flight-data APIs.
In this folder, they are validated via npm registry availability checks.
Their rendering behavior should still be verified in frontend integration demos.

## Setup
1. Enter folder:

```powershell
cd interface_tests
```

2. Create virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

3. Prepare keys:

```powershell
copy .env.example .env
```

Fill `.env` with your API keys.

If `.env` already exists in your workspace, edit it directly.

## Run all tests

```powershell
python run_all.py
```

After each run, reports are automatically saved to `interface_tests/results/`:
- `api_test_report_YYYYMMDD_HHMMSS.json`
- `api_test_report_YYYYMMDD_HHMMSS.md`
- `latest.json`
- `latest.md`

## Run single API test

```powershell
python -m clients.test_opensky
python -m clients.test_aerodatabox
python -m clients.test_aviationstack
python -m clients.test_leaflet
python -m clients.test_cesium
python -m clients.test_l7
python -m clients.test_openweather
```

## Output interpretation
- `PASS`: request succeeded and returned expected basic structure.
- `FAIL`: missing key, HTTP error, or response parse issue.

## Course report evidence
- Use `results/latest.md` as the latest test evidence for Word report.
- Keep historical snapshots (`api_test_report_*.md`) as appendix materials.
- Combine with `../docs/API搜索与记录.md` to show: search -> implementation -> test result.

## Notes
- API quotas may cause `429` or partial data.
- Update `AERODATABOX_TEST_PATH` to a valid airport/date range as needed.
