<template>
	<div class="layout">
		<section class="map-area">
			<header class="toolbar">
				<h1>Sky-Trace</h1>
				<span>{{
					store.loading ? "loading..." : `${store.flights.length} flights`
				}}</span>
			</header>

			<div class="map-shell">
				<div ref="mapContainer" class="map-canvas"></div>
				<div v-if="store.loading" class="map-status">正在加载航班数据...</div>
				<div v-else-if="store.trackLoading" class="map-status">
					正在加载选中航班轨迹...
				</div>
				<div v-else-if="!store.flights.length" class="map-status">
					暂无航班数据，等待后端返回快照。
				</div>
				<FlightDetailCard
					:detail="store.flightDetail"
					:loading="store.detailLoading"
					@close="handleSelectFlight(null)"
				/>
			</div>
		</section>

		<FlightListPanel
			:flights="store.filteredFlights"
			:selected-flight-id="store.selectedFlightId"
			:filter-status="store.filterStatus"
			:ws-online="store.wsOnline"
			@select="handleSelectFlight"
			@search="store.searchKeyword = $event"
			@filter="store.filterStatus = $event"
		/>
	</div>
</template>

<script setup lang="ts">
	import { onMounted, onUnmounted, ref, watch } from "vue";
	import maplibregl, {
		type GeoJSONSource,
		type LngLatBoundsLike,
		type Map as MapLibreMap,
	} from "maplibre-gl";
	import "maplibre-gl/dist/maplibre-gl.css";

import FlightDetailCard from "../components/FlightDetailCard.vue";
	import FlightListPanel from "../components/FlightListPanel.vue";
	import { useFlightStore } from "../stores/flight";
	import type { FlightBrief } from "../types/flight";

	const MAP_SOURCE_ID = "flights";
	const MAP_LAYER_ID = "flight-points";
	const MAP_SELECTED_LAYER_ID = "selected-flight-point";
	const MAP_TRACK_SOURCE_ID = "selected-flight-track";
	const MAP_TRACK_LAYER_ID = "selected-flight-track-line";

	const store = useFlightStore();
	const mapContainer = ref<HTMLElement | null>(null);
	const map = ref<MapLibreMap | null>(null);
	const hasFittedInitialBounds = ref(false);

async function handleSelectFlight(flightId: string | null) {
	await store.selectFlight(flightId);
	store.loadFlightDetail(flightId);
}

	function toGeoJson(flights: FlightBrief[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
		return {
			type: "FeatureCollection",
			features: flights.map((flight) => ({
				type: "Feature",
				geometry: {
					type: "Point",
					coordinates: [flight.lon, flight.lat],
				},
				properties: {
					flight_id: flight.flight_id,
					callsign: flight.callsign ?? flight.flight_id,
					heading: flight.heading ?? null,
					speed_kts: flight.speed_kts ?? null,
					altitude_ft: flight.altitude_ft ?? null,
					updated_at: flight.updated_at,
				},
			})),
		};
	}

	function createPopupHtml(properties: Record<string, unknown>): string {
		return `
			<div class="popup">
				<strong>${properties.callsign ?? properties.flight_id}</strong>
				<div>ID: ${properties.flight_id ?? "--"}</div>
				<div>高度: ${properties.altitude_ft ?? "--"} ft</div>
				<div>速度: ${properties.speed_kts ?? "--"} kts</div>
				<div>航向: ${properties.heading ?? "--"}°</div>
			</div>
		`;
	}

	function toTrackGeoJson(): GeoJSON.FeatureCollection<GeoJSON.LineString> {
		if (store.selectedTrackPoints.length < 2) {
			return {
				type: "FeatureCollection",
				features: [],
			};
		}

		return {
			type: "FeatureCollection",
			features: [
				{
					type: "Feature",
					geometry: {
						type: "LineString",
						coordinates: store.selectedTrackPoints.map((point) => [
							point.lon,
							point.lat,
						]),
					},
					properties: {
						flight_id: store.selectedFlightId ?? "",
					},
				},
			],
		};
	}

	function fitToFlights(flights: FlightBrief[]) {
		if (!map.value || hasFittedInitialBounds.value || flights.length === 0) {
			return;
		}

		if (flights.length === 1) {
			map.value.flyTo({
				center: [flights[0].lon, flights[0].lat],
				zoom: 6,
				essential: true,
			});
			hasFittedInitialBounds.value = true;
			return;
		}

		const bounds = flights.reduce<[number, number, number, number] | null>(
			(acc, flight) => {
				if (!acc) {
					return [flight.lon, flight.lat, flight.lon, flight.lat];
				}

				return [
					Math.min(acc[0], flight.lon),
					Math.min(acc[1], flight.lat),
					Math.max(acc[2], flight.lon),
					Math.max(acc[3], flight.lat),
				];
			},
			null,
		);

		if (bounds) {
			map.value.fitBounds(bounds as LngLatBoundsLike, {
				padding: 48,
				maxZoom: 7,
				essential: true,
			});
			hasFittedInitialBounds.value = true;
		}
	}

	function updateFlightLayer(flights: FlightBrief[]) {
		if (!map.value) {
			return;
		}

		const source = map.value.getSource(MAP_SOURCE_ID) as GeoJSONSource | undefined;
		if (!source) {
			return;
		}

		source.setData(toGeoJson(flights));
		updateSelectedFlightHighlight();
		fitToFlights(flights);
	}

	function updateTrackLayer() {
		if (!map.value) {
			return;
		}

		const source = map.value.getSource(MAP_TRACK_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		if (!source) {
			return;
		}

		source.setData(toTrackGeoJson());
	}

	function updateSelectedFlightHighlight() {
		if (!map.value || !map.value.getLayer(MAP_SELECTED_LAYER_ID)) {
			return;
		}

		const selectedId = store.selectedFlightId;
		map.value.setFilter(
			MAP_SELECTED_LAYER_ID,
			selectedId ? ["==", ["get", "flight_id"], selectedId] : ["==", ["get", "flight_id"], ""],
		);
	}

	function focusSelectedFlight(flight: FlightBrief | null) {
		if (!map.value || !flight) {
			return;
		}

		map.value.flyTo({
			center: [flight.lon, flight.lat],
			zoom: Math.max(map.value.getZoom(), 7),
			essential: true,
		});
	}

	function initMap() {
		if (!mapContainer.value) {
			return;
		}

		const mapInstance = new maplibregl.Map({
			container: mapContainer.value,
			style: "https://demotiles.maplibre.org/style.json",
			center: [113.2644, 23.1291],
			zoom: 4,
			attributionControl: true,
		});

		mapInstance.addControl(new maplibregl.NavigationControl(), "top-right");

		mapInstance.on("load", () => {
			mapInstance.addSource(MAP_SOURCE_ID, {
				type: "geojson",
				data: toGeoJson(store.flights),
			});

			mapInstance.addLayer({
				id: MAP_LAYER_ID,
				type: "circle",
				source: MAP_SOURCE_ID,
				paint: {
					"circle-radius": 6,
					"circle-color": "#2563eb",
					"circle-stroke-width": 2,
					"circle-stroke-color": "#dbeafe",
				},
			});

			mapInstance.addLayer({
				id: MAP_SELECTED_LAYER_ID,
				type: "circle",
				source: MAP_SOURCE_ID,
				filter: ["==", ["get", "flight_id"], ""],
				paint: {
					"circle-radius": 9,
					"circle-color": "#f59e0b",
					"circle-stroke-width": 3,
					"circle-stroke-color": "#ffffff",
				},
			});

			mapInstance.addSource(MAP_TRACK_SOURCE_ID, {
				type: "geojson",
				data: toTrackGeoJson(),
			});

			mapInstance.addLayer({
				id: MAP_TRACK_LAYER_ID,
				type: "line",
				source: MAP_TRACK_SOURCE_ID,
				layout: {
					"line-cap": "round",
					"line-join": "round",
				},
				paint: {
					"line-color": "#f59e0b",
					"line-width": 3,
					"line-opacity": 0.9,
				},
			});

			mapInstance.on("click", MAP_LAYER_ID, (event) => {
				const feature = event.features?.[0];
				if (!feature || feature.geometry.type !== "Point") {
					return;
				}

				const flightId = feature.properties?.flight_id;
				if (typeof flightId === "string") {
					handleSelectFlight(flightId);
				}

				new maplibregl.Popup({ offset: 12 })
					.setLngLat(feature.geometry.coordinates as [number, number])
					.setHTML(
						createPopupHtml(
							(feature.properties ?? {}) as Record<string, unknown>,
						),
					)
					.addTo(mapInstance);
			});

			mapInstance.on("mouseenter", MAP_LAYER_ID, () => {
				mapInstance.getCanvas().style.cursor = "pointer";
			});

			mapInstance.on("mouseleave", MAP_LAYER_ID, () => {
				mapInstance.getCanvas().style.cursor = "";
			});

			updateFlightLayer(store.flights);
			updateSelectedFlightHighlight();
			updateTrackLayer();
		});

		map.value = mapInstance;
	}

	watch(
		() => store.flights,
		(flights) => {
			updateFlightLayer(flights);
		},
		{ deep: true },
	);

	watch(
		() => store.selectedFlight,
		(flight) => {
			updateSelectedFlightHighlight();
			focusSelectedFlight(flight);
		},
		{ deep: true },
	);

	watch(
		() => store.selectedTrackPoints,
		() => {
			updateTrackLayer();
		},
		{ deep: true },
	);

	onMounted(async () => {
		initMap();
		await store.loadInitialFlights();
		store.connectSocket();
	});

	onUnmounted(() => {
		store.disconnectSocket();
		map.value?.remove();
		map.value = null;
	});
</script>

<style scoped>
	.layout {
		height: 100vh;
		display: flex;
	}

	.map-area {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.toolbar {
		height: 56px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 16px;
		border-bottom: 1px solid #d1d5db;
		background: #f8fafc;
	}

	.map-shell {
		flex: 1;
		position: relative;
		background: #dbeafe;
	}

	.map-canvas {
		width: 100%;
		height: 100%;
	}

	.map-status {
		position: absolute;
		left: 16px;
		bottom: 16px;
		padding: 10px 12px;
		border-radius: 10px;
		background: rgba(15, 23, 42, 0.78);
		color: #f8fafc;
		font-size: 13px;
		backdrop-filter: blur(4px);
	}
</style>
