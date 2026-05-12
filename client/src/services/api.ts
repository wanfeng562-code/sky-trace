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
	timeout: 10000,
});

export async function fetchFlights(
	params?: FlightQueryParams,
): Promise<FlightBrief[]> {
	const response = await api.get<
		ApiResponse<{ total: number; items: FlightBrief[] }>
	>("/flights", { params });
	return response.data.data.items;
}

export async function fetchFlightDetail(
	flightId: string,
): Promise<FlightDetail> {
	const response = await api.get<
		ApiResponse<
			FlightDetail & {
				last_position?: Partial<FlightBrief> | null;
			}
		>
	>(`/flights/${flightId}`);
	const detail = response.data.data;
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
	const response = await api.get<ApiResponse<TrackPoint[]>>(
		`/flights/${flightId}/track`,
	);
	return response.data.data;
}

export async function fetchFlightStats(): Promise<FlightStats> {
	const response = await api.get<ApiResponse<FlightStats>>(
		"/flights/summary/stats",
	);
	return response.data.data;
}

export async function fetchAirports(): Promise<AirportInfo[]> {
	const response = await api.get<ApiResponse<AirportInfo[]>>("/airports");
	return response.data.data;
}

export async function fetchPlaybackFrames(
	start: string,
	end: string,
	interval = 300,
): Promise<PlaybackData> {
	const response = await api.get<ApiResponse<PlaybackData>>("/playback", {
		params: { start, end, interval },
	});
	return response.data.data;
}

export async function fetchAirQuality(): Promise<AirQualityHub[]> {
	const response = await api.get<ApiResponse<Record<string, unknown>>>(
		"/datahub/air_quality",
	);
	const raw = response.data.data as Record<string, unknown>;
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
	const response = await api.get<ApiResponse<ScheduleEntry[]>>(
		`/airports/${iata}/schedules`,
		{ params: { direction } },
	);
	return response.data.data ?? [];
}
