import type { AirportInfo } from "../types/flight";
import {
	hydratePlaceNamesFromServer,
	queuePlaceNameSync,
	readCachedPlaceNameZh,
} from "../services/placeNameSync";
import {
	NAME_CACHE_TTL_MS,
	readPersistentCache,
	writePersistentCache,
} from "../services/persistentCache";
import { toSimplifiedChinese } from "../utils/zhLocale";

/** 城市 → 中文（覆盖 seed 中全部枢纽城市） */
const CITY_ZH: Record<string, string> = {
	"Abu Dhabi": "阿布扎比",
	"Addis Ababa": "亚的斯亚贝巴",
	Amsterdam: "阿姆斯特丹",
	Atlanta: "亚特兰大",
	Auckland: "奥克兰",
	Bangkok: "曼谷",
	Barcelona: "巴塞罗那",
	Beijing: "北京",
	Bengaluru: "班加罗尔",
	Bogota: "波哥大",
	Boston: "波士顿",
	Brisbane: "布里斯班",
	Brussels: "布鲁塞尔",
	Budapest: "布达佩斯",
	"Buenos Aires": "布宜诺斯艾利斯",
	Cairo: "开罗",
	Cancun: "坎昆",
	"Cape Town": "开普敦",
	Casablanca: "卡萨布兰卡",
	Changsha: "长沙",
	Chengdu: "成都",
	Chennai: "金奈",
	Chicago: "芝加哥",
	Christchurch: "基督城",
	Copenhagen: "哥本哈根",
	Dallas: "达拉斯",
	Delhi: "德里",
	Denver: "丹佛",
	Doha: "多哈",
	Dubai: "迪拜",
	Dublin: "都柏林",
	Frankfurt: "法兰克福",
	Guangzhou: "广州",
	Hangzhou: "杭州",
	Hanoi: "河内",
	Helsinki: "赫尔辛基",
	"Ho Chi Minh City": "胡志明市",
	"Hong Kong": "香港",
	Hyderabad: "海得拉巴",
	Istanbul: "伊斯坦布尔",
	Jakarta: "雅加达",
	Jeddah: "吉达",
	Johannesburg: "约翰内斯堡",
	Kolkata: "加尔各答",
	"Kuala Lumpur": "吉隆坡",
	Kunming: "昆明",
	Lagos: "拉各斯",
	"Las Vegas": "拉斯维加斯",
	Lima: "利马",
	Lisbon: "里斯本",
	London: "伦敦",
	"Los Angeles": "洛杉矶",
	Madrid: "马德里",
	Manila: "马尼拉",
	Melbourne: "墨尔本",
	"Mexico City": "墨西哥城",
	Miami: "迈阿密",
	Montreal: "蒙特利尔",
	Mumbai: "孟买",
	Munich: "慕尼黑",
	Nairobi: "内罗毕",
	Nanjing: "南京",
	"New York": "纽约",
	Newark: "纽瓦克",
	Oslo: "奥斯陆",
	"Panama City": "巴拿马城",
	Paris: "巴黎",
	Perth: "珀斯",
	Prague: "布拉格",
	"Rio de Janeiro": "里约热内卢",
	Riyadh: "利雅得",
	Rome: "罗马",
	"San Francisco": "旧金山",
	Santiago: "圣地亚哥",
	"Sao Paulo": "圣保罗",
	Seattle: "西雅图",
	Seoul: "首尔",
	Shanghai: "上海",
	Shenzhen: "深圳",
	Singapore: "新加坡",
	Stockholm: "斯德哥尔摩",
	Sydney: "悉尼",
	Taipei: "台北",
	Tokyo: "东京",
	Toronto: "多伦多",
	Vancouver: "温哥华",
	Vienna: "维也纳",
	Warsaw: "华沙",
	Washington: "华盛顿",
	Wuhan: "武汉",
	Xian: "西安",
	Zurich: "苏黎世",
	"Saint Petersburg": "圣彼得堡",
	Antalya: "安塔利亚",
	"Moscow": "莫斯科",
	"Domodedovo": "莫斯科",
	"St. Petersburg": "圣彼得堡",
	"St Petersburg": "圣彼得堡",
	"Ho Chi Minh": "胡志明市",
	"Kiev": "基辅",
	"Kyiv": "基辅",
	"Minsk": "明斯克",
	"Tashkent": "塔什干",
	"Almaty": "阿拉木图",
	"Baku": "巴库",
	"Tbilisi": "第比利斯",
	"Yerevan": "埃里温",
	"Tehran": "德黑兰",
	"Baghdad": "巴格达",
	"Kuwait City": "科威特城",
	"Muscat": "马斯喀特",
	"Karachi": "卡拉奇",
	"Lahore": "拉合尔",
	"Islamabad": "伊斯兰堡",
	"Dhaka": "达卡",
	"Colombo": "科伦坡",
	"Kathmandu": "加德满都",
	"Ulaanbaatar": "乌兰巴托",
	"Vladivostok": "符拉迪沃斯托克",
	"Novosibirsk": "新西伯利亚",
	"Yekaterinburg": "叶卡捷琳堡",
	"Sochi": "索契",
	"Krasnoyarsk": "克拉斯诺亚尔斯克",
	"Irkutsk": "伊尔库茨克",
	"Khabarovsk": "哈巴罗夫斯克",
	"Petropavlovsk": "彼得罗巴甫洛夫斯克",
	"Anchorage": "安克雷奇",
	"Honolulu": "檀香山",
	"Port Moresby": "莫尔兹比港",
	"Noumea": "努美阿",
	"Suva": "苏瓦",
	"Apia": "阿皮亚",
	"Nadi": "楠迪",
	Houston: "休斯顿",
	Orlando: "奥兰多",
	Phoenix: "凤凰城",
};

/** 同城多机场时的中文专名 */
const HUB_NAME_ZH: Record<string, string> = {
	PEK: "北京首都",
	PKX: "北京大兴",
	PVG: "上海浦东",
	SHA: "上海虹桥",
	SYD: "悉尼金斯福德·史密斯",
	CHC: "基督城",
	MEL: "墨尔本",
	BNE: "布里斯班",
	PER: "珀斯",
	ADL: "阿德莱德",
	HKG: "香港",
	TPE: "台北桃园",
	NRT: "东京成田",
	HND: "东京羽田",
	ICN: "首尔仁川",
	SIN: "新加坡樟宜",
	BKK: "曼谷素万那普",
	DXB: "迪拜",
	LHR: "伦敦希思罗",
	CDG: "巴黎戴高乐",
	FRA: "法兰克福",
	AMS: "阿姆斯特丹",
	LAX: "洛杉矶",
	JFK: "纽约肯尼迪",
	ORD: "芝加哥奥黑尔",
	ATL: "亚特兰大",
	DFW: "达拉斯沃斯堡",
	SFO: "旧金山",
	SEA: "西雅图",
	YVR: "温哥华",
	YYZ: "多伦多皮尔逊",
	CTU: "成都双流",
	TFU: "成都天府",
	GMP: "首尔金浦",
	DMK: "曼谷廊曼",
	BOG: "波哥大埃尔多拉多",
	LED: "圣彼得堡普尔科沃",
	AYT: "安塔利亚",
	MTR: "蒙特里亚",
	RMO: "基希讷乌",
	HOU: "休斯顿霍比",
	IAH: "休斯顿布什",
	MCO: "奥兰多",
	FLL: "劳德代尔堡",
	MIA: "迈阿密",
	PHX: "凤凰城",
	LAS: "拉斯维加斯",
	DEN: "丹佛",
	BOS: "波士顿",
	PHL: "费城",
	DCA: "华盛顿里根",
	IAD: "华盛顿杜勒斯",
};

/** 根据 IATA 返回机场简体中文名（用于详情页等） */
export function airportNameZh(
	iata: string | null | undefined,
	airports: readonly { iata: string; name: string; city?: string; country?: string }[],
): string {
	if (!iata?.trim()) return "";
	const code = iata.trim().toUpperCase();
	if (HUB_NAME_ZH[code]) return normalizeZh(HUB_NAME_ZH[code]);
	const ap =
		airportByIata.get(code) ??
		airports.find((a) => a.iata.toUpperCase() === code);
	if (!ap) return "";
	return formatAirportDisplay(ap as AirportInfo).nameZh;
}

const COUNTRY_ZH: Record<string, string> = {
	CN: "中国",
	US: "美国",
	GB: "英国",
	JP: "日本",
	KR: "韩国",
	TH: "泰国",
	AE: "阿联酋",
	SG: "新加坡",
	HK: "中国香港",
	TW: "中国台湾",
	FR: "法国",
	DE: "德国",
};

export interface AirportDisplayNames {
	iata: string;
	nameZh: string;
	nameEn: string;
	cityZh: string;
	countryLabel: string;
}

const displayMemCache = new Map<string, AirportDisplayNames>();
const airportByIata = new Map<string, AirportInfo>();

function normalizeZh(text: string): string {
	return toSimplifiedChinese(text.trim());
}

function buildDisplay(airport: AirportInfo): AirportDisplayNames {
	const cityRaw = airport.city ? (CITY_ZH[airport.city] ?? airport.city) : "";
	const cityZh = normalizeZh(cityRaw);
	const hub = HUB_NAME_ZH[airport.iata];
	const nameFromHub = hub ? normalizeZh(hub) : "";
	const nameFromCity = cityZh ? `${cityZh}国际机场` : "";
	const nameFromApi = airport.name ? normalizeZh(airport.name) : "";
	const nameZh = nameFromHub || nameFromCity || nameFromApi || airport.iata;
	const countryLabel = airport.country
		? normalizeZh(COUNTRY_ZH[airport.country] ?? airport.country)
		: "";
	return {
		iata: airport.iata,
		nameZh,
		nameEn: airport.name,
		cityZh,
		countryLabel,
	};
}

/** 批量预热显示名缓存（加载机场列表后调用） */
export function warmAirportDisplayCache(airports: readonly AirportInfo[]): void {
	airportByIata.clear();
	const keys: string[] = [];
	for (const ap of airports) {
		const code = ap.iata?.trim().toUpperCase();
		if (!code) continue;
		airportByIata.set(code, ap);
		keys.push(`ap.zh:${code}`);
		formatAirportDisplay(ap);
	}
	void hydratePlaceNamesFromServer(keys);
}

export function formatAirportDisplay(airport: AirportInfo): AirportDisplayNames {
	const iata = airport.iata?.trim().toUpperCase() ?? "";
	const memKey = `${iata}|${airport.name}|${airport.city ?? ""}|${airport.country ?? ""}`;
	const memHit = displayMemCache.get(memKey);
	if (memHit) return memHit;

	const cacheKey = iata ? `ap.zh:${iata}` : "";
	if (cacheKey) {
		const serverZh = readCachedPlaceNameZh(cacheKey);
		if (serverZh) {
			const fromServer: AirportDisplayNames = {
				iata,
				nameZh: serverZh,
				nameEn: airport.name,
				cityZh: airport.city ? normalizeZh(CITY_ZH[airport.city] ?? airport.city) : "",
				countryLabel: airport.country
					? normalizeZh(COUNTRY_ZH[airport.country] ?? airport.country)
					: "",
			};
			displayMemCache.set(memKey, fromServer);
			return fromServer;
		}
		const persisted = readPersistentCache<AirportDisplayNames>(cacheKey);
		if (persisted && persisted.iata === iata) {
			displayMemCache.set(memKey, persisted);
			return persisted;
		}
	}

	const result = buildDisplay(airport);
	displayMemCache.set(memKey, result);
	if (cacheKey) {
		writePersistentCache(cacheKey, result, NAME_CACHE_TTL_MS);
		queuePlaceNameSync({
			cache_key: cacheKey,
			name_zh: result.nameZh,
			name_en: result.nameEn,
			source_text: airport.name,
		});
	}
	return result;
}

/** 区域/地名中文（持久化简繁转换结果） */
export function resolvePlaceNameZh(
	cacheKey: string,
	rawName: string | null | undefined,
	fallback = "",
): string {
	if (!rawName?.trim()) return fallback;
	const key = `place.zh:${cacheKey}`;
	const cached = readCachedPlaceNameZh(key);
	if (cached) return cached;
	const simplified = normalizeZh(rawName);
	writePersistentCache(key, simplified, NAME_CACHE_TTL_MS);
	queuePlaceNameSync({
		cache_key: key,
		name_zh: simplified,
		source_text: rawName,
	});
	return simplified || fallback;
}
