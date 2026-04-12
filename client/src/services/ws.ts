import type { FlightBrief } from "../types/flight";

export type SnapshotHandler = (flights: FlightBrief[]) => void;

export function createFlightsSocket(onSnapshot: SnapshotHandler): WebSocket {
	const ws = new WebSocket(import.meta.env.VITE_WS_URL);

	ws.onmessage = (event) => {
		try {
			const payload = JSON.parse(event.data) as {
				event: string;
				data: FlightBrief[];
			};

			if (payload.event === "snapshot") {
				onSnapshot(payload.data);
			}
		} catch {
			// TODO: Add centralized error reporting for malformed socket payloads.
		}
	};

	// TODO: Add reconnect/backoff strategy for unstable network conditions.
	return ws;
}
