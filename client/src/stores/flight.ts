import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { fetchFlightTrack, fetchFlights } from "../services/api";
import { createFlightsSocket } from "../services/ws";
import type { FlightBrief, TrackPoint } from "../types/flight";

export const useFlightStore = defineStore("flight", () => {
	const flights = ref<FlightBrief[]>([]);
	const loading = ref(false);
	const socket = ref<WebSocket | null>(null);
	const selectedFlightId = ref<string | null>(null);
	const selectedTrackPoints = ref<TrackPoint[]>([]);
	const trackLoading = ref(false);

	async function loadInitialFlights() {
		loading.value = true;
		try {
			flights.value = await fetchFlights();
		} finally {
			loading.value = false;
		}
	}

	function connectSocket() {
		if (socket.value) {
			return;
		}

		socket.value = createFlightsSocket((snapshot) => {
			flights.value = snapshot;

			if (
				selectedFlightId.value &&
				!snapshot.some((flight) => flight.flight_id === selectedFlightId.value)
			) {
				selectedFlightId.value = null;
				selectedTrackPoints.value = [];
			}
		});
	}

	function disconnectSocket() {
		if (socket.value) {
			socket.value.close();
			socket.value = null;
		}
	}

	async function selectFlight(flightId: string | null) {
		selectedFlightId.value = flightId;

		if (!flightId) {
			selectedTrackPoints.value = [];
			return;
		}

		trackLoading.value = true;
		try {
			const track = await fetchFlightTrack(flightId);
			if (selectedFlightId.value === flightId) {
				selectedTrackPoints.value = track;
			}
		} catch {
			if (selectedFlightId.value === flightId) {
				selectedTrackPoints.value = [];
			}
		} finally {
			if (selectedFlightId.value === flightId) {
				trackLoading.value = false;
			}
		}
	}

	const total = computed(() => flights.value.length);
	const selectedFlight = computed<FlightBrief | null>(
		() =>
			flights.value.find((flight) => flight.flight_id === selectedFlightId.value) ??
			null,
	);

	return {
		flights,
		loading,
		selectedFlightId,
		selectedFlight,
		selectedTrackPoints,
		trackLoading,
		total,
		loadInitialFlights,
		connectSocket,
		disconnectSocket,
		selectFlight,
	};
});
