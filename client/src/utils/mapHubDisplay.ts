import { formatAirportDisplay } from "../data/airportDisplay";
import type { AirportInfo, FlightBrief } from "../types/flight";

function isDisplayableHub(a: AirportInfo): boolean {
	const pointType =
		a.point_type ?? (a.iata?.startsWith("GRD_") ? "grid" : "hub");
	if (pointType === "grid") return false;
	return a.is_hub === true || pointType === "hub";
}

export function countFlightsPerAirport(
	flights: FlightBrief[],
): Map<string, number> {
	const counts = new Map<string, number>();
	for (const f of flights) {
		if (f.departure_airport) {
			const k = f.departure_airport;
			counts.set(k, (counts.get(k) ?? 0) + 1);
		}
		if (f.arrival_airport) {
			const k = f.arrival_airport;
			counts.set(k, (counts.get(k) ?? 0) + 1);
		}
	}
	return counts;
}

/** 按 zoom + 当前航班量分级，远 zoom 不挤满全部枢纽 */
export function filterAirportsForZoom(
	airports: AirportInfo[],
	flights: FlightBrief[],
	zoom: number,
): AirportInfo[] {
	const hubs = airports.filter(isDisplayableHub);
	if (zoom >= 8) return hubs;

	const counts = countFlightsPerAirport(flights);
	const ranked = hubs
		.map((a) => ({ a, c: counts.get(a.iata) ?? 0 }))
		.sort((x, y) => y.c - x.c || x.a.iata.localeCompare(y.a.iata));

	// 初进约 5000km（zoom 3–4）略多显示枢纽，避免远视角过空
	const limit =
		zoom < 3
			? 18
			: zoom < 4
				? 32
				: zoom < 5
					? 52
					: zoom < 6
						? 72
						: zoom < 7
							? 96
							: hubs.length;

	return ranked.slice(0, limit).map((x) => x.a);
}

export function hubTierForAirport(
	iata: string,
	airports: AirportInfo[],
	flights: FlightBrief[],
): 1 | 2 | 3 {
	const hubs = airports.filter(isDisplayableHub);
	const counts = countFlightsPerAirport(flights);
	return assignHubTier(iata, hubs, counts);
}

function assignHubTier(
	iata: string,
	visible: AirportInfo[],
	counts: Map<string, number>,
): 1 | 2 | 3 {
	const sorted = visible
		.map((a) => ({ iata: a.iata, c: counts.get(a.iata) ?? 0 }))
		.sort((x, y) => y.c - x.c);
	const idx = sorted.findIndex((x) => x.iata === iata);
	if (idx < 0) return 3;
	const pct = idx / Math.max(sorted.length, 1);
	if (pct < 0.22) return 1;
	if (pct < 0.55) return 2;
	return 3;
}

/** 枢纽 IATA 标注专用点集（与圆点图层解耦，避免 symbol 不渲染） */
export function toHubLabelGeoJson(
	airports: AirportInfo[],
	flights: FlightBrief[],
	zoom: number,
): GeoJSON.FeatureCollection<GeoJSON.Point> {
	const visible = filterAirportsForZoom(airports, flights, zoom);
	return {
		type: "FeatureCollection",
		features: visible.map((a) => ({
			type: "Feature",
			geometry: { type: "Point", coordinates: [a.lon, a.lat] },
			properties: { iata: a.iata },
		})),
	};
}

export function toHubAirportGeoJson(
	airports: AirportInfo[],
	flights: FlightBrief[],
	zoom: number,
): GeoJSON.FeatureCollection<GeoJSON.Point> {
	const visible = filterAirportsForZoom(airports, flights, zoom);
	const counts = countFlightsPerAirport(flights);

	return {
		type: "FeatureCollection",
		features: visible.map((a) => {
			const pointType =
				a.point_type ?? (a.iata?.startsWith("GRD_") ? "grid" : "hub");
			return {
				type: "Feature",
				geometry: { type: "Point", coordinates: [a.lon, a.lat] },
				properties: {
					iata: a.iata,
					name: formatAirportDisplay(a).nameZh || a.name,
					point_type: pointType,
					is_hub: a.is_hub ?? pointType === "hub",
					hub_tier: assignHubTier(a.iata, visible, counts),
					flight_count: counts.get(a.iata) ?? 0,
				},
			};
		}),
	};
}
