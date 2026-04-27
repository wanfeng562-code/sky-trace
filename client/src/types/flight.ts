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

// 天气信息（仅枢纽机场有数据，其余为 null）
export interface WeatherInfo {
	temp_c: number | null;
	humidity_pct: number | null;
	wind_speed_mps: number | null;
	wind_deg: number | null;
	description: string | null;
	visibility_m: number | null;
}

// 单航班详情（扩展自 FlightBrief）
export interface FlightDetail extends FlightBrief {
	departure_airport: string | null;
	arrival_airport: string | null;
	aircraft_type: string | null;
	status: string | null;
	departure_weather: WeatherInfo | null;
	arrival_weather: WeatherInfo | null;
}

// 列表接口筛选参数
export interface FlightQueryParams {
	callsign?: string;
	bbox?: string; // "lon_min,lat_min,lon_max,lat_max"
	page?: number;
	page_size?: number;
}

// 统计摘要
export interface FlightStats {
	total: number;
	airborne: number;
	on_ground: number;
	updated_at: string;
}
