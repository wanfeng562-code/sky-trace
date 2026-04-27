import axios from "axios";

import type {
	ApiResponse,
	AirportInfo,
	FlightBrief,
	FlightDetail,
	FlightQueryParams,
	FlightStats,
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
