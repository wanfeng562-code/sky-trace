import axios from "axios";

import type { ApiResponse, FlightBrief, TrackPoint } from "../types/flight";

const api = axios.create({
	baseURL: import.meta.env.VITE_API_BASE_URL,
	timeout: 10000,
});

export async function fetchFlights(): Promise<FlightBrief[]> {
	// TODO: Add query params for viewport filtering and pagination.
	const response =
		await api.get<ApiResponse<{ total: number; items: FlightBrief[] }>>(
			"/flights",
		);
	return response.data.data.items;
}

export async function fetchFlightTrack(flightId: string): Promise<TrackPoint[]> {
	const response = await api.get<ApiResponse<TrackPoint[]>>(
		`/flights/${flightId}/track`,
	);
	return response.data.data;
}
