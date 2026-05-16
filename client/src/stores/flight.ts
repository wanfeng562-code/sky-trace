import { computed, ref, watch } from "vue";
import { defineStore } from "pinia";

import {
	fetchAirports,
	fetchAirQuality,
	fetchAirportSchedules,
	fetchFlightDetail,
	fetchFlightTrack,
	fetchFlights,
} from "../services/api";
import { createFlightsSocket } from "../services/ws";
import {
	AIRPORT_TO_COUNTRY,
	COUNTRIES,
	type CountryFilterMode,
	type SubRegion,
} from "../data/countries";
import type {
	AirportInfo,
	AirQualityHub,
	FlightBrief,
	FlightDetail,
	ScheduleEntry,
	TrackPoint,
} from "../types/flight";

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
	const filterCountry = ref<string | null>(null);
	const filterCountryMode = ref<CountryFilterMode>("airspace");
	const filterRegion = ref<string | null>(null);
	const flightDetail = ref<FlightDetail | null>(null);
	const detailLoading = ref(false);
	const airports = ref<AirportInfo[]>([]);
	const airportsLoaded = ref(false);
	const airQualityData = ref<AirQualityHub[]>([]);
	const showAqiLayer = ref(false);
	const scheduleAirport = ref<string | null>(null);
	const scheduleEntries = ref<ScheduleEntry[]>([]);
	const scheduleLoading = ref(false);

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
					!snapshot.some(
						(flight) => flight.flight_id === selectedFlightId.value,
					)
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
			flights.value.find(
				(flight) => flight.flight_id === selectedFlightId.value,
			) ?? null,
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

		if (filterCountry.value) {
			const cc = filterCountry.value;
			const country = COUNTRIES.find((c) => c.code === cc);
			if (country) {
				// Use sub-region bbox if one is selected, otherwise the country bbox
				const region: SubRegion | undefined = filterRegion.value
					? country.regions?.find((r) => r.code === filterRegion.value)
					: undefined;
				const bbox = region ?? country;
				const regionAirports = region?.airports ?? country.airports;

				if (filterCountryMode.value === "airspace") {
					list = list.filter(
						(f) =>
							f.lat >= bbox.latMin &&
							f.lat <= bbox.latMax &&
							f.lon >= bbox.lonMin &&
							f.lon <= bbox.lonMax,
					);
				} else if (filterCountryMode.value === "departure") {
					const airportSet = new Set(regionAirports);
					list = list.filter((f) => {
						const dep = f.departure_airport;
						if (!dep) return false;
						return airportSet.has(dep) || AIRPORT_TO_COUNTRY[dep] === cc;
					});
				} else if (filterCountryMode.value === "arrival") {
					const airportSet = new Set(regionAirports);
					list = list.filter((f) => {
						const arr = f.arrival_airport;
						if (!arr) return false;
						return airportSet.has(arr) || AIRPORT_TO_COUNTRY[arr] === cc;
					});
				}
			}
		}

		return list;
	});

	// Reset sub-region when country changes
	watch(filterCountry, () => {
		filterRegion.value = null;
	});

	async function loadAirports(force = false) {
		if (airportsLoaded.value && !force) return;
		try {
			airports.value = await fetchAirports(force);
			airportsLoaded.value = true;
		} catch {
			// 失败时保持空列表，不阻塞其他功能
		}
	}

	async function loadAirQuality() {
		try {
			airQualityData.value = await fetchAirQuality();
		} catch {
			// ignore
		}
	}

	async function loadSchedules(iata: string, direction = "dep") {
		scheduleAirport.value = iata;
		scheduleLoading.value = true;
		try {
			scheduleEntries.value = await fetchAirportSchedules(iata, direction);
		} catch {
			scheduleEntries.value = [];
		} finally {
			scheduleLoading.value = false;
		}
	}

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
		filterCountry,
		filterCountryMode,
		filterRegion,
		filteredFlights,
		flightDetail,
		detailLoading,
		airports,
		airQualityData,
		showAqiLayer,
		scheduleAirport,
		scheduleEntries,
		scheduleLoading,
		loadInitialFlights,
		connectSocket,
		disconnectSocket,
		selectFlight,
		loadFlightDetail,
		loadAirports,
		loadAirQuality,
		loadSchedules,
	};
});
