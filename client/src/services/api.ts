import axios from "axios";

import {
	AIRPORTS_CACHE_TTL_MS,
	PLAYBACK_CACHE_TTL_MS,
	readPersistentCache,
	writePersistentCache,
} from "./persistentCache";

import type {
	ApiResponse,
	AirportInfo,
	AirQualityHub,
	FlightBrief,
	FlightDetail,
	FlightQueryParams,
	FlightStats,
	PlaybackData,
	ScheduleEntry,
	TrackPoint,
	WeatherGridCell,
} from "../types/flight";

const api = axios.create({
	baseURL: import.meta.env.VITE_API_BASE_URL,
	timeout: 15000,
});

type GetPolicy = {
	ttlMs?: number;
	retries?: number;
	timeoutMs?: number;
};

type CacheEntry<T> = {
	expiresAt: number;
	data: T;
};

const inFlightGetRequests = new Map<string, Promise<unknown>>();
const getResponseCache = new Map<string, CacheEntry<unknown>>();

function stableStringify(value: unknown): string {
	if (value === null || typeof value !== "object") {
		return JSON.stringify(value);
	}
	if (Array.isArray(value)) {
		return `[${value.map((v) => stableStringify(v)).join(",")}]`;
	}
	const obj = value as Record<string, unknown>;
	const keys = Object.keys(obj).sort();
	return `{${keys
		.map((k) => `${JSON.stringify(k)}:${stableStringify(obj[k])}`)
		.join(",")}}`;
}

function buildGetRequestKey(url: string, params?: unknown): string {
	return `${url}?${stableStringify(params ?? {})}`;
}

function shouldRetryGet(error: unknown): boolean {
	if (!axios.isAxiosError(error)) return false;
	const status = error.response?.status;
	if (!status) return true;
	return status === 408 || status === 425 || status === 429 || status >= 500;
}

async function sleep(ms: number): Promise<void> {
	await new Promise((resolve) => setTimeout(resolve, ms));
}

async function getWithPolicy<T>(
	url: string,
	params?: unknown,
	policy: GetPolicy = {},
): Promise<T> {
	const ttlMs = policy.ttlMs ?? 0;
	const retries = policy.retries ?? 0;
	const key = buildGetRequestKey(url, params);
	const now = Date.now();

	if (ttlMs > 0) {
		const cached = getResponseCache.get(key);
		if (cached && cached.expiresAt > now) {
			return cached.data as T;
		}
	}

	const inFlight = inFlightGetRequests.get(key);
	if (inFlight) {
		return inFlight as Promise<T>;
	}

	const reqPromise = (async () => {
		let attempt = 0;
		while (true) {
			try {
				const response = await api.get<ApiResponse<T>>(url, {
					params,
					timeout: policy.timeoutMs,
				});
				const data = response.data.data;
				if (ttlMs > 0) {
					getResponseCache.set(key, {
						expiresAt: Date.now() + ttlMs,
						data,
					});
				}
				return data;
			} catch (error) {
				if (attempt >= retries || !shouldRetryGet(error)) {
					throw error;
				}
				const backoffMs = 150 * 2 ** attempt;
				attempt += 1;
				await sleep(backoffMs);
			}
		}
	})();

	inFlightGetRequests.set(key, reqPromise);
	try {
		return await reqPromise;
	} finally {
		inFlightGetRequests.delete(key);
	}
}

export async function fetchFlights(
	params?: FlightQueryParams,
): Promise<FlightBrief[]> {
	const pageSize = 2000;
	let page = 1;
	const all: FlightBrief[] = [];
	let total = Number.POSITIVE_INFINITY;

	const listCacheKey = `flights:list:${stableStringify(params ?? {})}`;
	if (!params?.callsign) {
		const cachedList = readPersistentCache<FlightBrief[]>(listCacheKey);
		if (cachedList?.length) return cachedList;
	}

	while (all.length < total) {
		const data = await getWithPolicy<{ total: number; items: FlightBrief[] }>(
			"/flights",
			{ ...params, page, page_size: pageSize },
			{ retries: 1, timeoutMs: 60000 },
		);
		total = data.total;
		all.push(...data.items);
		if (all.length >= total || !data.items.length) break;
		page += 1;
		if (page > 50) break;
	}

	if (!params?.callsign && all.length) {
		writePersistentCache(listCacheKey, all, 15_000);
	}
	return all;
}

export async function fetchFlightDetail(
	flightId: string,
): Promise<FlightDetail> {
	const detail = await getWithPolicy<
		FlightDetail & {
			last_position?: Partial<FlightBrief> | null;
		}
	>(`/flights/${flightId}`, undefined, {
		ttlMs: 5000,
		retries: 1,
		timeoutMs: 20000,
	});
	const last = detail.last_position ?? null;

	if (!last) {
		return detail;
	}

	const lat = detail.lat ?? last.lat;
	const lon = detail.lon ?? last.lon;
	const hasPos =
		lat != null &&
		lon != null &&
		Number.isFinite(lat) &&
		Number.isFinite(lon) &&
		Math.abs(lat) <= 90 &&
		Math.abs(lon) <= 180;

	if (!hasPos) {
		return detail;
	}

	return {
		...detail,
		lat,
		lon,
		heading: detail.heading ?? last.heading,
		speed_kts: detail.speed_kts ?? last.speed_kts,
		altitude_ft: detail.altitude_ft ?? last.altitude_ft,
		updated_at: detail.updated_at ?? last.updated_at ?? "",
	};
}

export async function fetchFlightTrack(
	flightId: string,
): Promise<TrackPoint[]> {
	return getWithPolicy<TrackPoint[]>(`/flights/${flightId}/track`, undefined, {
		retries: 1,
		timeoutMs: 20000,
	});
}

export async function fetchFlightStats(): Promise<FlightStats> {
	return getWithPolicy<FlightStats>("/flights/summary/stats", undefined, {
		ttlMs: 30000,
		retries: 1,
		timeoutMs: 15000,
	});
}

export async function fetchAirports(
	force = false,
	opts?: { hubsOnly?: boolean },
): Promise<AirportInfo[]> {
	const hubsOnly = opts?.hubsOnly !== false;
	const persistKey = `airports:${hubsOnly ? "hubs" : "all"}`;
	if (!force) {
		const persisted = readPersistentCache<AirportInfo[]>(persistKey);
		if (persisted?.length) return persisted;
	}
	const data = await getWithPolicy<AirportInfo[]>(
		"/airports",
		{ hubs_only: hubsOnly },
		{
			ttlMs: force ? 0 : 30 * 60 * 1000,
			retries: 1,
			timeoutMs: hubsOnly ? 20000 : 120000,
		},
	);
	if (data.length) {
		writePersistentCache(persistKey, data, AIRPORTS_CACHE_TTL_MS);
	}
	return data;
}

export async function fetchWeatherGrid(force = false): Promise<WeatherGridCell[]> {
	return getWithPolicy<WeatherGridCell[]>("/weather-grid", undefined, {
		ttlMs: force ? 0 : 60 * 1000,
		retries: 1,
		timeoutMs: 15000,
	});
}

export async function fetchPlaybackFrames(
	start: string,
	end: string,
	interval = 300,
): Promise<PlaybackData> {
	const persistKey = `playback:${start}|${end}|${interval}`;
	const persisted = readPersistentCache<PlaybackData>(persistKey);
	if (persisted?.frames) return persisted;
	const data = await getWithPolicy<PlaybackData>(
		"/playback",
		{ start, end, interval },
		{ ttlMs: PLAYBACK_CACHE_TTL_MS,
			retries: 1,
			timeoutMs: 30000,
		},
	);
	if (data.frames?.length) {
		writePersistentCache(persistKey, data, PLAYBACK_CACHE_TTL_MS);
	}
	return data;
}

export async function fetchDatahubWeather(
	force = false,
): Promise<Record<string, unknown>> {
	return getWithPolicy<Record<string, unknown>>(
		"/datahub/weather",
		undefined,
		{
			ttlMs: force ? 0 : 60 * 1000,
			retries: 1,
			timeoutMs: 15000,
		},
	);
}

export async function fetchAirQuality(): Promise<AirQualityHub[]> {
	const raw = await getWithPolicy<Record<string, unknown>>(
		"/datahub/air_quality",
		undefined,
		{ ttlMs: 60000, retries: 1, timeoutMs: 15000 },
	);
	// Backend returns dict: { IATA: { aqi, lat, lon, components, ... } }
	return Object.entries(raw).map(([iata, v]) => {
		const entry = v as Record<string, unknown>;
		return {
			iata,
			lat: (entry.lat as number) ?? 0,
			lon: (entry.lon as number) ?? 0,
			aqi: (entry.aqi as number) ?? 0,
			pm2_5: (entry.components as Record<string, number> | undefined)?.pm2_5,
			pm10: (entry.components as Record<string, number> | undefined)?.pm10,
		};
	});
}

export type PlaceNameRecord = {
	cache_key: string;
	name_zh: string;
	name_en?: string | null;
	source_text?: string | null;
};

export async function fetchPlaceNames(
	keys: string[],
): Promise<PlaceNameRecord[]> {
	if (!keys.length) return [];
	const data = await getWithPolicy<{ items: PlaceNameRecord[] }>(
		"/places/names",
		{ keys: keys.join(",") },
		{ ttlMs: 60_000, retries: 1, timeoutMs: 15000 },
	);
	return data.items ?? [];
}

export async function upsertPlaceNames(
	items: PlaceNameRecord[],
): Promise<number> {
	if (!items.length) return 0;
	const data = await api.put<ApiResponse<{ upserted: number }>>(
		"/places/names",
		{ items },
	);
	return data.data.data?.upserted ?? 0;
}

export async function fetchAirportSchedules(
	iata: string,
	direction = "dep",
): Promise<ScheduleEntry[]> {
	return (
		(await getWithPolicy<ScheduleEntry[]>(
			`/airports/${iata}/schedules`,
			{ direction },
			{ ttlMs: 15000, retries: 1, timeoutMs: 15000 },
		)) ?? []
	);
}
