import type { FlightBrief } from "../types/flight";



/** 参照 FA 分类的飞行类型（基于 OpenSky aircraft_category） */

export type FlightTypeFilter =

	| "all"

	| "commercial"

	| "general"

	| "helicopter"

	| "uav"

	| "light"

	| "other";



export const FLIGHT_TYPE_OPTIONS: {

	value: FlightTypeFilter;

	label: string;

}[] = [

	{ value: "all", label: "全部类型" },

	{ value: "commercial", label: "民航客机" },

	{ value: "general", label: "通用航空" },

	{ value: "helicopter", label: "直升机" },

	{ value: "uav", label: "无人机" },

	{ value: "light", label: "轻型航空器" },

	{ value: "other", label: "未分类/其他" },

];



/**

 * OpenSky ADS-B 机型类别（extended=1 字段 index 17）

 * @see https://openskynetwork.github.io/opensky-api/rest.html#all-state-vectors-response

 */

export const UNCATEGORIZED_CATEGORY = -1;



export const AIRCRAFT_CATEGORY_OPTIONS: { value: number; label: string }[] = [

	{ value: UNCATEGORIZED_CATEGORY, label: "未标注 (补充源)" },

	{ value: 0, label: "未知 (0)" },

	{ value: 1, label: "无 ADS-B (1)" },

	{ value: 2, label: "Light 轻型" },

	{ value: 3, label: "Small 小型" },

	{ value: 4, label: "Large 大型" },

	{ value: 5, label: "High Vortex 高涡流" },

	{ value: 6, label: "Heavy 重型" },

	{ value: 7, label: "High Perf 高性能" },

	{ value: 8, label: "Rotorcraft 旋翼" },

	{ value: 9, label: "Glider 滑翔" },

	{ value: 10, label: "轻于空气 (10)" },

	{ value: 11, label: "跳伞/滑翔伞 (11)" },

	{ value: 12, label: "超轻型 (12)" },

	{ value: 13, label: "保留 (13)" },

	{ value: 14, label: "UAV 无人机" },

	{ value: 15, label: "航天 (15)" },

	{ value: 16, label: "应急地面 (16)" },

	{ value: 17, label: "服务地面 (17)" },

	{ value: 18, label: "点障碍 (18)" },

];



const COMMERCIAL_CATS = new Set([4, 5, 6, 7]);

const GENERAL_CATS = new Set([2, 3, 9, 10, 12]);

const LIGHT_CATS = new Set([2, 3, 12]);

/** 不属于上述飞行类型分组的 OpenSky 类别 */

const OTHER_CATS = new Set([0, 1, 11, 13, 15, 16, 17, 18]);



const CHIP_CATEGORY_VALUES = new Set(

	AIRCRAFT_CATEGORY_OPTIONS.map((o) => o.value).filter(

		(v) => v !== UNCATEGORIZED_CATEGORY,

	),

);



export function matchesFlightType(

	flight: FlightBrief,

	filter: FlightTypeFilter,

): boolean {

	if (filter === "all") return true;

	const cat = flight.aircraft_category;

	if (filter === "other") {

		if (cat == null) return true;

		return OTHER_CATS.has(cat);

	}

	const c = cat ?? 0;

	switch (filter) {

		case "commercial":

			return COMMERCIAL_CATS.has(c);

		case "general":

			return GENERAL_CATS.has(c);

		case "helicopter":

			return c === 8;

		case "uav":

			return c === 14;

		case "light":

			return LIGHT_CATS.has(c);

		default:

			return true;

	}

}



/** 单选机型（null = 全部） */
export function matchesAircraftCategory(
	flight: FlightBrief,
	category: number | null,
): boolean {
	if (category == null) return true;
	if (category === UNCATEGORIZED_CATEGORY) {
		return flight.aircraft_category == null;
	}
	return flight.aircraft_category === category;
}



export function matchesAltitudeRange(

	flight: FlightBrief,

	minFt: number | null,

	maxFt: number | null,

): boolean {

	const alt = flight.altitude_ft;

	if (alt == null) {
		if (minFt == null && maxFt == null) return true;
		// 地面高度预设：无高度数据按地面状态一致处理
		if (minFt === 0 && maxFt != null && maxFt <= 100) return true;
		return false;
	}

	if (minFt != null && alt < minFt) return false;

	if (maxFt != null && alt > maxFt) return false;

	return true;

}



export function matchesSpeedRange(

	flight: FlightBrief,

	minKts: number | null,

	maxKts: number | null,

): boolean {

	const spd = flight.speed_kts;

	if (spd == null) return minKts == null && maxKts == null;

	if (minKts != null && spd < minKts) return false;

	if (maxKts != null && spd > maxKts) return false;

	return true;

}



/** 统计机型分类覆盖情况（用于筛选面板提示） */

export function getCategoryCoverage(flights: FlightBrief[]) {

	let nullCategory = 0;

	let inChips = 0;

	let otherKnown = 0;

	const byCode: Record<number, number> = {};



	for (const f of flights) {

		const cat = f.aircraft_category;

		if (cat == null) {

			nullCategory++;

			continue;

		}

		byCode[cat] = (byCode[cat] ?? 0) + 1;

		if (CHIP_CATEGORY_VALUES.has(cat)) {

			inChips++;

		} else {

			otherKnown++;

		}

	}



	return {

		total: flights.length,

		nullCategory,

		inChips,

		otherKnown,

		byCode,

	};

}



/** 各飞行类型命中数量（互有重叠，不可直接相加） */

export function countByFlightType(

	flights: FlightBrief[],

): Record<FlightTypeFilter, number> {

	const counts = Object.fromEntries(

		FLIGHT_TYPE_OPTIONS.map((o) => [o.value, 0]),

	) as Record<FlightTypeFilter, number>;



	for (const f of flights) {

		for (const opt of FLIGHT_TYPE_OPTIONS) {

			if (matchesFlightType(f, opt.value)) {

				counts[opt.value]++;

			}

		}

	}

	return counts;

}


