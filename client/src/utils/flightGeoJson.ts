import type { FlightBrief } from "../types/flight";

export type FlightPointFeature = GeoJSON.Feature<GeoJSON.Point>;

export type FlightGeoPatchResult = {
	geojson: GeoJSON.FeatureCollection<GeoJSON.Point>;
	index: Map<string, FlightPointFeature>;
	fleetChanged: boolean;
};

function flightProperties(flight: FlightBrief): GeoJSON.GeoJsonProperties {
	return {
		flight_id: flight.flight_id,
		callsign: flight.callsign ?? flight.flight_id,
		heading: flight.heading ?? null,
		speed_kts: flight.speed_kts ?? null,
		altitude_ft: flight.altitude_ft ?? null,
		departure_airport: flight.departure_airport ?? "",
		arrival_airport: flight.arrival_airport ?? "",
		updated_at: flight.updated_at,
	};
}

function createFlightFeature(flight: FlightBrief): FlightPointFeature {
	return {
		type: "Feature",
		id: flight.flight_id,
		geometry: {
			type: "Point",
			coordinates: [flight.lon, flight.lat],
		},
		properties: flightProperties(flight),
	};
}

/** Build or patch flight GeoJSON; reuse feature objects when only telemetry moves. */
export function patchFlightGeoJson(
	flights: FlightBrief[],
	prev: Map<string, FlightPointFeature> | null,
): FlightGeoPatchResult {
	const nextIndex = new Map<string, FlightPointFeature>();
	const nextIds = new Set<string>();
	let fleetChanged = !prev || prev.size !== flights.length;

	for (const flight of flights) {
		nextIds.add(flight.flight_id);
		let feat = prev?.get(flight.flight_id);
		if (!feat) {
			fleetChanged = true;
			feat = createFlightFeature(flight);
		} else {
			const [lon, lat] = feat.geometry.coordinates;
			if (lon !== flight.lon || lat !== flight.lat) {
				feat.geometry.coordinates[0] = flight.lon;
				feat.geometry.coordinates[1] = flight.lat;
			}
			const props = flightProperties(flight);
			const p = feat.properties as Record<string, unknown>;
			for (const key of Object.keys(props ?? {})) {
				if (p[key] !== (props as Record<string, unknown>)[key]) {
					p[key] = (props as Record<string, unknown>)[key];
				}
			}
		}
		nextIndex.set(flight.flight_id, feat);
	}

	if (!fleetChanged && prev) {
		for (const id of prev.keys()) {
			if (!nextIds.has(id)) {
				fleetChanged = true;
				break;
			}
		}
	}

	return {
		geojson: {
			type: "FeatureCollection",
			features: [...nextIndex.values()],
		},
		index: nextIndex,
		fleetChanged,
	};
}
