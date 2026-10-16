"""Vendor licensed glyphs for business overlays; no map data is downloaded.

Run once to refresh packaged files. Runtime map rendering uses these local files.
Requires only Python's standard library.
"""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "client/public-app/fonts"
FONT = "Noto Sans Regular"
REPO = "https://api.github.com/repos/maplibre/demotiles"


def get(url: str) -> bytes:
    with urlopen(url, timeout=30) as response:
        return response.read()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    commit = json.loads(get(f"{REPO}/commits/gh-pages"))["sha"]
    files = json.loads(get(f"{REPO}/contents/font/{quote(FONT)}?ref={commit}"))
    # CJK ideographs are generated locally by MapLibre; package punctuation,
    # Latin scripts, international airport labels, arrows and unit symbols.
    ranges = set(range(0, 12544, 256)) | {65280}
    selected = [f for f in files if f["name"].endswith(".pbf")
                and int(f["name"].split("-")[0]) in ranges]
    licenses = [f for f in files if "license" in f["name"].lower()]
    if not licenses:
        raise RuntimeError("Font license missing from upstream package")

    def download(item: dict) -> dict:
        data = get(item["download_url"])
        folder = OUT / FONT
        folder.mkdir(exist_ok=True)
        (folder / item["name"]).write_bytes(data)
        return {"file": f"{FONT}/{item['name']}", "sha256": sha256(data).hexdigest()}

    with ThreadPoolExecutor(max_workers=6) as executor:
        manifest = list(executor.map(download, selected + licenses))
    (OUT / "manifest.json").write_text(json.dumps({
        "source": "https://github.com/maplibre/demotiles", "commit": commit,
        "font": FONT, "files": manifest,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Vendored {len(selected)} glyph ranges and license at commit {commit}")


if __name__ == "__main__":
    main()
