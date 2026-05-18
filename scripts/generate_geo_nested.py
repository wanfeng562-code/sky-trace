"""Generate client/src/data/geoNested.ts — 4-level geo for CN + 3-level for US/JP/DE."""
import json
from pathlib import Path

# CN: province code -> list of (cityCode, cityName, latMin, latMax, lonMin, lonMax, airports, districts?)
# districts: (code, name, latMin, latMax, lonMin, lonMax)

def bbox(lat_min, lat_max, lon_min, lon_max, airports=None):
    d = {
        "latMin": lat_min, "latMax": lat_max, "lonMin": lon_min, "lonMax": lon_max,
    }
    if airports:
        d["airports"] = airports
    return d

CN = {
    "BJ": [
        ("BJ-URBAN", "北京市区", 39.75, 40.05, 116.10, 116.65, ["PEK", "PKX"], [
            ("BJ-CY", "朝阳", 39.85, 40.05, 116.35, 116.65, None),
            ("BJ-HD", "海淀", 39.90, 40.10, 116.10, 116.35, None),
            ("BJ-DC", "东城西城", 39.88, 39.96, 116.35, 116.45, None),
            ("BJ-FT", "丰台大兴", 39.68, 39.88, 116.20, 116.55, None),
        ]),
    ],
    "TJ": [("TJ-CITY", "天津市区", 38.90, 39.25, 116.95, 117.45, ["TSN"], None)],
    "HE": [("SJW-CITY", "石家庄", 37.90, 38.25, 114.30, 114.80, ["SJW"], None)],
    "SX": [("TYN-CITY", "太原", 37.60, 38.10, 112.40, 112.70, ["TYN"], None)],
    "NM": [("HET-CITY", "呼和浩特", 40.70, 41.00, 111.50, 112.00, ["HET"], None)],
    "LN": [
        ("SHE-CITY", "沈阳", 41.60, 42.00, 123.20, 123.60, ["SHE"], None),
        ("DLC-CITY", "大连", 38.80, 39.20, 121.40, 122.00, ["DLC"], None),
    ],
    "JL": [("CGQ-CITY", "长春", 43.70, 44.10, 125.10, 125.50, ["CGQ"], None)],
    "HL": [("HRB-CITY", "哈尔滨", 45.60, 46.00, 126.40, 126.80, ["HRB"], None)],
    "SH": [
        ("PVG-AREA", "浦东", 30.95, 31.35, 121.60, 122.00, ["PVG"], [
            ("SH-PD-CORE", "浦东核心", 31.10, 31.30, 121.70, 121.95, None),
            ("SH-PD-SOUTH", "浦东南部", 30.95, 31.10, 121.60, 121.80, None),
        ]),
        ("SHA-AREA", "虹桥", 31.10, 31.25, 121.30, 121.45, ["SHA"], None),
    ],
    "JS": [
        ("NKG-CITY", "南京", 31.90, 32.15, 118.60, 119.00, ["NKG"], None),
        ("WUX-CITY", "无锡", 31.45, 31.65, 120.20, 120.45, ["WUX"], None),
    ],
    "ZJ": [
        ("HGH-CITY", "杭州", 30.10, 30.40, 119.90, 120.35, ["HGH"], None),
        ("NGB-CITY", "宁波", 29.70, 30.00, 121.40, 121.70, ["NGB"], None),
    ],
    "AH": [("HFE-CITY", "合肥", 31.70, 32.00, 117.10, 117.45, ["HFE"], None)],
    "FJ": [
        ("XMN-CITY", "厦门", 24.40, 24.65, 118.05, 118.25, ["XMN"], None),
        ("FOC-CITY", "福州", 25.90, 26.15, 119.20, 119.45, ["FOC"], None),
    ],
    "JX": [("KHN-CITY", "南昌", 28.50, 28.75, 115.80, 116.00, ["KHN"], None)],
    "SD": [
        ("TNA-CITY", "济南", 36.50, 36.85, 116.90, 117.20, ["TNA"], None),
        ("TAO-CITY", "青岛", 36.00, 36.30, 120.25, 120.50, ["TAO"], None),
    ],
    "HA": [
        ("CGO-CITY", "郑州", 34.60, 34.90, 113.60, 113.90, ["CGO"], None),
        ("LYA-CITY", "洛阳", 34.55, 34.75, 112.35, 112.55, [], None),
    ],
    "HB": [("WUH-CITY", "武汉", 30.45, 30.75, 114.10, 114.50, ["WUH"], None)],
    "HN": [("CSX-CITY", "长沙", 28.05, 28.35, 112.85, 113.15, ["CSX"], None)],
    "GD": [
        ("CAN-AREA", "广州", 22.95, 23.45, 113.15, 113.55, ["CAN"], [
            ("GZ-TH", "天河越秀", 23.10, 23.20, 113.25, 113.40, None),
            ("GZ-BY", "白云", 23.30, 23.45, 113.25, 113.40, None),
            ("GZ-NS", "南沙番禺", 22.95, 23.10, 113.30, 113.55, None),
        ]),
        ("SZX-AREA", "深圳", 22.45, 22.75, 113.85, 114.25, ["SZX"], [
            ("SZ-FT", "福田罗湖", 22.50, 22.58, 114.00, 114.15, None),
            ("SZ-NS", "南山", 22.48, 22.55, 113.85, 114.00, None),
            ("SZ-BA", "宝安", 22.60, 22.75, 113.85, 114.05, None),
        ]),
        ("ZUH-CITY", "珠海", 22.00, 22.40, 113.45, 113.65, ["ZUH"], None),
    ],
    "GX": [("NNG-CITY", "南宁", 22.70, 22.90, 108.25, 108.45, ["NNG"], None)],
    "HI": [
        ("HAK-CITY", "海口", 19.90, 20.10, 110.25, 110.45, ["HAK"], None),
        ("SYX-CITY", "三亚", 18.20, 18.40, 109.35, 109.55, ["SYX"], None),
    ],
    "CQ": [("CKG-CITY", "重庆", 29.40, 29.75, 106.40, 106.65, ["CKG"], None)],
    "SC": [
        ("CTU-AREA", "成都", 30.45, 30.80, 103.90, 104.20, ["CTU", "TFU"], None),
    ],
    "GZ": [("KWE-CITY", "贵阳", 26.50, 26.65, 106.60, 106.80, ["KWE"], None)],
    "YN": [
        ("KMG-CITY", "昆明", 24.90, 25.10, 102.70, 102.95, ["KMG"], None),
    ],
    "XZ": [("LXA-CITY", "拉萨", 29.60, 29.70, 90.95, 91.15, ["LXA"], None)],
    "SN": [("XIY-CITY", "西安", 34.30, 34.50, 108.70, 109.00, ["XIY"], None)],
    "GS": [("LHW-CITY", "兰州", 36.00, 36.10, 103.55, 103.75, ["LHW"], None)],
    "QH": [("XNN-CITY", "西宁", 36.50, 36.65, 101.70, 101.85, ["XNN"], None)],
    "NX": [("INC-CITY", "银川", 38.40, 38.55, 106.35, 106.50, ["INC"], None)],
    "XJ": [("URC-CITY", "乌鲁木齐", 43.80, 44.00, 87.40, 87.65, ["URC"], None)],
}

US = {
    "CA": [
        ("CA-LA", "洛杉矶", 33.70, 34.35, -118.65, -117.90, ["LAX"], None),
        ("CA-SF", "旧金山湾区", 37.45, 37.85, -122.55, -121.90, ["SFO", "SJC", "OAK"], None),
        ("CA-SD", "圣迭戈", 32.60, 33.10, -117.30, -116.90, ["SAN"], None),
    ],
    "NY": [
        ("NY-NYC", "纽约都会", 40.55, 40.90, -74.25, -73.70, ["JFK", "LGA", "EWR"], [
            ("NY-MAN", "曼哈顿", 40.70, 40.82, -74.02, -73.90, None),
            ("NY-QUE", "皇后区", 40.65, 40.78, -73.95, -73.75, None),
            ("NY-BRK", "布鲁克林", 40.58, 40.70, -74.05, -73.90, None),
        ]),
    ],
    "TX": [
        ("TX-DFW", "达拉斯沃斯堡", 32.60, 33.10, -97.20, -96.50, ["DFW", "DAL"], None),
        ("TX-HOU", "休斯顿", 29.60, 30.05, -95.65, -95.10, ["IAH", "HOU"], None),
    ],
    "FL": [
        ("FL-MIA", "迈阿密", 25.70, 26.00, -80.35, -80.10, ["MIA", "FLL"], None),
        ("FL-ORL", "奥兰多", 28.35, 28.60, -81.50, -81.20, ["MCO"], None),
    ],
}

JP = {
    "JP-KNT": [
        ("TYO-AREA", "东京", 35.55, 35.85, 139.55, 139.90, ["HND", "NRT"], [
            ("TYO-C23", "都心", 35.65, 35.72, 139.68, 139.78, None),
            ("TYO-C24", "湾岸", 35.60, 35.68, 139.75, 139.90, None),
        ]),
    ],
    "JP-KNS": [("OSA-CITY", "大阪", 34.60, 34.75, 135.40, 135.60, ["KIX", "ITM"], None)],
}

DE = {
    "DE-BY": [
        ("DE-MUC", "慕尼黑", 48.10, 48.25, 11.45, 11.70, ["MUC"], None),
    ],
    "DE-BE": [("DE-BER", "柏林", 52.45, 52.58, 13.30, 13.55, ["BER"], None)],
}


def fmt_city(c):
    code, name, la, lb, lo, hi, airports, districts = c
    ap = f', airports: {json.dumps(airports)}' if airports else ""
    dist_block = ""
    if districts:
        items = []
        for d in districts:
            dc, dn, dla, dlb, dlo, dhi, dap = d
            dap_s = f", airports: {json.dumps(dap)}" if dap else ""
            items.append(
                f'{{ code: "{dc}", nameZh: "{dn}", latMin: {dla}, latMax: {dlb}, lonMin: {dlo}, lonMax: {dhi}{dap_s} }}'
            )
        dist_block = f", districts: [{', '.join(items)}]"
    return f'{{ code: "{code}", nameZh: "{name}", latMin: {la}, latMax: {lb}, lonMin: {lo}, lonMax: {hi}{ap}{dist_block} }}'


def fmt_country(data):
    parts = []
    for region, cities in data.items():
        city_str = ",\n      ".join(fmt_city(c) for c in cities)
        parts.append(f'  "{region}": [\n      {city_str},\n    ]')
    return "{\n" + ",\n".join(parts) + "\n}"


out = f'''/** Auto-generated by scripts/generate_geo_nested.py — do not edit by hand. */
import type {{ GeoCity, GeoDistrict }} from "./geoHierarchy";

export type NestedGeoMap = Record<string, Record<string, GeoCity[]>>;

export const NESTED_GEO_CN: NestedGeoMap = {fmt_country(CN)};

export const NESTED_GEO_US: NestedGeoMap = {fmt_country(US)};

export const NESTED_GEO_JP: NestedGeoMap = {fmt_country(JP)};

export const NESTED_GEO_DE: NestedGeoMap = {fmt_country(DE)};
'''

Path("client/src/data/geoNested.ts").write_text(out, encoding="utf-8")
print("wrote geoNested.ts", len(out))
