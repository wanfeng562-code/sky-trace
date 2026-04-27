import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
	fetchFlightDetail,
	fetchFlightTrack,
	fetchFlights,
} from "../services/api";
import { createFlightsSocket } from "../services/ws";
import type { FlightBrief, FlightDetail, TrackPoint } from "../types/flight";

export const useFlightStore = defineStore("flight", () => {
	const flights = ref<FlightBrief[]>([]);
	const loading = ref(false);
	const socket = ref<{ close: () => void } | null>(null);
	const wsOnline = ref(false);
	const selectedFlightId = ref<string | null>(null);
	const selectedTrackPoints = ref<TrackPoint[]>([]);
	const trackLoading = ref(false);
	const searchKeyword = ref<string>("");
	const filterStatus = ref<"all" | "airborne" | "on_ground">("all");
	const flightDetail = ref<FlightDetail | null>(null);
	const detailLoading = ref(false);

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

		socket.value = createFlightsSocket(
			(snapshot) => {
				flights.value = snapshot;

				if (
					selectedFlightId.value &&
					!snapshot.some((flight) => flight.flight_id === selectedFlightId.value)
				) {
					selectedFlightId.value = null;
					selectedTrackPoints.value = [];
					flightDetail.value = null;
				}
			},
			(online) => {
				wsOnline.value = online;
			},
		);
	}

	function disconnectSocket() {
		if (socket.value) {
			socket.value.close();
			socket.value = null;
		}
		wsOnline.value = false;
	}

	async function selectFlight(flightId: string | null) {
		selectedFlightId.value = flightId;

		if (!flightId) {
			selectedTrackPoints.value = [];
			flightDetail.value = null;
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
	const filteredFlights = computed(() => {
		let list = flights.value;
		if (searchKeyword.value.trim()) {
			const kw = searchKeyword.value.trim().toUpperCase();
			list = list.filter(
				(flight) =>
					flight.flight_id.toUpperCase().includes(kw) ||
					(flight.callsign ?? "").toUpperCase().includes(kw),
			);
		}

		if (filterStatus.value === "airborne") {
			list = list.filter((flight) => (flight.altitude_ft ?? 0) > 100);
		} else if (filterStatus.value === "on_ground") {
			list = list.filter((flight) => (flight.altitude_ft ?? 0) <= 100);
		}

		return list;
	});

	async function loadFlightDetail(flightId: string | null) {
		if (!flightId) {
			flightDetail.value = null;
			detailLoading.value = false;
			return;
		}

		detailLoading.value = true;
		try {
			const detail = await fetchFlightDetail(flightId);
			if (selectedFlightId.value === flightId) {
				flightDetail.value = detail;
			}
		} catch {
			if (selectedFlightId.value === flightId) {
				flightDetail.value = null;
			}
		} finally {
			if (selectedFlightId.value === flightId) {
				detailLoading.value = false;
			}
		}
	}

	return {
		flights,
		loading,
		wsOnline,
		selectedFlightId,
		selectedFlight,
		selectedTrackPoints,
		trackLoading,
		total,
		searchKeyword,
		filterStatus,
		filteredFlights,
		flightDetail,
		detailLoading,
		loadInitialFlights,
		connectSocket,
		disconnectSocket,
		selectFlight,
		loadFlightDetail,
	};
});
