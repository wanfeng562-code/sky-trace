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
} from "../data/countries";
import { resolveGeoBBox } from "../data/geoHierarchy";
import {
	matchesAircraftCategory,
	matchesAltitudeRange,
	matchesFlightType,
	matchesSpeedRange,
	type FlightTypeFilter,
} from "../utils/flightFilters";
import { warmAirportDisplayCache } from "../data/airportDisplay";
import { airportsMatch } from "../utils/flightTrackMap";
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
	const filterCity = ref<string | null>(null);
	const filterDistrict = ref<string | null>(null);
	const filterAltMin = ref<number | null>(null);
	const filterAltMax = ref<number | null>(null);
	const filterSpeedMin = ref<number | null>(null);
	const filterSpeedMax = ref<number | null>(null);
	const filterFlightType = ref<FlightTypeFilter>("all");
	const filterAircraftCategory = ref<number | null>(null);
	const flightDetail = ref<FlightDetail | null>(null);
	const detailLoading = ref(false);
	const airports = ref<AirportInfo[]>([]);
	const airportsLoaded = ref(false);
	const airQualityData = ref<AirQualityHub[]>([]);
	const showAqiLayer = ref(false);
	const scheduleAirport = ref<string | null>(null);
	const scheduleEntries = ref<ScheduleEntry[]>([]);
	const scheduleLoading = ref(false);

	const MARKED_KEY = "skytrace.markedFlights";

	function loadMarkedIds(): string[] {
		try {
			const raw = localStorage.getItem(MARKED_KEY);
			if (!raw) return [];
			const parsed = JSON.parse(raw) as unknown;
			if (!Array.isArray(parsed)) return [];
			return parsed.filter((id): id is string => typeof id === "string");
		} catch {
			return [];
		}
	}

	const markedFlightIds = ref<string[]>(loadMarkedIds());

	function persistMarkedIds() {
		try {
			localStorage.setItem(MARKED_KEY, JSON.stringify(markedFlightIds.value));
		} catch {
			/* ignore */
		}
	}

	function isMarked(flightId: string): boolean {
		return markedFlightIds.value.includes(flightId);
	}

	function markFlight(flightId: string) {
		if (!flightId || isMarked(flightId)) return;
		markedFlightIds.value = [...markedFlightIds.value, flightId];
		persistMarkedIds();
	}

	function unmarkFlight(flightId: string) {
		markedFlightIds.value = markedFlightIds.value.filter((id) => id !== flightId);
		persistMarkedIds();
	}

	function toggleMarkFlight(flightId: string) {
		if (isMarked(flightId)) unmarkFlight(flightId);
		else markFlight(flightId);
	}

	const markedFlights = computed(() => {
		const ids = new Set(markedFlightIds.value);
		return flights.value.filter((f) => ids.has(f.flight_id));
	});

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

		if (filterFlightType.value !== "all") {
			list = list.filter((f) =>
				matchesFlightType(f, filterFlightType.value),
			);
		}

		if (filterAircraftCategory.value != null) {
			list = list.filter((f) =>
				matchesAircraftCategory(f, filterAircraftCategory.value),
			);
		}

		list = list.filter((f) =>
			matchesAltitudeRange(
				f,
				filterAltMin.value,
				filterAltMax.value,
			),
		);
		list = list.filter((f) =>
			matchesSpeedRange(
				f,
				filterSpeedMin.value,
				filterSpeedMax.value,
			),
		);

		if (filterCountry.value) {
			const cc = filterCountry.value;
			const country = COUNTRIES.find((c) => c.code === cc);
			const bbox = resolveGeoBBox(
				cc,
				filterRegion.value,
				filterCity.value,
				filterDistrict.value,
			);
			if (bbox && country) {
				const region = filterRegion.value
					? country.regions?.find((r) => r.code === filterRegion.value)
					: undefined;
				const regionAirports =
					bbox.airports ?? region?.airports ?? country.airports;

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

	const activeFilterCount = computed(() => {
		let n = 0;
		if (filterCountry.value) n++;
		if (filterFlightType.value !== "all") n++;
		if (filterAircraftCategory.value != null) n++;
		if (filterAltMin.value != null || filterAltMax.value != null) n++;
		if (filterSpeedMin.value != null || filterSpeedMax.value != null) n++;
		return n;
	});

	/** 任一筛选条件生效（地图仅绘制命中航班） */
	const filtersActive = computed(
		() =>
			activeFilterCount.value > 0 ||
			filterStatus.value !== "all" ||
			searchKeyword.value.trim().length > 0,
	);

	function applyStatusPreset(status: "all" | "airborne" | "on_ground") {
		filterStatus.value = status;
	}

	function sanitizeFilterNumber(v: number | null): number | null {
		if (v == null) return null;
		return Number.isFinite(v) ? v : null;
	}

	watch(filterAltMin, (v) => {
		const n = sanitizeFilterNumber(v);
		if (v !== n) filterAltMin.value = n;
	});
	watch(filterAltMax, (v) => {
		const n = sanitizeFilterNumber(v);
		if (v !== n) filterAltMax.value = n;
	});
	watch(filterSpeedMin, (v) => {
		const n = sanitizeFilterNumber(v);
		if (v !== n) filterSpeedMin.value = n;
	});
	watch(filterSpeedMax, (v) => {
		const n = sanitizeFilterNumber(v);
		if (v !== n) filterSpeedMax.value = n;
	});

	function applyAltitudePreset(min: number, max: number | null) {
		filterAltMin.value = min;
		filterAltMax.value = max;
		if (min === 0 && max === 100) {
			filterStatus.value = "on_ground";
		} else if (min === 1000 && max === 25000) {
			filterStatus.value = "airborne";
		} else {
			filterStatus.value = "all";
		}
	}

	function resetAdvancedFilters() {
		filterStatus.value = "all";
		filterCountry.value = null;
		filterRegion.value = null;
		filterCity.value = null;
		filterDistrict.value = null;
		filterCountryMode.value = "airspace";
		filterAltMin.value = null;
		filterAltMax.value = null;
		filterSpeedMin.value = null;
		filterSpeedMax.value = null;
		filterFlightType.value = "all";
		filterAircraftCategory.value = null;
	}

	watch(filterCountry, () => {
		filterRegion.value = null;
		filterCity.value = null;
		filterDistrict.value = null;
	});

	watch(filterRegion, () => {
		filterCity.value = null;
		filterDistrict.value = null;
	});

	watch(filterCity, () => {
		filterDistrict.value = null;
	});

	async function loadAirports(force = false) {
		if (airportsLoaded.value && !force) return;
		try {
			airports.value = await fetchAirports(force);
			warmAirportDisplayCache(airports.value);
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

	let scheduleRequestSeq = 0;

	async function loadSchedules(iata: string, direction = "dep") {
		const seq = ++scheduleRequestSeq;
		scheduleAirport.value = iata;
		scheduleLoading.value = true;
		try {
			const entries = await fetchAirportSchedules(iata, direction);
			if (seq !== scheduleRequestSeq || scheduleAirport.value !== iata) {
				return;
			}
			scheduleEntries.value = entries;
		} catch {
			if (seq === scheduleRequestSeq && scheduleAirport.value === iata) {
				scheduleEntries.value = [];
			}
		} finally {
			if (seq === scheduleRequestSeq) {
				scheduleLoading.value = false;
			}
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
			let detail = await fetchFlightDetail(flightId);
			// 详情 API 可能未带机场坐标，从已加载枢纽列表补全以便绘制剩余航程
			if (detail.arrival_airport && detail.arrival_lat == null) {
				const arr = airports.value.find((a) =>
					airportsMatch(a.iata, detail.arrival_airport),
				);
				if (arr) {
					detail = {
						...detail,
						arrival_lat: arr.lat,
						arrival_lon: arr.lon,
					};
				}
			}
			if (detail.departure_airport && detail.departure_lat == null) {
				const dep = airports.value.find((a) =>
					airportsMatch(a.iata, detail.departure_airport),
				);
				if (dep) {
					detail = {
						...detail,
						departure_lat: dep.lat,
						departure_lon: dep.lon,
					};
				}
			}
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
		filterCity,
		filterDistrict,
		filterAltMin,
		filterAltMax,
		filterSpeedMin,
		filterSpeedMax,
		filterFlightType,
		filterAircraftCategory,
		activeFilterCount,
		filtersActive,
		applyStatusPreset,
		applyAltitudePreset,
		resetAdvancedFilters,
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
		markedFlightIds,
		markedFlights,
		isMarked,
		markFlight,
		unmarkFlight,
		toggleMarkFlight,
	};
});
