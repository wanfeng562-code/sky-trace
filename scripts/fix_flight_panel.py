from pathlib import Path

script_style = Path("client/src/components/FlightListPanel.vue").read_text(encoding="utf-8")
idx = script_style.find("<script setup")
script_style = script_style[idx:]

# Fix corrupted Chinese in script section
replacements = {
    'label: "鍏ㄩ儴"': 'label: "全部"',
    'label: "绌轰腑"': 'label: "空中"',
    'label: "鍦伴潰"': 'label: "地面"',
    'label: "棰嗙┖"': 'label: "领空"',
    'label: "鍑哄彂"': 'label: "出发"',
    'label: "鍒拌揪"': 'label: "到达"',
    'return "鍏ㄩ儴鐪佷唤"': 'return "全部省份"',
    'return "鍏ㄩ儴宸?': 'return "全部州"',
    'return "鍏ㄩ儴鍦板尯"': 'return "全部地区"',
    '? "鍏ㄩ儴鍩庡競" : "鍏ㄩ儴鍩庡競/閮戒細鍖?': '? "全部城市" : "全部城市/都会区"',
    '? "鍏ㄩ儴鍖哄幙" : "鍏ㄩ儴缁嗗垎鍖?': '? "全部区县" : "全部细分区"',
}
for old, new in replacements.items():
    script_style = script_style.replace(old, new)

script_style = script_style.replace(
    "hasNestedGeo,\n\t\tmaxGeoDepth,\n\t} from",
    "} from",
)

template = Path("scripts/flight_panel_template.vue").read_text(encoding="utf-8")
Path("client/src/components/FlightListPanel.vue").write_text(
    template + "\n" + script_style, encoding="utf-8"
)
print("ok")
