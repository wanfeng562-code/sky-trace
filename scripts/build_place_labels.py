"""Build local point labels from official GeoNames downloads (no boundaries).

python scripts/build_place_labels.py --input-dir out/map-validation-20261012
Input files: geonames-cities500.zip, geonames-alternateNamesV2.zip,
geonames-countryInfo.txt and geonames-readme.txt. Runtime needs no GeoNames API.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
# Explicit display list: source country/territory codes are never treated as
# an automatic list of independent countries. TW/HK/MO are regions of CN.
COUNTRY_CODES = set("AD AE AF AG AL AM AO AR AT AU AZ BA BB BD BE BF BG BH BI BJ BN BO BR BS BT BW BY BZ CA CD CF CG CH CI CL CM CN CO CR CU CV CY CZ DE DJ DK DM DO DZ EC EE EG ER ES ET FI FJ FM FR GA GB GD GE GH GM GN GQ GR GT GW GY HN HR HT HU ID IE IL IN IQ IR IS IT JM JO JP KE KG KH KI KM KN KP KR KW KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MG MH MK ML MM MN MR MT MU MV MW MX MY MZ NA NE NG NI NL NO NP NR NZ OM PA PE PG PH PK PL PT PW PY QA RO RS RU RW SA SB SC SD SE SG SI SK SL SM SN SO SR SS ST SV SY SZ TD TG TH TJ TL TM TN TO TR TT TV TZ UA UG US UY UZ VA VC VE VN VU WS YE ZA ZM ZW PS".split())
REGIONS = {"TW": "Taiwan Province, China", "HK": "Hong Kong SAR, China", "MO": "Macao SAR, China"}
ANCHORS = {"CN": [104.2, 35.8], "US": [-99, 39], "CA": [-105, 59], "RU": [100, 62], "AU": [134, -25], "BR": [-53, -10], "TW": [121, 23.7], "HK": [114.2, 22.35], "MO": [113.55, 22.16]}
NAMES = {"CN": "China", "GB": "United Kingdom", "US": "United States", "RU": "Russia", "KR": "South Korea", "KP": "North Korea", "CZ": "Czechia", "SZ": "Eswatini", "MK": "North Macedonia", "PS": "Palestine", "VA": "Vatican City"}


def latin_name(value):
    return bool(value.strip()) and all(not c.isalpha() or "LATIN" in unicodedata.name(c, "") for c in value)


def minimum_zoom(code, population):
    if code == "PPLC":
        return 3.5
    thresholds = [(5000000, 3.5), (1000000, 4), (500000, 4.5), (100000, 5.5), (50000, 6), (10000, 7), (2000, 8), (500, 9)]
    zoom = next((z for p, z in thresholds if population >= p), 10)
    zoom = min(zoom, {"PPLA": 5, "PPLA2": 6.5, "PPLA3": 8, "PPLA4": 9}.get(code, 10))
    if code == "PPLX":
        zoom = max(zoom, 11)
    if code in {"PPLQ", "PPLH", "PPLF"}:
        zoom = max(zoom, 13)
    return zoom


def encode(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    args = parser.parse_args()
    files = {n: args.input_dir / ("geonames-" + n) for n in ["cities500.zip", "alternateNamesV2.zip", "countryInfo.txt", "readme.txt"]}
    input_hashes = {n: hashlib.sha256(p.read_bytes()).hexdigest() for n, p in files.items()}
    with zipfile.ZipFile(files["cities500.zip"]) as z:
        raw = [line.split("\t") for line in z.read("cities500.txt").decode("utf-8").splitlines() if line]
    ids = {r[0] for r in raw}
    if len(ids) != len(raw):
        raise ValueError("Duplicate GeoNames ids in input")
    english = {}
    with zipfile.ZipFile(files["alternateNamesV2.zip"]) as z:
        with io.TextIOWrapper(z.open("alternateNamesV2.txt"), encoding="utf-8") as stream:
            for line in stream:
                r = line.rstrip("\n").split("\t")
                if len(r) < 8 or r[1] not in ids or r[2].split("-")[0] != "en":
                    continue
                if r[6] == "1" or r[7] == "1" or (len(r) > 9 and r[9]) or not latin_name(r[3]):
                    continue
                score = (r[4] == "1", r[5] == "1", r[2] == "en", -int(r[0]))
                if r[1] not in english or score > english[r[1]][0]:
                    english[r[1]] = (score, r[3].strip())
    cells = defaultdict(list)
    counts, name_counts, feature_counts = Counter(), Counter(), Counter()
    positions = defaultdict(list)
    overview = []
    for r in raw:
        lng, lat = float(r[5]), float(r[4])
        if not (-180 <= lng <= 180 and -90 <= lat <= 90):
            raise ValueError(f"Invalid coordinates: {r[0]}")
        name = english[r[0]][1] if r[0] in english else r[2].strip()
        source = "en" if r[0] in english else "latin"
        if not name or not latin_name(name):
            raise ValueError(f"Missing display name: {r[0]}")
        country = "CN" if r[8] in REGIONS else r[8]
        region = r[8] if r[8] in REGIONS else r[10]
        population = int(r[14] or 0)
        row = [int(r[0]), name, lng, lat, population, minimum_zoom(r[7], population), country, region, source, r[7]]
        col = min(17, int((lng + 180) // 20))
        grid_row = min(8, int((lat + 90) // 20))
        cells[f"{col}-{grid_row}"].append(row)
        if row[5] < 6:
            overview.append(row)
        counts[country] += 1
        name_counts[source] += 1
        feature_counts[r[7]] += 1
        positions[country].append([lng, lat])
    metadata = {}
    for line in files["countryInfo.txt"].read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            row = line.split("\t")
            metadata[row[0]] = row[4]
    countries = []
    for code in sorted(COUNTRY_CODES):
        if code not in metadata:
            raise ValueError(f"Country metadata missing: {code}")
        points = positions[code]
        if code in ANCHORS:
            anchor = ANCHORS[code]
        elif points:
            # Circular longitude mean avoids placing date-line countries in
            # the Atlantic. These are text anchors, never boundary geometry.
            lng = math.degrees(math.atan2(sum(math.sin(math.radians(p[0])) for p in points), sum(math.cos(math.radians(p[0])) for p in points)))
            anchor = [round(lng, 4), round(sum(p[1] for p in points) / len(points), 4)]
        else:
            raise ValueError(f"Country text anchor missing: {code}")
        countries.append([code, NAMES.get(code, metadata[code]), *anchor, "country", 1, 6])
    for code, name in REGIONS.items():
        countries.append([f"CN-{code}", name, *ANCHORS[code], "region", 3 if code == "TW" else 5, 9])
    out = ROOT / "client/public-app/place-labels"
    out.mkdir(parents=True, exist_ok=True)
    cell_dir = out / "cells"
    cell_dir.mkdir(exist_ok=True)
    published = {}

    def publish(stem, value, folder=out):
        data = encode(value)
        digest = hashlib.sha256(data).hexdigest()
        filename = f"{stem}.{digest[:12]}.json"
        (folder / filename).write_bytes(data)
        return {"file": ("cells/" if folder == cell_dir else "") + filename, "sha256": digest}

    for key, rows in sorted(cells.items()):
        rows.sort(key=lambda r: (r[5], -r[4], r[0]))
        published[key] = {**publish(key, rows, cell_dir), "count": len(rows)}
    overview.sort(key=lambda r: (r[5], -r[4], r[0]))
    manifest = {"schemaVersion": 1, "generatedAt": datetime.now(timezone.utc).isoformat(), "cellSize": 20,
                "source": "https://www.geonames.org/", "license": "CC-BY-4.0", "inputHashes": input_hashes,
                "recordCount": len(raw), "countryLabelCount": len(COUNTRY_CODES), "regionLabelCount": len(REGIONS),
                "nameCounts": dict(name_counts), "countryCounts": dict(sorted(counts.items())), "featureCounts": dict(feature_counts),
                "overview": publish("overview", {"countries": countries, "cities": overview}), "cells": published}
    if sum(v["count"] for v in published.values()) != len(raw):
        raise ValueError("Coverage mismatch")
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "LICENSE.txt").write_text("GeoNames point labels, adapted by Sky-Trace.\nSource: https://www.geonames.org/\nLicense: Creative Commons Attribution 4.0 International\nhttps://creativecommons.org/licenses/by/4.0/\n\nChanges: select current English aliases, retain Latin-name fallbacks, split by spatial cells, normalize TW/HK/MO as regions of CN, add display zoom levels and country text anchors. No source boundary geometry is included.\nNo guarantee of accuracy, timeliness or completeness. This is not an official Tianditu translation.\n", encoding="utf-8")
    (out / "SOURCE_README.txt").write_bytes(files["readme.txt"].read_bytes())
    (ROOT / "client/src/data/placeLabelManifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(raw), "cells": len(cells), "countries": len(COUNTRY_CODES), "names": dict(name_counts)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
