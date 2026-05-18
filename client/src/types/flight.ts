export interface FlightBrief {
	flight_id: string;
	callsign?: string;
	lat: number;
	lon: number;
	heading?: number;
	speed_kts?: number;
	altitude_ft?: number;
	aircraft_category?: number;
	departure_airport?: string;
	arrival_airport?: string;
	airline_iata?: string;
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
	departure_airport_zh?: string | null;
	arrival_airport_zh?: string | null;
	departure_lat?: number | null;
	departure_lon?: number | null;
	arrival_lat?: number | null;
	arrival_lon?: number | null;
	aircraft_type: string | null;
	status: string | null;
	dep_time?: string;
	arr_time?: string;
	airline_iata?: string;
	departure_weather: WeatherInfo | null;
	arrival_weather: WeatherInfo | null;
	current_weather: WeatherInfo | null;
}

// 历史回放
export interface PlaybackFlightPoint {
	id: string;
	lat: number;
	lon: number;
	alt: number | null;
	spd: number | null;
	hdg: number | null;
	cat: number | null;
	cs: string | null;
	/** 出发机场 IATA（快照写入时附带） */
	dep?: string | null;
	/** 到达机场 IATA */
	arr?: string | null;
}

export interface PlaybackFrame {
	ts: string;
	flights: PlaybackFlightPoint[];
}

export interface PlaybackData {
	start: string;
	end: string;
	interval_seconds: number;
	total_frames: number;
	frames: PlaybackFrame[];
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
	on_ground_count: number;
	airborne_count: number;
	by_source: Record<string, number>;
	by_altitude_band: Record<string, number>;
	by_speed_band: Record<string, number>;
	top_callsign_prefixes: { prefix: string; count: number }[];
}

// 枢纽机场信息
export interface AirportInfo {
	iata: string;
	name: string;
	city?: string;
	country?: string;
	lat: number;
	lon: number;
	is_hub?: boolean;
	point_type?: "hub" | "airport" | "grid" | "weather";
	cell_min_lat?: number;
	cell_min_lon?: number;
	cell_max_lat?: number;
	cell_max_lon?: number;
}

/** 5°×5° 天气网格单元（由后端根据活跃航班与天气缓存计算） */
export interface WeatherGridCell {
	id: string;
	cell_min_lat: number;
	cell_min_lon: number;
	cell_max_lat: number;
	cell_max_lon: number;
	center_lat: number;
	center_lon: number;
	flight_count: number;
	has_weather: boolean;
	temperature_c?: number | null;
	description?: string | null;
}

// 空气质量
export interface AirQualityHub {
	iata: string;
	lat: number;
	lon: number;
	aqi: number;
	pm2_5?: number;
	pm10?: number;
}

// 机场时刻表
export interface ScheduleEntry {
	flight_iata?: string;
	dep_iata?: string;
	arr_iata?: string;
	dep_time?: string;
	arr_time?: string;
	status?: string;
	airline_iata?: string;
}
