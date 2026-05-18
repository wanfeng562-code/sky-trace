import type { PlaybackFlightPoint } from "../types/flight";

export type TrailFlightPoint = Pick<
	PlaybackFlightPoint,
	"id" | "lat" | "lon" | "alt"
>;

export type PlaybackTrailState = {
	lastFrameIdx: number;
	features: Map<string, GeoJSON.Feature<GeoJSON.LineString>>;
};

export function createPlaybackTrailState(): PlaybackTrailState {
	return { lastFrameIdx: -1, features: new Map() };
}

export function resetPlaybackTrailState(state: PlaybackTrailState): void {
	state.lastFrameIdx = -1;
	state.features.clear();
}

function trimCoords(coords: [number, number][], maxLen: number): void {
	while (coords.length > maxLen) {
		coords.shift();
	}
}

function rebuildTrail(
	state: PlaybackTrailState,
	frameIdx: number,
	trailLength: number,
	flightsAtFrame: (idx: number) => TrailFlightPoint[],
): GeoJSON.FeatureCollection<GeoJSON.LineString> {
	state.features.clear();
	const histStart = Math.max(0, frameIdx - trailLength + 1);
	const frameMaps: Array<Map<string, [number, number]>> = [];
	for (let i = histStart; i <= frameIdx; i++) {
		const fm = new Map<string, [number, number]>();
		for (const f of flightsAtFrame(i)) {
			fm.set(f.id, [f.lon, f.lat]);
		}
		frameMaps.push(fm);
	}
	const currentFlights = flightsAtFrame(frameIdx);
	for (const flight of currentFlights) {
		const coords: [number, number][] = [];
		for (const fm of frameMaps) {
			const pos = fm.get(flight.id);
			if (pos) coords.push(pos);
		}
		if (coords.length >= 2) {
			state.features.set(flight.id, {
				type: "Feature",
				properties: { altitude_ft: flight.alt ?? 0 },
				geometry: { type: "LineString", coordinates: coords },
			});
		}
	}
	state.lastFrameIdx = frameIdx;
	return collectionFromState(state);
}

function collectionFromState(
	state: PlaybackTrailState,
): GeoJSON.FeatureCollection<GeoJSON.LineString> {
	return {
		type: "FeatureCollection",
		features: [...state.features.values()],
	};
}

/**
 * Incrementally update fleet trails when advancing one frame; full rebuild on seek/jump.
 */
export function updatePlaybackTrailGeoJson(
	state: PlaybackTrailState,
	frameIdx: number,
	trailLength: number,
	flightsAtFrame: (idx: number) => TrailFlightPoint[],
	opts?: { singleMode: boolean },
): GeoJSON.FeatureCollection<GeoJSON.LineString> {
	if (opts?.singleMode) {
		state.features.clear();
		state.lastFrameIdx = frameIdx;
		return { type: "FeatureCollection", features: [] };
	}

	const step = frameIdx - state.lastFrameIdx;
	if (step === 1 && state.lastFrameIdx >= 0) {
		const currentFlights = flightsAtFrame(frameIdx);
		const currentIds = new Set<string>();
		for (const flight of currentFlights) {
			currentIds.add(flight.id);
			let feat = state.features.get(flight.id);
			if (!feat) {
				feat = {
					type: "Feature",
					properties: { altitude_ft: flight.alt ?? 0 },
					geometry: { type: "LineString", coordinates: [] },
				};
				state.features.set(flight.id, feat);
			}
			const coords = feat.geometry.coordinates as [number, number][];
			const last = coords[coords.length - 1];
			if (!last || last[0] !== flight.lon || last[1] !== flight.lat) {
				coords.push([flight.lon, flight.lat]);
			}
			trimCoords(coords, trailLength);
			(feat.properties as { altitude_ft: number }).altitude_ft =
				flight.alt ?? 0;
		}
		for (const id of [...state.features.keys()]) {
			if (!currentIds.has(id)) {
				state.features.delete(id);
			}
		}
		state.lastFrameIdx = frameIdx;
		return collectionFromState(state);
	}

	return rebuildTrail(state, frameIdx, trailLength, flightsAtFrame);
}
