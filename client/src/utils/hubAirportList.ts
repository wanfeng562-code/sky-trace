import type { AirportInfo, FlightBrief } from "../types/flight";
import { airportsMatch } from "./flightTrackMap";
import { hubTierForAirport, countFlightsPerAirport } from "./mapHubDisplay";

function isDisplayableHub(a: AirportInfo): boolean {
	const pointType =
		a.point_type ?? (a.iata?.startsWith("GRD_") ? "grid" : "hub");
	if (pointType === "grid") return false;
	return a.is_hub === true || pointType === "hub";
}

export interface HubAirportSummary {
	airport: AirportInfo;
	hubTier: 1 | 2 | 3;
	flightCount: number;
	departures: FlightBrief[];
	arrivals: FlightBrief[];
	relatedFlights: FlightBrief[];
	airborneCount: number;
	groundCount: number;
}

export function buildHubAirportSummaries(
	airports: AirportInfo[],
	flights: FlightBrief[],
): HubAirportSummary[] {
	const hubs = airports.filter(isDisplayableHub);
	const counts = countFlightsPerAirport(flights);

	return hubs
		.map((airport) => {
			const iata = airport.iata;
			const departures = flights.filter((f) =>
				airportsMatch(f.departure_airport, iata),
			);
			const arrivals = flights.filter((f) =>
				airportsMatch(f.arrival_airport, iata),
			);
			const seen = new Set<string>();
			const relatedFlights: FlightBrief[] = [];
			for (const f of [...departures, ...arrivals]) {
				if (seen.has(f.flight_id)) continue;
				seen.add(f.flight_id);
				relatedFlights.push(f);
			}
			const airborneCount = relatedFlights.filter(
				(f) => (f.altitude_ft ?? 0) > 100,
			).length;
			return {
				airport,
				hubTier: hubTierForAirport(iata, airports, flights),
				flightCount: counts.get(iata) ?? 0,
				departures,
				arrivals,
				relatedFlights,
				airborneCount,
				groundCount: relatedFlights.length - airborneCount,
			};
		})
		.sort(
			(a, b) =>
				b.flightCount - a.flightCount ||
				a.airport.iata.localeCompare(b.airport.iata),
		);
}
