import type { AppLocale } from "../i18n";

/** OpenWeather 等 API 返回的英文天气描述 → 简体中文 */
const WEATHER_DESC_ZH: Record<string, string> = {
	"clear sky": "晴",
	"few clouds": "少云",
	"scattered clouds": "多云",
	"broken clouds": "阴",
	"overcast clouds": "阴天",
	"light rain": "小雨",
	"moderate rain": "中雨",
	"heavy intensity rain": "大雨",
	"very heavy rain": "暴雨",
	"extreme rain": "特大暴雨",
	"freezing rain": "冻雨",
	"light intensity drizzle": "毛毛雨",
	drizzle: "毛毛雨",
	"light intensity shower rain": "小阵雨",
	"shower rain": "阵雨",
	"heavy intensity shower rain": "大阵雨",
	"ragged shower rain": "阵雨",
	thunderstorm: "雷暴",
	"thunderstorm with light rain": "雷阵雨",
	"thunderstorm with rain": "雷雨",
	"thunderstorm with heavy rain": "强雷雨",
	"light thunderstorm": "轻雷暴",
	"heavy thunderstorm": "强雷暴",
	"light snow": "小雪",
	snow: "雪",
	"heavy snow": "大雪",
	sleet: "雨夹雪",
	"light shower sleet": "小阵性雨夹雪",
	"shower sleet": "阵性雨夹雪",
	"light rain and snow": "雨夹雪",
	"rain and snow": "雨夹雪",
	"light shower snow": "小阵雪",
	"shower snow": "阵雪",
	"heavy shower snow": "大阵雪",
	mist: "薄雾",
	fog: "雾",
	haze: "霾",
	sand: "扬沙",
	dust: "浮尘",
	smoke: "烟霾",
	squall: "飑",
	tornado: "龙卷风",
};

const STATUS_LABELS: Record<AppLocale, Record<string, string>> = {
	"zh-CN": {
		enroute: "飞行中",
		en_route: "飞行中",
		airborne: "飞行中",
		active: "飞行中",
		flying: "飞行中",
		departed: "已起飞",
		landed: "已落地",
		arrived: "已抵达",
		scheduled: "计划中",
		cancelled: "已取消",
		canceled: "已取消",
		diverted: "备降",
		delayed: "延误",
		ground: "地面",
	},
	"en-US": {
		enroute: "En route",
		en_route: "En route",
		airborne: "Airborne",
		active: "Active",
		flying: "Flying",
		departed: "Departed",
		landed: "Landed",
		arrived: "Arrived",
		scheduled: "Scheduled",
		cancelled: "Cancelled",
		canceled: "Canceled",
		diverted: "Diverted",
		delayed: "Delayed",
		ground: "On ground",
	},
};

const STATUS_CLASS: Record<string, string> = {
	enroute: "status-airborne",
	en_route: "status-airborne",
	airborne: "status-airborne",
	active: "status-airborne",
	flying: "status-airborne",
	departed: "status-airborne",
	landed: "status-ground",
	arrived: "status-ground",
	ground: "status-ground",
	scheduled: "status-scheduled",
	cancelled: "status-cancelled",
	canceled: "status-cancelled",
	diverted: "status-scheduled",
	delayed: "status-scheduled",
};

function normalizeKey(raw: string): string {
	return raw.trim().toLowerCase().replace(/-/g, "_").replace(/\s+/g, "_");
}

/** 将 API 天气描述转为当前界面语言 */
export function formatWeatherDescription(
	description: string | null | undefined,
	locale: AppLocale,
): string | null {
	if (!description?.trim()) return null;
	const raw = description.trim();
	if (locale !== "zh-CN") return raw;

	const lower = raw.toLowerCase();
	if (WEATHER_DESC_ZH[lower]) return WEATHER_DESC_ZH[lower];

	// 组合短语：heavy intensity rain → 大雨
	for (const [en, zh] of Object.entries(WEATHER_DESC_ZH)) {
		if (lower.includes(en)) return zh;
	}

	// 关键词兜底
	if (/\brain\b/.test(lower)) return lower.includes("light") ? "小雨" : "雨";
	if (/\bsnow\b/.test(lower)) return "雪";
	if (/\bcloud/.test(lower)) return "多云";
	if (/\bthunder/.test(lower)) return "雷暴";
	if (/\bfog\b|\bmist\b/.test(lower)) return "雾";
	if (/\bclear\b/.test(lower)) return "晴";

	return raw;
}

/** 航班状态文案（支持 en-route / en_route 等） */
export function formatFlightStatusLabel(
	status: string | null | undefined,
	locale: AppLocale,
	altitudeFt?: number | null,
): string {
	const labels = STATUS_LABELS[locale];
	if (status?.trim()) {
		const key = normalizeKey(status);
		if (labels[key]) return labels[key];
		const alt = status.trim().toLowerCase();
		for (const [k, label] of Object.entries(labels)) {
			if (alt.replace(/-/g, "_") === k || alt === k.replace(/_/g, "-")) {
				return label;
			}
		}
		return status;
	}
	if ((altitudeFt ?? 0) > 100) {
		return labels.en_route ?? "En route";
	}
	return labels.ground ?? "On ground";
}

export function flightStatusClass(
	status: string | null | undefined,
	altitudeFt?: number | null,
): string {
	if (status?.trim()) {
		const key = normalizeKey(status);
		return STATUS_CLASS[key] ?? "";
	}
	return (altitudeFt ?? 0) > 100 ? "status-airborne" : "status-ground";
}
