import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { fetchFlights } from "../services/api";
import { createFlightsSocket } from "../services/ws";
import type { FlightBrief } from "../types/flight";

export const useFlightStore = defineStore("flight", () => {
	const flights = ref<FlightBrief[]>([]);
	const loading = ref(false);
	const socket = ref<WebSocket | null>(null);

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
		});
	}

	function disconnectSocket() {
		if (socket.value) {
			socket.value.close();
			socket.value = null;
		}
	}

	// TODO: Add derived selectors for filtered list and selected flight detail.
	const total = computed(() => flights.value.length);

	return {
		flights,
		loading,
		total,
		loadInitialFlights,
		connectSocket,
		disconnectSocket,
	};
});
