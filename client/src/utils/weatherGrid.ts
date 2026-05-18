import type { AirportInfo, FlightBrief, WeatherGridCell } from "../types/flight";

/** 与后端 unified_pipeline 一致的 5° 网格步长 */
export const WEATHER_GRID_DEG = 5;

export function flightGridCorner(lat: number, lon: number): [number, number] {
	return [
		Math.floor(lat / WEATHER_GRID_DEG) * WEATHER_GRID_DEG,
		Math.floor(lon / WEATHER_GRID_DEG) * WEATHER_GRID_DEG,
	];
}

export function grdCellId(clat: number, clon: number): string {
	const latPart = clat >= 0 ? `+${clat}` : `${clat}`;
	const lonPart = clon >= 0 ? `+${clon}` : `${clon}`;
	return `GRD_${latPart}_${lonPart}`;
}

/** 解析 ``GRD_{lat}_{lon}``（与后端 parse_grd_cell_id 一致） */
export function parseGrdCellId(cellId: string): [number, number] | null {
	if (!cellId.startsWith("GRD_")) return null;
	const rest = cellId.slice(4);
	const sep = rest.indexOf("_");
	if (sep <= 0) return null;
	const clat = Number.parseInt(rest.slice(0, sep), 10);
	const clon = Number.parseInt(rest.slice(sep + 1), 10);
	if (Number.isNaN(clat) || Number.isNaN(clon)) return null;
	return [clat, clon];
}

function cellFromCorner(
	clat: number,
	clon: number,
	flight_count: number,
): WeatherGridCell {
	return {
		id: grdCellId(clat, clon),
		cell_min_lat: clat,
		cell_min_lon: clon,
		cell_max_lat: clat + WEATHER_GRID_DEG,
		cell_max_lon: clon + WEATHER_GRID_DEG,
		center_lat: clat + WEATHER_GRID_DEG / 2,
		center_lon: clon + WEATHER_GRID_DEG / 2,
		flight_count,
		has_weather: false,
	};
}

function weatherFieldsFromPayload(
	payload: unknown,
): { temperature_c: number | null; description: string | null } {
	if (!payload || typeof payload !== "object") {
		return { temperature_c: null, description: null };
	}
	const entry = payload as Record<string, unknown>;
	let temperature_c: number | null = null;
	const rawTemp = entry.temperature_c ?? entry.temp_c;
	if (typeof rawTemp === "number") temperature_c = rawTemp;

	let description: string | null = null;
	const weather = entry.weather;
	if (Array.isArray(weather) && weather[0] && typeof weather[0] === "object") {
		const d = (weather[0] as Record<string, unknown>).description;
		if (typeof d === "string" && d.trim()) description = d;
	}
	if (!description && typeof entry.description === "string") {
		description = entry.description;
	}

	return { temperature_c, description };
}

/**
 * 用 datahub 天气缓存中的 GRD_* 项标记网格是否已采集，并补充仅存在于缓存中的格子。
 */
export function enrichCellsWithGrdWeather(
	cells: WeatherGridCell[],
	weatherByKey: Record<string, unknown>,
): WeatherGridCell[] {
	const byId = new Map(cells.map((c) => [c.id, { ...c }]));

	for (const [key, payload] of Object.entries(weatherByKey)) {
		if (!key.startsWith("GRD_")) continue;
		const corner = parseGrdCellId(key);
		if (!corner) continue;
		const [clat, clon] = corner;
		const { temperature_c, description } = weatherFieldsFromPayload(payload);
		const existing = byId.get(key) ?? cellFromCorner(clat, clon, 0);
		byId.set(key, {
			...existing,
			has_weather: true,
			temperature_c,
			description,
		});
	}

	return Array.from(byId.values()).sort(
		(a, b) => a.cell_min_lat - b.cell_min_lat || a.cell_min_lon - b.cell_min_lon,
	);
}

function hubCellKeys(airports: AirportInfo[]): Set<string> {
	const keys = new Set<string>();
	for (const a of airports) {
		if (
			a.point_type === "grid" ||
			a.point_type === "weather" ||
			a.iata.startsWith("GRD_")
		) {
			continue;
		}
		if (a.is_hub === false) continue;
		const [clat, clon] = flightGridCorner(a.lat, a.lon);
		keys.add(`${clat},${clon}`);
	}
	return keys;
}

/**
 * 根据当前航班位置在前端推算 5° 天气网格（后端接口不可用时的回退）。
 */
export function computeWeatherGridFromFlights(
	flights: FlightBrief[],
	airports: AirportInfo[],
): WeatherGridCell[] {
	const hubs = hubCellKeys(airports);
	const counts = new Map<
		string,
		{ clat: number; clon: number; flight_count: number }
	>();

	for (const f of flights) {
		const [clat, clon] = flightGridCorner(f.lat, f.lon);
		const key = `${clat},${clon}`;
		if (hubs.has(key)) continue;
		const prev = counts.get(key);
		if (prev) prev.flight_count += 1;
		else counts.set(key, { clat, clon, flight_count: 1 });
	}

	return Array.from(counts.values())
		.sort((a, b) => a.clat - b.clat || a.clon - b.clon)
		.map(({ clat, clon, flight_count }) => ({
			id: grdCellId(clat, clon),
			cell_min_lat: clat,
			cell_min_lon: clon,
			cell_max_lat: clat + WEATHER_GRID_DEG,
			cell_max_lon: clon + WEATHER_GRID_DEG,
			center_lat: clat + WEATHER_GRID_DEG / 2,
			center_lon: clon + WEATHER_GRID_DEG / 2,
			flight_count,
			has_weather: false,
		}));
}
