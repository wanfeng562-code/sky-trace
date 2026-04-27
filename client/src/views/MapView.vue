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
	import { computed, onMounted, onUnmounted, ref, watch } from "vue";
	import maplibregl, {
		type GeoJSONSource,
		type LngLatBoundsLike,
		type Map as MapLibreMap,
	} from "maplibre-gl";
	import "maplibre-gl/dist/maplibre-gl.css";
	import planeIconUrl from "../icons/plane.svg?url";
	import planeGroundIconUrl from "../icons/plane_ground.svg?url";

	import FlightDetailCard from "../components/FlightDetailCard.vue";
	import FlightListPanel from "../components/FlightListPanel.vue";
	import { useFlightStore } from "../stores/flight";
	import type { AirportInfo, FlightBrief } from "../types/flight";

	const MAP_SOURCE_ID = "flights";
	const MAP_LAYER_ID = "flight-points";
	const MAP_SELECTED_LAYER_ID = "selected-flight-point";
	const MAP_TRACK_SOURCE_ID = "selected-flight-track";
	const MAP_TRACK_LAYER_ID = "selected-flight-track-line";
	const MAP_AIRPORT_SOURCE_ID = "airports";
	const MAP_AIRPORT_LAYER_ID = "airport-points";
	const MAP_AIRPORT_LABEL_LAYER_ID = "airport-labels";
	const MAP_AIRPORT_HIGHLIGHT_SOURCE_ID = "airports-highlight";
	const MAP_AIRPORT_HIGHLIGHT_LAYER_ID = "airport-highlight-points";
	const MAP_AIRPORT_HIGHLIGHT_LABEL_ID = "airport-highlight-labels";

	const store = useFlightStore();
	const mapContainer = ref<HTMLElement | null>(null);
	const map = ref<MapLibreMap | null>(null);
	const hasFittedInitialBounds = ref(false);
	/** 防抖计时器：避免 WS 快照连续触发时每次都重建 GeoJSON */
	let _flightUpdateTimer: ReturnType<typeof setTimeout> | null = null;

	async function handleSelectFlight(flightId: string | null) {
		await store.selectFlight(flightId);
		store.loadFlightDetail(flightId);
	}

	function toAirportGeoJson(
		list: AirportInfo[],
	): GeoJSON.FeatureCollection<GeoJSON.Point> {
		return {
			type: "FeatureCollection",
			features: list.map((a) => ({
				type: "Feature",
				geometry: { type: "Point", coordinates: [a.lon, a.lat] },
				properties: { iata: a.iata, name: a.name },
			})),
		};
	}

	function updateAirportHighlight() {
		if (!map.value) return;
		const detail = store.flightDetail;
		const depIata = detail?.departure_airport ?? null;
		const arrIata = detail?.arrival_airport ?? null;
		const highlighted = store.airports.filter(
			(a) => a.iata === depIata || a.iata === arrIata,
		);
		const src = map.value.getSource(MAP_AIRPORT_HIGHLIGHT_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		src?.setData(toAirportGeoJson(highlighted));
	}

	function toGeoJson(
		flights: FlightBrief[],
	): GeoJSON.FeatureCollection<GeoJSON.Point> {
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

		const source = map.value.getSource(MAP_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
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
		// 同时排除聚合节点，避免在低缩放级别下误匹配
		map.value.setFilter(
			MAP_SELECTED_LAYER_ID,
			selectedId
				? ["==", ["get", "flight_id"], selectedId]
				: ["==", ["get", "flight_id"], ""],
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
					if (!mapInstance.hasImage(id)) {
						mapInstance.addImage(id, ctx.getImageData(0, 0, w, h));
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

	/** 将地图中所有地名标注改为英文（上）+ 中文（下）并列 */
	function applyBilingualLabels(mapInstance: MapLibreMap) {
		const style = mapInstance.getStyle();
		for (const layer of style.layers) {
			if (layer.type !== "symbol") continue;
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const layout = (layer as any).layout ?? {};
			const field = layout["text-field"];
			if (!field) continue;
			const fieldStr = JSON.stringify(field);
			// 只处理引用 name 字段的图层
			if (!fieldStr.match(/"name/)) continue;
			// 跳过路牌、路线编号等非地名图层
			if (/"ref"/.test(fieldStr)) continue;
			if (
				layer.id.includes("shield") ||
				layer.id.includes("route") ||
				layer.id.includes("-ref")
			)
				continue;
			mapInstance.setLayoutProperty(layer.id, "text-field", [
				"case",
				// 优先使用简体中文字段，避免 name:zh 含「简/繁」混合
				[
					"!=",
					["coalesce", ["get", "name:zh-Hans"], ["get", "name:zh"], ""],
					"",
				],
				[
					"concat",
					["coalesce", ["get", "name_en"], ["get", "name"], ""],
					"\n",
					["coalesce", ["get", "name:zh-Hans"], ["get", "name:zh"], ""],
				],
				["coalesce", ["get", "name_en"], ["get", "name"], ""],
			]);
		}
	}

	function initMap() {
		if (!mapContainer.value) {
			return;
		}

		const mapInstance = new maplibregl.Map({
			container: mapContainer.value,
			style: "https://tiles.openfreemap.org/styles/liberty",
			center: [113.2644, 23.1291],
			zoom: 4,
			attributionControl: true,
		});

		mapInstance.addControl(new maplibregl.NavigationControl(), "top-right");
		mapInstance.addControl(
			new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }),
			"bottom-right",
		);

		mapInstance.on("load", async () => {
			// 双语地名：英文在上，中文在下
			applyBilingualLabels(mapInstance);

			// 地形晒渲（AWS 唔不需要 API Key 的免费 DEM 源）
			mapInstance.addSource("terrain-dem", {
				type: "raster-dem",
				tiles: [
					"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
				],
				tileSize: 256,
				encoding: "terrarium",
				maxzoom: 14,
			});
			const styleLayers = mapInstance.getStyle().layers;
			const firstSymbolLayer = styleLayers.find((l) => l.type === "symbol");
			mapInstance.addLayer(
				{
					id: "terrain-hillshade",
					type: "hillshade",
					source: "terrain-dem",
					paint: {
						"hillshade-intensity": 0.35,
						"hillshade-shadow-color": "#5a4630",
						"hillshade-highlight-color": "#ffffff",
						"hillshade-accent-color": "#5a4630",
					},
				},
				firstSymbolLayer?.id,
			);

			// 加载飞机 SVG 图标
			await Promise.all([
				loadMapIcon(mapInstance, "icon-plane", planeIconUrl),
				loadMapIcon(mapInstance, "icon-plane-ground", planeGroundIconUrl),
			]);

			mapInstance.addSource(MAP_SOURCE_ID, {
				type: "geojson",
				data: toGeoJson(store.flights),
			});

			// 机场图层（所有枢纽机场）
			mapInstance.addSource(MAP_AIRPORT_SOURCE_ID, {
				type: "geojson",
				data: toAirportGeoJson(store.airports),
			});

			mapInstance.addLayer({
				id: MAP_AIRPORT_LAYER_ID,
				type: "circle",
				source: MAP_AIRPORT_SOURCE_ID,
				paint: {
					"circle-radius": 5,
					"circle-color": "#6b7280",
					"circle-stroke-width": 1.5,
					"circle-stroke-color": "#ffffff",
				},
			});

			mapInstance.addLayer({
				id: MAP_AIRPORT_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_AIRPORT_SOURCE_ID,
				layout: {
					"text-field": ["get", "iata"],
					"text-size": 11,
					"text-anchor": "top",
					"text-offset": [0, 0.6],
					"text-font": ["Noto Sans Regular"],
				},
				paint: {
					"text-color": "#374151",
					"text-halo-color": "#ffffff",
					"text-halo-width": 1.5,
				},
			});

			// 选中航班的出发/到达机场高亮图层
			mapInstance.addSource(MAP_AIRPORT_HIGHLIGHT_SOURCE_ID, {
				type: "geojson",
				data: toAirportGeoJson([]),
			});

			mapInstance.addLayer({
				id: MAP_AIRPORT_HIGHLIGHT_LAYER_ID,
				type: "circle",
				source: MAP_AIRPORT_HIGHLIGHT_SOURCE_ID,
				paint: {
					"circle-radius": 8,
					"circle-color": "#10b981",
					"circle-stroke-width": 2,
					"circle-stroke-color": "#ffffff",
				},
			});

			mapInstance.addLayer({
				id: MAP_AIRPORT_HIGHLIGHT_LABEL_ID,
				type: "symbol",
				source: MAP_AIRPORT_HIGHLIGHT_SOURCE_ID,
				layout: {
					"text-field": ["concat", ["get", "iata"], "\n", ["get", "name"]],
					"text-size": 12,
					"text-anchor": "top",
					"text-offset": [0, 0.7],
					"text-font": ["Noto Sans Regular"],
				},
				paint: {
					"text-color": "#065f46",
					"text-halo-color": "#ffffff",
					"text-halo-width": 2,
				},
			});

			// 选中航班高亮光晔（先添加，渲染在图标之下）
			mapInstance.addLayer({
				id: MAP_SELECTED_LAYER_ID,
				type: "circle",
				source: MAP_SOURCE_ID,
				filter: ["==", ["get", "flight_id"], ""],
				paint: {
					"circle-radius": 14,
					"circle-color": "#f59e0b",
					"circle-opacity": 0.8,
					"circle-stroke-width": 0,
				},
			});

			// 航迹线（在飞机图标层之前添加，使飞机图标始终在最上层）
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

			// 航班图标（SVG，根据航向旋转，最后添加确保渲染在最顶层）
			mapInstance.addLayer({
				id: MAP_LAYER_ID,
				type: "symbol",
				source: MAP_SOURCE_ID,
				layout: {
					"icon-image": [
						"case",
						[">", ["coalesce", ["get", "altitude_ft"], 0], 100],
						"icon-plane",
						"icon-plane-ground",
					],
					"icon-size": 0.08,
					"icon-rotate": ["coalesce", ["get", "heading"], 0],
					"icon-rotation-alignment": "map",
					"icon-pitch-alignment": "viewport",
					"icon-allow-overlap": true,
					"icon-ignore-placement": true,
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

	// flights 数组由 WS 整体替换（浅变更），无需 deep watch
	// 防抖 1.5s：WS 推送间隔约 90s，防抖主要防止 WS+初始加载同时触发
	watch(
		() => store.flights,
		(newFlights) => {
			if (_flightUpdateTimer !== null) clearTimeout(_flightUpdateTimer);
			_flightUpdateTimer = setTimeout(() => {
				_flightUpdateTimer = null;
				updateFlightLayer(newFlights);
			}, 1500);
		},
	);

	watch(
		() => store.selectedFlight,
		(flight) => {
			updateSelectedFlightHighlight();
			focusSelectedFlight(flight);
		},
	);

	watch(
		() => store.selectedTrackPoints,
		() => {
			updateTrackLayer();
		},
	);

	watch(
		() => store.flightDetail,
		() => {
			updateAirportHighlight();
		},
	);

	watch(
		() => store.airports,
		(list) => {
			if (!map.value) return;
			const src = map.value.getSource(MAP_AIRPORT_SOURCE_ID) as
				| GeoJSONSource
				| undefined;
			src?.setData(toAirportGeoJson(list));
		},
	);

	onMounted(async () => {
		initMap();
		await store.loadInitialFlights();
		store.connectSocket();
		store.loadAirports();
	});

	onUnmounted(() => {
		if (_flightUpdateTimer !== null) {
			clearTimeout(_flightUpdateTimer);
			_flightUpdateTimer = null;
		}
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
