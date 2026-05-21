<template>
	<div class="playback-page">
		<!-- 顶部查询�?/ 摘要�?-->
		<div class="query-bar">
			<template v-if="!frames.length">
				<div class="qb-setup">
					<div class="qb-toolbar">
						<div class="qb-toolbar-primary">
							<div class="qb-time-group">
								<label class="qb-field">
									<span class="qb-field-label">{{ t("playback.start") }}</span>
									<input
										v-model="startInput"
										type="datetime-local"
										:max="endInput"
										class="qb-input"
									/>
								</label>
								<span class="qb-time-sep" aria-hidden="true">→</span>
								<label class="qb-field">
									<span class="qb-field-label">{{ t("playback.end") }}</span>
									<input
										v-model="endInput"
										type="datetime-local"
										:min="startInput"
										:max="endMaxIso"
										class="qb-input"
									/>
								</label>
							</div>
							<label class="qb-field qb-field-sample">
								<span class="qb-field-label">{{ t("playback.sample") }}</span>
								<select v-model.number="interval" class="qb-select">
									<option
										v-for="opt in intervalOptions"
										:key="opt.value"
										:value="opt.value"
									>
										{{ opt.label }}
									</option>
								</select>
							</label>
							<span class="qb-frames-badge">{{
								translate(localeStore.t, "playback.framesHint", {
									n: String(estimatedFrames),
								})
							}}</span>
							<div class="qb-mode-seg" role="group">
								<button
									type="button"
									class="qb-mode-seg-btn"
									:class="{ active: playbackMode === 'global' }"
									@click="playbackMode = 'global'"
								>
									{{ t("playback.modeGlobal") }}
								</button>
								<button
									type="button"
									class="qb-mode-seg-btn"
									:class="{ active: playbackMode === 'single' }"
									@click="playbackMode = 'single'"
								>
									{{ t("playback.modeSingle") }}
								</button>
							</div>
							<div class="qb-toolbar-actions">
								<div class="qb-help-anchor">
									<button
										type="button"
										class="qb-btn-icon"
										:class="{ active: showSetupHelp }"
										:aria-expanded="showSetupHelp"
										:title="t('playback.helpToggle')"
										@click="showSetupHelp = !showSetupHelp"
									>
										<svg viewBox="0 0 20 20" fill="currentColor">
											<path
												fill-rule="evenodd"
												d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"
												clip-rule="evenodd"
											/>
										</svg>
									</button>
									<aside v-if="showSetupHelp" class="qb-help-popover">
										<h3 class="qb-help-title">{{ t("playback.helpTitle") }}</h3>
										<ul class="qb-help-list">
											<li>{{ t("playback.help1") }}</li>
											<li>{{ t("playback.help2") }}</li>
											<li>{{ t("playback.help3") }}</li>
											<li>{{ t("playback.help4") }}</li>
										</ul>
									</aside>
								</div>
								<button
									class="qb-btn-load"
									:disabled="loadingData"
									@click="loadPlayback"
								>
									{{ loadingData ? t("playback.loading") : t("playback.load") }}
								</button>
							</div>
						</div>
						<div class="qb-toolbar-secondary">
							<div class="qb-chip-row">
								<span class="qb-chip-label">{{ t("playback.rangeQuick") }}</span>
								<button
									v-for="p in rangePresets"
									:key="p.hours"
									type="button"
									class="qb-chip"
									:class="{ active: activeRangeHours === p.hours }"
									@click="applyRangePreset(p.hours)"
								>
									{{ p.label }}
								</button>
							</div>
							<div class="qb-chip-row">
								<span class="qb-chip-label">{{ t("playback.sampleQuick") }}</span>
								<button
									v-for="opt in commonIntervalOptions"
									:key="opt.value"
									type="button"
									class="qb-chip"
									:class="{ active: interval === opt.value }"
									@click="setIntervalPreset(opt.value)"
								>
									{{ opt.label }}
								</button>
								<button
									type="button"
									class="qb-chip qb-chip-more"
									:class="{ active: showMoreIntervals || isExtraIntervalActive }"
									@click="showMoreIntervals = !showMoreIntervals"
								>
									{{ t("playback.moreSamples") }}
								</button>
							</div>
							<p class="qb-mode-hint-inline">
								{{
									playbackMode === "global"
										? t("playback.modeGlobalHint")
										: t("playback.modeSingleHint")
								}}
							</p>
						</div>
						<div v-if="showMoreIntervals" class="qb-toolbar-extra">
							<button
								v-for="opt in extraIntervalOptions"
								:key="opt.value"
								type="button"
								class="qb-chip"
								:class="{ active: interval === opt.value }"
								@click="setIntervalPreset(opt.value)"
							>
								{{ opt.label }}
							</button>
						</div>
					</div>
					<p v-if="errorMsg" class="qb-error">{{ errorMsg }}</p>
				</div>
			</template>
			<template v-else>
				<div class="qb-summary-row">
				<div class="qb-summary">
					<svg class="qb-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z"
							clip-rule="evenodd"
						/>
					</svg>
					<span class="qb-range"
						>{{ startInput.replace("T", " ") }} → {{ endInput.replace("T", " ") }}</span
					>
					<span class="qb-badge"
						>{{ frames.length }} {{ t("playback.framesWord") }} ·
						{{ durationStr }}</span
					>
				</div>
				<div
					v-if="playbackMode === 'global' || !focusFlightId"
					class="qb-live-stats"
				>
					<span
						><strong>{{ currentFlightCount.toLocaleString() }}</strong>
						{{ t("playback.flights") }}</span
					>
					<span class="qb-stat-sep">·</span>
					<span class="qb-stat-air"
						><strong>{{ airborneCount.toLocaleString() }}</strong>
						{{ t("playback.airborne") }}</span
					>
					<span class="qb-stat-sep">·</span>
					<span
						><strong>{{
							(currentFlightCount - airborneCount).toLocaleString()
						}}</strong>
						{{ t("playback.ground") }}</span
					>
					<span class="qb-stat-sep">·</span>
					<span>{{ progressPct.toFixed(0) }}%</span>
				</div>
				<div v-else class="qb-focus-stat">
					<strong>{{ focusFlightLabel }}</strong>
					<span class="qb-stat-sep">·</span>
					<span>{{ progressPct.toFixed(0) }}%</span>
				</div>
				<div class="qb-mode-seg qb-mode-seg-compact">
					<button
						type="button"
						class="qb-mode-seg-btn"
						:class="{ active: playbackMode === 'global' }"
						@click="setPlaybackMode('global')"
					>
						{{ t("playback.modeGlobal") }}
					</button>
					<button
						type="button"
						class="qb-mode-seg-btn"
						:class="{ active: playbackMode === 'single' }"
						@click="setPlaybackMode('single')"
					>
						{{ t("playback.modeSingle") }}
					</button>
				</div>
				<label
					v-if="playbackMode === 'single' && focusFlightId"
					class="qb-follow"
				>
					<input v-model="followAircraft" type="checkbox" />
					{{ t("playback.followAircraft") }}
				</label>
				<button class="qb-btn-reset" @click="resetPlayback">{{ t("playback.requery") }}</button>
				</div>
			</template>
		</div>

		<!-- 地图主体 -->
		<div class="map-wrap" :class="{ 'map-wrap--with-list': frames.length > 0 }">
			<div ref="mapEl" class="map-el" />
			<div v-if="!frames.length" class="map-hint map-hint-setup">
				<p class="map-hint-title">{{ t("playback.mapEmptyTitle") }}</p>
				<ol class="map-hint-steps">
					<li>{{ t("playback.mapEmptyStep1") }}</li>
					<li>{{ t("playback.mapEmptyStep2") }}</li>
					<li>{{ t("playback.mapEmptyStep3") }}</li>
				</ol>
			</div>
			<div
				v-else-if="playbackMode === 'single' && !focusFlightId"
				class="map-hint map-hint-warn"
			>
				<p class="map-hint-body">{{ t("playback.pickFlightFirst") }}</p>
			</div>
			<div
				v-else-if="currentFlightCount === 0"
				class="map-hint map-hint-warn"
			>
				<p class="map-hint-body">{{ t("playback.mapEmptyNoFlights") }}</p>
			</div>
			<PlaybackFlightListPanel
				v-if="frames.length"
				:flights="playbackCatalog"
				:selected-id="focusFlightId"
				:mode="playbackMode"
				@select="onCatalogSelect"
			/>
			<aside
				v-if="frames.length && activeFlightId"
				class="pb-detail"
			>
				<div class="pb-detail-header">
					<span>{{ t("playback.detail") }}</span>
					<button
						type="button"
						class="pb-detail-close"
						:title="t('playback.deselect')"
						@click="clearSelection"
					>
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
				</div>
				<FlightDetailCard
					:detail="displayDetail"
					:loading="detailLoading"
				/>
			</aside>
			<!-- 底部悬浮控制台：仅数据加载后显示 -->
			<div v-if="frames.length" class="play-dock">
			<!-- 时间�?-->
			<div class="dock-timeline">
				<span class="ts-edge">{{ fmtTs(frames[0]?.ts ?? "") }}</span>
				<input
					v-model.number="currentFrame"
					type="range"
					min="0"
					:max="frames.length - 1"
					class="tl-slider"
					@input="onSliderInput"
				/>
				<span class="ts-edge">{{
					fmtTs(frames[frames.length - 1]?.ts ?? "")
				}}</span>
			</div>
			<!-- 控制�?-->
			<div class="dock-controls">
				<div class="dock-btns">
					<button class="dk-btn" :title="t('playback.dockStart')" @click="goToStart">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M8.445 14.832A1 1 0 0010 14v-2.798l5.445 3.63A1 1 0 0017 14V6a1 1 0 00-1.555-.832L10 8.798V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z"
							/>
						</svg>
					</button>
					<button class="dk-btn" :title="t('playback.dockPrev')" @click="stepBack">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M11 4a7 7 0 100 14A7 7 0 0011 4zM9.5 9.172l3 1.5-3 1.5V9.172zM7 10a4 4 0 018 0v.001a4 4 0 01-8 0V10z"
							/>
						</svg>
					</button>
					<button
						class="dk-btn dk-play"
						:disabled="!canPlayback"
						:title="playing ? t('playback.dockPause') : t('playback.dockPlay')"
						@click="togglePlay"
					>
						<svg v-if="!playing" viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
								clip-rule="evenodd"
							/>
						</svg>
						<svg v-else viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
					<button class="dk-btn" :title="t('playback.dockNext')" @click="stepForward">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
					<button class="dk-btn" :title="t('playback.dockEnd')" @click="goToEnd">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4A1 1 0 0010 6v2.798l-5.445-3.63z"
							/>
						</svg>
					</button>
					<button
						:class="['dk-btn', { 'dk-active': loop }]"
						:title="t('playback.dockLoop')"
						@click="loop = !loop"
					>
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
				</div>
				<div class="dock-time">
					<span class="dk-ts">{{ fmtTs(currentTs) }}</span>
					<span class="dk-ratio"
						>{{ currentFrame + 1 }} / {{ frames.length }}</span
					>
				</div>
				<div class="dock-speed">
					<span class="dk-spd-lbl">{{ t("playback.dockSpeed") }}</span>
					<select v-model.number="speed" class="dk-spd-sel">
						<option :value="0.5">0.5×</option>
						<option :value="1">1×</option>
						<option :value="2">2×</option>
						<option :value="5">5×</option>
						<option :value="10">10×</option>
					</select>
				</div>
			</div>
		</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { computed, onMounted, onUnmounted, ref, watch } from "vue";
	import maplibregl from "maplibre-gl";
	import "maplibre-gl/dist/maplibre-gl.css";
	import { fetchPlaybackFrames } from "../services/api";
	import { translate, useLocaleStore } from "../i18n";
	import { useFlightStore } from "../stores/flight";
	import FlightDetailCard from "../components/FlightDetailCard.vue";
	import PlaybackFlightListPanel from "../components/playback/PlaybackFlightListPanel.vue";
	import {
		buildPlaybackCatalog,
		buildPlaybackFlightTrack,
		flightsForPlaybackFrame,
	} from "../utils/playbackCatalog";
	import type {
		FlightBrief,
		FlightDetail,
		PlaybackFlightPoint,
		PlaybackFrame,
	} from "../types/flight";
	import { resolveStyleAircraftColor, AIRCRAFT_COLOR } from "../config/aircraftColors";
	import {
		flightHoverIconImageLayout,
		flightHoverLabelLayout,
		flightHoverLabelPaint,
		flightIconImageLayout,
		flightIconSizeLayout,
	} from "../config/mapLayerStyles";
	import {
		AIRPORT_HIGHLIGHT_LAYER,
		AIRPORT_HIGHLIGHT_SOURCE,
		TRACK_HISTORY_SEG_LAYER_ID,
		buildHistoricalTrackSegmentCollection,
		buildPlannedRouteGeoJson,
		buildRouteAirportHighlightCollection,
		historicalTrackSegmentLinePaint,
		playbackFleetTrailLinePaint,
		resolveRouteAirports,
		routeAirportHighlightPaint,
	} from "../utils/flightTrackMap";
	import { HIDE_ALL_FEATURES_FILTER } from "../utils/mapFilters";
	import {
		buildOpenFreeMapStyleUrl,
		isOpenFreeMapPlaceLabelLayer,
		OPENFREEMAP_LABEL_FONTS,
		rewriteMapResourceUrl,
	} from "../utils/mapBasemap";
	import { scheduleMapUpdate } from "../utils/mapUpdateScheduler";
	import {
		patchFlightGeoJson,
		type FlightPointFeature,
	} from "../utils/flightGeoJson";
	import {
		resetFlightFeatureStateTracking,
		syncFlightHighlightStates,
	} from "../utils/flightFeatureState";
	import {
		createPlaybackTrailState,
		resetPlaybackTrailState,
		updatePlaybackTrailGeoJson,
	} from "../utils/playbackTrail";
	import planeIconRaw from "../icons/plane.svg?raw";
	import planeGroundIconRaw from "../icons/plane_ground.svg?raw";

	const MAPTILER_KEY = (import.meta.env.VITE_MAPTILER_KEY as string) || "";
	const STADIA_KEY = (import.meta.env.VITE_STADIA_KEY as string) || "";

	type MapProvider = "maptiler" | "stadia" | "openfreemap";

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

	const MAPTILER_STYLE_IDS = [
		"streets-v2-dark",
		"streets-v2",
		"outdoor-v2",
		"hybrid",
		"dataviz-dark",
		"dataviz",
	] as const;
	const STADIA_STYLE_IDS = [
		"alidade_smooth_dark",
		"alidade_smooth",
		"stamen_terrain",
		"alidade_satellite",
	] as const;
	const OPENFREEMAP_STYLE_IDS = ["liberty", "bright", "positron"] as const;

	function pickStyleId(ids: readonly string[], want: string): string {
		return ids.includes(want) ? want : ids[0]!;
	}

	const SOURCE_ID = "playback-flights";
	const LAYER_ID = "playback-icons";
	const HOVER_SOURCE_ID = "playback-flight-hover-tip";
	const HOVER_LABEL_LAYER_ID = "playback-hover-label";
	const HOVER_ICON_LAYER_ID = "playback-flight-hover-icon";
	const SELECTED_LAYER_ID = "playback-selected-flight";
	const MARKED_LAYER_ID = "playback-marked-flight";
	const MAX_PLAYBACK_FRAMES = 2000;
	const ALTITUDE_GLOW_LAYER_ID = "playback-altitude-glow";
	const TRAIL_SOURCE_ID = "playback-trails";
	const TRAIL_LAYER_ID = "playback-trail-lines";
	const TRAIL_LENGTH = 12;
	const PB_TRACK_SEG_SOURCE_ID = "playback-flight-track-segments";
	const PB_ROUTE_SOURCE_ID = "playback-planned-route";
	const PB_ROUTE_LAYER_ID = "playback-planned-route-line";
	const PB_AIRPORT_HIGHLIGHT_SOURCE_ID = AIRPORT_HIGHLIGHT_SOURCE;
	const PB_AIRPORT_HIGHLIGHT_LAYER_ID = AIRPORT_HIGHLIGHT_LAYER;
	const LABEL_LINE1 = "name:en";
	const LABEL_LINE2 = "name:zh-Hans";

	const mapEl = ref<HTMLElement | null>(null);
	let map: maplibregl.Map | null = null;
	let mapLayersReady = false;
	const trailState = createPlaybackTrailState();
	let playbackFlightIndex: Map<string, FlightPointFeature> | null = null;
	let lastFollowEaseAt = 0;

	const PB_FEATURE_SELECTED: maplibregl.FilterSpecification = [
		"==",
		["feature-state", "selected"],
		true,
	];
	const PB_FEATURE_MARKED: maplibregl.FilterSpecification = [
		"==",
		["feature-state", "marked"],
		true,
	];
	let currentProvider: MapProvider = MAP_DEFAULT_PROVIDER as MapProvider;
	let currentStyleId = MAP_DEFAULT_STYLE;
	let flightHoverHandlersBound = false;
	let hoveredFlightId: string | null = null;

	// ── 表单状�?──────────────────────────────────────────────────────────────
	const store = useFlightStore();
	const localeStore = useLocaleStore();
	const t = (path: string) => translate(localeStore.t, path);

	const INTERVAL_SECS = [
		60, 300, 600, 1800, 3600, 7200, 21600, 43200, 86400,
	] as const;
	const COMMON_INTERVAL_SECS = new Set<number>([60, 300, 600, 3600]);

	const showSetupHelp = ref(false);
	const showMoreIntervals = ref(false);

	const intervalOptions = computed(() =>
		INTERVAL_SECS.map((value) => ({
			value,
			label: translate(localeStore.t, `playback.i.${value}`),
		})),
	);

	const commonIntervalOptions = computed(() =>
		intervalOptions.value.filter((o) => COMMON_INTERVAL_SECS.has(o.value)),
	);

	const extraIntervalOptions = computed(() =>
		intervalOptions.value.filter((o) => !COMMON_INTERVAL_SECS.has(o.value)),
	);

	const isExtraIntervalActive = computed(() =>
		extraIntervalOptions.value.some((o) => o.value === interval.value),
	);

	const rangePresets = computed(() => {
		const d = localeStore.t;
		return [
			{ hours: 1, label: translate(d, "playback.range1h") },
			{ hours: 2, label: translate(d, "playback.range2h") },
			{ hours: 6, label: translate(d, "playback.range6h") },
			{ hours: 12, label: translate(d, "playback.range12h") },
			{ hours: 24, label: translate(d, "playback.range24h") },
		];
	});

	const startInput = ref(fmtDatetimeLocal(Date.now() - 3600_000));
	const endInput = ref(fmtDatetimeLocal(Date.now()));
	const interval = ref(300);

	const endMaxIso = computed(() => fmtDatetimeLocal(Date.now()));

	function clampEndToNow() {
		const now = Date.now();
		const e = new Date(endInput.value).getTime();
		if (!Number.isFinite(e) || e > now) {
			endInput.value = fmtDatetimeLocal(now);
		}
	}

	watch(endInput, clampEndToNow);

	const RANGE_PRESET_INTERVALS: Record<number, number> = {
		1: 60,
		2: 300,
		6: 600,
		12: 1800,
		24: 3600,
	};

	const estimatedFrames = computed(() => {
		const s = new Date(startInput.value).getTime();
		const e = new Date(endInput.value).getTime();
		if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) return 0;
		return Math.ceil((e - s) / 1000 / interval.value);
	});

	const activeRangeHours = computed(() => {
		const now = Date.now();
		const e = new Date(endInput.value).getTime();
		const s = new Date(startInput.value).getTime();
		if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) return null;
		if (Math.abs(e - now) > 120_000) return null;
		const spanH = (e - s) / 3600_000;
		for (const hours of [1, 2, 6, 12, 24] as const) {
			if (Math.abs(spanH - hours) < 0.08) return hours;
		}
		return null;
	});

	function suggestIntervalForRange(startMs: number, endMs: number): number {
		const spanSec = Math.max(1, (endMs - startMs) / 1000);
		const TARGET_FRAMES = 100;
		const ideal = spanSec / TARGET_FRAMES;
		const opts = [...INTERVAL_SECS].sort((a, b) => a - b);
		let best = opts[opts.length - 1] ?? 300;
		let bestScore = Infinity;
		for (const opt of opts) {
			const frames = Math.ceil(spanSec / opt);
			if (frames > MAX_PLAYBACK_FRAMES) continue;
			const score = Math.abs(Math.log(opt) - Math.log(Math.max(ideal, 1)));
			if (score < bestScore) {
				bestScore = score;
				best = opt;
			}
		}
		return best;
	}

	function intervalForRangeHours(hours: number): number {
		return RANGE_PRESET_INTERVALS[hours] ?? suggestIntervalForRange(
			Date.now() - hours * 3600_000,
			Date.now(),
		);
	}

	/** 帧数超限时缩短时段：固定结束时间，只把开始时间往后推 */
	function trimRangeToMaxFrames() {
		const stepMs = interval.value * 1000;
		const now = Date.now();
		let e = new Date(endInput.value).getTime();
		let s = new Date(startInput.value).getTime();
		if (!Number.isFinite(s) || !Number.isFinite(e) || e <= s) return;
		if (e > now) {
			e = now;
			endInput.value = fmtDatetimeLocal(e);
		}
		const maxSpan = stepMs * MAX_PLAYBACK_FRAMES;
		if (e - s > maxSpan) {
			startInput.value = fmtDatetimeLocal(e - maxSpan);
		}
	}

	function applyRangePreset(hours: number) {
		const end = Date.now();
		endInput.value = fmtDatetimeLocal(end);
		startInput.value = fmtDatetimeLocal(end - hours * 3600_000);
		interval.value = intervalForRangeHours(hours);
		trimRangeToMaxFrames();
	}

	function setIntervalPreset(sec: number) {
		interval.value = sec;
		trimRangeToMaxFrames();
	}

	function playbackPointToDetail(p: PlaybackFlightPoint): FlightDetail {
		const cat = playbackCatalog.value.find((c) => c.id === p.id);
		return {
			flight_id: p.id,
			callsign: p.cs ?? undefined,
			lat: p.lat,
			lon: p.lon,
			heading: p.hdg ?? undefined,
			speed_kts: p.spd ?? undefined,
			altitude_ft: p.alt ?? undefined,
			aircraft_category: p.cat ?? undefined,
			updated_at: currentTs.value || new Date().toISOString(),
			departure_airport: p.dep ?? cat?.departure_airport ?? null,
			arrival_airport: p.arr ?? cat?.arrival_airport ?? null,
			aircraft_type: null,
			status: null,
			departure_weather: null,
			arrival_weather: null,
			current_weather: null,
		};
	}

	const playbackDetail = computed<FlightDetail | null>(() => {
		const id = activeFlightId.value;
		if (!id || !frames.value.length) return null;
		const p =
			frames.value[currentFrame.value]?.flights.find((f) => f.id === id) ??
			getPlaybackPointAtOrBefore(id, currentFrame.value);
		return p ? playbackPointToDetail(p) : null;
	});

	const displayDetail = computed<FlightDetail | null>(() => {
		const pb = playbackDetail.value;
		const api = store.flightDetail;
		if (!pb) return api;
		if (!api || api.flight_id !== pb.flight_id) return pb;
		return {
			...pb,
			aircraft_type: api.aircraft_type ?? pb.aircraft_type,
			status: api.status ?? pb.status,
			departure_airport_zh:
				api.departure_airport_zh ?? pb.departure_airport_zh,
			arrival_airport_zh: api.arrival_airport_zh ?? pb.arrival_airport_zh,
			departure_lat: pb.departure_lat ?? api.departure_lat,
			departure_lon: pb.departure_lon ?? api.departure_lon,
			arrival_lat: pb.arrival_lat ?? api.arrival_lat,
			arrival_lon: pb.arrival_lon ?? api.arrival_lon,
			departure_weather: api.departure_weather ?? pb.departure_weather,
			arrival_weather: api.arrival_weather ?? pb.arrival_weather,
			current_weather: api.current_weather ?? pb.current_weather,
		};
	});

	const detailLoading = computed(
		() =>
			store.detailLoading &&
			!!focusFlightId.value &&
			!playbackDetail.value,
	);

	async function handleSelectPlaybackFlight(flightId: string) {
		focusFlightId.value = flightId;
		void store.loadFlightDetail(flightId);
		if (map) {
			updateSelectedHighlight(map);
			renderFrame(currentFrame.value);
			updatePlaybackSelectionOverlays();
		}
	}

	function clearSelection() {
		focusFlightId.value = null;
		void store.loadFlightDetail(null);
	}

	function resetPlayback() {
		frames.value = [];
		currentFrame.value = 0;
		playing.value = false;
		clearPlayTimer();
		focusFlightId.value = null;
		clearSelection();
		renderFrame(0);
	}

	watch(interval, () => {
		trimRangeToMaxFrames();
	});

	// ── 回放状�?──────────────────────────────────────────────────────────────
	const playbackMode = ref<"global" | "single">("global");
	const focusFlightId = ref<string | null>(null);
	const followAircraft = ref(true);

	const playbackCatalog = computed(() => buildPlaybackCatalog(frames.value));

	const focusFlightLabel = computed(() => {
		const id = focusFlightId.value;
		if (!id) return "";
		const row = playbackCatalog.value.find((f) => f.id === id);
		return row?.callsign ?? id;
	});

	const activeFlightId = computed(
		() => focusFlightId.value ?? store.selectedFlightId,
	);

	const canPlayback = computed(
		() => playbackMode.value !== "single" || !!focusFlightId.value,
	);

	const playbackTrackPoints = computed(() => {
		const id = activeFlightId.value;
		if (!id || !frames.value.length) return [];
		return buildPlaybackFlightTrack(frames.value, id, currentFrame.value);
	});

	function flightsAtFrame(idx: number): PlaybackFlightPoint[] {
		return flightsForPlaybackFrame(
			frames.value[idx],
			playbackMode.value,
			focusFlightId.value,
		);
	}

	function getPlaybackPointAtOrBefore(
		flightId: string,
		frameIdx: number,
	): PlaybackFlightPoint | null {
		for (let i = frameIdx; i >= 0; i--) {
			const p = frames.value[i]?.flights.find((f) => f.id === flightId);
			if (p) return p;
		}
		return null;
	}

	function setPlaybackMode(mode: "global" | "single") {
		playbackMode.value = mode;
		if (mode === "global") return;
		playing.value = false;
		clearPlayTimer();
	}

	function onCatalogSelect(flightId: string) {
		focusFlightId.value = flightId;
		void handleSelectPlaybackFlight(flightId);
	}

	const loadingData = ref(false);
	const errorMsg = ref("");
	const frames = ref<PlaybackFrame[]>([]);
	const currentFrame = ref(0);
	const playing = ref(false);
	const speed = ref(2);
	const loop = ref(false);
	let playTimer: ReturnType<typeof setTimeout> | null = null;

	const currentTs = computed(() => frames.value[currentFrame.value]?.ts ?? "");
	const currentFlights = computed(() => flightsAtFrame(currentFrame.value));

	const currentFlightCount = computed(() => currentFlights.value.length);

	const airborneCount = computed(
		() => currentFlights.value.filter((f) => (f.alt ?? 0) > 100).length,
	);
	const progressPct = computed(() =>
		frames.value.length > 1
			? (currentFrame.value / (frames.value.length - 1)) * 100
			: 0,
	);
	const durationStr = computed(() => {
		if (frames.value.length < 2) return "";
		const ms =
			new Date(frames.value[frames.value.length - 1].ts).getTime() -
			new Date(frames.value[0].ts).getTime();
		const min = Math.round(ms / 60000);
		const d = localeStore.t;
		if (min < 60) {
			return translate(d, "playback.durationMin", { n: String(min) });
		}
		const h = Math.floor(min / 60);
		const m = min % 60;
		if (m > 0) {
			return translate(d, "playback.durationHm", {
				h: String(h),
				m: String(m),
			});
		}
		return translate(d, "playback.durationH", { h: String(h) });
	});

	// ── 工具函数 ──────────────────────────────────────────────────────────────
	function fmtDatetimeLocal(ms: number): string {
		const d = new Date(ms);
		const pad = (n: number) => String(n).padStart(2, "0");
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

	function fmtTs(ts: string): string {
		if (!ts) return "--";
		const d = new Date(ts);
		const pad = (n: number) => String(n).padStart(2, "0");
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

	function buildMaptilerStyleUrl(styleId: string): string {
		if (import.meta.env.PROD) {
			return `https://api.maptiler.com/maps/${styleId}/style.json?key=${MAPTILER_KEY}`;
		}
		return `/maptiler-proxy/maps/${styleId}/style.json?key=${MAPTILER_KEY}`;
	}

	function buildStadiaStyleUrl(styleId: string): string {
		if (import.meta.env.PROD) {
			return `https://tiles.stadiamaps.com/styles/${styleId}/style.json${STADIA_KEY ? `?api_key=${STADIA_KEY}` : ""}`;
		}
		return `/stadia-proxy/styles/${styleId}/style.json${STADIA_KEY ? `?api_key=${STADIA_KEY}` : ""}`;
	}


	const MAPTILER_STYLE_ALIASES: Record<string, string> = {
		"satellite-hybrid": "hybrid",
	};

	function normalizePlaybackMaptiler(styleId: string): string {
		return MAPTILER_STYLE_ALIASES[styleId] ?? styleId;
	}

	async function determineInitialStyle(): Promise<{
		url: string;
		provider: MapProvider;
		styleId: string;
	}> {
		const wantProvider = MAP_DEFAULT_PROVIDER as MapProvider;
		const wantStyle = MAP_DEFAULT_STYLE;

		if (wantProvider === "openfreemap") {
			const styleId = pickStyleId(OPENFREEMAP_STYLE_IDS, wantStyle);
			return {
				url: buildOpenFreeMapStyleUrl(styleId),
				provider: "openfreemap",
				styleId,
			};
		}

		if (wantProvider === "maptiler" && MAPTILER_KEY) {
			const wantNorm = normalizePlaybackMaptiler(wantStyle);
			const styleId = pickStyleId(MAPTILER_STYLE_IDS, wantNorm);
			try {
				const resp = await fetch(buildMaptilerStyleUrl(styleId));
				if (resp.ok) {
					return {
						url: buildMaptilerStyleUrl(styleId),
						provider: "maptiler",
						styleId,
					};
				}
			} catch {
				// continue fallback chain
			}
		}

		if (wantProvider === "stadia" && STADIA_KEY) {
			const styleId = pickStyleId(STADIA_STYLE_IDS, wantStyle);
			return {
				url: buildStadiaStyleUrl(styleId),
				provider: "stadia",
				styleId,
			};
		}

		if (wantProvider !== "maptiler" && MAPTILER_KEY) {
			const styleId = MAPTILER_STYLE_IDS[0];
			try {
				const resp = await fetch(buildMaptilerStyleUrl(styleId));
				if (resp.ok) {
					return {
						url: buildMaptilerStyleUrl(styleId),
						provider: "maptiler",
						styleId,
					};
				}
			} catch {
				// continue fallback chain
			}
		}

		if (STADIA_KEY) {
			const styleId = STADIA_STYLE_IDS[0];
			return { url: buildStadiaStyleUrl(styleId), provider: "stadia", styleId };
		}

		const styleId = OPENFREEMAP_STYLE_IDS[0];
		return {
			url: buildOpenFreeMapStyleUrl(styleId),
			provider: "openfreemap",
			styleId,
		};
	}

	function transformRequest(url: string): { url: string } {
		return { url: rewriteMapResourceUrl(url) };
	}

	function applyBilingualLabels(mapInstance: maplibregl.Map) {
		const style = mapInstance.getStyle();
		const boldFonts: Record<MapProvider, string[]> = {
			maptiler: ["Open Sans Bold", "Arial Unicode MS Regular"],
			stadia: ["Open Sans Bold", "Arial Unicode MS Regular"],
			openfreemap: [...OPENFREEMAP_LABEL_FONTS],
		};
		const fonts = boldFonts[currentProvider] ?? [
			"Open Sans Bold",
			"Arial Unicode MS Regular",
		];
		const useOpenFreeMapNativePlaceLabels = currentProvider === "openfreemap";

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

		function line2Expr(langKey: string): unknown[] {
			if (langKey === "name:en") {
				return ["coalesce", ["get", "name:en"], ["get", "name_en"], ""];
			}
			if (langKey === "name") {
				return ["coalesce", ["get", "name"], ""];
			}
			if (langKey === "name:zh-Hans" || langKey === "name:zh-Hant") {
				return ["coalesce", ["get", langKey], ["get", "name:zh"], ""];
			}
			return ["coalesce", ["get", langKey], ""];
		}

		function hasLang(langKey: string): unknown[] {
			if (langKey === "name:en") {
				return ["coalesce", ["get", "name:en"], ["get", "name_en"], ""];
			}
			if (langKey === "name:zh-Hans" || langKey === "name:zh-Hant") {
				return ["coalesce", ["get", langKey], ["get", "name:zh"], ""];
			}
			return ["coalesce", ["get", langKey], ""];
		}

		const textField: unknown[] = [
			"case",
			["!=", hasLang(LABEL_LINE2), ""],
			["concat", line1Expr(LABEL_LINE1), "\n", line2Expr(LABEL_LINE2)],
			line1Expr(LABEL_LINE1),
		];

		for (const layer of style.layers) {
			if (layer.type !== "symbol") continue;
			const layout =
				(layer as { layout?: Record<string, unknown> }).layout ?? {};
			const field = layout["text-field"];
			if (!field) continue;
			const fieldStr = JSON.stringify(field);
			if (!fieldStr.includes("name")) continue;
			if (/"ref"/.test(fieldStr)) continue;
			if (
				layer.id.includes("shield") ||
				layer.id.includes("route") ||
				layer.id.includes("-ref")
			) {
				continue;
			}

			if (
				useOpenFreeMapNativePlaceLabels &&
				isOpenFreeMapPlaceLabelLayer(layer.id)
			) {
				mapInstance.setLayoutProperty(layer.id, "text-font", fonts);
				continue;
			}

			mapInstance.setLayoutProperty(layer.id, "text-field", textField);
			mapInstance.setLayoutProperty(layer.id, "text-font", fonts);
		}
	}

	// ── SVG 图标加载（与 MapView 相同�?Canvas 策略，永�?reject）─────────────────────
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

	function loadSvgIcon(
		mapInstance: maplibregl.Map,
		id: string,
		svgRaw: string,
		color: string,
	): Promise<void> {
		const colored = svgWithAircraftStyle(svgRaw, color);
		const url =
			"data:image/svg+xml;charset=utf-8," + encodeURIComponent(colored);
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
					resolve();
					return;
				}
				ctx.drawImage(img, 0, 0, w, h);
				try {
					if (mapInstance.hasImage(id)) mapInstance.removeImage(id);
					mapInstance.addImage(id, ctx.getImageData(0, 0, w, h));
				} catch (e) {
					console.warn(`[PlaybackIcon] addImage 失败: ${id}`, e);
				}
				resolve();
			};
			img.onerror = (e) => {
				console.warn(`[PlaybackIcon] 图标加载失败: ${id}`, e);
				resolve();
			};
			img.src = url;
		});
	}

	function clearFlightHover(mapInstance: maplibregl.Map) {
		hoveredFlightId = null;
		if (mapInstance.getLayer(HOVER_ICON_LAYER_ID)) {
			mapInstance.setFilter(HOVER_ICON_LAYER_ID, HIDE_ALL_FEATURES_FILTER);
		}
		const tip = mapInstance.getSource(HOVER_SOURCE_ID) as
			| maplibregl.GeoJSONSource
			| undefined;
		tip?.setData({ type: "FeatureCollection", features: [] });
	}

	function setFlightHover(
		mapInstance: maplibregl.Map,
		feature: GeoJSON.Feature<GeoJSON.Point>,
	) {
		const props = feature.properties ?? {};
		const flightId = props.flight_id;
		if (typeof flightId !== "string" || !flightId) return;
		if (hoveredFlightId === flightId) return;

		hoveredFlightId = flightId;
		if (mapInstance.getLayer(HOVER_ICON_LAYER_ID)) {
			mapInstance.setFilter(HOVER_ICON_LAYER_ID, [
				"==",
				["get", "flight_id"],
				flightId,
			]);
		}

		const altRaw = props.altitude_ft as number | null | undefined;
		const spdRaw = props.speed_kts as number | null | undefined;
		const alt =
			altRaw != null && Number.isFinite(altRaw) ? Math.round(altRaw) : null;
		const spd =
			spdRaw != null && Number.isFinite(spdRaw) ? Math.round(spdRaw) : null;
		const l1 = String(props.callsign ?? flightId).trim() || flightId;
		const l2 =
			alt != null && spd != null
				? `${alt}  ${spd}`
				: alt != null
					? String(alt)
					: spd != null
						? String(spd)
						: "";

		const tip = mapInstance.getSource(HOVER_SOURCE_ID) as
			| maplibregl.GeoJSONSource
			| undefined;
		tip?.setData({
			type: "FeatureCollection",
			features: [
				{
					type: "Feature",
					geometry: feature.geometry,
					properties: { l1, l2, l3: "" },
				},
			],
		});
	}

	function flightHoverHitLayers(mapInstance: maplibregl.Map): string[] {
		return [HOVER_ICON_LAYER_ID, LAYER_ID].filter((id) =>
			Boolean(mapInstance.getLayer(id)),
		);
	}

	function syncPlaybackHighlights(mapInstance: maplibregl.Map) {
		syncFlightHighlightStates(mapInstance, SOURCE_ID, {
			selectedId: activeFlightId.value,
			markedIds: store.markedFlightIds,
			hoveredId: null,
		});
	}

	function updateSelectedHighlight(mapInstance: maplibregl.Map) {
		if (!mapInstance.getLayer(SELECTED_LAYER_ID)) return;
		syncPlaybackHighlights(mapInstance);
	}

	function updateMarkedHighlight(mapInstance: maplibregl.Map) {
		if (!mapInstance.getLayer(MARKED_LAYER_ID)) return;
		syncPlaybackHighlights(mapInstance);
	}

	function bindPlaybackFlightHandlers(mapInstance: maplibregl.Map) {
		if (flightHoverHandlersBound) return;
		flightHoverHandlersBound = true;

		mapInstance.on("mousemove", (event) => {
			const layers = flightHoverHitLayers(mapInstance);
			if (!layers.length) return;

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

		mapInstance.on("click", (event) => {
			const layers = flightHoverHitLayers(mapInstance);
			if (!layers.length) return;
			const feature = mapInstance.queryRenderedFeatures(event.point, {
				layers,
			})[0];
			if (!feature || feature.geometry.type !== "Point") return;
			const flightId = feature.properties?.flight_id;
			if (typeof flightId === "string" && flightId) {
				void handleSelectPlaybackFlight(flightId);
			}
		});
	}

	async function reinitPlaybackLayers(mapInstance: maplibregl.Map) {
		applyBilingualLabels(mapInstance);
		const firstSymbolLayer = mapInstance
			.getStyle()
			.layers.find((layer) => layer.type === "symbol");

		if (!mapInstance.getSource(TRAIL_SOURCE_ID)) {
			mapInstance.addSource(TRAIL_SOURCE_ID, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
		}
		if (!mapInstance.getLayer(TRAIL_LAYER_ID)) {
			mapInstance.addLayer({
				id: TRAIL_LAYER_ID,
				type: "line",
				source: TRAIL_SOURCE_ID,
				layout: { "line-cap": "round", "line-join": "round" },
				paint: playbackFleetTrailLinePaint(),
			});
		}

		if (!mapInstance.getSource(PB_TRACK_SEG_SOURCE_ID)) {
			mapInstance.addSource(PB_TRACK_SEG_SOURCE_ID, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
		}
		if (!mapInstance.getLayer(TRACK_HISTORY_SEG_LAYER_ID)) {
			mapInstance.addLayer({
				id: TRACK_HISTORY_SEG_LAYER_ID,
				type: "line",
				source: PB_TRACK_SEG_SOURCE_ID,
				layout: { visibility: "none", "line-cap": "round", "line-join": "round" },
				paint: historicalTrackSegmentLinePaint(),
			});
		}

		if (!mapInstance.getSource(PB_ROUTE_SOURCE_ID)) {
			mapInstance.addSource(PB_ROUTE_SOURCE_ID, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
		}
		if (!mapInstance.getLayer(PB_ROUTE_LAYER_ID)) {
			mapInstance.addLayer({
				id: PB_ROUTE_LAYER_ID,
				type: "line",
				source: PB_ROUTE_SOURCE_ID,
				layout: { visibility: "none", "line-cap": "round", "line-join": "round" },
				paint: {
					"line-color": "#22d3ee",
					"line-width": 3,
					"line-opacity": 0.92,
					"line-dasharray": [2, 2.5],
				},
			});
		}

		if (!mapInstance.getSource(PB_AIRPORT_HIGHLIGHT_SOURCE_ID)) {
			mapInstance.addSource(PB_AIRPORT_HIGHLIGHT_SOURCE_ID, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
		}
		if (!mapInstance.getLayer(PB_AIRPORT_HIGHLIGHT_LAYER_ID)) {
			mapInstance.addLayer({
				id: PB_AIRPORT_HIGHLIGHT_LAYER_ID,
				type: "circle",
				source: PB_AIRPORT_HIGHLIGHT_SOURCE_ID,
				layout: { visibility: "none" },
				paint: routeAirportHighlightPaint(),
			});
		}

		if (!mapInstance.getSource(SOURCE_ID)) {
			mapInstance.addSource(SOURCE_ID, {
				type: "geojson",
				promoteId: "flight_id",
				data: { type: "FeatureCollection", features: [] },
			});
		}

		if (!mapInstance.getLayer(ALTITUDE_GLOW_LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: ALTITUDE_GLOW_LAYER_ID,
					type: "circle",
					source: SOURCE_ID,
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

		if (!mapInstance.getLayer(LAYER_ID)) {
			mapInstance.addLayer(
				{
					id: LAYER_ID,
					type: "symbol",
					source: SOURCE_ID,
					layout: {
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
					},
				},
				firstSymbolLayer?.id,
			);
		}

		if (!mapInstance.getLayer(MARKED_LAYER_ID)) {
			mapInstance.addLayer({
				id: MARKED_LAYER_ID,
				type: "circle",
				source: SOURCE_ID,
				filter: PB_FEATURE_MARKED,
				paint: {
					"circle-radius": 20,
					"circle-color": "rgba(244, 63, 94, 0.12)",
					"circle-stroke-color": "#fb7185",
					"circle-stroke-width": 3,
					"circle-opacity": 1,
				},
			});
		}

		if (!mapInstance.getLayer(SELECTED_LAYER_ID)) {
			mapInstance.addLayer({
				id: SELECTED_LAYER_ID,
				type: "circle",
				source: SOURCE_ID,
				filter: PB_FEATURE_SELECTED,
				paint: {
					"circle-radius": 14,
					"circle-color": "#f59e0b",
					"circle-opacity": 0.8,
					"circle-stroke-width": 0,
				},
			});
		}

		if (!mapInstance.getLayer(HOVER_ICON_LAYER_ID)) {
			mapInstance.addLayer({
				id: HOVER_ICON_LAYER_ID,
				type: "symbol",
				source: SOURCE_ID,
				filter: HIDE_ALL_FEATURES_FILTER,
				layout: {
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
					"icon-opacity": 1,
				},
			});
		}

		if (!mapInstance.getSource(HOVER_SOURCE_ID)) {
			mapInstance.addSource(HOVER_SOURCE_ID, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});
		}

		if (!mapInstance.getLayer(HOVER_LABEL_LAYER_ID)) {
			mapInstance.addLayer({
				id: HOVER_LABEL_LAYER_ID,
				type: "symbol",
				source: HOVER_SOURCE_ID,
				layout: {
					...flightHoverLabelLayout(),
					visibility: "visible",
					"symbol-placement": "point",
				},
				paint: flightHoverLabelPaint(),
			});
		}

		const iconColor = resolveStyleAircraftColor(currentStyleId);
		const coral = AIRCRAFT_COLOR.coral;
		await Promise.all([
			loadSvgIcon(mapInstance, "icon-plane", planeIconRaw, iconColor),
			loadSvgIcon(mapInstance, "icon-plane-ground", planeGroundIconRaw, iconColor),
			loadSvgIcon(mapInstance, "icon-plane-coral", planeIconRaw, coral),
			loadSvgIcon(
				mapInstance,
				"icon-plane-ground-coral",
				planeGroundIconRaw,
				coral,
			),
		]);

		updatePlaybackSelectionOverlays();

		renderFrame(currentFrame.value);
		updateSelectedHighlight(mapInstance);
		updateMarkedHighlight(mapInstance);
		bindPlaybackFlightHandlers(mapInstance);
		mapLayersReady = true;
		if (frames.value.length) renderFrame(currentFrame.value);
	}

	// ── GeoJSON 构建 ─────────────────────────────────────────────────────────
	function playbackFrameAsBrief(idx: number): FlightBrief[] {
		const frame = frames.value[idx];
		if (!frame) return [];
		let flights = flightsAtFrame(idx);
		if (
			playbackMode.value === "single" &&
			focusFlightId.value &&
			flights.length === 0
		) {
			const p = getPlaybackPointAtOrBefore(focusFlightId.value, idx);
			if (p) flights = [p];
		}
		return flights.map((f) => ({
			flight_id: f.id,
			callsign: f.cs ?? f.id,
			lat: f.lat,
			lon: f.lon,
			heading: f.hdg ?? undefined,
			speed_kts: f.spd ?? undefined,
			altitude_ft: f.alt ?? undefined,
			updated_at: frame.ts,
		}));
	}

	function buildFlightGeoJson(idx: number): GeoJSON.FeatureCollection {
		const patched = patchFlightGeoJson(
			playbackFrameAsBrief(idx),
			playbackFlightIndex,
		);
		playbackFlightIndex = patched.index;
		return patched.geojson;
	}

	function buildTrailGeoJson(frameIdx: number): GeoJSON.FeatureCollection {
		return updatePlaybackTrailGeoJson(
			trailState,
			frameIdx,
			TRAIL_LENGTH,
			(i) => flightsAtFrame(i),
			{
				singleMode:
					playbackMode.value === "single" && !!focusFlightId.value,
			},
		);
	}

	function toPlaybackRouteGeoJson(): GeoJSON.FeatureCollection<GeoJSON.LineString> {
		const detail = displayDetail.value;
		const pb = playbackDetail.value;
		if (!detail || !pb) {
			return { type: "FeatureCollection", features: [] };
		}
		const flightBrief: FlightBrief = {
			flight_id: pb.flight_id,
			callsign: pb.callsign,
			lat: pb.lat,
			lon: pb.lon,
			heading: pb.heading,
			speed_kts: pb.speed_kts,
			altitude_ft: pb.altitude_ft,
			aircraft_category: pb.aircraft_category,
			departure_airport: pb.departure_airport ?? undefined,
			arrival_airport: pb.arrival_airport ?? undefined,
			updated_at: pb.updated_at,
		};
		return buildPlannedRouteGeoJson({
			flight: flightBrief,
			detail,
			trackPoints: playbackTrackPoints.value,
			airports: store.airports,
		});
	}

	function updatePlaybackSelectionOverlays() {
		if (!map || !mapLayersReady) return;
		const detail = displayDetail.value;

		const trackSrc = map.getSource(PB_TRACK_SEG_SOURCE_ID) as
			| maplibregl.GeoJSONSource
			| undefined;
		const trackId = activeFlightId.value ?? "";
		const trackPts =
			playbackTrackPoints.value.length >= 2
				? playbackTrackPoints.value
				: store.selectedTrackPoints;
		trackSrc?.setData(
			buildHistoricalTrackSegmentCollection(trackPts, trackId),
		);

		const routeGeo = toPlaybackRouteGeoJson();
		const routeSrc = map.getSource(PB_ROUTE_SOURCE_ID) as
			| maplibregl.GeoJSONSource
			| undefined;
		routeSrc?.setData(routeGeo);

		const apSrc = map.getSource(PB_AIRPORT_HIGHLIGHT_SOURCE_ID) as
			| maplibregl.GeoJSONSource
			| undefined;
		apSrc?.setData(
			buildRouteAirportHighlightCollection(
				resolveRouteAirports({
					departure_airport: detail?.departure_airport,
					arrival_airport: detail?.arrival_airport,
					departure_lat: detail?.departure_lat,
					departure_lon: detail?.departure_lon,
					arrival_lat: detail?.arrival_lat,
					arrival_lon: detail?.arrival_lon,
					airportsInStore: store.airports,
				}),
			),
		);

		const hasRoute = !!(
			detail?.departure_airport ||
			detail?.arrival_airport
		);
		if (map.getLayer(PB_AIRPORT_HIGHLIGHT_LAYER_ID)) {
			map.setLayoutProperty(
				PB_AIRPORT_HIGHLIGHT_LAYER_ID,
				"visibility",
				hasRoute ? "visible" : "none",
			);
		}
		const showTrack =
			!!trackId &&
			(playbackTrackPoints.value.length >= 2 ||
				store.selectedTrackPoints.length >= 2);
		if (map.getLayer(TRACK_HISTORY_SEG_LAYER_ID)) {
			map.setLayoutProperty(
				TRACK_HISTORY_SEG_LAYER_ID,
				"visibility",
				showTrack ? "visible" : "none",
			);
		}
		const showRoute = routeGeo.features.length > 0;
		if (map.getLayer(PB_ROUTE_LAYER_ID)) {
			map.setLayoutProperty(
				PB_ROUTE_LAYER_ID,
				"visibility",
				showRoute ? "visible" : "none",
			);
		}
	}

	// ── 渲染�?───────────────────────────────────────────────────────────────
	function renderFrame(idx: number) {
		if (!map || !mapLayersReady) return;
		const flightGeo = buildFlightGeoJson(idx);
		const trailGeo = buildTrailGeoJson(idx);
		scheduleMapUpdate(() => {
			if (!map || !mapLayersReady) return;
			(map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined)?.setData(
				flightGeo,
			);
			(
				map.getSource(TRAIL_SOURCE_ID) as maplibregl.GeoJSONSource | undefined
			)?.setData(trailGeo);
			updateSelectedHighlight(map);
			updateMarkedHighlight(map);
			updatePlaybackSelectionOverlays();
			if (
				followAircraft.value &&
				playbackMode.value === "single" &&
				focusFlightId.value
			) {
				const now = Date.now();
				if (now - lastFollowEaseAt >= 400) {
					const p = getPlaybackPointAtOrBefore(focusFlightId.value, idx);
					if (p) {
						lastFollowEaseAt = now;
						map.easeTo({
							center: [p.lon, p.lat],
							duration: 280,
							essential: true,
						});
					}
				}
			}
		});
	}

	// ── 数据加载 ─────────────────────────────────────────────────────────────
	async function loadPlayback() {
		if (!startInput.value || !endInput.value) return;
		clampEndToNow();
		trimRangeToMaxFrames();
		loadingData.value = true;
		errorMsg.value = "";
		playing.value = false;
		clearPlayTimer();
		focusFlightId.value = null;
		clearSelection();
		try {
			const data = await fetchPlaybackFrames(
				new Date(startInput.value).toISOString(),
				new Date(endInput.value).toISOString(),
				interval.value,
			);
			frames.value = data.frames ?? [];
			resetPlaybackTrailState(trailState);
			playbackFlightIndex = null;
			resetFlightFeatureStateTracking();
			if (frames.value.length === 0) {
				errorMsg.value = t("playback.noData");
				return;
			}
			currentFrame.value = 0;
			renderFrame(0);
		} catch (e: unknown) {
			errorMsg.value = (e as Error).message ?? t("playback.loadFailed");
		} finally {
			loadingData.value = false;
		}
	}

	// ── 回放控制 ─────────────────────────────────────────────────────────────
	function togglePlay() {
		if (!canPlayback.value) return;
		playing.value = !playing.value;
		if (playing.value) scheduleNext();
		else clearPlayTimer();
	}

	function scheduleNext() {
		clearPlayTimer();
		const BASE_MS = 600; // 1× 速度下每�?600ms
		const frameMs = Math.max(50, BASE_MS / speed.value);
		playTimer = setTimeout(() => {
			if (!playing.value) return;
			if (currentFrame.value < frames.value.length - 1) {
				currentFrame.value++;
				renderFrame(currentFrame.value);
				scheduleNext();
			} else if (loop.value) {
				currentFrame.value = 0;
				renderFrame(0);
				scheduleNext();
			} else {
				playing.value = false;
			}
		}, frameMs);
	}

	function clearPlayTimer() {
		if (playTimer !== null) {
			clearTimeout(playTimer);
			playTimer = null;
		}
	}

	function onSliderInput() {
		renderFrame(currentFrame.value);
	}

	function goToStart() {
		currentFrame.value = 0;
		renderFrame(0);
	}
	function goToEnd() {
		const n = frames.value.length - 1;
		currentFrame.value = n;
		renderFrame(n);
	}
	function stepForward() {
		if (currentFrame.value < frames.value.length - 1) {
			currentFrame.value++;
			renderFrame(currentFrame.value);
		}
	}
	function stepBack() {
		if (currentFrame.value > 0) {
			currentFrame.value--;
			renderFrame(currentFrame.value);
		}
	}

	watch(speed, () => {
		if (playing.value) scheduleNext();
	});

	watch(activeFlightId, () => {
		if (map) updateSelectedHighlight(map);
		renderFrame(currentFrame.value);
	});

	watch(
		() => [store.selectedTrackPoints, store.flightDetail, displayDetail.value],
		() => {
			updatePlaybackSelectionOverlays();
		},
		{ deep: true },
	);

	watch(
		() => [...store.markedFlightIds],
		() => {
			if (!map) return;
			if (
				hoveredFlightId &&
				!store.markedFlightIds.includes(hoveredFlightId)
			) {
				clearFlightHover(map);
			}
			updateMarkedHighlight(map);
			renderFrame(currentFrame.value);
		},
	);

	watch([playbackMode, focusFlightId], () => {
		if (!mapLayersReady) return;
		if (playbackMode.value === "single" && !focusFlightId.value) {
			playing.value = false;
			clearPlayTimer();
		}
		renderFrame(currentFrame.value);
	});

	// ── 地图初始�?────────────────────────────────────────────────────────────
	function initMap() {
		if (!mapEl.value) return;
		void (async () => {
			const { url, provider, styleId } = await determineInitialStyle();
			currentProvider = provider;
			currentStyleId = styleId;

			map = new maplibregl.Map({
				container: mapEl.value!,
				style: url,
				center: [MAP_INIT_LNG, MAP_INIT_LAT],
				zoom: MAP_INIT_ZOOM,
				attributionControl: true,
				localIdeographFontFamily:
					"Noto Sans CJK SC, Microsoft YaHei, SimHei, sans-serif",
				refreshExpiredTiles: false,
				maxTileCacheSize: 2048,
				maxTileCacheZoomLevels: 8,
				cancelPendingTileRequestsWhileZooming: false,
				fadeDuration: 150,
				transformRequest,
			});

			map.addControl(new maplibregl.NavigationControl(), "top-right");
			map.addControl(
				new maplibregl.ScaleControl({ maxWidth: 480, unit: "metric" }),
				"bottom-right",
			);

			map.on("error", (e) => {
				const status = (e.error as { status?: number })?.status;
				if (
					(status === 403 || status === 429) &&
					currentProvider === "maptiler" &&
					STADIA_KEY
				) {
					currentProvider = "stadia";
					currentStyleId = "alidade_smooth_dark";
					map!.setStyle(buildStadiaStyleUrl(currentStyleId), { diff: false });
					flightHoverHandlersBound = false;
					map!.once("style.load", () => {
						void reinitPlaybackLayers(map!);
					});
				}
			});

			map.on("load", () => {
				void reinitPlaybackLayers(map!);
			});
		})();
	}

	watch(
		() => frames.value.length,
		(len) => {
			if (len > 0 && mapLayersReady) renderFrame(currentFrame.value);
		},
	);

	onMounted(() => {
		store.disconnectSocket();
		applyRangePreset(1);
		initMap();
	});
	onUnmounted(() => {
		clearPlayTimer();
		map?.remove();
	});
</script>

<style scoped>
	/* ── 根布局 */
	.playback-page {
		height: 100%;
		display: flex;
		flex-direction: column;
		background: var(--bg-base);
		color: var(--text-primary);
		overflow: hidden;
	}

	/* ── 顶部查询�?*/
	.query-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 10px 16px;
		flex-shrink: 0;
		z-index: 10;
	}

	.qb-focus-stat {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 12px;
		color: var(--text-muted);
		flex: 1;
	}

	.qb-focus-stat strong {
		font-weight: 600;
		color: var(--accent);
	}

	.qb-setup {
		display: flex;
		flex-direction: column;
		gap: 6px;
	}

	.qb-toolbar {
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.qb-toolbar-primary {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: 10px 12px;
	}

	.qb-toolbar-secondary {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 14px;
		padding-top: 2px;
		border-top: 1px solid color-mix(in srgb, var(--border) 70%, transparent);
	}

	.qb-toolbar-extra {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
		padding: 6px 0 2px 52px;
	}

	.qb-time-group {
		display: flex;
		align-items: flex-end;
		gap: 8px;
		flex-wrap: wrap;
	}

	.qb-time-sep {
		padding-bottom: 7px;
		font-size: 12px;
		color: var(--text-muted);
	}

	.qb-field {
		display: flex;
		flex-direction: column;
		gap: 3px;
	}

	.qb-field-label {
		font-size: 10px;
		font-weight: 500;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.qb-field-sample .qb-select {
		min-width: 96px;
	}

	.qb-frames-badge {
		padding: 5px 10px;
		border-radius: var(--radius-sm);
		background: var(--bg-elevated);
		border: 1px solid var(--border);
		font-size: 11px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}

	.qb-mode-seg {
		display: inline-flex;
		padding: 2px;
		background: var(--bg-elevated);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
	}

	.qb-mode-seg-compact {
		flex-shrink: 0;
	}

	.qb-mode-seg-btn {
		padding: 5px 12px;
		border: none;
		border-radius: calc(var(--radius-md) - 2px);
		background: transparent;
		font-size: 11px;
		color: var(--text-secondary);
		cursor: pointer;
		transition:
			background 0.15s,
			color 0.15s;
	}

	.qb-mode-seg-btn:hover {
		color: var(--text-primary);
	}

	.qb-mode-seg-btn.active {
		background: var(--accent-subtle);
		color: var(--accent);
		font-weight: 500;
	}

	.qb-toolbar-actions {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-left: auto;
	}

	.qb-help-anchor {
		position: relative;
	}

	.qb-btn-icon {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-elevated);
		color: var(--text-muted);
		cursor: pointer;
	}

	.qb-btn-icon svg {
		width: 16px;
		height: 16px;
	}

	.qb-btn-icon:hover,
	.qb-btn-icon.active {
		border-color: var(--accent);
		color: var(--accent);
		background: var(--accent-subtle);
	}

	.qb-help-popover {
		position: absolute;
		top: calc(100% + 6px);
		right: 0;
		z-index: 20;
		width: min(300px, 80vw);
		padding: 12px 14px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		box-shadow: var(--shadow-lg);
		font-size: 11px;
		line-height: 1.55;
		color: var(--text-muted);
	}

	.qb-chip-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}

	.qb-chip-label {
		font-size: 10px;
		font-weight: 500;
		color: var(--text-muted);
		margin-right: 2px;
		white-space: nowrap;
	}

	.qb-chip {
		padding: 3px 9px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--bg-elevated);
		font-size: 11px;
		color: var(--text-secondary);
		cursor: pointer;
		white-space: nowrap;
	}

	.qb-chip-more {
		border-style: dashed;
	}

	.qb-chip:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.qb-chip.active {
		border-color: var(--accent);
		background: var(--accent-subtle);
		color: var(--accent);
	}

	.qb-mode-hint-inline {
		flex: 1;
		min-width: min(240px, 100%);
		margin: 0;
		font-size: 11px;
		line-height: 1.4;
		color: var(--text-muted);
	}

	.qb-help-title {
		margin: 0 0 6px;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-secondary);
	}

	.qb-help-list {
		margin: 0;
		padding-left: 16px;
	}

	.qb-help-list li + li {
		margin-top: 4px;
	}

	.qb-label {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 12px;
		color: var(--text-secondary);
	}

	.qb-hint {
		font-size: 11px;
		color: var(--text-muted);
	}

	.qb-presets {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}

	.qb-preset-group-label {
		font-size: 11px;
		color: var(--text-muted);
		margin-right: 2px;
	}

	.qb-preset {
		padding: 4px 10px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-elevated);
		font-size: 11px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.qb-presets-interval,
	.qb-presets-range {
		width: 100%;
	}

	.qb-preset:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.qb-preset.active {
		border-color: var(--accent);
		background: var(--accent-subtle);
		color: var(--accent);
	}

	.qb-input,
	.qb-select {
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-primary);
		padding: 4px 8px;
		font-size: 12px;
		outline: none;
	}

	.qb-input:focus,
	.qb-select:focus {
		border-color: var(--accent);
	}

	.qb-btn-load {
		padding: 5px 16px;
		background: var(--accent);
		color: #fff;
		border: none;
		border-radius: var(--radius-md);
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		transition: background var(--t-fast);
	}

	.qb-btn-load:hover:not(:disabled) {
		background: var(--accent-hover);
	}
	.qb-btn-load:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.qb-error {
		color: var(--danger);
		font-size: 12px;
		margin: 0;
	}

	.qb-summary-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 8px 12px;
		width: 100%;
	}

	.qb-summary {
		display: flex;
		align-items: center;
		gap: 8px;
	}


	.qb-follow {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: var(--text-secondary);
		cursor: pointer;
		user-select: none;
	}

	.qb-icon {
		width: 14px;
		height: 14px;
		color: var(--text-muted);
		flex-shrink: 0;
	}
	.qb-range {
		font-size: 12px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}
	.qb-badge {
		padding: 2px 8px;
		background: var(--accent-subtle);
		color: var(--accent);
		border-radius: 999px;
		font-size: 11px;
	}

	.qb-btn-reset {
		margin-left: auto;
		padding: 4px 12px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		font-size: 12px;
		cursor: pointer;
	}
	.qb-btn-reset:hover {
		background: var(--border);
		color: var(--text-primary);
	}

	/* ── 地图 */
	.map-wrap {
		flex: 1;
		position: relative;
		min-height: 0;
	}

	.map-wrap--with-list .play-dock {
		width: min(720px, calc(100% - 320px));
		margin-left: 156px;
	}

	.map-wrap--with-list .map-hint {
		margin-left: 156px;
	}

	.dk-btn.dk-play:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
	.map-el {
		width: 100%;
		height: 100%;
	}

	.map-hint {
		position: absolute;
		left: 50%;
		top: 50%;
		transform: translate(-50%, -50%);
		max-width: min(420px, 90%);
		padding: 16px 20px;
		text-align: center;
		background: color-mix(in srgb, var(--bg-surface) 92%, transparent);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		pointer-events: none;
		z-index: 4;
	}

	.map-hint-warn {
		border-color: color-mix(in srgb, var(--danger) 40%, var(--border));
	}

	.map-hint-title {
		margin: 0 0 6px;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.map-hint-body {
		margin: 0;
		font-size: 12px;
		line-height: 1.5;
		color: var(--text-muted);
	}

	.map-hint-setup {
		text-align: left;
		max-width: min(360px, 92%);
	}

	.map-hint-steps {
		margin: 0;
		padding-left: 20px;
		font-size: 12px;
		line-height: 1.55;
		color: var(--text-muted);
	}

	.map-hint-steps li + li {
		margin-top: 6px;
	}

	.map-hint-steps li::marker {
		color: var(--accent);
		font-weight: 600;
	}

	.pb-detail {
		position: absolute;
		top: 12px;
		right: 12px;
		width: min(320px, calc(100% - 24px));
		max-height: calc(100% - 24px);
		display: flex;
		flex-direction: column;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		z-index: 5;
		overflow: hidden;
	}

	.pb-detail-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 10px 12px;
		border-bottom: 1px solid var(--border);
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
		flex-shrink: 0;
	}

	.pb-detail-close {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
	}

	.pb-detail-close svg {
		width: 14px;
		height: 14px;
	}

	.pb-detail-close:hover {
		background: var(--bg-elevated);
		color: var(--text-primary);
	}

	.pb-detail :deep(.dp-panel),
	.pb-detail :deep(.dp-loading),
	.pb-detail :deep(.dp-empty) {
		overflow: auto;
	}

	.qb-live-stats {
		display: flex;
		align-items: center;
		gap: 8px;
		font-size: 12px;
		color: var(--text-muted);
		flex: 1;
	}

	.qb-live-stats strong {
		font-weight: 600;
		color: var(--text-primary);
		margin-right: 2px;
	}

	.qb-stat-air strong {
		color: var(--accent);
	}

	.qb-stat-sep {
		color: var(--border-strong);
	}

	/* ── 底部悬浮控制�?*/
	.play-dock {
		position: absolute;
		left: 50%;
		bottom: 20px;
		transform: translateX(-50%);
		width: min(720px, calc(100% - 48px));
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-xl);
		padding: 12px 20px 14px;
		box-shadow: var(--shadow-panel);
		z-index: 10;
	}

	.dock-timeline {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
	}

	.ts-edge {
		font-size: 10px;
		color: var(--text-muted);
		white-space: nowrap;
	}

	.tl-slider {
		flex: 1;
		accent-color: var(--accent);
		cursor: pointer;
		height: 4px;
	}

	.dock-controls {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}

	.dock-btns {
		display: flex;
		gap: 4px;
	}

	.dk-btn {
		width: 30px;
		height: 30px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0;
		transition: all var(--t-fast);
	}
	.dk-btn svg {
		width: 14px;
		height: 14px;
	}
	.dk-btn:hover {
		background: var(--border);
		color: var(--text-primary);
	}

	.dk-play {
		width: 36px;
		height: 36px;
		background: var(--success);
		border-color: var(--success);
		color: #fff;
	}
	.dk-play svg {
		width: 18px;
		height: 18px;
	}
	.dk-play:hover {
		background: #059669;
	}

	.dk-active {
		background: var(--accent-subtle) !important;
		border-color: var(--accent) !important;
		color: var(--accent) !important;
	}

	.dock-time {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		min-width: 120px;
	}
	.dk-ts {
		font-size: 13px;
		font-weight: 600;
		color: var(--accent);
		font-variant-numeric: tabular-nums;
	}
	.dk-ratio {
		font-size: 10px;
		color: var(--text-muted);
	}

	.dock-speed {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-left: auto;
	}
	.dk-spd-lbl {
		font-size: 11px;
		color: var(--text-muted);
	}
	.dk-spd-sel {
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-primary);
		padding: 3px 6px;
		font-size: 12px;
		outline: none;
	}
	.dk-spd-sel:focus {
		border-color: var(--accent);
	}
</style>
