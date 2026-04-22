export interface FlightBrief {
	flight_id: string;
	callsign?: string;
	lat: number;
	lon: number;
	heading?: number;
	speed_kts?: number;
	altitude_ft?: number;
	updated_at: string;
}

export interface TrackPoint {
	ts: string;
	lat: number;
	lon: number;
	altitude_ft?: number;
	speed_kts?: number;
}

export interface ApiResponse<T> {
	code: number;
	message: string;
	data: T;
}
