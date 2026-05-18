"""从 Natural Earth admin1 按 iso_a2 拆分各国矢量边界（供前端 regionBoundaries 使用）。"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NE_PATH = ROOT / "client/public/geo/ne_admin1.json"
OUT_DIR = ROOT / "client/public/geo"


def main() -> None:
    data = json.loads(NE_PATH.read_text(encoding="utf-8"))
    by_cc: dict[str, list[dict]] = defaultdict(list)
    for f in data["features"]:
        p = f.get("properties") or {}
        cc = p.get("iso_a2")
        if not isinstance(cc, str) or len(cc) != 2:
            continue
        cc = cc.upper()
        if cc in ("-99", "99"):
            continue
        by_cc[cc].append(f)

    for cc, feats in sorted(by_cc.items()):
        fc = {"type": "FeatureCollection", "features": feats}
        out = OUT_DIR / f"{cc.lower()}-admin1.json"
        out.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {out.name}: {len(feats)} features")


if __name__ == "__main__":
    main()
