<template>
	<div class="map-layout">

		<div class="map-workspace">
			<MapSidebar
				v-model:collapsed="sidebarCollapsed"
				v-model:active-tab="sidebarTab"
				:flights="store.filteredFlights"
				:all-flights="store.flights"
				:airports="store.airports"
				:selected-flight-id="store.selectedFlightId"
				:selected-hub-iata="selectedHubIata"
				:hub-count="hubAirportCount"
				@select-flight="handleSelectFlight"
				@hub-locate="handleHubLocate"
				@hub-schedule="handleHubSchedule"
				@hub-clear="clearHubFocus"
				@collapse="onSidebarCollapse"
				@layout-settled="onSidebarLayoutSettled"
			/>

			<div class="map-shell">
				<div ref="mapContainer" class="map-canvas"></div>
				<div v-if="basemapUnavailable" class="map-basemap-status" role="status">{{ basemapStatus }}</div>
				<div v-else-if="localLabelsUnavailable" class="map-basemap-status" role="status">{{ localeStore.t.basemap.localLabelsUnavailable }}</div>
				<MapControlsOverlay
					v-model:layers-open="showLayerPanel"
					v-model:basemap-open="showBasemapPanel"
					:map="map"
					:map-bearing="mapBearing"
					@zoom-in="mapZoomIn"
					@zoom-out="mapZoomOut"
					@reset-bearing="mapResetBearing"
					@geolocate="mapGeolocate"
				/>
				<MapLayerPopover
					v-model:open="showLayerPanel"
					v-model:show-aqi="store.showAqiLayer"
					v-model:show-aqi-heatmap="showAqiHeatmap"
					v-model:show-wind="showWindLayer"
					v-model:show-temp="showTempLayer"
					v-model:show-density="showDensityLayer"
					v-model:show-hubs="showHubAirports"
					v-model:show-grid="showGridPoints"
				/>
				<MapBasemapPopover
					v-model:open="showBasemapPanel"
					:provider="currentProvider"
					:style-id="currentStyleId"
					:styles="currentProviderStyles"
					:unavailable="basemapUnavailable"
					@switch-style="switchStyle"
				/>
				<div v-if="store.loading" class="map-status">{{ ui.loadingFlights }}</div>
				<div v-else-if="store.trackLoading" class="map-status">
					{{ ui.loadingTrack }}
				</div>
				<div v-else-if="!store.flights.length" class="map-status">
					{{ !BACKEND_ENABLED ? ui.backendPaused : ui.waitingSnapshot }}
				</div>
			</div>

			<MapContextPanel
				v-model:active-tab="contextTab"
				:open="contextPanelOpen"
				:show-rail="contextPanelCollapsed && contextHasContent"
				:rail-label="contextRailLabel"
				:show-detail-tab="showDetailTab"
				:show-schedule-tab="!!store.scheduleAirport"
				:detail="store.flightDetail"
				:detail-loading="store.detailLoading"
				@collapse="collapseContextPanel"
				@expand="expandContextPanel"
				@close="closeContextPanel"
				@layout-settled="onSidebarLayoutSettled"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { formatWeatherDescription } from "../utils/flightDetailLocale";
	import { useBusinessLocale } from "../i18n/useBusinessLocale";
	const { ui } = useBusinessLocale();
	import { BACKEND_ENABLED } from "../config/backend";
	defineOptions({ name: "MapView" });

	import {
		computed,
		markRaw,
		nextTick,
		onDeactivated,
		onActivated,
		onMounted,
		onUnmounted,
		ref,
		shallowRef,
		watch,
	} from "vue";
	import maplibregl, {
		type FilterSpecification,
		type GeoJSONSource,
		type LngLatBoundsLike,
		type Map as MapLibreMap,
	} from "maplibre-gl";
	import "maplibre-gl/dist/maplibre-gl.css";
	import planeIconRaw from "../icons/plane.svg?raw";
	import planeGroundIconRaw from "../icons/plane_ground.svg?raw";

	import MapBasemapPopover from "../components/map/MapBasemapPopover.vue";
	import MapContextPanel from "../components/map/MapContextPanel.vue";
	import MapControlsOverlay from "../components/map/MapControlsOverlay.vue";
	import MapLayerPopover from "../components/map/MapLayerPopover.vue";
	import MapSidebar from "../components/map/MapSidebar.vue";
	import { translate, useLocaleStore } from "../i18n";
	import { flyToUserLocation } from "../utils/mapGeolocateControl";
	import {
		AIRPORT_HIGHLIGHT_LAYER,
		AIRPORT_HIGHLIGHT_SOURCE,
		TRACK_HISTORY_SEG_LAYER_ID,
		buildHistoricalTrackSegmentCollection,
		buildPlannedRouteGeoJson,
		buildRouteAirportHighlightCollection,
		historicalTrackSegmentLinePaint,
		resolveRouteAirports,
		routeAirportHighlightPaint,
	} from "../utils/flightTrackMap";
	import { fetchDatahubWeather, fetchWeatherGrid } from "../services/api";
	import {
		AIRCRAFT_COLOR,
		resolveStyleAircraftColor,
	} from "../config/aircraftColors";
	import {
		HUB_CIRCLE_TIER_1,
		HUB_LABEL_COLOR,
		HUB_LABEL_HALO,
	} from "../config/mapVisualTheme";
	import {
		applyMapMarkerLabelStyles,
		applyPremiumOverlayStyles,
		flightHoverLabelLayout,
		flightHoverLabelPaint,
		flightHoverIconImageLayout,
		flightIconImageLayout,
		flightIconSizeLayout,
		formatWindLabel,
		aqiCirclePaint,
		aqiHeatmapPaint,
		aqiLabelLayout,
		aqiLabelPaint,
		flightDensityHeatmapPaint,
		hubAirportCirclePaint,
		hubAirportHighlightLabelLayout,
		hubAirportLabelLayout,
		hubAirportLabelPaint,
		regionHighlightFillPaint,
		regionHighlightGlowPaint,
		regionHighlightLinePaint,
		tempCirclePaint,
		tempHeatmapPaint,
		weatherGridFillPaint,
		weatherGridMarkerLayout,
		weatherGridMarkerPaint,
		weatherGridOutlinePaint,
		windArrowLayout,
		windArrowPaint,
		windLabelLayout,
		windLabelPaint,
	} from "../config/mapLayerStyles";
	import { toHubAirportGeoJson } from "../utils/mapHubDisplay";
	import { HIDE_ALL_FEATURES_FILTER } from "../utils/mapFilters";
	import { ensureOverlayLayerOrder } from "../utils/mapLayerOrder";
	import {
		scheduleMapUpdate,
		cancelScheduledMapUpdates,
	} from "../utils/mapUpdateScheduler";
	import {
		patchFlightGeoJson,
		type FlightPointFeature,
	} from "../utils/flightGeoJson";
	import {
		clearFlightFeatureStates,
		resetFlightFeatureStateTracking,
		syncFlightHighlightStates,
	} from "../utils/flightFeatureState";
	import { resolveGeoBBox } from "../data/geoHierarchy";
	import {
		createBasemapStyle, DEFAULT_BASEMAP_STYLE, TIANDITU_KEY, basemapApprovalNumber,
		TIANDITU_STYLE_IDS, normalizeBasemapStyle, basemapStatusMessage,
		type MapProvider,
	} from "../utils/mapBasemap";
	import { createPlaceLabelController } from "../utils/localPlaceLabels";
	import { applyOverlaySymbolFonts } from "../config/mapLabelFonts";
	import type { StyleSpecification } from "maplibre-gl";
	import {
		computeWeatherGridFromFlights,
		enrichCellsWithGrdWeather,
	} from "../utils/weatherGrid";
	import { useFlightStore } from "../stores/flight";
	import { COUNTRIES } from "../data/countries";
	import type {
		AirportInfo,
		AirQualityHub,
		FlightBrief,
		WeatherGridCell,
	} from "../types/flight";

	// ── API keys from .env ───────────────────────────────────────────────────────
	const MAP_DEFAULT_STYLE = DEFAULT_BASEMAP_STYLE;
	const MAP_INIT_LNG = parseFloat(
		(import.meta.env.VITE_MAP_INIT_LNG as string) || "113.2644",
	);
	const MAP_INIT_LAT = parseFloat(
		(import.meta.env.VITE_MAP_INIT_LAT as string) || "23.1291",
	);
	const MAP_INIT_ZOOM = parseFloat(
		(import.meta.env.VITE_MAP_INIT_ZOOM as string) || "4",
	);

	const MAP_SOURCE_ID = "flights";
	const MAP_LAYER_ID = "flight-points";
	const MAP_FLIGHT_HOVER_ICON_LAYER_ID = "flight-hover-icon";
	const MAP_HOVER_SOURCE_ID = "flight-hover-tip";
	const MAP_HOVER_LABEL_LAYER_ID = "flight-hover-label";
	const MAP_SELECTED_LAYER_ID = "selected-flight-point";
	const MAP_MARKED_LAYER_ID = "marked-flight-ring";
	const MAP_TRACK_SEG_SOURCE_ID = "flight-track-history-segments";
	const MAP_AIRPORT_SOURCE_ID = "airports";
	const MAP_AIRPORT_LAYER_ID = "airport-points";
	const MAP_AIRPORT_LABEL_LAYER_ID = "airport-labels";
	const MAP_GRID_SOURCE_ID = "weather-grid-cells";
	const MAP_GRID_POINTS_SOURCE_ID = "weather-grid-centers";
	const MAP_GRID_FILL_LAYER_ID = "weather-grid-fill";
	const MAP_GRID_LINE_LAYER_ID = "weather-grid-outline";
	const MAP_GRID_MARKER_LAYER_ID = "weather-grid-markers";
	const MAP_AIRPORT_HIGHLIGHT_SOURCE_ID = AIRPORT_HIGHLIGHT_SOURCE;
	const MAP_AIRPORT_HIGHLIGHT_LAYER_ID = AIRPORT_HIGHLIGHT_LAYER;
	const MAP_AIRPORT_HIGHLIGHT_LABEL_ID = "airport-route-highlight-labels";
	const MAP_AQI_SOURCE_ID = "aqi-hubs";
	const MAP_AQI_LAYER_ID = "aqi-circles";
	const MAP_AQI_LABEL_LAYER_ID = "aqi-labels";
	/** 剩余航程：source / layer 分离（与早期可工作版本一致） */
	const MAP_ROUTE_SOURCE_ID = "planned-route";
	const MAP_ROUTE_LAYER_ID = "planned-route-line";

	// New enhanced layer IDs
	const MAP_AQI_HEATMAP_LAYER_ID = "aqi-heatmap";
	const MAP_WIND_SOURCE_ID = "weather-hubs";
	const MAP_WIND_ARROW_LAYER_ID = "wind-arrows";
	const MAP_WIND_LABEL_LAYER_ID = "wind-speed-labels";
	const MAP_TEMP_LAYER_ID = "temp-circles";
	const MAP_TEMP_HEATMAP_LAYER_ID = "temp-heatmap";
	const MAP_DENSITY_LAYER_ID = "flight-density";
	// Region filter highlight layers
	const MAP_REGION_HIGHLIGHT_SOURCE = "region-highlight";
	const MAP_REGION_HIGHLIGHT_FILL_ID = "region-highlight-fill";
	const MAP_REGION_HIGHLIGHT_GLOW_ID = "region-highlight-glow";
	const MAP_REGION_HIGHLIGHT_LINE_ID = "region-highlight-line";

	// ── State ────────────────────────────────────────────────────────────────────
	const store = useFlightStore();
	const localeStore = useLocaleStore();

	function mapStyleLabel(_provider: MapProvider, styleId: string): string {
		return translate(localeStore.t, `mapStyles.tianditu.${styleId}`);
	}
	const mapContainer = ref<HTMLElement | null>(null);
	const map = shallowRef<MapLibreMap | null>(null);
	const hasFittedInitialBounds = ref(false);

	const currentProvider = ref<MapProvider>("tianditu");
	const currentStyleId = ref(MAP_DEFAULT_STYLE);
	const basemapUnavailable = ref(!TIANDITU_KEY);
	const basemapStatusCode = ref<number>();
	const basemapStatus = computed(() => basemapStatusMessage(basemapStatusCode.value, localeStore.locale));
	const localLabelsUnavailable = ref(false);
	let placeLabels: ReturnType<typeof createPlaceLabelController> | null = null;
	watch(() => localeStore.locale, () => placeLabels?.refresh());

	const showLayerPanel = ref(false);
	const showBasemapPanel = ref(false);
	onDeactivated(() => {
		showBasemapPanel.value = false;
		showLayerPanel.value = false;
	});
	onActivated(() => {
		store.connectSocket();
		map.value?.resize();
		placeLabels?.refresh();
	});
	const mapBearing = ref(0);

	function syncMapBearing() {
		mapBearing.value = map.value?.getBearing() ?? 0;
	}

	function mapZoomIn() {
		map.value?.zoomIn({ duration: 200 });
	}
	function mapZoomOut() {
		map.value?.zoomOut({ duration: 200 });
	}
	function mapResetBearing() {
		map.value?.easeTo({ bearing: 0, pitch: 0, duration: 400 });
	}
	function mapGeolocate() {
		if (map.value) void flyToUserLocation(map.value);
	}

	watch(showLayerPanel, (open) => {
		if (open) showBasemapPanel.value = false;
	});
	watch(showBasemapPanel, (open) => {
		if (open) showLayerPanel.value = false;
	});
	const sidebarCollapsed = ref(false);
	const sidebarTab = ref<"flights" | "filters" | "hubs" | "marked">("flights");
	const contextTab = ref<"detail" | "schedule">("detail");
	const contextPanelCollapsed = ref(false);
	const selectedHubIata = ref<string | null>(null);

	const hubAirportCount = computed(() => {
		return store.airports.filter((a) => {
			const pt = a.point_type ?? (a.iata?.startsWith("GRD_") ? "grid" : "hub");
			if (pt === "grid") return false;
			return a.is_hub === true || pt === "hub";
		}).length;
	});

	const showDetailTab = computed(
		() => !!(store.flightDetail || store.detailLoading),
	);

	const contextHasContent = computed(
		() =>
			!!store.selectedFlightId ||
			store.detailLoading ||
			!!store.scheduleAirport,
	);

	const contextPanelOpen = computed(
		() => !contextPanelCollapsed.value && contextHasContent.value,
	);

	const contextRailLabel = computed(() => {
		if (store.selectedFlight) {
			return (
				store.selectedFlight.callsign?.trim() || store.selectedFlight.flight_id
			);
		}
		if (store.scheduleAirport) return store.scheduleAirport;
		return "";
	});

	function resizeMapCanvas() {
		map.value?.resize();
	}

	function onSidebarCollapse() {
		requestAnimationFrame(resizeMapCanvas);
	}

	function onSidebarLayoutSettled() {
		resizeMapCanvas();
	}

	function clearHubFocus() {
		selectedHubIata.value = null;
		if (store.scheduleAirport) {
			store.scheduleAirport = null;
			store.scheduleEntries = [];
		}
		updateAirportHighlight();
		syncHubHighlightVisibility();
	}

	function collapseContextPanel() {
		contextPanelCollapsed.value = true;
		syncContextPanel();
	}

	function expandContextPanel() {
		contextPanelCollapsed.value = false;
		syncContextPanel();
	}

	function closeContextPanel() {
		contextPanelCollapsed.value = true;
		clearHubFocus();
		void handleSelectFlight(null);
	}

	function syncContextPanel() {
		if (!contextPanelOpen.value) return;
		void nextTick(() => {
			setTimeout(() => map.value?.resize(), 220);
		});
	}
	const showAqiHeatmap = ref(false);
	const showWindLayer = ref(false);
	const showTempLayer = ref(false);
	const showDensityLayer = ref(false);
	const showHubAirports = ref(true);
	const showGridPoints = ref(false);
	const weatherGridCells = ref<WeatherGridCell[]>([]);
	let _gridRefreshTimer: ReturnType<typeof setInterval> | null = null;
	let _gridFlightRefreshTimer: ReturnType<typeof setTimeout> | null = null;
	let gridPopup: maplibregl.Popup | null = null;

	interface WeatherHubEntry {
		iata: string;
		lat: number;
		lon: number;
		wind_speed_mps: number | null;
		wind_deg: number | null;
		temperature_c: number | null;
		humidity: number | null;
		description: string | null;
	}
	const weatherHubs = ref<WeatherHubEntry[]>([]);
	let hoveredFlightId: string | null = null;
	let flightHoverHandlersBound = false;
	let overlayOrderIdlePending = false;

	/** 防抖计时器：避免 WS 快照连续触发时每次都重建 GeoJSON */
	let _flightUpdateTimer: ReturnType<typeof setTimeout> | null = null;
	let flightFeatureIndex: Map<string, FlightPointFeature> | null = null;

	/** 底图切换串行队列：避免短时间多次 setStyle 造成并发抖动 */
	let _styleSwitching = false;
	let _pendingStyleSwitch: { url: StyleSpecification; styleId: string } | null = null;

	function resolveAircraftIconColors(): { fly: string; ground: string } {
		const color = resolveStyleAircraftColor(currentStyleId.value);
		return { fly: color, ground: color };
	}

	async function applyStyleWithQueue(url: StyleSpecification, styleId: string) {
		if (!map.value) return;
		if (_styleSwitching) {
			_pendingStyleSwitch = { url, styleId };
			return;
		}
		_styleSwitching = true;
		map.value.setStyle(url, { diff: false });
		map.value.once("style.load", async () => {
			try {
				await reinitLayers(map.value!);
				updateFlightLayer(flightsForMap());
				updateSelectedFlightHighlight();
				updateTrackLayer();
				updateRouteLayer();
				updateAirportHighlight();
			} finally {
				_styleSwitching = false;
				if (_pendingStyleSwitch) {
					const next = _pendingStyleSwitch;
					_pendingStyleSwitch = null;
					currentStyleId.value = normalizeBasemapStyle(next.styleId);
					void applyStyleWithQueue(next.url, next.styleId);
				}
			}
		});
	}

	async function refreshAircraftIcons(mapInstance: MapLibreMap) {
		const colors = resolveAircraftIconColors();
		const coral = AIRCRAFT_COLOR.coral;
		try {
			await Promise.all([
				loadColoredSvgIcon(mapInstance, "icon-plane", planeIconRaw, colors.fly),
				loadColoredSvgIcon(
					mapInstance,
					"icon-plane-ground",
					planeGroundIconRaw,
					colors.ground,
				),
				loadColoredSvgIcon(
					mapInstance,
					"icon-plane-coral",
					planeIconRaw,
					coral,
				),
				loadColoredSvgIcon(
					mapInstance,
					"icon-plane-ground-coral",
					planeGroundIconRaw,
					coral,
				),
			]);
			console.debug("[Aircraft Icon] updated", colors, currentStyleId.value);
		} catch (err) {
			console.error("[Aircraft Icon] refresh failed", err);
		}
	}

	const currentProviderStyles = computed(() => TIANDITU_STYLE_IDS.map((id) => ({
		id, label: mapStyleLabel("tianditu", id),
	})));

	async function determineInitialStyle() {
		return {
			url: createBasemapStyle(MAP_DEFAULT_STYLE, TIANDITU_KEY, basemapApprovalNumber(MAP_DEFAULT_STYLE)),
			provider: "tianditu" as MapProvider, styleId: MAP_DEFAULT_STYLE,
		};
	}

	/**
	 * Re-add all custom sources and layers after a style switch.
	 * MapLibre removes all sources/layers when setStyle() is called.
	 */
	async function reinitLayers(mapInstance: MapLibreMap) {
		applyBusinessOverlayFonts(mapInstance);

		await refreshAircraftIcons(mapInstance);

		addCustomLayers(mapInstance);
		if (!placeLabels) placeLabels = createPlaceLabelController(mapInstance, {
			locale: () => localeStore.locale,
			style: () => currentStyleId.value,
			onUnavailable: value => { localLabelsUnavailable.value = value; },
		});
		placeLabels.refresh();
		scheduleOverlayLayerOrder(mapInstance);
		syncEnvironmentalOverlayMode();
		updateHubAirportLayer();
		void applyRegionFilterHighlight(
			store.filterCountry,
			store.filterRegion,
			store.filterCity,
			store.filterDistrict,
		);
		if (showGridPoints.value) {
			void refreshWeatherGrid(false);
		}
	}

	/**
	 * Switch the active map style within the current provider.
	 */
	async function switchStyle(styleId: string) {
		if (!map.value) return;
		const id = normalizeBasemapStyle(styleId);
		if (id === currentStyleId.value && !_styleSwitching) return;
		currentStyleId.value = id;
		basemapUnavailable.value = !TIANDITU_KEY;
		basemapStatusCode.value = undefined;
		void applyStyleWithQueue(createBasemapStyle(id, TIANDITU_KEY, basemapApprovalNumber(id)), id);
	}

	// ── Weather hub fetch (for wind/temp layers) ─────────────────────────────────
	async function loadWeatherHubs() {
		try {
			const weatherData = await fetchDatahubWeather(false);
			weatherHubs.value = Object.entries(weatherData)
				.filter(([iata]) => !iata.startsWith("GRD_"))
				.map(([iata, w]) => {
					const entry = w as Record<string, unknown>;
					const wind = (entry.wind ?? {}) as Record<string, unknown>;
					const weather = (entry.weather ?? {}) as Record<string, unknown>;
					return {
						iata,
						lat: entry.lat as number,
						lon: entry.lon as number,
						wind_speed_mps: (wind.speed as number | null) ?? null,
						wind_deg: (wind.deg as number | null) ?? null,
						temperature_c: (entry.temperature_c as number | null) ?? null,
						humidity: (entry.humidity as number | null) ?? null,
						description: (weather.description as string | null) ?? null,
					};
				})
				.filter((h) => h.lat && h.lon);
			if (showGridPoints.value) {
				void refreshWeatherGrid(false);
			}
		} catch (e) {
			console.warn("[WeatherHubs] fetch failed", e);
		}
	}

	function toWeatherGeoJson(): GeoJSON.FeatureCollection<GeoJSON.Point> {
		return {
			type: "FeatureCollection",
			features: weatherHubs.value.map((h) => {
				const wind_speed_mps = h.wind_speed_mps ?? null;
				const wind_deg = h.wind_deg ?? null;
				return {
					type: "Feature",
					geometry: { type: "Point", coordinates: [h.lon, h.lat] },
					properties: {
						iata: h.iata,
						wind_speed_mps: wind_speed_mps ?? 0,
						wind_deg: wind_deg ?? 0,
						wind_label: formatWindLabel({
							iata: h.iata,
							wind_speed_mps,
							wind_deg,
						}),
						temperature_c: h.temperature_c ?? 0,
						humidity: h.humidity ?? 0,
						description: h.description ?? "",
					},
				};
			}),
		};
	}

	function updateWeatherLayer() {
		if (!map.value) return;
		const src = map.value.getSource(MAP_WIND_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		src?.setData(toWeatherGeoJson());
	}

	// ── Layer visibility toggles ─────────────────────────────────────────────────
	function setLayerVisibility(layerId: string, visible: boolean) {
		if (!map.value || !map.value.getLayer(layerId)) return;
		map.value.setLayoutProperty(
			layerId,
			"visibility",
			visible ? "visible" : "none",
		);
	}

	/** 开启环境叠加层时压低飞机不透明度，让热力/场图层可见（对齐 FR24/FA） */
	function hasFieldOverlay(): boolean {
		return (
			store.showAqiLayer ||
			showAqiHeatmap.value ||
			showTempLayer.value ||
			showDensityLayer.value
		);
	}

	function syncEnvironmentalOverlayMode() {
		const mapInstance = map.value;
		if (!mapInstance?.getLayer(MAP_LAYER_ID)) return;
		const fieldOn = hasFieldOverlay();
		const dim = fieldOn || showGridPoints.value;
		mapInstance.setPaintProperty(
			MAP_LAYER_ID,
			"icon-opacity",
			fieldOn ? 0.22 : dim ? 0.45 : 1,
		);
		if (mapInstance.getLayer("flight-altitude-glow")) {
			mapInstance.setPaintProperty(
				"flight-altitude-glow",
				"circle-opacity",
				fieldOn ? 0 : dim ? 0.08 : 0.22,
			);
		}
	}

	function syncHubHighlightVisibility() {
		if (!map.value) return;
		const hubActive =
			!!selectedHubIata.value &&
			(showHubAirports.value || !!store.scheduleAirport);
		const flightActive = !!(
			store.flightDetail?.departure_airport ||
			store.flightDetail?.arrival_airport
		);
		const vis = hubActive || flightActive;
		setLayerVisibility(MAP_AIRPORT_HIGHLIGHT_LAYER_ID, vis);
		setLayerVisibility(MAP_AIRPORT_HIGHLIGHT_LABEL_ID, vis);
	}

	async function handleSelectFlight(flightId: string | null) {
		await store.selectFlight(flightId);
		store.loadFlightDetail(flightId);
		if (flightId) {
			contextPanelCollapsed.value = false;
			contextTab.value = "detail";
			syncContextPanel();
		}
	}

	function handleHubLocate(iata: string) {
		selectedHubIata.value = iata;
		const ap = store.airports.find((a) => a.iata === iata);
		if (!ap || !map.value) return;
		map.value.flyTo({
			center: [ap.lon, ap.lat],
			zoom: Math.max(map.value.getZoom(), 7),
			essential: true,
		});
		updateAirportHighlight();
	}

	async function handleHubSchedule(iata: string) {
		selectedHubIata.value = iata;
		await store.loadSchedules(iata, "dep");
		contextPanelCollapsed.value = false;
		contextTab.value = "schedule";
		syncContextPanel();
		updateAirportHighlight();
	}

	function toAirQualityGeoJson(
		list: AirQualityHub[],
	): GeoJSON.FeatureCollection<GeoJSON.Point> {
		return {
			type: "FeatureCollection",
			features: list
				.filter((h) => h.aqi > 0 && h.lat && h.lon)
				.map((h) => ({
					type: "Feature",
					geometry: { type: "Point", coordinates: [h.lon, h.lat] },
					properties: { iata: h.iata, aqi: h.aqi, pm2_5: h.pm2_5 ?? null },
				})),
		};
	}

	function updateAqiLayer() {
		if (!map.value) return;
		const src = map.value.getSource(MAP_AQI_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		src?.setData(toAirQualityGeoJson(store.airQualityData));
	}

	function toAirportGeoJson(
		list: AirportInfo[],
	): GeoJSON.FeatureCollection<GeoJSON.Point> {
		return {
			type: "FeatureCollection",
			features: list
				.filter((a) => {
					const pointType =
						a.point_type ?? (a.iata?.startsWith("GRD_") ? "grid" : "hub");
					return pointType !== "grid";
				})
				.map((a) => {
					const pointType =
						a.point_type ?? (a.iata?.startsWith("GRD_") ? "grid" : "hub");
					return {
						type: "Feature",
						geometry: { type: "Point", coordinates: [a.lon, a.lat] },
						properties: {
							iata: a.iata,
							name: a.name,
							point_type: pointType,
							is_hub: a.is_hub ?? pointType === "hub",
						},
					};
				}),
		};
	}

	let hubZoomListenerBound = false;
	let _hubZoomTimer: ReturnType<typeof setTimeout> | null = null;

	function updateHubAirportLayer() {
		if (!map.value) return;
		const zoom = map.value.getZoom();
		const src = map.value.getSource(MAP_AIRPORT_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		src?.setData(toHubAirportGeoJson(store.airports, store.flights, zoom));
		scheduleOverlayLayerOrder(map.value);
		applyMapMarkerLabelStyles(map.value);
	}

	function flightsForMap(): FlightBrief[] {
		if (!store.filtersActive) return store.flights;
		const ids = new Set<string>();
		for (const f of store.filteredFlights) ids.add(f.flight_id);
		if (store.selectedFlightId) ids.add(store.selectedFlightId);
		for (const id of store.markedFlightIds) ids.add(id);
		if (!ids.size) return [];
		return store.flights.filter((f) => ids.has(f.flight_id));
	}

	function syncMapFlightHighlights() {
		if (!map.value) return;
		syncFlightHighlightStates(map.value, MAP_SOURCE_ID, {
			selectedId: store.selectedFlightId,
			markedIds: store.markedFlightIds,
			hoveredId: hoveredFlightId,
		});
	}

	function clearFlightHover(mapInstance: MapLibreMap) {
		hoveredFlightId = null;
		syncFlightHighlightStates(mapInstance, MAP_SOURCE_ID, {
			selectedId: store.selectedFlightId,
			markedIds: store.markedFlightIds,
			hoveredId: null,
		});
		const tip = mapInstance.getSource(MAP_HOVER_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		tip?.setData({ type: "FeatureCollection", features: [] });
	}

	function setFlightHover(
		mapInstance: MapLibreMap,
		feature: GeoJSON.Feature<GeoJSON.Point>,
	) {
		const props = feature.properties ?? {};
		const flightId = props.flight_id;
		if (typeof flightId !== "string" || !flightId) return;

		if (hoveredFlightId === flightId) return;

		hoveredFlightId = flightId;
		syncFlightHighlightStates(mapInstance, MAP_SOURCE_ID, {
			selectedId: store.selectedFlightId,
			markedIds: store.markedFlightIds,
			hoveredId: flightId,
		});

		const altRaw = props.altitude_ft as number | null | undefined;
		const spdRaw = props.speed_kts as number | null | undefined;
		const alt =
			altRaw != null && Number.isFinite(altRaw) ? Math.round(altRaw) : null;
		const spd =
			spdRaw != null && Number.isFinite(spdRaw) ? Math.round(spdRaw) : null;
		const dep = String(props.departure_airport ?? "").trim();
		const arr = String(props.arrival_airport ?? "").trim();
		const l1 = String(props.callsign ?? flightId).trim() || flightId;
		const l2 =
			alt != null && spd != null
				? `${alt}  ${spd}`
				: alt != null
					? String(alt)
					: spd != null
						? String(spd)
						: "";
		const l3 = dep || arr ? `${dep} ${arr}`.trim() : "";

		const tip = mapInstance.getSource(MAP_HOVER_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		tip?.setData({
			type: "FeatureCollection",
			features: [
				{
					type: "Feature",
					geometry: feature.geometry,
					properties: { l1, l2, l3 },
				},
			],
		});
		if (mapInstance.getLayer(MAP_HOVER_LABEL_LAYER_ID)) {
			mapInstance.setLayoutProperty(
				MAP_HOVER_LABEL_LAYER_ID,
				"visibility",
				"visible",
			);
		}
	}

	function flightHoverHitLayers(mapInstance: MapLibreMap): string[] {
		return [MAP_FLIGHT_HOVER_ICON_LAYER_ID, MAP_LAYER_ID].filter((id) =>
			mapInstance.getLayer(id),
		);
	}

	/** 地图级命中：避免珊瑚高亮层盖住 flight-points 后 mouseleave 立刻清除 */
	function bindFlightHoverHandlers(mapInstance: MapLibreMap) {
		if (flightHoverHandlersBound) return;
		flightHoverHandlersBound = true;

		mapInstance.on("mousemove", (event) => {
			const layers = flightHoverHitLayers(mapInstance);
			if (layers.length === 0) return;

			const feature = mapInstance.queryRenderedFeatures(event.point, {
				layers,
			})[0];

			if (!feature || feature.geometry.type !== "Point") {
				clearFlightHover(mapInstance);
				mapInstance.getCanvas().style.cursor = "";
				return;
			}

			mapInstance.getCanvas().style.cursor = "pointer";
			setFlightHover(mapInstance, feature as GeoJSON.Feature<GeoJSON.Point>);
		});

		mapInstance.on("mouseout", () => {
			clearFlightHover(mapInstance);
			mapInstance.getCanvas().style.cursor = "";
		});
	}

	/** 样式/数据变更后再抬一次文字层，避免被底图 symbol 盖住 */
	function scheduleOverlayLayerOrder(mapInstance: MapLibreMap) {
		ensureOverlayLayerOrder(mapInstance);
		applyOverlaySymbolFonts(mapInstance);
		applyMapMarkerLabelStyles(mapInstance);
		if (overlayOrderIdlePending) return;
		overlayOrderIdlePending = true;
		const run = () => {
			overlayOrderIdlePending = false;
			ensureOverlayLayerOrder(mapInstance);
		applyOverlaySymbolFonts(mapInstance);
			applyMapMarkerLabelStyles(mapInstance);
		};
		if (mapInstance.loaded()) {
			mapInstance.once("idle", run);
		} else {
			mapInstance.once("load", () => mapInstance.once("idle", run));
		}
	}

	function scheduleHubAirportLayerUpdate() {
		if (_hubZoomTimer !== null) clearTimeout(_hubZoomTimer);
		_hubZoomTimer = setTimeout(() => {
			_hubZoomTimer = null;
			scheduleMapUpdate(() => updateHubAirportLayer());
		}, 280);
	}

	function bindHubZoomListener(mapInstance: MapLibreMap) {
		if (hubZoomListenerBound) return;
		hubZoomListenerBound = true;
		mapInstance.on("zoomend", scheduleHubAirportLayerUpdate);
	}

	function toWeatherGridCenterGeoJson(
		cells: WeatherGridCell[],
	): GeoJSON.FeatureCollection<GeoJSON.Point> {
		return {
			type: "FeatureCollection",
			features: cells.map((c) => ({
				type: "Feature",
				geometry: {
					type: "Point",
					coordinates: [c.center_lon, c.center_lat],
				},
				properties: {
					id: c.id,
					has_weather: c.has_weather ? 1 : 0,
				},
			})),
		};
	}

	function toWeatherGridGeoJson(
		cells: WeatherGridCell[],
	): GeoJSON.FeatureCollection<GeoJSON.Polygon> {
		return {
			type: "FeatureCollection",
			features: cells.map((c) => ({
				type: "Feature",
				geometry: {
					type: "Polygon",
					coordinates: [
						[
							[c.cell_min_lon, c.cell_min_lat],
							[c.cell_max_lon, c.cell_min_lat],
							[c.cell_max_lon, c.cell_max_lat],
							[c.cell_min_lon, c.cell_max_lat],
							[c.cell_min_lon, c.cell_min_lat],
						],
					],
				},
				properties: {
					id: c.id,
					has_weather: c.has_weather ? 1 : 0,
					flight_count: c.flight_count,
					temperature_c: c.temperature_c ?? null,
					description: c.description ?? "",
				},
			})),
		};
	}

	function updateWeatherGridLayer() {
		if (!map.value) return;
		const cells = weatherGridCells.value;
		const polySrc = map.value.getSource(MAP_GRID_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		polySrc?.setData(toWeatherGridGeoJson(cells));
		const ptSrc = map.value.getSource(MAP_GRID_POINTS_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		ptSrc?.setData(toWeatherGridCenterGeoJson(cells));
	}

	async function refreshWeatherGrid(force = false) {
		let cells: WeatherGridCell[] = [];
		try {
			cells = await fetchWeatherGrid(force);
		} catch {
			cells = [];
		}
		if (cells.length === 0 && store.flights.length > 0) {
			cells = computeWeatherGridFromFlights(store.flights, store.airports);
		}
		try {
			const weatherData = await fetchDatahubWeather(force);
			cells = enrichCellsWithGrdWeather(cells, weatherData);
		} catch {
			// 无天气缓存时保留灰色“待采集”网格
		}
		weatherGridCells.value = cells;
		updateWeatherGridLayer();
	}

	function ensureWeatherGridLayers(
		mapInstance: MapLibreMap,
		beforeId?: string,
	) {
		const anchor =
			beforeId ??
			mapInstance.getStyle().layers.find((l) => l.type === "symbol")?.id;
		if (!mapInstance.getSource(MAP_GRID_SOURCE_ID)) {
			mapInstance.addSource(MAP_GRID_SOURCE_ID, {
				type: "geojson",
				data: toWeatherGridGeoJson(weatherGridCells.value),
			});
		}
		if (!mapInstance.getSource(MAP_GRID_POINTS_SOURCE_ID)) {
			mapInstance.addSource(MAP_GRID_POINTS_SOURCE_ID, {
				type: "geojson",
				data: toWeatherGridCenterGeoJson(weatherGridCells.value),
			});
		}
		if (!mapInstance.getLayer(MAP_GRID_FILL_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_GRID_FILL_LAYER_ID,
					type: "fill",
					source: MAP_GRID_SOURCE_ID,
					layout: {
						visibility: showGridPoints.value ? "visible" : "none",
					},
					paint: weatherGridFillPaint(),
				},
				anchor,
			);
		}
		if (!mapInstance.getLayer(MAP_GRID_LINE_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_GRID_LINE_LAYER_ID,
					type: "line",
					source: MAP_GRID_SOURCE_ID,
					layout: {
						visibility: showGridPoints.value ? "visible" : "none",
					},
					paint: weatherGridOutlinePaint(),
				},
				anchor,
			);
		}
		if (!mapInstance.getLayer(MAP_GRID_MARKER_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_GRID_MARKER_LAYER_ID,
					type: "symbol",
					source: MAP_GRID_POINTS_SOURCE_ID,
					layout: {
					"text-font": ["Noto Sans Regular"],
						visibility: showGridPoints.value ? "visible" : "none",
						...weatherGridMarkerLayout(),
					},
					paint: weatherGridMarkerPaint(),
				},
				anchor,
			);
		}
		updateWeatherGridLayer();
	}

	function startGridRefresh() {
		stopGridRefresh();
		void refreshWeatherGrid(false);
		_gridRefreshTimer = setInterval(() => {
			if (showGridPoints.value) void refreshWeatherGrid(false);
		}, 60_000);
	}

	function stopGridRefresh() {
		if (_gridRefreshTimer !== null) {
			clearInterval(_gridRefreshTimer);
			_gridRefreshTimer = null;
		}
		if (_gridFlightRefreshTimer !== null) {
			clearTimeout(_gridFlightRefreshTimer);
			_gridFlightRefreshTimer = null;
		}
		gridPopup?.remove();
		gridPopup = null;
	}

	function updateAirportHighlight() {
		if (!map.value) return;
		const detail = store.flightDetail;
		const hubIata =
			selectedHubIata.value &&
			(showHubAirports.value || store.scheduleAirport === selectedHubIata.value)
				? selectedHubIata.value
				: null;
		const points = resolveRouteAirports({
			departure_airport: detail?.departure_airport,
			arrival_airport: detail?.arrival_airport,
			departure_lat: detail?.departure_lat,
			departure_lon: detail?.departure_lon,
			arrival_lat: detail?.arrival_lat,
			arrival_lon: detail?.arrival_lon,
			hubIata,
			airportsInStore: store.airports,
		});
		const src = map.value.getSource(MAP_AIRPORT_HIGHLIGHT_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		src?.setData(buildRouteAirportHighlightCollection(points));
		syncHubHighlightVisibility();
	}

	/** 剩余航程示意：当前位置 → 目的地（直线，非历史轨迹） */
	function toRouteGeoJson(): GeoJSON.FeatureCollection<GeoJSON.LineString> {
		return buildPlannedRouteGeoJson({
			flight: store.selectedFlight,
			detail: store.flightDetail,
			trackPoints: store.selectedTrackPoints,
			airports: store.airports,
		});
	}

	function updateRouteLayer() {
		if (!map.value) return;
		const src = map.value.getSource(MAP_ROUTE_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		src?.setData(toRouteGeoJson());
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

		const source = map.value.getSource(MAP_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		if (!source) {
			return;
		}

		const prevIds = flightFeatureIndex
			? new Set(flightFeatureIndex.keys())
			: new Set<string>();
		const { geojson, index, fleetChanged } = patchFlightGeoJson(
			flights,
			flightFeatureIndex,
		);
		flightFeatureIndex = index;

		if (fleetChanged) {
			for (const id of prevIds) {
				if (!index.has(id)) {
					clearFlightFeatureStates(map.value, MAP_SOURCE_ID, [id]);
				}
			}
		}

		source.setData(geojson);
		syncMapFlightHighlights();
		syncEnvironmentalOverlayMode();
		fitToFlights(flights);
	}

	function scheduleFlightLayerUpdate(debounceMs = 0) {
		const run = () => {
			if (!map.value) return;
			updateFlightLayer(flightsForMap());
		};
		if (debounceMs <= 0) {
			scheduleMapUpdate(run);
			return;
		}
		if (_flightUpdateTimer !== null) clearTimeout(_flightUpdateTimer);
		_flightUpdateTimer = setTimeout(() => {
			_flightUpdateTimer = null;
			scheduleMapUpdate(run);
		}, debounceMs);
	}


	function updateTrackLayer() {
		if (!map.value) return;
		const source = map.value.getSource(MAP_TRACK_SEG_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		if (!source) return;
		source.setData(
			buildHistoricalTrackSegmentCollection(
				store.selectedTrackPoints,
				store.selectedFlightId ?? "",
			),
		);
	}

	function updateSelectedFlightHighlight() {
		syncMapFlightHighlights();
	}

	function updateMarkedFlightHighlight() {
		syncMapFlightHighlights();
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

	/** 琥珀金填充 + 细暗描边，避免在沙漠/绿地融入背景 */
	function svgWithAircraftStyle(svgRaw: string, fillColor: string): string {
		const strokeColor = "#140f08";
		const strokeWidth = 42;
		let s = svgRaw
			.replace(/fill="(?!none)[^"]*"/g, `fill="${fillColor}"`)
			.replace(/fill:(?!\s*none)[^;}"']*/g, `fill:${fillColor}`);
		s = s.replace(
			/<path /g,
			`<path stroke="${strokeColor}" stroke-width="${strokeWidth}" stroke-linejoin="round" stroke-linecap="round" paint-order="stroke fill" `,
		);
		return s;
	}

	/** 加载自定义图标并注册到地图实例（SVG → Canvas → ImageData，兼容所有浏览器）*/
	function loadMapIcon(
		mapInstance: MapLibreMap,
		id: string,
		url: string,
	): Promise<void> {
		return new Promise((resolve) => {
			const img = new Image();
			img.onload = () => {
				const w = img.naturalWidth || 256;
				const h = img.naturalHeight || 256;
				const canvas = document.createElement("canvas");
				canvas.width = w;
				canvas.height = h;
				const ctx = canvas.getContext("2d");
				if (!ctx) {
					console.warn(`[MapIcon] 无法创建 Canvas 上下文：${id}`);
					resolve();
					return;
				}
				ctx.drawImage(img, 0, 0, w, h);
				try {
					// 使用 addImage 覆盖已有图标，自动更新
					try {
						mapInstance.addImage(id, ctx.getImageData(0, 0, w, h));
					} catch (updateErr) {
						// addImage 可能抛出"已存在"错误，尝试 updateImage
						if (mapInstance.hasImage(id)) {
							mapInstance.updateImage(id, ctx.getImageData(0, 0, w, h));
						} else {
							throw updateErr;
						}
					}
				} catch (e) {
					console.warn(`[MapIcon] addImage 失败：${id}`, e);
				}
				resolve();
			};
			img.onerror = (e) => {
				console.warn(`[MapIcon] 图片加载失败：${id}`, e);
				resolve();
			};
			img.src = url;
		});
	}

	/**
	 * 加载着色后的 SVG 图标（将填充色替换为 fillColor 后注册）
	 * 若图标已注册则先移除再重新注册，以便颜色能够更新
	 */
	function loadColoredSvgIcon(
		mapInstance: MapLibreMap,
		id: string,
		svgRaw: string,
		fillColor: string,
	): Promise<void> {
		const colored = svgWithAircraftStyle(svgRaw, fillColor);
		const dataUrl =
			"data:image/svg+xml;charset=utf-8," + encodeURIComponent(colored);
		// 先移除已有图标，避免并发更新导致竞态条件
		if (mapInstance.hasImage(id)) {
			try {
				mapInstance.removeImage(id);
			} catch (e) {
				console.warn(`[MapIcon] removeImage 失败: ${id}`, e);
			}
		}
		return loadMapIcon(mapInstance, id, dataUrl);
	}

	/** Official raster annotations remain unchanged; fonts apply to business overlays only. */
	function applyBusinessOverlayFonts(mapInstance: MapLibreMap) {
		applyOverlaySymbolFonts(mapInstance);
	}

	function initMap() {
		if (!mapContainer.value) {
			return;
		}
		// initMap is async internally but we keep its outer signature sync for onMounted
		void (async () => {
			const {
				url: styleUrl,
				provider,
				styleId,
			} = await determineInitialStyle();
			currentProvider.value = provider;
			if (styleId) currentStyleId.value = styleId;

			const mapInstance = new maplibregl.Map({
				container: mapContainer.value!,
				style: styleUrl,
				center: [MAP_INIT_LNG, MAP_INIT_LAT],
				zoom: MAP_INIT_ZOOM,
				minZoom: 1,
				maxZoom: 18,
				attributionControl: { compact: false },
				localIdeographFontFamily:
					"Noto Sans CJK SC, Microsoft YaHei, SimHei, sans-serif",
				refreshExpiredTiles: false,
				maxTileCacheSize: 2048,
				maxTileCacheZoomLevels: 8,
				cancelPendingTileRequestsWhileZooming: false,
				fadeDuration: 150,
			});

			mapInstance.addControl(
				new maplibregl.ScaleControl({ maxWidth: 480, unit: "metric" }),
				"bottom-left",
			);

			mapInstance.on("error", (e) => {
				const sourceId = (e as { sourceId?: string }).sourceId;
				if (!sourceId?.startsWith("tianditu-")) return;
				basemapUnavailable.value = true;
				basemapStatusCode.value = (e.error as { status?: number })?.status;
			});

			mapInstance.on("load", async () => {
				await reinitLayers(mapInstance);
				updateFlightLayer(flightsForMap());
				updateSelectedFlightHighlight();
				updateTrackLayer();
				updateRouteLayer();
			});

			mapInstance.on("rotate", syncMapBearing);
			syncMapBearing();

			map.value = markRaw(mapInstance);
		})();
	}

	/**
	 * Add all custom data sources and layers to the map.
	 * Called after initial load and after every style switch.
	 */
	function addCustomLayers(mapInstance: MapLibreMap) {
		const styleLayers = mapInstance.getStyle().layers;
		const firstSymbolLayer = styleLayers.find((l) => /^tianditu-(cva|cia|cta)$/.test(l.id));

		// ── Weather / wind / temp source ────────────────────────────────────────
		if (!mapInstance.getSource(MAP_WIND_SOURCE_ID)) {
			mapInstance.addSource(MAP_WIND_SOURCE_ID, {
				type: "geojson",
				data: toWeatherGeoJson(),
			});
		}

		// Temperature circles (hidden by default)
		if (!mapInstance.getLayer(MAP_TEMP_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_TEMP_LAYER_ID,
				type: "circle",
				source: MAP_WIND_SOURCE_ID,
				layout: { visibility: "none" },
				paint: tempCirclePaint(),
			});
		}

		// ── Flight density heatmap source = MAP_SOURCE_ID (already added) ────────
		// Added as a heatmap layer using the same flights geojson source.
		// We'll add it after MAP_SOURCE_ID is added below.

		// ── Airport source（图层在飞机之上，见 flight-points 之后）──────────────
		if (!mapInstance.getSource(MAP_AIRPORT_SOURCE_ID)) {
			mapInstance.addSource(MAP_AIRPORT_SOURCE_ID, {
				type: "geojson",
				data: toHubAirportGeoJson(
					store.airports,
					store.flights,
					mapInstance.getZoom(),
				),
			});
		}
		ensureWeatherGridLayers(mapInstance, firstSymbolLayer?.id);

		if (!mapInstance.getSource(MAP_AIRPORT_HIGHLIGHT_SOURCE_ID)) {
			mapInstance.addSource(MAP_AIRPORT_HIGHLIGHT_SOURCE_ID, {
				type: "geojson",
				data: toAirportGeoJson([]),
			});
		}

		// ── AQI source & layers ────────────────────────────────────────────────
		if (!mapInstance.getSource(MAP_AQI_SOURCE_ID)) {
			mapInstance.addSource(MAP_AQI_SOURCE_ID, {
				type: "geojson",
				data: toAirQualityGeoJson(store.airQualityData),
			});
		}

		// AQI heatmap (PM2.5 weight, hidden by default) — 背景数据层，置于地图标注之下
		if (!mapInstance.getLayer(MAP_AQI_HEATMAP_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_AQI_HEATMAP_LAYER_ID,
					type: "heatmap",
					source: MAP_AQI_SOURCE_ID,
					layout: { visibility: "none" },
					paint: aqiHeatmapPaint(),
				},
				firstSymbolLayer?.id,
			);
		}

		if (!mapInstance.getLayer(MAP_AQI_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AQI_LAYER_ID,
				type: "circle",
				source: MAP_AQI_SOURCE_ID,
				layout: { visibility: store.showAqiLayer ? "visible" : "none" },
				paint: aqiCirclePaint(),
			});
		}

		if (!mapInstance.getLayer(MAP_AQI_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AQI_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_AQI_SOURCE_ID,
				layout: {
					"text-font": ["Noto Sans Regular"],
					visibility: store.showAqiLayer ? "visible" : "none",
					...aqiLabelLayout(),
				},
				paint: aqiLabelPaint(),
			});
		}

		// ── Flights source & layers ───────────────────────────────────────────────
		if (!mapInstance.getSource(MAP_SOURCE_ID)) {
			const initial = patchFlightGeoJson(flightsForMap(), null);
			flightFeatureIndex = initial.index;
			mapInstance.addSource(MAP_SOURCE_ID, {
				type: "geojson",
				promoteId: "flight_id",
				data: initial.geojson,
			});
		}

		if (!mapInstance.getSource(MAP_HOVER_SOURCE_ID)) {
			mapInstance.addSource(MAP_HOVER_SOURCE_ID, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
		}

		if (!mapInstance.getLayer(MAP_TEMP_HEATMAP_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_TEMP_HEATMAP_LAYER_ID,
					type: "heatmap",
					source: MAP_WIND_SOURCE_ID,
					layout: { visibility: "none" },
					paint: tempHeatmapPaint(),
				},
				firstSymbolLayer?.id,
			);
		}

		// Flight density heatmap (hidden by default) — 背景层，置于地图标注之下
		if (!mapInstance.getLayer(MAP_DENSITY_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_DENSITY_LAYER_ID,
					type: "heatmap",
					source: MAP_SOURCE_ID,
					layout: { visibility: "none" },
					paint: flightDensityHeatmapPaint(),
				},
				firstSymbolLayer?.id,
			);
		}

		// Selected flight highlight
		// NOTE: feature-state is NOT supported in MapLibre filter expressions (v4+);
		// use paint opacity expressions to show/hide per-feature instead.
		if (!mapInstance.getLayer(MAP_SELECTED_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_SELECTED_LAYER_ID,
				type: "circle",
				source: MAP_SOURCE_ID,
				paint: {
					"circle-radius": 14,
					"circle-color": "#f59e0b",
					"circle-opacity": [
						"case",
						["boolean", ["feature-state", "selected"], false],
						0.8,
						0,
					],
					"circle-stroke-width": 0,
				},
			});
		}

		if (!mapInstance.getLayer(MAP_MARKED_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_MARKED_LAYER_ID,
				type: "circle",
				source: MAP_SOURCE_ID,
				paint: {
					"circle-radius": 20,
					"circle-color": "rgba(244, 63, 94, 0.12)",
					"circle-stroke-color": "#fb7185",
					"circle-stroke-width": [
						"case",
						["boolean", ["feature-state", "marked"], false],
						3,
						0,
					],
					"circle-opacity": [
						"case",
						["boolean", ["feature-state", "marked"], false],
						1,
						0,
					],
				},
			});
		}

		// 清理重构期间产生的错误图层 id，避免与当前 planned-route 冲突
		for (const legacyLayerId of [
			"skytrace-remaining-route-line",
			"skytrace-remaining-route-glow",
			"flight-track-planned",
			"flight-track-planned-glow",
		]) {
			if (mapInstance.getLayer(legacyLayerId)) {
				try {
					mapInstance.removeLayer(legacyLayerId);
				} catch {
					/* ignore */
				}
			}
		}
		for (const legacySourceId of [
			"skytrace-remaining-route-geo",
			"geo-flight-planned-route",
			"flight-track-planned-src",
		]) {
			if (mapInstance.getSource(legacySourceId)) {
				try {
					mapInstance.removeSource(legacySourceId);
				} catch {
					/* ignore */
				}
			}
		}

		// 剩余航程（早期可工作方案：独立 source + 单层 line，仅 setData 更新）
		if (!mapInstance.getSource(MAP_ROUTE_SOURCE_ID)) {
			mapInstance.addSource(MAP_ROUTE_SOURCE_ID, {
				type: "geojson",
				data: toRouteGeoJson(),
			});
		}
		if (!mapInstance.getLayer(MAP_ROUTE_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_ROUTE_LAYER_ID,
				type: "line",
				source: MAP_ROUTE_SOURCE_ID,
				layout: { "line-cap": "round", "line-join": "round" },
				paint: {
					"line-color": "#22d3ee",
					"line-width": 3,
					"line-opacity": 0.92,
					"line-dasharray": [2, 2.5],
				},
			});
		}

		if (!mapInstance.getSource(MAP_TRACK_SEG_SOURCE_ID)) {
			mapInstance.addSource(MAP_TRACK_SEG_SOURCE_ID, {
				type: "geojson",
				data: buildHistoricalTrackSegmentCollection(
					store.selectedTrackPoints,
					store.selectedFlightId ?? "",
				),
			});
		}
		if (!mapInstance.getLayer(TRACK_HISTORY_SEG_LAYER_ID)) {
			mapInstance.addLayer({
				id: TRACK_HISTORY_SEG_LAYER_ID,
				type: "line",
				source: MAP_TRACK_SEG_SOURCE_ID,
				layout: { "line-cap": "round", "line-join": "round" },
				paint: historicalTrackSegmentLinePaint(),
			});
		}

		// ── Region filter highlight — 行政区划边界（置于地图标注之下）──────────────────
		if (!mapInstance.getSource(MAP_REGION_HIGHLIGHT_SOURCE)) {
			mapInstance.addSource(MAP_REGION_HIGHLIGHT_SOURCE, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
		}
		if (!mapInstance.getLayer(MAP_REGION_HIGHLIGHT_FILL_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_REGION_HIGHLIGHT_FILL_ID,
					type: "fill",
					source: MAP_REGION_HIGHLIGHT_SOURCE,
					paint: regionHighlightFillPaint(),
				},
				firstSymbolLayer?.id,
			);
		}
		if (!mapInstance.getLayer(MAP_REGION_HIGHLIGHT_GLOW_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_REGION_HIGHLIGHT_GLOW_ID,
					type: "line",
					source: MAP_REGION_HIGHLIGHT_SOURCE,
					paint: regionHighlightGlowPaint(),
				},
				firstSymbolLayer?.id,
			);
		}
		if (!mapInstance.getLayer(MAP_REGION_HIGHLIGHT_LINE_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_REGION_HIGHLIGHT_LINE_ID,
					type: "line",
					source: MAP_REGION_HIGHLIGHT_SOURCE,
					paint: regionHighlightLinePaint(),
				},
				firstSymbolLayer?.id,
			);
		}

		// 海拔高度晕染圈（在飞机图标之下，按高度着色）— 参考 FlightAware/FR24 配色
		if (!mapInstance.getLayer("flight-altitude-glow")) {
			mapInstance.addLayer(
				{
					id: "flight-altitude-glow",
					type: "circle",
					source: MAP_SOURCE_ID,
					paint: {
						"circle-radius": [
							"interpolate",
							["linear"],
							["zoom"],
							3,
							5,
							8,
							9,
							12,
							14,
						],
						"circle-opacity": 0.22,
						"circle-blur": 0.8,
						"circle-pitch-alignment": "viewport",
						"circle-color": [
							"interpolate",
							["linear"],
							["coalesce", ["get", "altitude_ft"], 0],
							0,
							"#6b7280",
							1000,
							"#fbbf24",
							10000,
							"#f97316",
							25000,
							"#60a5fa",
							38000,
							"#06b6d4",
						],
					},
				},
				firstSymbolLayer?.id,
			);
		}

		// 飞机图标图层 — 在天气/网格之上、枢纽之下；标注层仍在其上
		if (!mapInstance.getLayer(MAP_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_LAYER_ID,
					type: "symbol",
					source: MAP_SOURCE_ID,
					layout: {
					"text-font": ["Noto Sans Regular"],
						"icon-image": flightIconImageLayout(),
						"icon-size": flightIconSizeLayout(),
						"icon-rotate": ["coalesce", ["get", "heading"], 0],
						"icon-rotation-alignment": "map",
						"icon-pitch-alignment": "viewport",
						"icon-allow-overlap": true,
						"icon-ignore-placement": true,
					},
					paint: {
						"icon-halo-color": "rgba(20, 15, 8, 0.92)",
						"icon-halo-width": 1.25,
						"icon-opacity": 1,
					},
				},
				firstSymbolLayer?.id,
			);
		} else {
			mapInstance.setLayoutProperty(
				MAP_LAYER_ID,
				"icon-image",
				flightIconImageLayout(),
			);
			mapInstance.setLayoutProperty(
				MAP_LAYER_ID,
				"icon-size",
				flightIconSizeLayout(),
			);
		}

		if (!mapInstance.getLayer(MAP_FLIGHT_HOVER_ICON_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_FLIGHT_HOVER_ICON_LAYER_ID,
				type: "symbol",
				source: MAP_SOURCE_ID,
				// NOTE: feature-state is NOT supported in MapLibre filter expressions (v4+);
				// use icon-opacity paint expression instead.
				layout: {
					"text-font": ["Noto Sans Regular"],
					"icon-image": flightHoverIconImageLayout(),
					"icon-size": flightIconSizeLayout(),
					"icon-rotate": ["coalesce", ["get", "heading"], 0],
					"icon-rotation-alignment": "map",
					"icon-pitch-alignment": "viewport",
					"icon-allow-overlap": true,
					"icon-ignore-placement": true,
				},
				paint: {
					"icon-halo-color": "rgba(20, 15, 8, 0.92)",
					"icon-halo-width": 1.25,
					"icon-opacity": [
						"case",
						["boolean", ["feature-state", "hover"], false],
						1,
						0,
					],
				},
			});
		}

		// 枢纽机场 — 高饱和实心圆 + 黄字黑 halo，置于飞机之上
		if (!mapInstance.getLayer(MAP_AIRPORT_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_AIRPORT_LAYER_ID,
					type: "circle",
					source: MAP_AIRPORT_SOURCE_ID,
					filter: ["!=", ["get", "point_type"], "grid"],
					layout: {
						visibility: showHubAirports.value ? "visible" : "none",
					},
					paint: hubAirportCirclePaint(),
				},
				firstSymbolLayer?.id,
			);
		}
		if (!mapInstance.getLayer(MAP_AIRPORT_HIGHLIGHT_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AIRPORT_HIGHLIGHT_LAYER_ID,
				type: "circle",
				source: MAP_AIRPORT_HIGHLIGHT_SOURCE_ID,
				paint: routeAirportHighlightPaint(),
			});
		}

		applyPremiumOverlayStyles(mapInstance, currentProvider.value);

		// ── 文字标注层：一律不加 beforeId，创建后再统一抬到栈顶 ────────────────
		if (!mapInstance.getLayer(MAP_WIND_ARROW_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_WIND_ARROW_LAYER_ID,
				type: "symbol",
				source: MAP_WIND_SOURCE_ID,
				layout: {
					"text-font": ["Noto Sans Regular"],
					visibility: showWindLayer.value ? "visible" : "none",
					...windArrowLayout(),
				},
				paint: windArrowPaint(),
			});
		}

		if (!mapInstance.getLayer(MAP_WIND_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_WIND_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_WIND_SOURCE_ID,
				layout: {
					"text-font": ["Noto Sans Regular"],
					visibility: showWindLayer.value ? "visible" : "none",
					...windLabelLayout(),
				},
				paint: windLabelPaint(),
			});
		}

		if (!mapInstance.getLayer(MAP_AIRPORT_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AIRPORT_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_AIRPORT_SOURCE_ID,
				layout: {
					"text-font": ["Noto Sans Regular"],
					visibility: showHubAirports.value ? "visible" : "none",
					...hubAirportLabelLayout(),
				},
				paint: hubAirportLabelPaint(),
			});
		}

		if (!mapInstance.getLayer(MAP_AIRPORT_HIGHLIGHT_LABEL_ID)) {
			mapInstance.addLayer({
				id: MAP_AIRPORT_HIGHLIGHT_LABEL_ID,
				type: "symbol",
				source: MAP_AIRPORT_HIGHLIGHT_SOURCE_ID,
				layout: {
					"text-font": ["Noto Sans Regular"],
					visibility: "none",
					...hubAirportHighlightLabelLayout(),
				},
				paint: hubAirportLabelPaint(),
			});
		}

		if (!mapInstance.getLayer(MAP_HOVER_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_HOVER_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_HOVER_SOURCE_ID,
				layout: {
					"text-font": ["Noto Sans Regular"],
					...flightHoverLabelLayout(),
					visibility: "visible",
					"symbol-placement": "point",
				},
				paint: flightHoverLabelPaint(),
			});
		}

		scheduleOverlayLayerOrder(mapInstance);
		applyMapMarkerLabelStyles(mapInstance);
		syncEnvironmentalOverlayMode();
		syncHubHighlightVisibility();
		bindHubZoomListener(mapInstance);
		bindFlightHoverHandlers(mapInstance);

		// Events
		mapInstance.on("click", MAP_LAYER_ID, (event) => {
			const feature = event.features?.[0];
			if (!feature || feature.geometry.type !== "Point") return;
			const flightId = feature.properties?.flight_id;
			if (typeof flightId === "string") handleSelectFlight(flightId);
		});

		const handleAirportPointClick = (event: maplibregl.MapLayerMouseEvent) => {
			if (!showHubAirports.value) return;
			const feature = event.features?.[0];
			if (!feature) return;
			const iata = feature.properties?.iata as string | undefined;
			if (!iata) return;
			if (selectedHubIata.value === iata && store.scheduleAirport === iata) {
				clearHubFocus();
				return;
			}
			selectedHubIata.value = iata;
			void store.loadSchedules(iata, "dep");
			contextTab.value = "schedule";
			syncContextPanel();
		};
		mapInstance.on("click", MAP_AIRPORT_LAYER_ID, handleAirportPointClick);
		mapInstance.on("mouseenter", MAP_AIRPORT_LAYER_ID, () => {
			mapInstance.getCanvas().style.cursor = "pointer";
		});
		mapInstance.on("mouseleave", MAP_AIRPORT_LAYER_ID, () => {
			mapInstance.getCanvas().style.cursor = "";
		});

		const handleGridCellClick = (event: maplibregl.MapLayerMouseEvent) => {
			const feature = event.features?.[0];
			if (!feature) return;
			const props = feature.properties ?? {};
			const id = String(props.id ?? ui.value.grid);
			const flightCount = Number(props.flight_count ?? 0);
			const hasWeather = Boolean(props.has_weather);
			const temp = props.temperature_c;
			const desc = String(props.description ?? "").trim();
			let weatherLine = `${ui.value.weather}: ${ui.value.weatherPending}`;
			if (hasWeather) {
				const parts: string[] = [];
				if (temp != null && temp !== "") parts.push(`${temp}°C`);
				if (desc) parts.push(formatWeatherDescription(desc, localeStore.locale) || "");
				weatherLine = `${ui.value.weather}: ${parts.join(" ") || ui.value.collected}`;
			}
			if (!gridPopup) {
				gridPopup = new maplibregl.Popup({
					closeButton: true,
					maxWidth: "300px",
				});
			}
			const content = document.createElement("div");
			content.style.cssText = "font-size:13px;line-height:1.55";
			for (const line of [id, `${ui.value.flightsInArea}: ${flightCount} ${ui.value.unitFlights}`, weatherLine]) {
				const row = document.createElement("div");
				row.textContent = line;
				content.appendChild(row);
			}
			gridPopup.setLngLat(event.lngLat).setDOMContent(content).addTo(mapInstance);
		};
		mapInstance.on("click", MAP_GRID_FILL_LAYER_ID, handleGridCellClick);
		mapInstance.on("mouseenter", MAP_GRID_FILL_LAYER_ID, () => {
			mapInstance.getCanvas().style.cursor = "pointer";
		});
		mapInstance.on("mouseleave", MAP_GRID_FILL_LAYER_ID, () => {
			mapInstance.getCanvas().style.cursor = "";
		});
	}

	// WS 快照：较长防抖；筛选变化：立即合并到同一 RAF 批次
	watch(
		() => store.flights,
		() => {
			if (map.value) clearFlightHover(map.value);
			scheduleFlightLayerUpdate(1200);
		},
	);

	watch(
		() => [store.filteredFlights, store.filtersActive] as const,
		() => {
			if (map.value) clearFlightHover(map.value);
			scheduleFlightLayerUpdate(0);
		},
	);

	watch(
		() => [...store.markedFlightIds],
		() => {
			if (!map.value) return;
			if (hoveredFlightId && !store.markedFlightIds.includes(hoveredFlightId)) {
				clearFlightHover(map.value);
			}
			syncMapFlightHighlights();
			if (store.filtersActive) {
				scheduleFlightLayerUpdate(0);
			}
		},
	);


	/** Region bounds locate the view only; they are never rendered as administrative borders. */
	async function applyRegionFilterHighlight(
		cc: string | null, regionCode: string | null, cityCode: string | null, districtCode: string | null,
	) {
		if (!map.value) return;
		const src = map.value.getSource(MAP_REGION_HIGHLIGHT_SOURCE) as GeoJSONSource | undefined;
		src?.setData({ type: "FeatureCollection", features: [] });
		if (!cc) return;
		const bbox = resolveGeoBBox(cc, regionCode, cityCode, districtCode);
		if (bbox) map.value.fitBounds([[bbox.lonMin, bbox.latMin], [bbox.lonMax, bbox.latMax]], {
			padding: 48, maxZoom: 10, duration: 800, essential: true,
		});
	}

	watch(
		() =>
			[
				store.filterCountry,
				store.filterRegion,
				store.filterCity,
				store.filterDistrict,
			] as const,
		([cc, region, city, district]) => {
			void applyRegionFilterHighlight(cc, region, city, district);
		},
	);

	watch(
		() => store.selectedFlight,
		(flight) => {
			updateSelectedFlightHighlight();
			focusSelectedFlight(flight);
			updateRouteLayer();
		},
	);

	watch(
		() => store.selectedFlightId,
		() => {
			updateRouteLayer();
		},
	);

	watch(
		() => store.selectedTrackPoints,
		() => {
			updateTrackLayer();
			updateRouteLayer();
		},
	);

	watch(
		() => store.flightDetail,
		() => {
			updateAirportHighlight();
			updateRouteLayer();
		},
	);

	let _hubDataTimer: ReturnType<typeof setTimeout> | null = null;
	watch(
		() => [store.airports, store.flights.length] as const,
		() => {
			if (_hubDataTimer !== null) clearTimeout(_hubDataTimer);
			_hubDataTimer = setTimeout(() => {
				_hubDataTimer = null;
				scheduleMapUpdate(() => {
					updateHubAirportLayer();
					updateRouteLayer();
				});
			}, 500);
		},
	);

	// AQI：FA 式连续场（热力图为主，离散点仅高 zoom 辅助）
	watch(
		() => store.showAqiLayer,
		(show) => {
			if (show) showAqiHeatmap.value = true;
			setLayerVisibility(
				MAP_AQI_HEATMAP_LAYER_ID,
				show || showAqiHeatmap.value,
			);
			setLayerVisibility(MAP_AQI_LAYER_ID, false);
			setLayerVisibility(MAP_AQI_LABEL_LAYER_ID, false);
			syncEnvironmentalOverlayMode();
			if (map.value) ensureOverlayLayerOrder(map.value);
		},
	);

	watch(showAqiHeatmap, (show) => {
		setLayerVisibility(MAP_AQI_HEATMAP_LAYER_ID, show || store.showAqiLayer);
		syncEnvironmentalOverlayMode();
		if (map.value) ensureOverlayLayerOrder(map.value);
	});

	// 风速风向图层
	watch(showWindLayer, async (show) => {
		if (show && weatherHubs.value.length === 0) await loadWeatherHubs();
		updateWeatherLayer();
		setLayerVisibility(MAP_WIND_ARROW_LAYER_ID, show);
		setLayerVisibility(MAP_WIND_LABEL_LAYER_ID, show);
		syncEnvironmentalOverlayMode();
		if (map.value) {
			scheduleOverlayLayerOrder(map.value);
			applyMapMarkerLabelStyles(map.value);
		}
	});

	// 温度图层（连续温度场热力图，非离散气泡）
	watch(showTempLayer, async (show) => {
		if (show && weatherHubs.value.length === 0) await loadWeatherHubs();
		updateWeatherLayer();
		setLayerVisibility(MAP_TEMP_HEATMAP_LAYER_ID, show);
		setLayerVisibility(MAP_TEMP_LAYER_ID, false);
		syncEnvironmentalOverlayMode();
		if (map.value) ensureOverlayLayerOrder(map.value);
	});

	// 航班密度热力图
	watch(showDensityLayer, (show) => {
		setLayerVisibility(MAP_DENSITY_LAYER_ID, show);
		syncEnvironmentalOverlayMode();
		if (map.value) ensureOverlayLayerOrder(map.value);
	});

	// 枢纽机场与网格观测点分层开关
	watch(showHubAirports, (show) => {
		if (!show) clearHubFocus();
		setLayerVisibility(MAP_AIRPORT_LAYER_ID, show);
		setLayerVisibility(MAP_AIRPORT_LABEL_LAYER_ID, show);
		syncHubHighlightVisibility();
		if (map.value && show) applyMapMarkerLabelStyles(map.value);
		if (map.value) ensureOverlayLayerOrder(map.value);
	});
	watch(showGridPoints, (show) => {
		const mapInstance = map.value;
		if (mapInstance) {
			ensureWeatherGridLayers(mapInstance);
		}
		setLayerVisibility(MAP_GRID_FILL_LAYER_ID, show);
		setLayerVisibility(MAP_GRID_LINE_LAYER_ID, show);
		setLayerVisibility(MAP_GRID_MARKER_LAYER_ID, show);
		syncEnvironmentalOverlayMode();
		if (mapInstance) ensureOverlayLayerOrder(mapInstance);
		if (mapInstance) applyOverlaySymbolFonts(mapInstance);
		if (show) {
			void refreshWeatherGrid(false);
			startGridRefresh();
		} else {
			stopGridRefresh();
		}
	});

	watch(
		() => store.flights.length,
		() => {
			if (!showGridPoints.value) return;
			if (_gridFlightRefreshTimer !== null) {
				clearTimeout(_gridFlightRefreshTimer);
			}
			_gridFlightRefreshTimer = setTimeout(() => {
				_gridFlightRefreshTimer = null;
				void refreshWeatherGrid(false);
			}, 1500);
		},
	);

	// AQI 数据更新（浅监听，避免 deep watch 全量扫描）
	watch(
		() => store.airQualityData.length,
		() => {
			scheduleMapUpdate(() => updateAqiLayer());
		},
	);


	// 选中航班时自动切换到详情 tab
	watch(
		() => store.detailLoading,
		(loading) => {
			if (loading) {
				contextTab.value = "detail";
				syncContextPanel();
			}
		},
	);

	watch(selectedHubIata, () => {
		updateAirportHighlight();
	});
	watch(
		() => store.scheduleAirport,
		() => {
			updateAirportHighlight();
		},
	);

	watch(contextPanelOpen, () => syncContextPanel());
	watch(sidebarCollapsed, () => onSidebarCollapse());

	onMounted(async () => {
		initMap();
		await store.loadInitialFlights();
		store.connectSocket();
		store.loadAirports();
		store.loadAirQuality();
		// Pre-load weather hub data in background
		loadWeatherHubs();
	});

	onUnmounted(() => {
		if (_flightUpdateTimer !== null) {
			clearTimeout(_flightUpdateTimer);
			_flightUpdateTimer = null;
		}
		if (_hubZoomTimer !== null) {
			clearTimeout(_hubZoomTimer);
			_hubZoomTimer = null;
		}
		if (_hubDataTimer !== null) {
			clearTimeout(_hubDataTimer);
			_hubDataTimer = null;
		}
		cancelScheduledMapUpdates();
		resetFlightFeatureStateTracking();
		flightFeatureIndex = null;
		flightHoverHandlersBound = false;
		overlayOrderIdlePending = false;
		stopGridRefresh();
		store.disconnectSocket();
		placeLabels?.dispose();
		map.value?.remove();
		map.value = null;
	});
</script>

<style scoped>
	.map-layout {
		height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--bg-base);
		overflow: hidden;
	}

	.map-workspace {
		flex: 1;
		display: flex;
		min-height: 0;
		overflow: hidden;
	}

	.map-shell {
		flex: 1;
		position: relative;
		min-width: 0;
		background: #0f1419;
		contain: layout;
	}

	.map-canvas {
		width: 100%;
		height: 100%;
	}

	.map-basemap-status {
		position: absolute; left: 16px; bottom: 40px; z-index: 5;
		padding: 8px 12px; max-width: calc(100% - 32px);
		background: var(--bg-surface); color: var(--warning); border-radius: 8px;
		font-size: 12px; pointer-events: none;
	}

	.map-status {
		position: absolute;
		left: 16px;
		bottom: 48px;
		padding: 8px 12px;
		border-radius: var(--radius-md);
		background: var(--bg-surface);
		border: 1px solid var(--border);
		color: var(--text-primary);
		font-size: 13px;
		box-shadow: var(--shadow-sm);
	}

	:global(.maplibregl-ctrl-bottom-left) {
		left: 12px;
		bottom: 12px;
	}

	:global(.maplibregl-ctrl-bottom-left .maplibregl-ctrl-scale) {
		border: 1px solid var(--border);
		border-top: 2px solid var(--text-muted);
		background: var(--bg-surface);
		color: var(--text-secondary);
		font-size: 11px;
		padding: 2px 6px;
		border-radius: var(--radius-sm);
	}
</style>
