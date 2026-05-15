<template>
	<div class="layout">
		<!-- 底图切换失败提示条 -->
		<transition name="toast">
			<div
				v-if="showFallbackToast"
				class="fallback-toast"
				@click="showFallbackToast = false"
			>
				⚠️ {{ mapFallbackReason }}，已切换至备用底图（{{
					currentProvider
				}}）。点击关闭
			</div>
		</transition>

		<!-- 任务栏 -->
		<header class="task-bar">
			<div class="tb-left">
				<button
					:class="['tb-btn', { active: showLayerPanel }]"
					@click="showLayerPanel = !showLayerPanel"
					title="图层 / 底图设置"
				>
					<svg class="tb-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"
						/>
					</svg>
					图层
				</button>
				<button
					:class="['tb-btn', { active: store.showAqiLayer }]"
					@click="store.showAqiLayer = !store.showAqiLayer"
					title="AQI 空气质量"
				>
					<svg class="tb-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M5.05 4.05a7 7 0 119.9 9.9A7 7 0 015.05 4.05zM10 14a1 1 0 100-2 1 1 0 000 2zm1-5a1 1 0 10-2 0v2a1 1 0 002 0V9z"
							clip-rule="evenodd"
						/>
					</svg>
					AQI
				</button>
			</div>
			<div class="tb-center">
				<span class="tb-stat">
					<span class="tb-num">{{ store.flights.length }}</span>
					<span class="tb-label">追踪</span>
				</span>
				<span class="tb-sep">|</span>
				<span class="tb-stat tb-air">
					<span class="tb-num">{{ airborneCnt }}</span>
					<span class="tb-label">飞行中</span>
				</span>
				<span class="tb-sep">|</span>
				<span class="tb-stat tb-gnd">
					<span class="tb-num">{{ store.flights.length - airborneCnt }}</span>
					<span class="tb-label">地面</span>
				</span>
			</div>
			<div class="tb-right">
				<button
					:class="['tb-btn', { active: !panelCollapsed }]"
					@click="panelCollapsed = !panelCollapsed"
					title="切换侧栏"
				>
					<svg class="tb-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							d="M4 3a1 1 0 000 2h12a1 1 0 100-2H4zm0 4a1 1 0 000 2h8a1 1 0 100-2H4zm0 4a1 1 0 000 2h12a1 1 0 100-2H4z"
						/>
					</svg>
				</button>
			</div>
		</header>

		<!-- 工作区 -->
		<div class="work-area">
			<!-- 左：图层抽屉 -->
			<aside :class="['layer-drawer', { open: showLayerPanel }]">
				<div class="drawer-header">
					<span class="drawer-title">图层与底图</span>
					<button
						class="drawer-close"
						@click="showLayerPanel = false"
						title="关闭"
					>
						<svg viewBox="0 0 16 16" fill="currentColor">
							<path
								d="M4.293 4.293a1 1 0 011.414 0L8 6.586l2.293-2.293a1 1 0 111.414 1.414L9.414 8l2.293 2.293a1 1 0 01-1.414 1.414L8 9.414l-2.293 2.293a1 1 0 01-1.414-1.414L6.586 8 4.293 5.707a1 1 0 010-1.414z"
							/>
						</svg>
					</button>
				</div>
				<div class="drawer-body">
					<div class="panel-section">
						<div class="panel-title">地图来源</div>
						<div class="style-grid">
							<button
								v-if="MAPTILER_KEY"
								:class="[
									'style-btn',
									{ active: currentProvider === 'maptiler' },
								]"
								@click="switchProvider('maptiler')"
							>
								MapTiler
							</button>
							<button
								v-if="STADIA_KEY"
								:class="['style-btn', { active: currentProvider === 'stadia' }]"
								@click="switchProvider('stadia')"
							>
								Stadia
							</button>
							<button
								:class="[
									'style-btn',
									{ active: currentProvider === 'openfreemap' },
								]"
								@click="switchProvider('openfreemap')"
							>
								OpenFreeMap
							</button>
						</div>
						<div v-if="mapFallbackActive" class="panel-note">
							⚠️ 已自动回退到 {{ currentProvider }}
						</div>
					</div>
					<div class="panel-section">
						<div class="panel-title">底图样式</div>
						<div class="style-grid">
							<button
								v-for="s in currentProviderStyles"
								:key="s.id"
								:class="['style-btn', { active: currentStyleId === s.id }]"
								@click="switchStyle(s.id)"
							>
								{{ s.label }}
							</button>
						</div>
					</div>
					<div class="panel-section">
						<div class="panel-title">飞机颜色</div>
						<div class="style-grid">
							<button
								v-for="preset in AIRCRAFT_COLOR_PRESETS"
								:key="preset.id"
								:class="[
									'style-btn',
									{ active: aircraftColorPresetId === preset.id },
								]"
								@click="aircraftColorPresetId = preset.id"
							>
								<span
									class="aircraft-color-chip"
									:style="{ background: preset.fly }"
								></span>
								{{ preset.label }}
							</button>
						</div>
						<div class="panel-note">当前：{{ currentAircraftColorLabel }}</div>
					</div>
					<div class="panel-section">
						<div class="panel-title">叠加图层</div>
						<label class="layer-toggle"
							><input type="checkbox" v-model="store.showAqiLayer" /><span
								>AQI 空气质量</span
							></label
						>
						<label class="layer-toggle"
							><input type="checkbox" v-model="showAqiHeatmap" /><span
								>PM2.5 热力图</span
							></label
						>
						<label class="layer-toggle"
							><input type="checkbox" v-model="showWindLayer" /><span
								>风速风向</span
							></label
						>
						<label class="layer-toggle"
							><input type="checkbox" v-model="showTempLayer" /><span
								>温度分布</span
							></label
						>
						<label class="layer-toggle"
							><input type="checkbox" v-model="showDensityLayer" /><span
								>航班密度热力图</span
							></label
						>
					</div>
					<div class="panel-section">
						<div class="panel-title">标注语言</div>
						<div class="label-row">
							<span class="label-sub">行数</span>
							<div class="style-grid">
								<button
									:class="['style-btn', { active: labelLines === 1 }]"
									@click="labelLines = 1"
								>
									单行
								</button>
								<button
									:class="['style-btn', { active: labelLines === 2 }]"
									@click="labelLines = 2"
								>
									双行
								</button>
							</div>
						</div>
						<div class="label-row">
							<span class="label-sub">{{
								labelLines === 2 ? "第一行" : "语言"
							}}</span>
							<select class="lang-select" v-model="labelLine1">
								<option
									v-for="opt in LABEL_LANG_OPTIONS"
									:key="opt.key"
									:value="opt.key"
								>
									{{ opt.label }}
								</option>
							</select>
						</div>
						<div v-if="labelLines === 2" class="label-row">
							<span class="label-sub">第二行</span>
							<select class="lang-select" v-model="labelLine2">
								<option
									v-for="opt in LABEL_LANG_OPTIONS"
									:key="opt.key"
									:value="opt.key"
								>
									{{ opt.label }}
								</option>
							</select>
						</div>
					</div>
				</div>
			</aside>

			<!-- 中：地图 -->
			<div class="map-shell">
				<div ref="mapContainer" class="map-canvas"></div>
				<div v-if="store.loading" class="map-status">正在加载航班数据...</div>
				<div v-else-if="store.trackLoading" class="map-status">
					正在加载选中航班轨迹...
				</div>
				<div v-else-if="!store.flights.length" class="map-status">
					暂无航班数据，等待后端返回快照。
				</div>
			</div>

			<!-- 右：统一上下文面板 -->
			<aside :class="['context-panel', { collapsed: panelCollapsed }]">
				<div class="cp-tabs">
					<button
						:class="['cp-tab', { active: contextTab === 'flights' }]"
						@click="contextTab = 'flights'"
					>
						航班
						<span class="cp-badge">{{ store.filteredFlights.length }}</span>
					</button>
					<button
						v-if="store.flightDetail || store.detailLoading"
						:class="['cp-tab', { active: contextTab === 'detail' }]"
						@click="contextTab = 'detail'"
					>
						详情
					</button>
					<button
						v-if="store.scheduleAirport"
						:class="['cp-tab', { active: contextTab === 'schedule' }]"
						@click="contextTab = 'schedule'"
					>
						时刻
					</button>
				</div>
				<div class="cp-body">
					<FlightListPanel
						v-show="contextTab === 'flights'"
						:flights="store.filteredFlights"
						:selected-flight-id="store.selectedFlightId"
						:filter-status="store.filterStatus"
						:filter-country="store.filterCountry"
						:filter-country-mode="store.filterCountryMode"
						:filter-region="store.filterRegion"
						:ws-online="store.wsOnline"
						@select="handleSelectFlight"
						@search="store.searchKeyword = $event"
						@filter="store.filterStatus = $event"
						@filter-country="store.filterCountry = $event"
						@filter-country-mode="store.filterCountryMode = $event"
						@filter-region="store.filterRegion = $event"
					/>
					<FlightDetailCard
						v-show="contextTab === 'detail'"
						:detail="store.flightDetail"
						:loading="store.detailLoading"
						@close="handleSelectFlight(null)"
					/>
					<SchedulePanel v-show="contextTab === 'schedule'" />
				</div>
			</aside>
		</div>
	</div>
</template>

<script setup lang="ts">
	import {
		computed,
		markRaw,
		nextTick,
		onMounted,
		onUnmounted,
		ref,
		watch,
	} from "vue";
	import maplibregl, {
		type GeoJSONSource,
		type LngLatBoundsLike,
		type Map as MapLibreMap,
	} from "maplibre-gl";
	import "maplibre-gl/dist/maplibre-gl.css";
	import planeIconRaw from "../icons/plane.svg?raw";
	import planeGroundIconRaw from "../icons/plane_ground.svg?raw";

	import FlightDetailCard from "../components/FlightDetailCard.vue";
	import FlightListPanel from "../components/FlightListPanel.vue";
	import SchedulePanel from "../components/SchedulePanel.vue";
	import { useFlightStore } from "../stores/flight";
	import { COUNTRIES } from "../data/countries";
	import type {
		AirportInfo,
		AirQualityHub,
		FlightBrief,
	} from "../types/flight";

	// ── API keys from .env ───────────────────────────────────────────────────────
	const MAPTILER_KEY = (import.meta.env.VITE_MAPTILER_KEY as string) || "";
	const STADIA_KEY = (import.meta.env.VITE_STADIA_KEY as string) || "";

	// ── Map config from .env ─────────────────────────────────────────────────────
	const MAP_DEFAULT_PROVIDER =
		(import.meta.env.VITE_MAP_DEFAULT_PROVIDER as string) || "maptiler";
	const MAP_DEFAULT_STYLE =
		(import.meta.env.VITE_MAP_DEFAULT_STYLE as string) || "streets-v2-dark";
	const MAP_INIT_LNG = parseFloat(
		(import.meta.env.VITE_MAP_INIT_LNG as string) || "113.2644",
	);
	const MAP_INIT_LAT = parseFloat(
		(import.meta.env.VITE_MAP_INIT_LAT as string) || "23.1291",
	);
	const MAP_INIT_ZOOM = parseFloat(
		(import.meta.env.VITE_MAP_INIT_ZOOM as string) || "4",
	);

	// ── Basemap style catalogues ─────────────────────────────────────────────────
	const MAPTILER_STYLES = [
		{ id: "streets-v2-dark", label: "街道深色" },
		{ id: "streets-v2", label: "街道浅色" },
		{ id: "outdoor-v2", label: "户外地形" },
		{ id: "hybrid", label: "卫星影像" },
		{ id: "dataviz-dark", label: "数据深色" },
		{ id: "dataviz", label: "数据浅色" },
	];
	const STADIA_STYLES = [
		{ id: "alidade_smooth_dark", label: "深色平滑" },
		{ id: "alidade_smooth", label: "浅色平滑" },
		{ id: "stamen_terrain", label: "地形图" },
		{ id: "alidade_satellite", label: "卫星影像" },
	];
	const OPENFREEMAP_STYLES = [
		{ id: "liberty", label: "自然风格" },
		{ id: "bright", label: "明亮风格" },
		{ id: "positron", label: "简洁浅色" },
	];

	// ── Aircraft icon color scheme per map style ──────────────────────────────────
	// fly: flying aircraft fill color; ground: taxiing/parked aircraft fill color
	const STYLE_ICON_COLORS: Record<string, { fly: string; ground: string }> = {
		// MapTiler
		"streets-v2-dark": { fly: "#22d3ee", ground: "#e2e8f0" },
		"streets-v2": { fly: "#1d4ed8", ground: "#334155" },
		"outdoor-v2": { fly: "#b45309", ground: "#374151" },
		hybrid: { fly: "#f59e0b", ground: "#e2e8f0" },
		satellite: { fly: "#f59e0b", ground: "#e2e8f0" },
		"dataviz-dark": { fly: "#f97316", ground: "#cbd5e1" },
		dataviz: { fly: "#be123c", ground: "#334155" },
		// Backward compatibility for old id used in previous versions
		"satellite-hybrid": { fly: "#f59e0b", ground: "#e2e8f0" },
		// Stadia
		alidade_smooth_dark: { fly: "#34d399", ground: "#e2e8f0" },
		alidade_smooth: { fly: "#1e40af", ground: "#334155" },
		stamen_terrain: { fly: "#0f766e", ground: "#374151" },
		alidade_satellite: { fly: "#f59e0b", ground: "#e2e8f0" },
		// OpenFreeMap
		liberty: { fly: "#7c3aed", ground: "#334155" },
		bright: { fly: "#0f766e", ground: "#374151" },
		positron: { fly: "#111827", ground: "#4b5563" },
	};
	/** Default colors used when style ID is not in the table */
	const DEFAULT_ICON_COLORS = { fly: "#f59e0b", ground: "#e2e8f0" };

	const AIRCRAFT_COLOR_PRESETS = [
		{ id: "auto", label: "自动", fly: "#60a5fa", ground: "#94a3b8" },
		{ id: "ocean-blue", label: "海洋蓝", fly: "#60a5fa", ground: "#94a3b8" },
		{
			id: "yellow",
			label: "荧光黄 #FFFF00",
			fly: "#FFFF00",
			ground: "#f1f5f9",
		},
		{ id: "lime", label: "亮明黄 #CCFF00", fly: "#CCFF00", ground: "#e2e8f0" },
		{ id: "white", label: "纯白 #FFFFFF", fly: "#FFFFFF", ground: "#e2e8f0" },
		{ id: "ice", label: "浅冰白 #F8FAFC", fly: "#F8FAFC", ground: "#cbd5e1" },
		{
			id: "orangered",
			label: "橙红 #FF4500",
			fly: "#FF4500",
			ground: "#f1f5f9",
		},
		{ id: "coral", label: "珊瑚红 #FF7F50", fly: "#FF7F50", ground: "#e2e8f0" },
		{
			id: "deep-blue",
			label: "深海蓝 #1A237E（专业商务风）",
			fly: "#1A237E",
			ground: "#e2e8f0",
		},
		{
			id: "charcoal",
			label: "深炭灰 #333333（极致清晰）",
			fly: "#333333",
			ground: "#f1f5f9",
		},
		{
			id: "jade-green",
			label: "翡翠绿 #2E7D32（清新自然风）",
			fly: "#2E7D32",
			ground: "#e2e8f0",
		},
	] as const;
	type AircraftColorPresetId = (typeof AIRCRAFT_COLOR_PRESETS)[number]["id"];

	const MAPTILER_STYLE_ALIASES: Record<string, string> = {
		"satellite-hybrid": "hybrid",
	};

	function normalizeMaptilerStyleId(styleId: string): string {
		return MAPTILER_STYLE_ALIASES[styleId] ?? styleId;
	}

	// ── Label language settings ────────────────────────────────────────────────────
	const LABEL_LANG_OPTIONS = [
		{ key: "name:en", label: "英语" },
		{ key: "name:zh-Hans", label: "简体中文" },
		{ key: "name:zh-Hant", label: "繁体中文" },
		{ key: "name:ja", label: "日语" },
		{ key: "name:ko", label: "한국어" },
		{ key: "name", label: "本地名称" },
	] as const;

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
	const MAP_AQI_SOURCE_ID = "aqi-hubs";
	const MAP_AQI_LAYER_ID = "aqi-circles";
	const MAP_AQI_LABEL_LAYER_ID = "aqi-labels";
	const MAP_ROUTE_SOURCE_ID = "planned-route";
	const MAP_ROUTE_LAYER_ID = "planned-route-line";
	const MAP_TRACK_ARROW_LAYER_ID = "selected-flight-track-arrows";

	// New enhanced layer IDs
	const MAP_AQI_HEATMAP_LAYER_ID = "aqi-heatmap";
	const MAP_WIND_SOURCE_ID = "weather-hubs";
	const MAP_WIND_ARROW_LAYER_ID = "wind-arrows";
	const MAP_WIND_LABEL_LAYER_ID = "wind-speed-labels";
	const MAP_TEMP_LAYER_ID = "temp-circles";
	const MAP_DENSITY_LAYER_ID = "flight-density";
	// Region filter highlight layers
	const MAP_REGION_HIGHLIGHT_SOURCE = "region-highlight";
	const MAP_REGION_HIGHLIGHT_FILL_ID = "region-highlight-fill";
	const MAP_REGION_HIGHLIGHT_GLOW_ID = "region-highlight-glow";
	const MAP_REGION_HIGHLIGHT_LINE_ID = "region-highlight-line";

	/** AQI 等级颜色：1=优良, 2=良好, 3=轻度污染, 4=中度污染, 5=重度污染 */
	const AQI_COLORS = ["#00e400", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97"];

	// ── State ────────────────────────────────────────────────────────────────────
	const store = useFlightStore();
	const mapContainer = ref<HTMLElement | null>(null);
	const map = ref<MapLibreMap | null>(null);
	const hasFittedInitialBounds = ref(false);

	type MapProvider = "maptiler" | "stadia" | "openfreemap";
	const currentProvider = ref<MapProvider>(MAP_DEFAULT_PROVIDER as MapProvider);
	const currentStyleId = ref(MAP_DEFAULT_STYLE);
	const mapFallbackActive = ref(false);
	const mapFallbackReason = ref("");
	const showFallbackToast = ref(false);

	const showLayerPanel = ref(false);

	/** 右侧上下文面板状态 */
	const contextTab = ref<"flights" | "detail" | "schedule">("flights");
	const panelCollapsed = ref(false);
	const airborneCnt = computed(
		() => store.flights.filter((f) => (f.altitude_ft ?? 0) > 100).length,
	);
	const showAqiHeatmap = ref(false);
	const showWindLayer = ref(false);
	const showTempLayer = ref(false);
	const showDensityLayer = ref(false);
	const aircraftColorPresetId = ref<AircraftColorPresetId>("auto");
	const currentAircraftColorLabel = computed(() => {
		return (
			AIRCRAFT_COLOR_PRESETS.find((p) => p.id === aircraftColorPresetId.value)
				?.label ?? "自动"
		);
	});

	// ── Label language settings ───────────────────────────────────────────────────
	const labelLines = ref<1 | 2>(2);
	const labelLine1 = ref("name:en");
	const labelLine2 = ref("name:zh-Hans");

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

	/** 防抖计时器：避免 WS 快照连续触发时每次都重建 GeoJSON */
	let _flightUpdateTimer: ReturnType<typeof setTimeout> | null = null;

	/** 飞机颜色更新防抖计时器 */
	let _aircraftColorUpdateTimer: ReturnType<typeof setTimeout> | null = null;

	function resolveAircraftIconColors(): { fly: string; ground: string } {
		const styleColors =
			STYLE_ICON_COLORS[currentStyleId.value] ?? DEFAULT_ICON_COLORS;
		if (aircraftColorPresetId.value === "auto") {
			return styleColors;
		}
		const preset = AIRCRAFT_COLOR_PRESETS.find(
			(p) => p.id === aircraftColorPresetId.value,
		);
		if (!preset) return styleColors;
		return {
			fly: preset.fly,
			ground: preset.ground,
		};
	}

	async function refreshAircraftIcons(mapInstance: MapLibreMap) {
		const colors = resolveAircraftIconColors();
		try {
			await Promise.all([
				loadColoredSvgIcon(mapInstance, "icon-plane", planeIconRaw, colors.fly),
				loadColoredSvgIcon(
					mapInstance,
					"icon-plane-ground",
					planeGroundIconRaw,
					colors.ground,
				),
			]);
			console.debug(
				"[Aircraft Icon] updated",
				colors,
				aircraftColorPresetId.value,
			);
		} catch (err) {
			console.error("[Aircraft Icon] refresh failed", err);
		}
	}

	// ── Basemap URL helpers ──────────────────────────────────────────────────────
	function buildMaptilerStyleUrl(styleId: string): string {
		const normalized = normalizeMaptilerStyleId(styleId);
		return `/maptiler-proxy/maps/${normalized}/style.json?key=${MAPTILER_KEY}`;
	}
	function buildStadiaStyleUrl(styleId: string): string {
		return `/stadia-proxy/styles/${styleId}/style.json${STADIA_KEY ? `?api_key=${STADIA_KEY}` : ""}`;
	}
	function buildOpenFreeMapStyleUrl(styleId: string): string {
		return `https://tiles.openfreemap.org/styles/${styleId}`;
	}

	/** Computed list of styles for the currently active provider. */
	const currentProviderStyles = computed(() => {
		if (currentProvider.value === "maptiler") return MAPTILER_STYLES;
		if (currentProvider.value === "stadia") return STADIA_STYLES;
		return OPENFREEMAP_STYLES;
	});

	/**
	 * Pre-flight check: honours VITE_MAP_DEFAULT_PROVIDER / VITE_MAP_DEFAULT_STYLE,
	 * then falls back through maptiler → stadia → openfreemap as keys allow.
	 * Returns the resolved style URL and chosen provider.
	 */
	async function determineInitialStyle(): Promise<{
		url: string;
		provider: MapProvider;
		styleId: string;
	}> {
		const wantProvider = MAP_DEFAULT_PROVIDER as MapProvider;
		const wantStyle = MAP_DEFAULT_STYLE;

		// ── Try the configured provider first ───────────────────────────────
		if (wantProvider === "openfreemap") {
			const s =
				OPENFREEMAP_STYLES.find((x) => x.id === wantStyle) ||
				OPENFREEMAP_STYLES[0];
			return {
				url: buildOpenFreeMapStyleUrl(s.id),
				provider: "openfreemap",
				styleId: s.id,
			};
		}

		if (wantProvider === "maptiler" && MAPTILER_KEY) {
			const wantStyleNormalized = normalizeMaptilerStyleId(wantStyle);
			const styleId =
				MAPTILER_STYLES.find((x) => x.id === wantStyleNormalized)?.id ||
				MAPTILER_STYLES[0].id;
			try {
				const resp = await fetch(buildMaptilerStyleUrl(styleId));
				if (resp.ok) {
					return {
						url: buildMaptilerStyleUrl(styleId),
						provider: "maptiler",
						styleId,
					};
				}
				mapFallbackActive.value = true;
				mapFallbackReason.value = `MapTiler 返回 HTTP ${resp.status}`;
			} catch {
				mapFallbackActive.value = true;
				mapFallbackReason.value = "无法连接 MapTiler";
			}
		}

		if (wantProvider === "stadia" && STADIA_KEY) {
			const styleId =
				STADIA_STYLES.find((x) => x.id === wantStyle)?.id ||
				STADIA_STYLES[0].id;
			return {
				url: buildStadiaStyleUrl(styleId),
				provider: "stadia",
				styleId,
			};
		}

		// ── Fallback chain ───────────────────────────────────────────────────
		if (wantProvider !== "maptiler" && MAPTILER_KEY) {
			const styleId = MAPTILER_STYLES[0].id;
			try {
				const resp = await fetch(buildMaptilerStyleUrl(styleId));
				if (resp.ok) {
					mapFallbackActive.value = true;
					mapFallbackReason.value = `已回退至 MapTiler`;
					return {
						url: buildMaptilerStyleUrl(styleId),
						provider: "maptiler",
						styleId,
					};
				}
			} catch {
				/* continue to next fallback */
			}
		}

		if (STADIA_KEY) {
			const styleId = STADIA_STYLES[0].id;
			if (wantProvider !== "stadia") {
				mapFallbackActive.value = true;
				mapFallbackReason.value = "已回退至 Stadia Maps";
			}
			return { url: buildStadiaStyleUrl(styleId), provider: "stadia", styleId };
		}

		const s = OPENFREEMAP_STYLES[0];
		return {
			url: buildOpenFreeMapStyleUrl(s.id),
			provider: "openfreemap",
			styleId: s.id,
		};
	}

	/**
	 * MapLibre transformRequest: rewrites external tile/font/sprite URLs to local
	 * proxy paths so all map tile traffic flows through the Vite dev proxy (or backend
	 * proxy in production) rather than going directly to MapTiler/Stadia CDNs.
	 *
	 * IMPORTANT: Must return absolute URLs (not relative paths like /maptiler-proxy/...).
	 * MapLibre passes the transformed URL to a Web Worker running in a blob: URL context.
	 * In blob: workers, relative path-absolute URLs cannot be resolved
	 * (new Request('/foo') throws "Failed to parse URL from /foo"), so tile fetches
	 * would silently fail. Using window.location.origin ensures absolute URLs that
	 * the worker can fetch as same-origin requests.
	 */
	function transformRequest(url: string): { url: string } {
		const origin = window.location.origin;
		if (url.startsWith("https://api.maptiler.com")) {
			return {
				url: url.replace(
					"https://api.maptiler.com",
					`${origin}/maptiler-proxy`,
				),
			};
		}
		if (url.startsWith("https://tiles.stadiamaps.com")) {
			return {
				url: url.replace(
					"https://tiles.stadiamaps.com",
					`${origin}/stadia-proxy`,
				),
			};
		}
		return { url };
	}

	/**
	 * Re-add all custom sources and layers after a style switch.
	 * MapLibre removes all sources/layers when setStyle() is called.
	 */
	async function reinitLayers(mapInstance: MapLibreMap) {
		applyBilingualLabels(mapInstance);

		// Terrain DEM
		if (!mapInstance.getSource("terrain-dem")) {
			mapInstance.addSource("terrain-dem", {
				type: "raster-dem",
				tiles: [
					"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
				],
				tileSize: 256,
				encoding: "terrarium",
				maxzoom: 14,
			});
			const firstSym = mapInstance
				.getStyle()
				.layers.find((l) => l.type === "symbol");
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
				firstSym?.id,
			);
		}

		await refreshAircraftIcons(mapInstance);

		addCustomLayers(mapInstance);
		updateRegionHighlight(store.filterCountry, store.filterRegion);
	}

	/**
	 * Switch the active map style within the current provider.
	 */
	async function switchStyle(styleId: string) {
		if (!map.value) return;
		let url: string;
		let resolvedStyleId = styleId;
		if (currentProvider.value === "maptiler") {
			resolvedStyleId = normalizeMaptilerStyleId(styleId);
			url = buildMaptilerStyleUrl(resolvedStyleId);
		} else if (currentProvider.value === "stadia") {
			url = buildStadiaStyleUrl(styleId);
		} else {
			url = buildOpenFreeMapStyleUrl(styleId);
		}
		currentStyleId.value = resolvedStyleId;
		// diff:false forces a full style reload so MapLibre v4 fires 'style.load'.
		// With the default diff:true, MapLibre only fires 'styledata' and never
		// fires 'style.load', so reinitLayers would never be called.
		map.value.setStyle(url, { diff: false });
		map.value.once("style.load", () => {
			reinitLayers(map.value!);
		});
	}

	/**
	 * Switch to a different map provider, optionally specifying a style.
	 * Defaults to the first style in the new provider's catalogue.
	 */
	async function switchProvider(provider: MapProvider, styleId?: string) {
		if (!map.value) return;
		currentProvider.value = provider;
		let url: string;
		let sid: string;
		if (provider === "maptiler") {
			const defaultStyle = normalizeMaptilerStyleId(MAP_DEFAULT_STYLE);
			sid =
				styleId ||
				MAPTILER_STYLES.find((s) => s.id === defaultStyle)?.id ||
				MAPTILER_STYLES[0].id;
			sid = normalizeMaptilerStyleId(sid);
			url = buildMaptilerStyleUrl(sid);
		} else if (provider === "stadia") {
			sid = styleId || STADIA_STYLES[0].id;
			url = buildStadiaStyleUrl(sid);
		} else {
			const s =
				OPENFREEMAP_STYLES.find((x) => x.id === styleId) ||
				OPENFREEMAP_STYLES[0];
			sid = s.id;
			url = buildOpenFreeMapStyleUrl(sid);
		}
		currentStyleId.value = sid;
		map.value.setStyle(url, { diff: false });
		map.value.once("style.load", () => {
			reinitLayers(map.value!);
		});
	}

	// ── Weather hub fetch (for wind/temp layers) ─────────────────────────────────
	async function loadWeatherHubs() {
		try {
			const apiBase = import.meta.env.VITE_API_BASE_URL as string;
			const resp = await fetch(`${apiBase}/datahub/weather`);
			if (!resp.ok) return;
			const json = await resp.json();
			if (json.data) {
				weatherHubs.value = Object.entries(json.data)
					.filter(([iata]) => !iata.startsWith("GRD_"))
					.map(([iata, w]: [string, unknown]) => {
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
			}
		} catch (e) {
			console.warn("[WeatherHubs] fetch failed", e);
		}
	}

	function toWeatherGeoJson(): GeoJSON.FeatureCollection<GeoJSON.Point> {
		return {
			type: "FeatureCollection",
			features: weatherHubs.value.map((h) => ({
				type: "Feature",
				geometry: { type: "Point", coordinates: [h.lon, h.lat] },
				properties: {
					iata: h.iata,
					wind_speed_mps: h.wind_speed_mps ?? 0,
					wind_deg: h.wind_deg ?? 0,
					temperature_c: h.temperature_c ?? 0,
					humidity: h.humidity ?? 0,
					description: h.description ?? "",
				},
			})),
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

	async function handleSelectFlight(flightId: string | null) {
		await store.selectFlight(flightId);
		store.loadFlightDetail(flightId);
		if (flightId) {
			panelCollapsed.value = false;
			contextTab.value = "detail";
		} else {
			contextTab.value = "flights";
		}
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

	/** 计划路线 GeoJSON：当前位置 → 目的地机场（虚线，仅在已知到达机场时有数据）*/
	function toRouteGeoJson(): GeoJSON.FeatureCollection<GeoJSON.LineString> {
		const flight = store.selectedFlight;
		const detail = store.flightDetail;
		if (!flight || !detail?.arrival_airport) {
			return { type: "FeatureCollection", features: [] };
		}
		const arrAirport = store.airports.find(
			(a) => a.iata === detail.arrival_airport,
		);
		if (!arrAirport) {
			return { type: "FeatureCollection", features: [] };
		}
		return {
			type: "FeatureCollection",
			features: [
				{
					type: "Feature",
					geometry: {
						type: "LineString",
						coordinates: [
							[flight.lon, flight.lat],
							[arrAirport.lon, arrAirport.lat],
						],
					},
					properties: { arr_iata: arrAirport.iata },
				},
			],
		};
	}

	function updateRouteLayer() {
		if (!map.value) return;
		const src = map.value.getSource(MAP_ROUTE_SOURCE_ID) as
			| GeoJSONSource
			| undefined;
		src?.setData(toRouteGeoJson());
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

	/** 将 SVG 文本中的填充色替换为指定颜色（保留 fill="none" 不变） */
	function svgWithColor(svgRaw: string, color: string): string {
		return svgRaw
			.replace(/fill="(?!none)[^"]*"/g, `fill="${color}"`)
			.replace(/fill:(?!\s*none)[^;}"']*/g, `fill:${color}`);
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
		const colored = svgWithColor(svgRaw, fillColor);
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

	/** 将地图中所有地名标注改为可配置的双语/单语样式，并加粗字体 */
	function applyBilingualLabels(mapInstance: MapLibreMap) {
		const style = mapInstance.getStyle();

		// 按提供商选取粗体字体栈（使用各自 glyph set 中存在的粗体字体）
		const boldFonts: Record<MapProvider, string[]> = {
			maptiler: ["Open Sans Bold", "Arial Unicode MS Regular"],
			stadia: ["Open Sans Bold", "Arial Unicode MS Regular"],
			openfreemap: [
				"Metropolis Bold",
				"Noto Sans Bold",
				"Arial Unicode MS Regular",
			],
		};
		const fonts = boldFonts[currentProvider.value] ?? [
			"Open Sans Bold",
			"Arial Unicode MS Regular",
		];

		/**
		 * 主行表达式：英文/本地名称，有充分兜底
		 * MapTiler 同时存在 name:en（冒号）和 name_en（下划线）两种格式，均尝试
		 */
		function line1Expr(langKey: string): unknown[] {
			if (langKey === "name:en") {
				return [
					"coalesce",
					["get", "name:en"],
					["get", "name_en"],
					["get", "name:latin"],
					["get", "name"],
					"",
				];
			}
			if (langKey === "name") {
				return ["coalesce", ["get", "name"], ""];
			}
			// 中文变体：优先 name:zh-Hans/zh-Hant，回退到 name:zh（OSM 通用中文字段，覆盖更广）
			if (langKey === "name:zh-Hans" || langKey === "name:zh-Hant") {
				return [
					"coalesce",
					["get", langKey],
					["get", "name:zh"],
					["get", "name"],
					"",
				];
			}
			return ["coalesce", ["get", langKey], ["get", "name"], ""];
		}

		/**
		 * 副行表达式：只取指定语言字段，不跨语言回退
		 * 避免 zh-Hans 为空时回退到英文，造成两行显示相同内容
		 * 中文变体额外尝试 name:zh（同为中文，不会产生重复）
		 */
		function line2Expr(langKey: string): unknown[] {
			if (langKey === "name:en") {
				return ["coalesce", ["get", "name:en"], ["get", "name_en"], ""];
			}
			if (langKey === "name") {
				return ["coalesce", ["get", "name"], ""];
			}
			// 中文变体：name:zh-Hans → name:zh（仍为中文，安全回退）
			if (langKey === "name:zh-Hans" || langKey === "name:zh-Hant") {
				return ["coalesce", ["get", langKey], ["get", "name:zh"], ""];
			}
			return ["coalesce", ["get", langKey], ""];
		}

		/**
		 * 条件检测：该语言字段是否有实际内容（不跨语言回退）
		 * 用于决定是否显示双行，防止 zh-Hans 空时误显示两行相同文字
		 * 中文变体也检测 name:zh 字段
		 */
		function hasLang(langKey: string): unknown[] {
			if (langKey === "name:en") {
				return ["coalesce", ["get", "name:en"], ["get", "name_en"], ""];
			}
			// 中文变体：同时检测 name:zh 是否有内容
			if (langKey === "name:zh-Hans" || langKey === "name:zh-Hant") {
				return ["coalesce", ["get", langKey], ["get", "name:zh"], ""];
			}
			return ["coalesce", ["get", langKey], ""];
		}

		const textField =
			labelLines.value === 1
				? line1Expr(labelLine1.value)
				: [
						"case",
						// 仅当第二语言字段本身有内容时显示双行（严格检测，无跨语言回退）
						["!=", hasLang(labelLine2.value), ""],
						[
							"concat",
							line1Expr(labelLine1.value),
							"\n",
							line2Expr(labelLine2.value),
						],
						line1Expr(labelLine1.value),
					];

		for (const layer of style.layers) {
			if (layer.type !== "symbol") continue;
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			const layout = (layer as any).layout ?? {};
			const field = layout["text-field"];
			if (!field) continue;
			const fieldStr = JSON.stringify(field);
			// 只处理引用 name 字段的图层（兼容 ["get","name:en"] 和 "{name:latin}" 两种格式）
			if (!fieldStr.includes("name")) continue;
			// 跳过路牌、路线编号等非地名图层
			if (/"ref"/.test(fieldStr)) continue;
			if (
				layer.id.includes("shield") ||
				layer.id.includes("route") ||
				layer.id.includes("-ref")
			)
				continue;

			mapInstance.setLayoutProperty(layer.id, "text-field", textField);
			mapInstance.setLayoutProperty(layer.id, "text-font", fonts);
		}
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

			if (mapFallbackActive.value && mapFallbackReason.value) {
				showFallbackToast.value = true;
				setTimeout(() => {
					showFallbackToast.value = false;
				}, 8000);
			}

			const mapInstance = new maplibregl.Map({
				container: mapContainer.value!,
				style: styleUrl,
				center: [MAP_INIT_LNG, MAP_INIT_LAT],
				zoom: MAP_INIT_ZOOM,
				attributionControl: true,
				refreshExpiredTiles: false,
				maxTileCacheSize: 2048,
				maxTileCacheZoomLevels: 8,
				cancelPendingTileRequestsWhileZooming: false,
				fadeDuration: 150,
				transformRequest,
			});

			mapInstance.addControl(new maplibregl.NavigationControl(), "top-right");
			mapInstance.addControl(
				new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }),
				"bottom-right",
			);

			// Runtime error: detect quota exceeded (403/429) and failover
			mapInstance.on("error", (e) => {
				const status = (e.error as { status?: number })?.status;
				if (
					(status === 403 || status === 429) &&
					currentProvider.value === "maptiler" &&
					STADIA_KEY
				) {
					const reason =
						status === 429
							? "MapTiler 配额已用尽 (429)"
							: "MapTiler 访问被拒绝 (403)";
					mapFallbackActive.value = true;
					mapFallbackReason.value = reason;
					currentProvider.value = "stadia";
					const stadiaDefault = "alidade_smooth_dark";
					currentStyleId.value = stadiaDefault;
					mapInstance.setStyle(buildStadiaStyleUrl(stadiaDefault), {
						diff: false,
					});
					mapInstance.once("style.load", () => reinitLayers(mapInstance));
					showFallbackToast.value = true;
					setTimeout(() => {
						showFallbackToast.value = false;
					}, 8000);
				}
			});

			mapInstance.on("load", async () => {
				await reinitLayers(mapInstance);
				updateFlightLayer(store.flights);
				updateSelectedFlightHighlight();
				updateTrackLayer();
				updateRouteLayer();
			});

			map.value = markRaw(mapInstance);
		})();
	}

	/**
	 * Add all custom data sources and layers to the map.
	 * Called after initial load and after every style switch.
	 */
	function addCustomLayers(mapInstance: MapLibreMap) {
		const styleLayers = mapInstance.getStyle().layers;
		const firstSymbolLayer = styleLayers.find((l) => l.type === "symbol");

		// Terrain DEM
		if (!mapInstance.getSource("terrain-dem")) {
			mapInstance.addSource("terrain-dem", {
				type: "raster-dem",
				tiles: [
					"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
				],
				tileSize: 256,
				encoding: "terrarium",
				maxzoom: 14,
			});
		}
		if (!mapInstance.getLayer("terrain-hillshade")) {
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
		}

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
				paint: {
					"circle-radius": 18,
					"circle-opacity": 0.55,
					"circle-stroke-width": 1,
					"circle-stroke-color": "rgba(255,255,255,0.6)",
					// Color ramp: cold(-20°C)=blue → cool(0°C)=cyan → warm(25°C)=yellow → hot(40°C)=red
					"circle-color": [
						"interpolate",
						["linear"],
						["get", "temperature_c"],
						-20,
						"#2196f3",
						0,
						"#00bcd4",
						15,
						"#4caf50",
						25,
						"#ffeb3b",
						35,
						"#ff9800",
						45,
						"#f44336",
					],
				},
			});
		}

		// Wind direction arrows + speed labels (hidden by default)
		if (!mapInstance.getLayer(MAP_WIND_ARROW_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_WIND_ARROW_LAYER_ID,
				type: "symbol",
				source: MAP_WIND_SOURCE_ID,
				layout: {
					visibility: "none",
					"text-field": "↑",
					"text-size": 20,
					"text-rotate": ["get", "wind_deg"],
					"text-rotation-alignment": "map",
					"text-allow-overlap": true,
					"text-ignore-placement": true,
				},
				paint: {
					"text-color": "#e0f2fe",
					"text-halo-color": "rgba(0,0,0,0.5)",
					"text-halo-width": 1,
				},
			});
		}

		if (!mapInstance.getLayer(MAP_WIND_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_WIND_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_WIND_SOURCE_ID,
				layout: {
					visibility: "none",
					"text-field": [
						"concat",
						["get", "iata"],
						"\n",
						["to-string", ["round", ["get", "wind_speed_mps"]]],
						"m/s",
						"\n",
						["to-string", ["round", ["get", "temperature_c"]]],
						"°C",
					],
					"text-size": 10,
					"text-anchor": "top",
					"text-offset": [0, 1.2],
					"text-font": ["Noto Sans Regular"],
					"text-allow-overlap": false,
				},
				paint: {
					"text-color": "#f0f9ff",
					"text-halo-color": "rgba(0,0,0,0.6)",
					"text-halo-width": 1.5,
				},
			});
		}

		// ── Flight density heatmap source = MAP_SOURCE_ID (already added) ────────
		// Added as a heatmap layer using the same flights geojson source.
		// We'll add it after MAP_SOURCE_ID is added below.

		// ── Airport layers ────────────────────────────────────────────────────────
		if (!mapInstance.getSource(MAP_AIRPORT_SOURCE_ID)) {
			mapInstance.addSource(MAP_AIRPORT_SOURCE_ID, {
				type: "geojson",
				data: toAirportGeoJson(store.airports),
			});
		}
		if (!mapInstance.getLayer(MAP_AIRPORT_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AIRPORT_LAYER_ID,
				type: "circle",
				source: MAP_AIRPORT_SOURCE_ID,
				paint: {
					// 参考 FR24/FlightAware：白底深边，全色调均清晰可见
					"circle-radius": [
						"interpolate",
						["linear"],
						["zoom"],
						3,
						4,
						8,
						6,
						12,
						8,
					],
					"circle-color": "#ffffff",
					"circle-stroke-width": 2,
					"circle-stroke-color": "#374151",
					"circle-pitch-alignment": "viewport",
				},
			});
		}
		if (!mapInstance.getLayer(MAP_AIRPORT_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AIRPORT_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_AIRPORT_SOURCE_ID,
				layout: {
					"text-field": ["get", "iata"],
					"text-size": 11,
					"text-anchor": "top",
					"text-offset": [0, 0.7],
					"text-font": ["Noto Sans Bold", "Noto Sans Regular"],
				},
				paint: {
					"text-color": "#111827",
					"text-halo-color": "#ffffff",
					"text-halo-width": 2,
				},
			});
		}

		if (!mapInstance.getSource(MAP_AIRPORT_HIGHLIGHT_SOURCE_ID)) {
			mapInstance.addSource(MAP_AIRPORT_HIGHLIGHT_SOURCE_ID, {
				type: "geojson",
				data: toAirportGeoJson([]),
			});
		}
		if (!mapInstance.getLayer(MAP_AIRPORT_HIGHLIGHT_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AIRPORT_HIGHLIGHT_LAYER_ID,
				type: "circle",
				source: MAP_AIRPORT_HIGHLIGHT_SOURCE_ID,
				paint: {
					"circle-radius": [
						"interpolate",
						["linear"],
						["zoom"],
						3,
						6,
						8,
						10,
						12,
						14,
					],
					"circle-color": "#d1fae5",
					"circle-stroke-width": 2.5,
					"circle-stroke-color": "#059669",
					"circle-blur": 0.1,
					"circle-pitch-alignment": "viewport",
				},
			});
		}
		if (!mapInstance.getLayer(MAP_AIRPORT_HIGHLIGHT_LABEL_ID)) {
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
					paint: {
						"heatmap-weight": [
							"interpolate",
							["linear"],
							["coalesce", ["get", "pm2_5"], 0],
							0,
							0,
							75,
							1,
						],
						"heatmap-intensity": [
							"interpolate",
							["linear"],
							["zoom"],
							4,
							0.5,
							9,
							2,
						],
						"heatmap-radius": [
							"interpolate",
							["linear"],
							["zoom"],
							4,
							40,
							9,
							80,
						],
						"heatmap-opacity": 0.7,
						"heatmap-color": [
							"interpolate",
							["linear"],
							["heatmap-density"],
							0,
							"rgba(0,228,0,0)",
							0.2,
							"rgba(255,255,0,0.6)",
							0.5,
							"rgba(255,126,0,0.75)",
							0.8,
							"rgba(255,0,0,0.85)",
							1.0,
							"rgba(143,63,151,0.9)",
						],
					},
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
				paint: {
					// 半径按 AQI 等级比例缩放，轻度=12, 中度=16, 重度=22
					"circle-radius": [
						"step",
						["get", "aqi"],
						10,
						2,
						14,
						3,
						18,
						4,
						22,
						5,
						26,
					],
					"circle-blur": 0.5,
					"circle-opacity": 0.6,
					"circle-stroke-width": 1.5,
					"circle-stroke-color": "rgba(255,255,255,0.8)",
					"circle-pitch-alignment": "viewport",
					"circle-color": [
						"step",
						["get", "aqi"],
						AQI_COLORS[0],
						2,
						AQI_COLORS[1],
						3,
						AQI_COLORS[2],
						4,
						AQI_COLORS[3],
						5,
						AQI_COLORS[4],
					],
				},
			});
		}

		if (!mapInstance.getLayer(MAP_AQI_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_AQI_LABEL_LAYER_ID,
				type: "symbol",
				source: MAP_AQI_SOURCE_ID,
				layout: {
					visibility: store.showAqiLayer ? "visible" : "none",
					"text-field": [
						"concat",
						["get", "iata"],
						"\nAQI:",
						["to-string", ["get", "aqi"]],
					],
					"text-size": 10,
					"text-anchor": "center",
					"text-font": ["Noto Sans Regular"],
				},
				paint: {
					"text-color": "#111827",
					"text-halo-color": "#ffffff",
					"text-halo-width": 1.5,
				},
			});
		}

		// ── Flights source & layers ───────────────────────────────────────────────
		if (!mapInstance.getSource(MAP_SOURCE_ID)) {
			mapInstance.addSource(MAP_SOURCE_ID, {
				type: "geojson",
				data: toGeoJson(store.flights),
			});
		}

		// Flight density heatmap (hidden by default) — 背景层，置于地图标注之下
		if (!mapInstance.getLayer(MAP_DENSITY_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: MAP_DENSITY_LAYER_ID,
					type: "heatmap",
					source: MAP_SOURCE_ID,
					layout: { visibility: "none" },
					paint: {
						"heatmap-weight": 0.5,
						"heatmap-intensity": [
							"interpolate",
							["linear"],
							["zoom"],
							3,
							0.3,
							9,
							1.5,
						],
						"heatmap-radius": [
							"interpolate",
							["linear"],
							["zoom"],
							3,
							15,
							9,
							30,
						],
						"heatmap-opacity": 0.6,
						"heatmap-color": [
							"interpolate",
							["linear"],
							["heatmap-density"],
							0,
							"rgba(0,0,255,0)",
							0.2,
							"rgba(0,128,255,0.5)",
							0.5,
							"rgba(0,255,200,0.7)",
							0.8,
							"rgba(255,200,0,0.85)",
							1.0,
							"rgba(255,50,0,0.9)",
						],
					},
				},
				firstSymbolLayer?.id,
			);
		}

		// Selected flight highlight
		if (!mapInstance.getLayer(MAP_SELECTED_LAYER_ID)) {
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
		}

		// Planned route
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
				layout: { "line-cap": "butt", "line-join": "round" },
				paint: {
					"line-color": "#60a5fa",
					"line-width": 2,
					"line-opacity": 0.75,
					"line-dasharray": [4, 3],
				},
			});
		}

		// Track line
		if (!mapInstance.getSource(MAP_TRACK_SOURCE_ID)) {
			mapInstance.addSource(MAP_TRACK_SOURCE_ID, {
				type: "geojson",
				data: toTrackGeoJson(),
			});
		}
		if (!mapInstance.getLayer(MAP_TRACK_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_TRACK_LAYER_ID,
				type: "line",
				source: MAP_TRACK_SOURCE_ID,
				layout: { "line-cap": "round", "line-join": "round" },
				paint: {
					"line-color": "#f59e0b",
					"line-width": 3,
					"line-opacity": 0.9,
				},
			});
		}
		if (!mapInstance.getLayer(MAP_TRACK_ARROW_LAYER_ID)) {
			mapInstance.addLayer({
				id: MAP_TRACK_ARROW_LAYER_ID,
				type: "symbol",
				source: MAP_TRACK_SOURCE_ID,
				layout: {
					"symbol-placement": "line",
					"symbol-spacing": 60,
					"text-field": "▶",
					"text-size": 10,
					"text-rotation-alignment": "map",
					"text-allow-overlap": true,
					"text-ignore-placement": true,
				},
				paint: { "text-color": "#f59e0b", "text-opacity": 0.9 },
			});
		}

		// ── Region filter highlight — 区域背景框（置于地图标注之下）──────────────────────
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
					paint: { "fill-color": "#60a5fa", "fill-opacity": 0.06 },
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
					paint: {
						"line-color": "#93c5fd",
						"line-width": 10,
						"line-blur": 8,
						"line-opacity": 0.3,
					},
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
					paint: {
						"line-color": "#60a5fa",
						"line-width": 2,
						"line-opacity": 0.9,
					},
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

		// 飞机图标图层 — 插入在地图标注层之前，使城市/路名标注始终可见
		if (!mapInstance.getLayer(MAP_LAYER_ID)) {
			mapInstance.addLayer(
				{
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
						"icon-size": [
							"interpolate",
							["linear"],
							["zoom"],
							3,
							0.06,
							6,
							0.1,
							10,
							0.15,
							14,
							0.2,
						],
						"icon-rotate": ["coalesce", ["get", "heading"], 0],
						"icon-rotation-alignment": "map",
						"icon-pitch-alignment": "viewport",
						"icon-allow-overlap": true,
						"icon-ignore-placement": true,
					},
				},
				firstSymbolLayer?.id,
			);
		}

		// Events
		mapInstance.on("click", MAP_LAYER_ID, (event) => {
			const feature = event.features?.[0];
			if (!feature || feature.geometry.type !== "Point") return;
			const flightId = feature.properties?.flight_id;
			if (typeof flightId === "string") handleSelectFlight(flightId);
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

		mapInstance.on("click", MAP_AIRPORT_LAYER_ID, (event) => {
			const feature = event.features?.[0];
			if (!feature) return;
			const iata = feature.properties?.iata as string | undefined;
			if (iata) store.scheduleAirport = iata;
		});
		mapInstance.on("mouseenter", MAP_AIRPORT_LAYER_ID, () => {
			mapInstance.getCanvas().style.cursor = "pointer";
		});
		mapInstance.on("mouseleave", MAP_AIRPORT_LAYER_ID, () => {
			mapInstance.getCanvas().style.cursor = "";
		});
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

	/** 更新国家/地区选择的边界高亮框 */
	function updateRegionHighlight(cc: string | null, regionCode: string | null) {
		if (!map.value) return;
		const src = map.value.getSource(MAP_REGION_HIGHLIGHT_SOURCE) as
			| GeoJSONSource
			| undefined;
		if (!src) return;
		if (!cc) {
			src.setData({ type: "FeatureCollection", features: [] });
			return;
		}
		const country = COUNTRIES.find((c) => c.code === cc);
		if (!country) return;
		const b =
			regionCode != null
				? (country.regions?.find((r) => r.code === regionCode) ?? country)
				: country;
		src.setData({
			type: "FeatureCollection",
			features: [
				{
					type: "Feature",
					properties: {},
					geometry: {
						type: "Polygon",
						coordinates: [
							[
								[b.lonMin, b.latMin],
								[b.lonMax, b.latMin],
								[b.lonMax, b.latMax],
								[b.lonMin, b.latMax],
								[b.lonMin, b.latMin],
							],
						],
					},
				},
			],
		});
	}

	// 国家/地区筛选时自动聚焦地图视野 + 边界高亮
	watch(
		[() => store.filterCountry, () => store.filterRegion],
		([cc, region]) => {
			updateRegionHighlight(cc, region);
			if (!map.value || !cc) return;
			const country = COUNTRIES.find((c) => c.code === cc);
			if (!country) return;
			const bbox =
				region != null
					? (country.regions?.find((r) => r.code === region) ?? country)
					: country;
			map.value.fitBounds(
				[
					bbox.lonMin,
					bbox.latMin,
					bbox.lonMax,
					bbox.latMax,
				] as LngLatBoundsLike,
				{ padding: 60, maxZoom: 8, essential: true },
			);
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
		() => store.selectedTrackPoints,
		() => {
			updateTrackLayer();
		},
	);

	watch(
		() => store.flightDetail,
		() => {
			updateAirportHighlight();
			updateRouteLayer();
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
			updateRouteLayer();
		},
	);

	// AQI 图层显示/隐藏
	watch(
		() => store.showAqiLayer,
		(show) => {
			if (!map.value) return;
			const vis = show ? "visible" : "none";
			setLayerVisibility(MAP_AQI_LAYER_ID, show);
			setLayerVisibility(MAP_AQI_LABEL_LAYER_ID, show);
		},
	);

	// AQI 热力图
	watch(showAqiHeatmap, (show) => {
		setLayerVisibility(MAP_AQI_HEATMAP_LAYER_ID, show);
	});

	// 风速风向图层
	watch(showWindLayer, async (show) => {
		if (show && weatherHubs.value.length === 0) await loadWeatherHubs();
		updateWeatherLayer();
		setLayerVisibility(MAP_WIND_ARROW_LAYER_ID, show);
		setLayerVisibility(MAP_WIND_LABEL_LAYER_ID, show);
	});

	// 温度图层
	watch(showTempLayer, async (show) => {
		if (show && weatherHubs.value.length === 0) await loadWeatherHubs();
		updateWeatherLayer();
		setLayerVisibility(MAP_TEMP_LAYER_ID, show);
	});

	// 航班密度热力图
	watch(showDensityLayer, (show) => {
		setLayerVisibility(MAP_DENSITY_LAYER_ID, show);
	});

	// AQI 数据更新
	watch(
		() => store.airQualityData,
		() => {
			updateAqiLayer();
		},
		{ deep: true },
	);

	// 语言设置变化时重新应用双语标注
	watch([labelLines, labelLine1, labelLine2], () => {
		if (map.value) applyBilingualLabels(map.value);
	});

	// 飞机颜色预设变化时刷新 icon（无需重载底图）
	// 加入防抖避免快速切换导致并发问题
	watch(aircraftColorPresetId, () => {
		if (_aircraftColorUpdateTimer !== null)
			clearTimeout(_aircraftColorUpdateTimer);
		_aircraftColorUpdateTimer = setTimeout(async () => {
			if (!map.value) return;
			try {
				await refreshAircraftIcons(map.value);
			} catch (err) {
				console.error("[Aircraft Color Watch] 刷新失败", err);
			}
		}, 100);
	});

	// 选中航班时自动切换到详情 tab
	watch(
		() => store.detailLoading,
		(loading) => {
			if (loading) {
				panelCollapsed.value = false;
				contextTab.value = "detail";
			}
		},
	);

	// 点击机场时自动切换到时刻表 tab
	watch(
		() => store.scheduleAirport,
		(iata) => {
			if (iata) {
				panelCollapsed.value = false;
				contextTab.value = "schedule";
			} else {
				contextTab.value = "flights";
			}
		},
	);

	// 面板折叠后 resize 地图
	watch(panelCollapsed, async () => {
		await nextTick();
		setTimeout(() => map.value?.resize(), 220);
	});

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
		store.disconnectSocket();
		map.value?.remove();
		map.value = null;
	});
</script>

<style scoped>
	/* ── 根布局：纵向弹性列 */
	.layout {
		height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--bg-base);
		overflow: hidden;
	}

	/* ── 任务栏 */
	.task-bar {
		height: 44px;
		flex-shrink: 0;
		display: flex;
		align-items: center;
		padding: 0 10px;
		gap: 6px;
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		z-index: 20;
	}

	.tb-left,
	.tb-right {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.tb-center {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
	}

	.tb-right {
		margin-left: auto;
	}

	.tb-btn {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 4px 10px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--t-fast);
	}

	.tb-btn:hover {
		background: var(--border);
		color: var(--text-primary);
	}

	.tb-btn.active {
		background: var(--accent-subtle);
		color: var(--accent);
		border-color: var(--accent);
	}

	.tb-icon {
		width: 13px;
		height: 13px;
		flex-shrink: 0;
	}

	.tb-stat {
		display: flex;
		align-items: baseline;
		gap: 3px;
	}

	.tb-num {
		font-size: 15px;
		font-weight: 700;
		color: var(--text-primary);
		font-variant-numeric: tabular-nums;
	}

	.tb-label {
		font-size: 10px;
		color: var(--text-muted);
		text-transform: uppercase;
	}

	.tb-air .tb-num {
		color: var(--accent);
	}
	.tb-gnd .tb-num {
		color: var(--text-secondary);
	}

	.tb-sep {
		color: var(--border-strong);
		font-size: 12px;
	}

	/* ── 工作区：横向弹性行 */
	.work-area {
		flex: 1;
		display: flex;
		min-height: 0;
		overflow: hidden;
	}

	/* ── 图层抽屉（从左滑入） */
	.layer-drawer {
		width: 0;
		flex-shrink: 0;
		overflow: hidden;
		transition: width var(--t-base);
		background: var(--bg-surface);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
	}

	.layer-drawer.open {
		width: 236px;
	}

	.drawer-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 12px 8px;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.drawer-title {
		font-size: 12px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text-secondary);
	}

	.drawer-close {
		width: 22px;
		height: 22px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		color: var(--text-muted);
		cursor: pointer;
		border-radius: var(--radius-sm);
		padding: 0;
	}

	.drawer-close svg {
		width: 10px;
		height: 10px;
	}

	.drawer-close:hover {
		background: var(--bg-raised);
		color: var(--text-primary);
	}

	.drawer-body {
		flex: 1;
		overflow-y: auto;
		padding: 12px;
	}

	/* ── 共用面板区块 */
	.panel-section {
		margin-bottom: 14px;
	}

	.panel-section:last-child {
		margin-bottom: 0;
	}

	.panel-title {
		font-size: 11px;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text-muted);
		margin-bottom: 8px;
	}

	.style-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 5px;
	}

	.style-btn {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 8px;
		border: 1px solid var(--border-strong);
		border-radius: var(--radius-sm);
		background: var(--bg-raised);
		color: var(--text-secondary);
		font-size: 11px;
		cursor: pointer;
		transition: all var(--t-fast);
	}

	.style-btn:hover {
		background: var(--border);
		color: var(--text-primary);
	}

	.style-btn.active {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}

	.aircraft-color-chip {
		width: 10px;
		height: 10px;
		border-radius: 999px;
		border: 1px solid rgba(255, 255, 255, 0.35);
		flex-shrink: 0;
	}

	.layer-toggle {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 6px;
		font-size: 12px;
		color: var(--text-secondary);
		cursor: pointer;
		user-select: none;
	}

	.layer-toggle input[type="checkbox"] {
		accent-color: var(--accent);
	}

	.panel-note {
		font-size: 11px;
		color: var(--warning);
		margin-top: 4px;
	}

	.label-row {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-top: 6px;
	}

	.label-sub {
		font-size: 11px;
		color: var(--text-secondary);
		min-width: 36px;
		flex-shrink: 0;
	}

	.lang-select {
		flex: 1;
		font-size: 12px;
		padding: 3px 6px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--bg-raised);
		color: var(--text-primary);
		cursor: pointer;
		outline: none;
	}

	.lang-select:focus {
		border-color: var(--accent);
	}

	/* ── Fallback toast */
	.fallback-toast {
		position: fixed;
		top: 60px;
		left: 50%;
		transform: translateX(-50%);
		z-index: 1000;
		background: rgba(180, 83, 9, 0.93);
		color: #fff;
		padding: 10px 20px;
		border-radius: var(--radius-lg);
		font-size: 13px;
		cursor: pointer;
		backdrop-filter: blur(6px);
		box-shadow: var(--shadow-md);
		max-width: 480px;
		text-align: center;
	}

	.toast-enter-active,
	.toast-leave-active {
		transition:
			opacity 0.3s,
			transform 0.3s;
	}

	.toast-enter-from,
	.toast-leave-to {
		opacity: 0;
		transform: translateX(-50%) translateY(-16px);
	}

	/* ── 地图 */
	.map-shell {
		flex: 1;
		position: relative;
		min-width: 0;
	}

	.map-canvas {
		width: 100%;
		height: 100%;
	}

	.map-status {
		position: absolute;
		left: 16px;
		bottom: 16px;
		padding: 8px 12px;
		border-radius: var(--radius-md);
		background: var(--bg-overlay);
		color: var(--text-primary);
		font-size: 13px;
		backdrop-filter: blur(4px);
	}

	/* ── 右侧上下文面板 */
	.context-panel {
		width: var(--panel-w);
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		background: var(--bg-surface);
		border-left: 1px solid var(--border);
		transition: width var(--t-base);
	}

	.context-panel.collapsed {
		width: 0;
	}

	.cp-tabs {
		display: flex;
		align-items: center;
		flex-shrink: 0;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface);
		padding: 0 4px;
	}

	.cp-tab {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 8px 12px;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-secondary);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		white-space: nowrap;
		margin-bottom: -1px;
		transition:
			color var(--t-fast),
			border-color var(--t-fast);
	}

	.cp-tab:hover {
		color: var(--text-primary);
	}

	.cp-tab.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}

	.cp-badge {
		padding: 1px 6px;
		background: var(--bg-raised);
		border-radius: 999px;
		font-size: 10px;
		color: var(--text-muted);
	}

	.cp-tab.active .cp-badge {
		background: var(--accent-subtle);
		color: var(--accent);
	}

	.cp-body {
		flex: 1;
		min-height: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}
</style>
