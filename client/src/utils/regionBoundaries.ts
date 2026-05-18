import { resolveGeoBBox, type GeoBBox } from "../data/geoHierarchy";
import { COUNTRIES } from "../data/countries";
import {
	BOUNDARY_CACHE_TTL_MS,
	readPersistentCache,
	writePersistentCache,
} from "../services/persistentCache";

/** 中国省级行政区划 adcode（DataV / 阿里云区划） */
const CN_PROVINCE_ADCODE: Record<string, string> = {
	BJ: "110000",
	TJ: "120000",
	HE: "130000",
	SX: "140000",
	NM: "150000",
	LN: "210000",
	JL: "220000",
	HL: "230000",
	SH: "310000",
	JS: "320000",
	ZJ: "330000",
	AH: "340000",
	FJ: "350000",
	JX: "360000",
	SD: "370000",
	HA: "410000",
	HB: "420000",
	HN: "430000",
	GD: "440000",
	GX: "450000",
	HI: "460000",
	CQ: "500000",
	SC: "510000",
	GZ: "520000",
	YN: "530000",
	XZ: "540000",
	SN: "610000",
	GS: "620000",
	QH: "630000",
	NX: "640000",
	XJ: "650000",
	MO: "820000",
};

/** 重点城市 adcode（与 geoNested 中 code 对应） */
const CN_CITY_ADCODE: Record<string, string> = {
	"BJ-URBAN": "110100",
	"TJ-CITY": "120100",
	"PVG-AREA": "310115",
	"SHA-AREA": "310100",
	"CAN-AREA": "440100",
	"SZX-AREA": "440300",
	"CTU-AREA": "510100",
	"WUH-CITY": "420100",
	"XIY-CITY": "610100",
};

const CN_DISTRICT_ADCODE: Record<string, string> = {
	"BJ-CY": "110105",
	"BJ-HD": "110108",
	"BJ-DC": "110101",
	"BJ-FT": "110106",
	"SH-PD-CORE": "310115",
	"GZ-TH": "440106",
	"GZ-BY": "440111",
	"SZ-FT": "440304",
	"SZ-NS": "440305",
};

const US_STATE_NAMES: Record<string, string> = {
	AL: "Alabama",
	AK: "Alaska",
	AZ: "Arizona",
	AR: "Arkansas",
	CA: "California",
	CO: "Colorado",
	CT: "Connecticut",
	DE: "Delaware",
	FL: "Florida",
	GA: "Georgia",
	HI: "Hawaii",
	ID: "Idaho",
	IL: "Illinois",
	IN: "Indiana",
	IA: "Iowa",
	KS: "Kansas",
	KY: "Kentucky",
	LA: "Louisiana",
	ME: "Maine",
	MD: "Maryland",
	MA: "Massachusetts",
	MI: "Michigan",
	MN: "Minnesota",
	MS: "Mississippi",
	MO: "Missouri",
	MT: "Montana",
	NE: "Nebraska",
	NV: "Nevada",
	NH: "New Hampshire",
	NJ: "New Jersey",
	NM: "New Mexico",
	NY: "New York",
	NC: "North Carolina",
	ND: "North Dakota",
	OH: "Ohio",
	OK: "Oklahoma",
	OR: "Oregon",
	PA: "Pennsylvania",
	RI: "Rhode Island",
	SC: "South Carolina",
	SD: "South Dakota",
	TN: "Tennessee",
	TX: "Texas",
	UT: "Utah",
	VT: "Vermont",
	VA: "Virginia",
	WA: "Washington",
	WV: "West Virginia",
	WI: "Wisconsin",
	WY: "Wyoming",
};

const boundaryCache = new Map<string, GeoJSON.Geometry>();

function cacheKey(parts: string[]): string {
	return parts.filter(Boolean).join("|");
}

function readBoundaryFromDisk(key: string): GeoJSON.Geometry | null {
	const raw = readPersistentCache<GeoJSON.Geometry>(`boundary:${key}`);
	return raw?.type ? raw : null;
}

function writeBoundaryToDisk(key: string, geom: GeoJSON.Geometry): void {
	try {
		writePersistentCache(`boundary:${key}`, geom, BOUNDARY_CACHE_TTL_MS);
	} catch {
		/* ignore */
	}
}

function rememberBoundary(key: string, geom: GeoJSON.Geometry): GeoJSON.Geometry {
	boundaryCache.set(key, geom);
	writeBoundaryToDisk(key, geom);
	return geom;
}

function recallBoundary(key: string): GeoJSON.Geometry | null {
	if (boundaryCache.has(key)) return boundaryCache.get(key)!;
	const disk = readBoundaryFromDisk(key);
	if (disk) {
		boundaryCache.set(key, disk);
		return disk;
	}
	return null;
}

function bboxToPolygon(bbox: GeoBBox): GeoJSON.Polygon {
	return {
		type: "Polygon",
		coordinates: [
			[
				[bbox.lonMin, bbox.latMin],
				[bbox.lonMax, bbox.latMin],
				[bbox.lonMax, bbox.latMax],
				[bbox.lonMin, bbox.latMax],
				[bbox.lonMin, bbox.latMin],
			],
		],
	};
}

function featureAdcode(feature: GeoJSON.Feature): string | null {
	const p = feature.properties;
	if (!p || typeof p !== "object") return null;
	const raw = (p as Record<string, unknown>).adcode ?? (p as Record<string, unknown>).code;
	if (raw == null) return null;
	return String(raw);
}

/** 判断 child 是否属于 parent 的下一级区划（国标 6 位 adcode） */
function isDescendantAdcode(parentAdcode: string, childAdcode: string): boolean {
	if (childAdcode === parentAdcode) return false;
	if (parentAdcode === "100000") {
		return childAdcode.length === 6 && childAdcode.endsWith("0000");
	}
	if (parentAdcode.endsWith("0000")) {
		return childAdcode.startsWith(parentAdcode.slice(0, 2));
	}
	if (parentAdcode.endsWith("00")) {
		return (
			childAdcode.startsWith(parentAdcode.slice(0, 4)) &&
			childAdcode.length >= 6
		);
	}
	return childAdcode.startsWith(parentAdcode);
}

function mergeFeaturesToMultiPolygon(
	features: GeoJSON.Feature[],
): GeoJSON.Polygon | GeoJSON.MultiPolygon | null {
	const polygons: GeoJSON.Position[][][] = [];
	for (const f of features) {
		const g = f.geometry;
		if (!g) continue;
		if (g.type === "Polygon") {
			polygons.push(g.coordinates);
		} else if (g.type === "MultiPolygon") {
			for (const p of g.coordinates) {
				polygons.push(p);
			}
		}
	}
	if (polygons.length === 0) return null;
	if (polygons.length === 1) {
		return { type: "Polygon", coordinates: polygons[0] };
	}
	return { type: "MultiPolygon", coordinates: polygons };
}

/**
 * DataV 常返回 FeatureCollection（子级区县/市罗列）。
 * 优先匹配与请求 adcode 一致的要素；否则合并所有直属子级，避免只取 features[0]。
 */
function normalizeGeometry(
	raw: GeoJSON.Feature | GeoJSON.FeatureCollection | GeoJSON.Geometry,
	expectedAdcode?: string,
): GeoJSON.Geometry | null {
	if (raw.type === "FeatureCollection") {
		const features = raw.features.filter((f) => f.geometry);
		if (!features.length) return null;

		if (expectedAdcode) {
			const exact = features.find(
				(f) => featureAdcode(f) === expectedAdcode,
			);
			if (exact?.geometry) return exact.geometry;

			const descendants = features.filter((f) => {
				const ad = featureAdcode(f);
				return ad != null && isDescendantAdcode(expectedAdcode, ad);
			});
			if (descendants.length > 0) {
				return mergeFeaturesToMultiPolygon(descendants);
			}
		}

		if (features.length === 1) return features[0].geometry ?? null;
		return mergeFeaturesToMultiPolygon(features);
	}
	if (raw.type === "Feature") {
		return raw.geometry ?? null;
	}
	if (
		raw.type === "Polygon" ||
		raw.type === "MultiPolygon" ||
		raw.type === "LineString" ||
		raw.type === "MultiLineString"
	) {
		return raw;
	}
	return null;
}

async function fetchDatavBoundary(adcode: string): Promise<GeoJSON.Geometry | null> {
	const key = `datav:v2:${adcode}`;
	const hit = recallBoundary(key);
	if (hit) return hit;

	try {
		const res = await fetch(
			`https://geo.datav.aliyun.com/areas_v3/bound/${adcode}_full.json`,
		);
		if (!res.ok) return null;
		const json = (await res.json()) as
			| GeoJSON.Feature
			| GeoJSON.FeatureCollection;
		const geom = normalizeGeometry(json, adcode);
		if (geom) return rememberBoundary(key, geom);
		return geom;
	} catch {
		return null;
	}
}

/** Natural Earth 按国拆分的 admin1（见 scripts/build_admin1_geo.py），动态加载 404 则回退 bbox */
const admin1FcCache = new Map<string, GeoJSON.FeatureCollection>();
const admin1Missing = new Set<string>();

function admin1Url(countryCode: string): string {
	return `/geo/${countryCode.toLowerCase()}-admin1.json`;
}

function hasSpecificSubArea(
	cityCode: string | null,
	districtCode: string | null,
): boolean {
	if (districtCode) return true;
	if (cityCode && !cityCode.endsWith("-ALL")) return true;
	return false;
}

function featureInBBox(
	feature: GeoJSON.Feature,
	bbox: GeoBBox,
): boolean {
	const p = feature.properties as Record<string, unknown> | undefined;
	const lat = p?.latitude;
	const lon = p?.longitude;
	if (typeof lat === "number" && typeof lon === "number") {
		return (
			lat >= bbox.latMin &&
			lat <= bbox.latMax &&
			lon >= bbox.lonMin &&
			lon <= bbox.lonMax
		);
	}
	const bb = bboxFromGeometry(feature.geometry!);
	if (!bb) return false;
	const [, latMin, , latMax] = bb;
	const [lonMin, , lonMax] = bb;
	return (
		latMax >= bbox.latMin &&
		latMin <= bbox.latMax &&
		lonMax >= bbox.lonMin &&
		lonMin <= bbox.lonMax
	);
}

async function loadAdmin1Fc(
	countryCode: string,
): Promise<GeoJSON.FeatureCollection | null> {
	if (admin1FcCache.has(countryCode)) return admin1FcCache.get(countryCode)!;
	if (admin1Missing.has(countryCode)) return null;
	try {
		const res = await fetch(admin1Url(countryCode));
		if (!res.ok) {
			admin1Missing.add(countryCode);
			return null;
		}
		const fc = (await res.json()) as GeoJSON.FeatureCollection;
		admin1FcCache.set(countryCode, fc);
		return fc;
	} catch {
		admin1Missing.add(countryCode);
		return null;
	}
}

async function fetchAdmin1ByRegionCode(
	countryCode: string,
	regionCode: string,
	bbox: GeoBBox | null,
): Promise<GeoJSON.Geometry | null> {
	const fc = await loadAdmin1Fc(countryCode);
	if (!fc) return null;

	const codeUp = regionCode.toUpperCase();
	const exact = fc.features.find((f) => {
		const iso = String(
			(f.properties as Record<string, unknown> | undefined)?.iso_3166_2 ??
				"",
		).toUpperCase();
		if (!iso) return false;
		if (iso === codeUp) return true;
		if (iso === `${countryCode}-${codeUp}`) return true;
		if (iso.endsWith(`-${codeUp}`)) return true;
		return false;
	});
	if (exact?.geometry) return exact.geometry;

	if (bbox) {
		const matched = fc.features.filter((f) => featureInBBox(f, bbox));
		return mergeFeaturesToMultiPolygon(matched);
	}
	return null;
}

async function fetchCountryAdmin1Outline(
	countryCode: string,
): Promise<GeoJSON.Geometry | null> {
	const fc = await loadAdmin1Fc(countryCode);
	if (!fc?.features.length) return null;
	return mergeFeaturesToMultiPolygon(fc.features);
}

let usStatesFc: GeoJSON.FeatureCollection | null = null;

async function loadUsStates(): Promise<GeoJSON.FeatureCollection> {
	if (usStatesFc) return usStatesFc;
	const res = await fetch("/geo/us-states.json");
	usStatesFc = (await res.json()) as GeoJSON.FeatureCollection;
	return usStatesFc;
}

async function fetchUsStateBoundary(
	stateCode: string,
): Promise<GeoJSON.Geometry | null> {
	const key = `us:${stateCode}`;
	if (boundaryCache.has(key)) return boundaryCache.get(key)!;

	const name = US_STATE_NAMES[stateCode];
	if (!name) return null;
	const fc = await loadUsStates();
	const feature = fc.features.find(
		(f) =>
			String(f.properties?.name ?? "").toLowerCase() === name.toLowerCase(),
	);
	const geom = feature?.geometry ?? null;
	if (geom) boundaryCache.set(key, geom);
	return geom;
}

function resolveCnAdcode(
	regionCode: string | null,
	cityCode: string | null,
	districtCode: string | null,
): string | null {
	if (districtCode && CN_DISTRICT_ADCODE[districtCode]) {
		return CN_DISTRICT_ADCODE[districtCode];
	}
	// 「全省/全市」占位项（如 BJ-ALL）→ 使用上一级边界
	if (cityCode && !cityCode.endsWith("-ALL") && CN_CITY_ADCODE[cityCode]) {
		return CN_CITY_ADCODE[cityCode];
	}
	if (regionCode && CN_PROVINCE_ADCODE[regionCode]) {
		return CN_PROVINCE_ADCODE[regionCode];
	}
	if (!regionCode && !cityCode && !districtCode) {
		return "100000";
	}
	return null;
}

/**
 * 按当前筛选层级解析真实区划边界；无矢量数据时回退为 bbox 矩形。
 */
export async function resolveRegionBoundaryGeometry(
	countryCode: string,
	regionCode: string | null,
	cityCode: string | null,
	districtCode: string | null,
): Promise<GeoJSON.Geometry> {
	const key = cacheKey([countryCode, regionCode, cityCode, districtCode]);
	const cached = recallBoundary(key);
	if (cached) return cached;

	const bbox = resolveGeoBBox(countryCode, regionCode, cityCode, districtCode);
	const specific = hasSpecificSubArea(cityCode, districtCode);

	let geom: GeoJSON.Geometry | null = null;

	if (countryCode === "CN") {
		const adcode = resolveCnAdcode(regionCode, cityCode, districtCode);
		if (specific && bbox && !adcode) {
			geom = bboxToPolygon(bbox);
		} else if (adcode) {
			geom = await fetchDatavBoundary(adcode);
		}
	} else if (countryCode === "US" && regionCode && !specific) {
		geom = await fetchAdmin1ByRegionCode(countryCode, regionCode, bbox);
		if (!geom) geom = await fetchUsStateBoundary(regionCode);
	} else if (regionCode && !specific) {
		geom = await fetchAdmin1ByRegionCode(countryCode, regionCode, bbox);
	} else if (!regionCode && !cityCode && !districtCode) {
		if (countryCode === "CN") {
			geom = await fetchDatavBoundary("100000");
		} else {
			geom = await fetchCountryAdmin1Outline(countryCode);
		}
	} else if (specific && bbox) {
		geom = await fetchAdmin1ByRegionCode(countryCode, regionCode ?? "", bbox);
	}

	if (!geom && bbox) {
		geom = bboxToPolygon(bbox);
	} else if (!geom) {
		const country = COUNTRIES.find((c) => c.code === countryCode);
		if (country) geom = bboxToPolygon(country);
	}

	const result =
		geom ??
		bboxToPolygon({ latMin: -85, latMax: 85, lonMin: -180, lonMax: 180 });
	return rememberBoundary(key, result);
}

export function geometryToFeature(geometry: GeoJSON.Geometry): GeoJSON.Feature {
	return {
		type: "Feature",
		properties: {},
		geometry,
	};
}

/** 从 Polygon / MultiPolygon 计算 fitBounds 用的 bbox */
export function bboxFromGeometry(
	geometry: GeoJSON.Geometry,
): GeoJSON.BBox | null {
	const coords: number[][] = [];

	function walk(g: GeoJSON.Geometry) {
		if (g.type === "Polygon") {
			for (const ring of g.coordinates) {
				for (const c of ring) coords.push(c);
			}
		} else if (g.type === "MultiPolygon") {
			for (const poly of g.coordinates) {
				for (const ring of poly) {
					for (const c of ring) coords.push(c);
				}
			}
		}
	}
	walk(geometry);
	if (!coords.length) return null;

	let lonMin = Infinity;
	let lonMax = -Infinity;
	let latMin = Infinity;
	let latMax = -Infinity;
	for (const [lon, lat] of coords) {
		lonMin = Math.min(lonMin, lon);
		lonMax = Math.max(lonMax, lon);
		latMin = Math.min(latMin, lat);
		latMax = Math.max(latMax, lat);
	}
	return [lonMin, latMin, lonMax, latMax];
}
