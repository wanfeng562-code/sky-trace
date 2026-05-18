import type { ExpressionSpecification, LineLayerSpecification } from "maplibre-gl";
import type { AirportInfo, FlightBrief, TrackPoint } from "../types/flight";

/** 已飞轨迹（参考 FR24：暖色实线，近飞机端更亮；按高度分段着色） */
export const TRACK_HISTORY_LAYER_ID = "flight-track-history";
export const TRACK_HISTORY_SEG_LAYER_ID = "flight-track-history-segments";

/** 剩余航程专用 id（勿与底图或历史轨迹重名） */
export const TRACK_PLANNED_SOURCE_ID = "skytrace-remaining-route-geo";
export const TRACK_PLANNED_GLOW_LAYER_ID = "skytrace-remaining-route-glow";
export const TRACK_PLANNED_LAYER_ID = "skytrace-remaining-route-line";

/** 历史错误 id，初始化时清理 */
export const TRACK_PLANNED_LEGACY_SOURCE_IDS = [
	"geo-flight-planned-route",
	"flight-track-planned-src",
	"flight-track-planned",
	"flight-track-planned-glow",
	"playback-flight-track-planned-src",
	"playback-flight-track-planned",
	"geo-playback-planned-route",
] as const;

/** 常见 ICAO → IATA（商业数据源可能只给四字码） */
const ICAO_TO_IATA: Readonly<Record<string, string>> = {
	ZSPD: "PVG",
	ZGGG: "CAN",
	ZGSZ: "SZX",
	ZBAA: "PEK",
	ZBAD: "PKX",
	ZUTF: "CTU",
	VHHH: "HKG",
	RCTP: "TPE",
	LEMD: "MAD",
	LEBL: "BCN",
	LFPG: "CDG",
	EGLL: "LHR",
	EDDF: "FRA",
	EHAM: "AMS",
	OMDB: "DXB",
	OTHH: "DOH",
	WSSS: "SIN",
	WMKK: "KUL",
	VTBS: "BKK",
	RJAA: "NRT",
	RJTT: "HND",
	RKSI: "ICN",
	KLAX: "LAX",
	KSFO: "SFO",
	KJFK: "JFK",
	KORD: "ORD",
	KATL: "ATL",
};

export const AIRPORT_HIGHLIGHT_SOURCE = "airports-route-highlight";
export const AIRPORT_HIGHLIGHT_LAYER = "airport-route-highlight-points";

/** 常见枢纽坐标兜底（API / 本地库均未命中时） */
const FALLBACK_AIRPORT_COORDS: Readonly<Record<string, readonly [number, number]>> = {
	PVG: [31.1434, 121.805],
	PEK: [40.0799, 116.6031],
	PKX: [39.5099, 116.4108],
	SHA: [31.1979, 121.336],
	CAN: [23.3924, 113.299],
	SZX: [22.6393, 113.811],
	CTU: [30.5785, 103.947],
	HKG: [22.308, 113.918],
	TPE: [25.0797, 121.234],
	MAD: [40.4934, -3.5722],
	BCN: [41.2971, 2.0785],
	CDG: [49.0097, 2.5479],
	LHR: [51.47, -0.4543],
	FRA: [50.0379, 8.5622],
	AMS: [52.3086, 4.7639],
	DXB: [25.2528, 55.3644],
	DOH: [25.2731, 51.608],
	SIN: [1.3644, 103.991],
	KUL: [2.7456, 101.71],
	BKK: [13.69, 100.7501],
	NRT: [35.772, 140.3929],
	HND: [35.5494, 139.7798],
	ICN: [37.4602, 126.4407],
	LAX: [33.9425, -118.408],
	SFO: [37.619, -122.375],
	JFK: [40.6413, -73.7781],
	ORD: [41.9742, -87.9073],
	ATL: [33.6367, -84.4281],
};

/** 历史轨迹主线：沿 line-progress 由旧到新渐亮（需 GeoJSON lineMetrics） */
export function historicalTrackMainLinePaint(): LineLayerSpecification["paint"] {
	return {
		"line-width": 3,
		"line-opacity": 0.92,
		"line-gradient": [
			"interpolate",
			["linear"],
			["line-progress"],
			0,
			"rgba(251, 191, 36, 0.18)",
			0.65,
			"rgba(245, 158, 11, 0.55)",
			1,
			"rgba(234, 179, 8, 0.98)",
		],
	};
}

/** 按航段高度着色（参考 FR24 高度色带，简化版） */
export function historicalTrackSegmentLinePaint(): LineLayerSpecification["paint"] {
	return {
		"line-width": 2.5,
		"line-opacity": 0.85,
		"line-color": [
			"interpolate",
			["linear"],
			["get", "altitude_ft"],
			0,
			"#9ca3af",
			500,
			"#fbbf24",
			5000,
			"#f59e0b",
			18000,
			"#84cc16",
			28000,
			"#38bdf8",
			38000,
			"#818cf8",
		],
	};
}

/** 剩余航程底层光晕 */
export function plannedRouteGlowLinePaint(): LineLayerSpecification["paint"] {
	return {
		"line-color": "#06b6d4",
		"line-width": 7,
		"line-opacity": 0.45,
		"line-blur": 1,
		"line-cap": "round",
	};
}

/** 剩余航程主线（实线，避免 dasharray 在部分 GPU/样式下不渲染） */
export function plannedRouteLinePaint(): LineLayerSpecification["paint"] {
	return {
		"line-color": "#22d3ee",
		"line-width": 4,
		"line-opacity": 1,
		"line-cap": "round",
		"line-join": "round",
	};
}

export function buildHistoricalTrackLineFeature(
	points: TrackPoint[],
	flightId: string,
): GeoJSON.Feature<GeoJSON.LineString> | null {
	if (points.length < 2) return null;
	return {
		type: "Feature",
		properties: { flight_id: flightId, kind: "history" },
		geometry: {
			type: "LineString",
			coordinates: points.map((p) => [p.lon, p.lat]),
		},
	};
}

/** 将轨迹拆成线段以便按高度着色 */
export function buildHistoricalTrackSegmentCollection(
	points: TrackPoint[],
	flightId: string,
): GeoJSON.FeatureCollection<GeoJSON.LineString> {
	const features: GeoJSON.Feature<GeoJSON.LineString>[] = [];
	for (let i = 0; i < points.length - 1; i++) {
		const a = points[i];
		const b = points[i + 1];
		features.push({
			type: "Feature",
			properties: {
				flight_id: flightId,
				altitude_ft: b.altitude_ft ?? a.altitude_ft ?? 0,
				seg: i,
			},
			geometry: {
				type: "LineString",
				coordinates: [
					[a.lon, a.lat],
					[b.lon, b.lat],
				],
			},
		});
	}
	return { type: "FeatureCollection", features };
}

export function buildPlannedRouteFeature(
	originLon: number,
	originLat: number,
	arrLon: number,
	arrLat: number,
	arrIata: string,
): GeoJSON.Feature<GeoJSON.LineString> {
	return {
		type: "Feature",
		properties: { arr_iata: arrIata, kind: "planned" },
		geometry: {
			type: "LineString",
			coordinates: [
				[originLon, originLat],
				[arrLon, arrLat],
			],
		},
	};
}

export function normalizeAirportCode(
	code: string | null | undefined,
): string | null {
	return normalizeIata(code);
}

export function airportsMatch(
	a: string | null | undefined,
	b: string | null | undefined,
): boolean {
	const na = normalizeIata(a);
	const nb = normalizeIata(b);
	return na != null && nb != null && na === nb;
}

function normalizeIata(code: string | null | undefined): string | null {
	const c = code?.trim().toUpperCase();
	if (!c) return null;
	if (c.length === 3) return c;
	if (c.length === 4) return ICAO_TO_IATA[c] ?? null;
	return null;
}

function toNum(v: number | string | null | undefined): number | null {
	if (v == null || v === "") return null;
	const n = typeof v === "number" ? v : Number(v);
	return Number.isFinite(n) ? n : null;
}

function isValidCoord(lat: number | null | undefined, lon: number | null | undefined): boolean {
	const la = toNum(lat);
	const lo = toNum(lon);
	return la != null && lo != null && Math.abs(la) <= 90 && Math.abs(lo) <= 180;
}

/** 剩余航程起点：飞机当前实时位置 */
export function resolveFlightMapPosition(
	flight: FlightBrief | null,
	detail: Pick<FlightBrief, "lat" | "lon"> | null,
	trackPoints: readonly TrackPoint[],
): { lat: number; lon: number } | null {
	if (flight && isValidCoord(flight.lat, flight.lon)) {
		return { lat: toNum(flight.lat)!, lon: toNum(flight.lon)! };
	}
	if (detail && isValidCoord(detail.lat, detail.lon)) {
		return { lat: toNum(detail.lat)!, lon: toNum(detail.lon)! };
	}
	if (trackPoints.length > 0) {
		const last = trackPoints[trackPoints.length - 1]!;
		if (isValidCoord(last.lat, last.lon)) {
			return { lat: toNum(last.lat)!, lon: toNum(last.lon)! };
		}
	}
	return null;
}

export function resolveAirportCoords(
	iata: string | null | undefined,
	lat: number | null | undefined,
	lon: number | null | undefined,
	airports: readonly AirportInfo[],
): { lat: number; lon: number; iata: string } | null {
	const code = normalizeIata(iata);
	if (!code) return null;

	const la = toNum(lat);
	const lo = toNum(lon);
	if (la != null && lo != null && isValidCoord(la, lo)) {
		return { iata: code, lat: la, lon: lo };
	}

	const ap = airports.find((a) => normalizeIata(a.iata) === code);
	if (ap && isValidCoord(ap.lat, ap.lon)) {
		return { iata: code, lat: toNum(ap.lat)!, lon: toNum(ap.lon)! };
	}

	const fb = FALLBACK_AIRPORT_COORDS[code];
	if (fb) {
		return { iata: code, lat: fb[0], lon: fb[1] };
	}

	return null;
}

/** 构建剩余航程 GeoJSON（实时地图 / 回放共用） */
export function buildPlannedRouteGeoJson(input: {
	flight: FlightBrief | null;
	detail: {
		arrival_airport?: string | null;
		arrival_lat?: number | null;
		arrival_lon?: number | null;
		lat?: number;
		lon?: number;
	} | null;
	trackPoints: readonly TrackPoint[];
	airports: readonly AirportInfo[];
}): GeoJSON.FeatureCollection<GeoJSON.LineString> {
	const empty: GeoJSON.FeatureCollection<GeoJSON.LineString> = {
		type: "FeatureCollection",
		features: [],
	};

	const arrivalIata = normalizeIata(
		input.detail?.arrival_airport ?? input.flight?.arrival_airport,
	);
	if (!arrivalIata) return empty;

	const origin = resolveFlightMapPosition(
		input.flight,
		input.detail,
		input.trackPoints,
	);
	const dest = resolveAirportCoords(
		arrivalIata,
		input.detail?.arrival_lat,
		input.detail?.arrival_lon,
		input.airports,
	);
	if (!origin || !dest) return empty;

	const dLat = origin.lat - dest.lat;
	const dLon = origin.lon - dest.lon;
	if (dLat * dLat + dLon * dLon < 1e-10) return empty;

	return {
		type: "FeatureCollection",
		features: [
			buildPlannedRouteFeature(
				origin.lon,
				origin.lat,
				dest.lon,
				dest.lat,
				dest.iata,
			),
		],
	};
}

type PlannedRouteMap = {
	getSource(id: string): unknown;
	getLayer(id: string): unknown;
	removeLayer(id: string): void;
	removeSource(id: string): void;
	addSource(id: string, spec: { type: "geojson"; data: GeoJSON.GeoJSON }): void;
	addLayer(spec: {
		id: string;
		type: "line";
		source: string;
		layout?: Record<string, string>;
		paint: LineLayerSpecification["paint"];
	}): void;
	moveLayer(id: string, beforeId?: string): void;
};

function removePlannedRouteStack(
	map: PlannedRouteMap,
	sourceId: string,
	glowLayerId: string,
	lineLayerId: string,
	extraLegacySourceIds: string[] = [],
): void {
	for (const layerId of [lineLayerId, glowLayerId]) {
		if (map.getLayer(layerId)) {
			try {
				map.removeLayer(layerId);
			} catch {
				/* ignore */
			}
		}
	}
	const sourceIds = new Set([
		sourceId,
		...TRACK_PLANNED_LEGACY_SOURCE_IDS,
		...extraLegacySourceIds,
	]);
	for (const sid of sourceIds) {
		if (!sid || !map.getSource(sid)) continue;
		try {
			map.removeSource(sid);
		} catch {
			/* ignore */
		}
	}
}

/** 将剩余航程图层移到样式栈最顶端（避免被后插入的 overlay 盖住） */
export function movePlannedRouteLayersToTop(
	map: PlannedRouteMap,
	glowLayerId: string,
	lineLayerId: string,
): void {
	for (const layerId of [glowLayerId, lineLayerId]) {
		if (!map.getLayer(layerId)) continue;
		try {
			map.moveLayer(layerId);
		} catch {
			/* ignore */
		}
	}
}

/**
 * 同步剩余航程图层：有数据时整组重建并置顶；无数据时移除。
 */
export function syncPlannedRouteLayer(
	map: PlannedRouteMap,
	sourceId: string,
	glowLayerId: string,
	lineLayerId: string,
	data: GeoJSON.FeatureCollection<GeoJSON.LineString>,
	extraLegacySourceIds: string[] = [],
): void {
	const shouldShow = data.features.length > 0;

	removePlannedRouteStack(map, sourceId, glowLayerId, lineLayerId, extraLegacySourceIds);

	if (!shouldShow) return;

	map.addSource(sourceId, { type: "geojson", data });
	map.addLayer({
		id: glowLayerId,
		type: "line",
		source: sourceId,
		layout: {
			visibility: "visible",
			"line-cap": "round",
			"line-join": "round",
		},
		paint: plannedRouteGlowLinePaint(),
	});
	map.addLayer({
		id: lineLayerId,
		type: "line",
		source: sourceId,
		layout: {
			visibility: "visible",
			"line-cap": "round",
			"line-join": "round",
		},
		paint: plannedRouteLinePaint(),
	});
	movePlannedRouteLayersToTop(map, glowLayerId, lineLayerId);
}

/** @deprecated 使用 syncPlannedRouteLayer */
export function ensurePlannedRouteLayers(
	map: PlannedRouteMap,
	sourceId: string,
	glowLayerId: string,
	lineLayerId: string,
	initialData: GeoJSON.FeatureCollection<GeoJSON.LineString>,
	legacySourceIds: string[] = [],
): void {
	syncPlannedRouteLayer(
		map,
		sourceId,
		glowLayerId,
		lineLayerId,
		initialData,
		legacySourceIds,
	);
}

export type RouteAirportRole = "dep" | "arr" | "hub";

export interface RouteAirportPoint {
	iata: string;
	lat: number;
	lon: number;
	role: RouteAirportRole;
	name?: string;
}

export function buildRouteAirportHighlightCollection(
	points: RouteAirportPoint[],
): GeoJSON.FeatureCollection<GeoJSON.Point> {
	return {
		type: "FeatureCollection",
		features: points.map((p) => ({
			type: "Feature",
			properties: {
				iata: p.iata,
				role: p.role,
				name: p.name ?? p.iata,
			},
			geometry: {
				type: "Point",
				coordinates: [p.lon, p.lat],
			},
		})),
	};
}

export function routeAirportHighlightPaint(): {
	"circle-radius": ExpressionSpecification;
	"circle-color": ExpressionSpecification;
	"circle-stroke-width": number;
	"circle-stroke-color": string;
	"circle-opacity": number;
	"circle-pitch-alignment": "viewport";
} {
	return {
		"circle-radius": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			7,
			8,
			11,
			12,
			14,
		],
		"circle-color": [
			"match",
			["get", "role"],
			"dep",
			"#22c55e",
			"arr",
			"#f97316",
			"hub",
			"#a78bfa",
			"#94a3b8",
		],
		"circle-stroke-width": 2.5,
		"circle-stroke-color": "#f8fafc",
		"circle-opacity": 1,
		"circle-pitch-alignment": "viewport",
	};
}

/** 回放页：所有飞机的短轨迹（半透明高度色） */
export function playbackFleetTrailLinePaint(): LineLayerSpecification["paint"] {
	return {
		"line-width": 1.8,
		"line-opacity": 0.5,
		"line-color": [
			"interpolate",
			["linear"],
			["coalesce", ["get", "altitude_ft"], 0],
			0,
			"#6b7280",
			3000,
			"#fbbf24",
			20000,
			"#60a5fa",
			35000,
			"#a78bfa",
		],
	};
}

export function resolveRouteAirports(input: {
	departure_airport?: string | null;
	arrival_airport?: string | null;
	departure_lat?: number | null;
	departure_lon?: number | null;
	arrival_lat?: number | null;
	arrival_lon?: number | null;
	hubIata?: string | null;
	airportsInStore: readonly AirportInfo[];
}): RouteAirportPoint[] {
	const out: RouteAirportPoint[] = [];
	const seen = new Set<string>();

	const add = (
		iata: string | null | undefined,
		role: RouteAirportRole,
		lat?: number | null,
		lon?: number | null,
	) => {
		const resolved = resolveAirportCoords(iata, lat, lon, input.airportsInStore);
		if (!resolved || seen.has(resolved.iata)) return;
		seen.add(resolved.iata);
		const fromStore = input.airportsInStore.find(
			(a) => normalizeIata(a.iata) === resolved.iata,
		);
		out.push({
			iata: resolved.iata,
			lat: resolved.lat,
			lon: resolved.lon,
			role,
			name: fromStore?.name,
		});
	};

	add(input.departure_airport, "dep", input.departure_lat, input.departure_lon);
	add(input.arrival_airport, "arr", input.arrival_lat, input.arrival_lon);
	if (input.hubIata) {
		add(input.hubIata, "hub");
	}
	return out;
}
