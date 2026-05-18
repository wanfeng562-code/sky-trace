import type {
	PlaybackFlightPoint,
	PlaybackFrame,
	TrackPoint,
} from "../types/flight";

/** 时段内曾出现在快照中的航班（并集，非某一时刻） */
export interface PlaybackCatalogFlight {
	id: string;
	callsign: string;
	departure_airport: string | null;
	arrival_airport: string | null;
	/** 首次出现在快照中的时间 */
	first_seen: string;
	/** 末次出现在快照中的时间 */
	last_seen: string;
	/** 出现的帧数 */
	appear_frames: number;
}

/**
 * 从已加载的回放帧构建航班目录。
 * 列表含义：在 [start, end] 时段内至少出现过一次的航班（与 FR24 单航班回放入口一致）。
 */
export function buildPlaybackCatalog(frames: readonly PlaybackFrame[]): PlaybackCatalogFlight[] {
	const map = new Map<string, PlaybackCatalogFlight>();

	for (const frame of frames) {
		for (const f of frame.flights) {
			const existing = map.get(f.id);
			if (!existing) {
				map.set(f.id, {
					id: f.id,
					callsign: (f.cs ?? f.id).trim() || f.id,
					departure_airport: f.dep ?? null,
					arrival_airport: f.arr ?? null,
					first_seen: frame.ts,
					last_seen: frame.ts,
					appear_frames: 1,
				});
				continue;
			}
			existing.last_seen = frame.ts;
			existing.appear_frames += 1;
			if (f.cs?.trim()) existing.callsign = f.cs.trim();
			if (f.dep) existing.departure_airport = f.dep;
			if (f.arr) existing.arrival_airport = f.arr;
		}
	}

	return [...map.values()].sort((a, b) =>
		a.callsign.localeCompare(b.callsign, undefined, { sensitivity: "base" }),
	);
}

export function filterCatalog(
	list: readonly PlaybackCatalogFlight[],
	keyword: string,
): PlaybackCatalogFlight[] {
	const q = keyword.trim().toLowerCase();
	if (!q) return [...list];
	return list.filter((f) => {
		const cs = f.callsign.toLowerCase();
		const dep = (f.departure_airport ?? "").toLowerCase();
		const arr = (f.arrival_airport ?? "").toLowerCase();
		return (
			cs.includes(q) ||
			f.id.toLowerCase().includes(q) ||
			dep.includes(q) ||
			arr.includes(q)
		);
	});
}

/** 从快照帧提取某航班截至 frameIdx 的轨迹点（用于单航班回放着色轨迹） */
export function buildPlaybackFlightTrack(
	frames: readonly PlaybackFrame[],
	flightId: string,
	upToFrameIdx?: number,
): TrackPoint[] {
	const limit =
		upToFrameIdx == null
			? frames.length - 1
			: Math.min(upToFrameIdx, frames.length - 1);
	const points: TrackPoint[] = [];
	for (let i = 0; i <= limit; i++) {
		const frame = frames[i];
		if (!frame) continue;
		const f = frame.flights.find((x) => x.id === flightId);
		if (!f) continue;
		points.push({
			ts: frame.ts,
			lat: f.lat,
			lon: f.lon,
			altitude_ft: f.alt ?? undefined,
			speed_kts: f.spd ?? undefined,
		});
	}
	return points;
}

/** 当前帧要绘制的飞机（全局 / 单航班） */
export function flightsForPlaybackFrame(
	frame: PlaybackFrame | undefined,
	mode: "global" | "single",
	focusFlightId: string | null,
): PlaybackFlightPoint[] {
	if (!frame) return [];
	if (mode !== "single" || !focusFlightId) return frame.flights;
	return frame.flights.filter((f) => f.id === focusFlightId);
}
