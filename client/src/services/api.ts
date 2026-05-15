import axios from "axios";

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
	const data = await getWithPolicy<{ total: number; items: FlightBrief[] }>(
		"/flights",
		params,
		{ retries: 1, timeoutMs: 18000 },
	);
	return data.items;
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

	return {
		...detail,
		lat: detail.lat ?? last.lat ?? 0,
		lon: detail.lon ?? last.lon ?? 0,
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

export async function fetchAirports(): Promise<AirportInfo[]> {
	return getWithPolicy<AirportInfo[]>("/airports", undefined, {
		ttlMs: 30 * 60 * 1000,
		retries: 1,
		timeoutMs: 15000,
	});
}

export async function fetchPlaybackFrames(
	start: string,
	end: string,
	interval = 300,
): Promise<PlaybackData> {
	return getWithPolicy<PlaybackData>(
		"/playback",
		{ start, end, interval },
		{ retries: 1, timeoutMs: 30000 },
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
