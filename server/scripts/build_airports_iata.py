#!/usr/bin/env python3
"""Download OurAirports CSV and build server/data/airports.iata.json (IATA catalog)."""

from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"
OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "airports.iata.json"
VALID_TYPES = frozenset({"large_airport", "medium_airport", "small_airport"})


def main() -> None:
    print(f"Downloading {OURAIRPORTS_URL} ...")
    with urllib.request.urlopen(OURAIRPORTS_URL, timeout=120) as resp:
        text = resp.read().decode("utf-8")

    rows: list[dict] = []
    for item in csv.DictReader(text.splitlines()):
        iata = (item.get("iata_code") or "").strip().upper()
        if len(iata) != 3:
            continue
        apt_type = (item.get("type") or "").strip()
        if apt_type not in VALID_TYPES:
            continue
        name = (item.get("name") or "").strip()
        city = (item.get("municipality") or "").strip()
        country = (item.get("iso_country") or "").strip().upper()
        try:
            lat = float(item.get("latitude_deg") or 0)
            lon = float(item.get("longitude_deg") or 0)
        except (TypeError, ValueError):
            continue
        if not name:
            continue
        rows.append(
            {
                "iata_code": iata,
                "name": name,
                "city": city,
                "country": country,
                "lat": lat,
                "lon": lon,
                "is_hub": False,
            }
        )

    rows.sort(key=lambda r: r["iata_code"])
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Wrote {len(rows)} airports → {OUT_PATH}")


if __name__ == "__main__":
    main()
