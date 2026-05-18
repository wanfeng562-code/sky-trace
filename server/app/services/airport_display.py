"""Airport display names for API responses (Simplified Chinese)."""

from __future__ import annotations

# 枢纽 / 常见机场专名
HUB_NAME_ZH: dict[str, str] = {
    "PEK": "北京首都",
    "PKX": "北京大兴",
    "PVG": "上海浦东",
    "SHA": "上海虹桥",
    "CAN": "广州白云",
    "SZX": "深圳宝安",
    "CTU": "成都双流",
    "TFU": "成都天府",
    "HKG": "香港",
    "TPE": "台北桃园",
    "NRT": "东京成田",
    "HND": "东京羽田",
    "ICN": "首尔仁川",
    "GMP": "首尔金浦",
    "SIN": "新加坡樟宜",
    "BKK": "曼谷素万那普",
    "DMK": "曼谷廊曼",
    "DXB": "迪拜",
    "LHR": "伦敦希思罗",
    "CDG": "巴黎戴高乐",
    "FRA": "法兰克福",
    "AMS": "阿姆斯特丹",
    "LAX": "洛杉矶",
    "JFK": "纽约肯尼迪",
    "EWR": "纽约纽瓦克",
    "ORD": "芝加哥奥黑尔",
    "ATL": "亚特兰大",
    "DFW": "达拉斯沃斯堡",
    "DEN": "丹佛",
    "SFO": "旧金山",
    "SEA": "西雅图",
    "MIA": "迈阿密",
    "MCO": "奥兰多",
    "FLL": "劳德代尔堡",
    "TPA": "坦帕",
    "IAH": "休斯顿布什",
    "HOU": "休斯顿霍比",
    "PHX": "凤凰城",
    "LAS": "拉斯维加斯",
    "SAN": "圣迭戈",
    "BOS": "波士顿",
    "PHL": "费城",
    "DCA": "华盛顿里根",
    "IAD": "华盛顿杜勒斯",
    "MSP": "明尼阿波利斯",
    "DTW": "底特律",
    "CLT": "夏洛特",
    "SLC": "盐湖城",
    "PDX": "波特兰",
    "YVR": "温哥华",
    "YYZ": "多伦多皮尔逊",
    "SYD": "悉尼金斯福德·史密斯",
    "MEL": "墨尔本",
    "BNE": "布里斯班",
    "BOG": "波哥大埃尔多拉多",
    "LED": "圣彼得堡普尔科沃",
    "AYT": "安塔利亚",
}

CITY_ZH: dict[str, str] = {
    "Houston": "休斯顿",
    "Orlando": "奥兰多",
    "Miami": "迈阿密",
    "Atlanta": "亚特兰大",
    "Chicago": "芝加哥",
    "Dallas": "达拉斯",
    "Denver": "丹佛",
    "Los Angeles": "洛杉矶",
    "New York": "纽约",
    "London": "伦敦",
    "Paris": "巴黎",
    "Frankfurt": "法兰克福",
    "Amsterdam": "阿姆斯特丹",
    "Beijing": "北京",
    "Shanghai": "上海",
    "Guangzhou": "广州",
    "Shenzhen": "深圳",
    "Chengdu": "成都",
    "Hong Kong": "香港",
    "Tokyo": "东京",
    "Seoul": "首尔",
    "Singapore": "新加坡",
    "Bangkok": "曼谷",
    "Dubai": "迪拜",
    "Sydney": "悉尼",
    "Melbourne": "墨尔本",
    "Saint Petersburg": "圣彼得堡",
    "St. Petersburg": "圣彼得堡",
    "Antalya": "安塔利亚",
    "Bogota": "波哥大",
    "Las Vegas": "拉斯维加斯",
    "Phoenix": "凤凰城",
    "Boston": "波士顿",
    "Seattle": "西雅图",
    "San Francisco": "旧金山",
    "Washington": "华盛顿",
    "Toronto": "多伦多",
    "Vancouver": "温哥华",
}


def airport_name_zh(
    iata: str | None,
    *,
    name: str = "",
    city: str = "",
    country: str = "",
) -> str:
    if not iata or not str(iata).strip():
        return ""
    code = str(iata).strip().upper()
    if code in HUB_NAME_ZH:
        return HUB_NAME_ZH[code]
    city_zh = CITY_ZH.get(city.strip(), "") if city else ""
    if city_zh:
        return f"{city_zh}机场"
    if name:
        return name
    return code
