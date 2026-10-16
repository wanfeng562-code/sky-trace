import type { FlightBrief } from "../types/flight";
import { BACKEND_ENABLED } from "../config/backend";

export type SnapshotHandler = (flights: FlightBrief[]) => void;
export type StatusHandler = (online: boolean) => void;

const RECONNECT_DELAYS = [2000, 4000, 8000, 15000, 30000];

export function createFlightsSocket(
	onSnapshot: SnapshotHandler,
	onStatusChange?: StatusHandler,
): { close: () => void } {
	if (!BACKEND_ENABLED) { onStatusChange?.(false); return { close() {} }; }
	let ws: WebSocket | null = null;
	let retryCount = 0;
	let closed = false;
	let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

	function connect() {
		if (closed) return;
		reconnectTimer = null;
		ws = new WebSocket(import.meta.env.VITE_WS_URL);

		ws.onopen = () => {
			if (closed) { ws?.close(); return; }
			retryCount = 0;
			onStatusChange?.(true);
		};

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
				// 忽略格式错误的帧
			}
		};

		ws.onclose = () => {
			onStatusChange?.(false);
			if (!closed) {
				const delay =
					RECONNECT_DELAYS[Math.min(retryCount, RECONNECT_DELAYS.length - 1)];
				retryCount++;
				reconnectTimer = setTimeout(connect, delay);
			}
		};

		ws.onerror = () => {
			ws?.close();
		};
	}

	connect();

	return {
		close() {
			closed = true;
			if (reconnectTimer !== null) clearTimeout(reconnectTimer);
			ws?.close();
		},
	};
}
