<template>
	<div class="playback-page">
		<!-- 顶部查询栏 / 摘要行 -->
		<div class="query-bar">
			<template v-if="!frames.length">
				<!-- 未加载：展开输入行 -->
				<label class="qb-label"
					>开始
					<input
						v-model="startInput"
						type="datetime-local"
						:max="endInput"
						class="qb-input"
				/></label>
				<label class="qb-label"
					>结束
					<input
						v-model="endInput"
						type="datetime-local"
						:min="startInput"
						class="qb-input"
				/></label>
				<label class="qb-label"
					>采样
					<select v-model.number="interval" class="qb-select">
						<option :value="60">1 分钟</option>
						<option :value="300">5 分钟</option>
						<option :value="600">10 分钟</option>
						<option :value="1800">30 分钟</option>
					</select>
				</label>
				<button
					class="qb-btn-load"
					:disabled="loadingData"
					@click="loadPlayback"
				>
					{{ loadingData ? "加载中…" : "加载数据" }}
				</button>
				<p v-if="errorMsg" class="qb-error">{{ errorMsg }}</p>
			</template>
			<template v-else>
				<!-- 已加载：折叠摘要行 -->
				<div class="qb-summary">
					<svg class="qb-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z"
							clip-rule="evenodd"
						/>
					</svg>
					<span class="qb-range"
						>{{ startInput.replace("T", " ") }} →
						{{ endInput.replace("T", " ") }}</span
					>
					<span class="qb-badge"
						>{{ frames.length }} 帧 · {{ durationStr }}</span
					>
				</div>
				<button class="qb-btn-reset" @click="frames = []">重新查询</button>
			</template>
		</div>

		<!-- 地图主体 -->
		<div class="map-wrap">
			<div ref="mapEl" class="map-el" />

			<!-- 左上小卡片统计 -->
			<div v-if="frames.length" class="stats-panel">
				<div class="stat-row">
					<span class="stat-num">{{
						currentFlightCount.toLocaleString()
					}}</span>
					<span class="stat-lbl">架次</span>
				</div>
				<div class="stat-row">
					<span class="stat-num airborne">{{
						airborneCount.toLocaleString()
					}}</span>
					<span class="stat-lbl">飞行中</span>
				</div>
				<div class="stat-row">
					<span class="stat-num ground">{{
						(currentFlightCount - airborneCount).toLocaleString()
					}}</span>
					<span class="stat-lbl">地面</span>
				</div>
				<div class="stat-progress">
					<div class="prog-bar">
						<div class="prog-fill" :style="{ width: progressPct + '%' }" />
					</div>
					<span class="prog-lbl">{{ progressPct.toFixed(0) }}%</span>
				</div>
			</div>
		</div>

		<!-- 底部 Dock：仅数据加载后显示 -->
		<div v-if="frames.length" class="play-dock">
			<!-- 时间轴 -->
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
			<!-- 控制行 -->
			<div class="dock-controls">
				<div class="dock-btns">
					<button class="dk-btn" title="回到开头" @click="goToStart">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M8.445 14.832A1 1 0 0010 14v-2.798l5.445 3.63A1 1 0 0017 14V6a1 1 0 00-1.555-.832L10 8.798V6a1 1 0 00-1.555-.832l-6 4a1 1 0 000 1.664l6 4z"
							/>
						</svg>
					</button>
					<button class="dk-btn" title="上一帧" @click="stepBack">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M11 4a7 7 0 100 14A7 7 0 0011 4zM9.5 9.172l3 1.5-3 1.5V9.172zM7 10a4 4 0 018 0v.001a4 4 0 01-8 0V10z"
							/>
						</svg>
					</button>
					<button
						class="dk-btn dk-play"
						:title="playing ? '暂停' : '播放'"
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
					<button class="dk-btn" title="下一帧" @click="stepForward">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
					<button class="dk-btn" title="跳到末尾" @click="goToEnd">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4A1 1 0 0010 6v2.798l-5.445-3.63z"
							/>
						</svg>
					</button>
					<button
						:class="['dk-btn', { 'dk-active': loop }]"
						title="循环播放"
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
					<span class="dk-spd-lbl">速度</span>
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
</template>

<script setup lang="ts">
	import { computed, onMounted, onUnmounted, ref, watch } from "vue";
	import maplibregl from "maplibre-gl";
	import "maplibre-gl/dist/maplibre-gl.css";
	import { fetchPlaybackFrames } from "../services/api";
	import type { PlaybackFrame } from "../types/flight";
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

	const MAPTILER_STYLES = [
		{ id: "streets-v2-dark", label: "街道深色" },
		{ id: "streets-v2", label: "街道浅色" },
		{ id: "outdoor-v2", label: "户外地形" },
		{ id: "satellite-hybrid", label: "卫星影像" },
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

	const STYLE_ICON_COLORS: Record<string, { fly: string; ground: string }> = {
		"streets-v2-dark": { fly: "#60a5fa", ground: "#94a3b8" },
		"dataviz-dark": { fly: "#60a5fa", ground: "#94a3b8" },
		"streets-v2": { fly: "#1d4ed8", ground: "#475569" },
		"outdoor-v2": { fly: "#1d4ed8", ground: "#475569" },
		dataviz: { fly: "#1d4ed8", ground: "#475569" },
		"satellite-hybrid": { fly: "#fbbf24", ground: "#94a3b8" },
		alidade_smooth_dark: { fly: "#60a5fa", ground: "#94a3b8" },
		alidade_smooth: { fly: "#1d4ed8", ground: "#475569" },
		stamen_terrain: { fly: "#1d4ed8", ground: "#475569" },
		alidade_satellite: { fly: "#fbbf24", ground: "#94a3b8" },
		liberty: { fly: "#1d4ed8", ground: "#475569" },
		bright: { fly: "#1d4ed8", ground: "#475569" },
		positron: { fly: "#1d4ed8", ground: "#475569" },
	};
	const DEFAULT_ICON_COLORS = { fly: "#60a5fa", ground: "#94a3b8" };

	const SOURCE_ID = "playback-flights";
	const LAYER_ID = "playback-icons";
	const ALTITUDE_GLOW_LAYER_ID = "playback-altitude-glow";
	const TRAIL_SOURCE_ID = "playback-trails";
	const TRAIL_LAYER_ID = "playback-trail-lines";
	const TRAIL_LENGTH = 6; // 保留最近 N 帧的轨迹
	const LABEL_LINE1 = "name:en";
	const LABEL_LINE2 = "name:zh-Hans";

	const mapEl = ref<HTMLElement | null>(null);
	let map: maplibregl.Map | null = null;
	let currentProvider: MapProvider = MAP_DEFAULT_PROVIDER as MapProvider;
	let currentStyleId = MAP_DEFAULT_STYLE;
	let popupHandlersBound = false;

	// ── 表单状态 ──────────────────────────────────────────────────────────────
	const startInput = ref(fmtDatetimeLocal(Date.now() - 3600_000));
	const endInput = ref(fmtDatetimeLocal(Date.now()));
	const interval = ref(300);

	// ── 回放状态 ──────────────────────────────────────────────────────────────
	const loadingData = ref(false);
	const errorMsg = ref("");
	const frames = ref<PlaybackFrame[]>([]);
	const currentFrame = ref(0);
	const playing = ref(false);
	const speed = ref(2);
	const loop = ref(false);
	let playTimer: ReturnType<typeof setTimeout> | null = null;

	const currentTs = computed(() => frames.value[currentFrame.value]?.ts ?? "");
	const currentFlightCount = computed(
		() => frames.value[currentFrame.value]?.flights.length ?? 0,
	);
	const airborneCount = computed(
		() =>
			frames.value[currentFrame.value]?.flights.filter(
				(f) => (f.alt ?? 0) > 100,
			).length ?? 0,
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
		if (min < 60) return `${min} 分钟`;
		const h = Math.floor(min / 60);
		const m = min % 60;
		return m > 0 ? `${h} 小时 ${m} 分钟` : `${h} 小时`;
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
		return `/maptiler-proxy/maps/${styleId}/style.json?key=${MAPTILER_KEY}`;
	}

	function buildStadiaStyleUrl(styleId: string): string {
		return `/stadia-proxy/styles/${styleId}/style.json${STADIA_KEY ? `?api_key=${STADIA_KEY}` : ""}`;
	}

	function buildOpenFreeMapStyleUrl(styleId: string): string {
		return `https://tiles.openfreemap.org/styles/${styleId}`;
	}

	async function determineInitialStyle(): Promise<{
		url: string;
		provider: MapProvider;
		styleId: string;
	}> {
		const wantProvider = MAP_DEFAULT_PROVIDER as MapProvider;
		const wantStyle = MAP_DEFAULT_STYLE;

		if (wantProvider === "openfreemap") {
			const styleId =
				OPENFREEMAP_STYLES.find((item) => item.id === wantStyle)?.id ||
				OPENFREEMAP_STYLES[0].id;
			return {
				url: buildOpenFreeMapStyleUrl(styleId),
				provider: "openfreemap",
				styleId,
			};
		}

		if (wantProvider === "maptiler" && MAPTILER_KEY) {
			const styleId =
				MAPTILER_STYLES.find((item) => item.id === wantStyle)?.id ||
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
			} catch {
				// continue fallback chain
			}
		}

		if (wantProvider === "stadia" && STADIA_KEY) {
			const styleId =
				STADIA_STYLES.find((item) => item.id === wantStyle)?.id ||
				STADIA_STYLES[0].id;
			return {
				url: buildStadiaStyleUrl(styleId),
				provider: "stadia",
				styleId,
			};
		}

		if (wantProvider !== "maptiler" && MAPTILER_KEY) {
			const styleId = MAPTILER_STYLES[0].id;
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
			const styleId = STADIA_STYLES[0].id;
			return { url: buildStadiaStyleUrl(styleId), provider: "stadia", styleId };
		}

		const styleId = OPENFREEMAP_STYLES[0].id;
		return {
			url: buildOpenFreeMapStyleUrl(styleId),
			provider: "openfreemap",
			styleId,
		};
	}

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

	function applyBilingualLabels(mapInstance: maplibregl.Map) {
		const style = mapInstance.getStyle();
		const boldFonts: Record<MapProvider, string[]> = {
			maptiler: ["Open Sans Bold", "Arial Unicode MS Regular"],
			stadia: ["Open Sans Bold", "Arial Unicode MS Regular"],
			openfreemap: [
				"Metropolis Bold",
				"Noto Sans Bold",
				"Arial Unicode MS Regular",
			],
		};
		const fonts = boldFonts[currentProvider] ?? [
			"Open Sans Bold",
			"Arial Unicode MS Regular",
		];

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

			mapInstance.setLayoutProperty(layer.id, "text-field", textField);
			mapInstance.setLayoutProperty(layer.id, "text-font", fonts);
		}
	}

	// ── SVG 图标加载（与 MapView 相同的 Canvas 策略，永不 reject）─────────────────────
	function svgWithColor(svgRaw: string, color: string): string {
		return svgRaw
			.replace(/fill="(?!none)[^"]*"/g, `fill="${color}"`)
			.replace(/fill:(?!\s*none)[^;}"']*/g, `fill:${color}`);
	}

	function loadSvgIcon(
		mapInstance: maplibregl.Map,
		id: string,
		svgRaw: string,
		color: string,
	): Promise<void> {
		const colored = svgWithColor(svgRaw, color);
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
				resolve(); // 不 reject，确保图层仍然添加
			};
			img.src = url;
		});
	}

	function ensurePopupHandlers(mapInstance: maplibregl.Map) {
		if (popupHandlersBound) return;
		popupHandlersBound = true;

		const popup = new maplibregl.Popup({
			closeButton: false,
			closeOnClick: false,
			offset: 12,
		});

		mapInstance.on("mouseenter", LAYER_ID, (e) => {
			mapInstance.getCanvas().style.cursor = "pointer";
			const feat = e.features?.[0];
			if (!feat || feat.geometry.type !== "Point") return;
			const { cs, alt, spd } = feat.properties as {
				cs: string;
				alt: number;
				spd: number;
			};
			popup
				.setLngLat(feat.geometry.coordinates as [number, number])
				.setHTML(
					`<strong>${cs}</strong><br>${Math.round(alt ?? 0).toLocaleString()} ft · ${Math.round(spd ?? 0)} kts`,
				)
				.addTo(mapInstance);
		});

		mapInstance.on("mouseleave", LAYER_ID, () => {
			mapInstance.getCanvas().style.cursor = "";
			popup.remove();
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
				paint: {
					"line-color": [
						"interpolate",
						["linear"],
						["get", "alt"],
						0,
						"#6b7280",
						5000,
						"#f59e0b",
						25000,
						"#60a5fa",
						45000,
						"#06b6d4",
					],
					"line-width": 1.5,
					"line-opacity": 0.45,
				},
			});
		}

		if (!mapInstance.getSource(SOURCE_ID)) {
			mapInstance.addSource(SOURCE_ID, {
				type: "geojson",
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
							["coalesce", ["get", "alt"], 0],
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
						"icon-image": [
							"case",
							[">", ["coalesce", ["get", "alt"], 0], 100],
							"pb-plane",
							"pb-plane-ground",
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
						"icon-rotate": ["coalesce", ["get", "hdg"], 0],
						"icon-rotation-alignment": "map",
						"icon-pitch-alignment": "viewport",
						"icon-allow-overlap": true,
						"icon-ignore-placement": true,
					},
				},
				firstSymbolLayer?.id,
			);
		}

		const iconColors = STYLE_ICON_COLORS[currentStyleId] ?? DEFAULT_ICON_COLORS;
		await Promise.all([
			loadSvgIcon(mapInstance, "pb-plane", planeIconRaw, iconColors.fly),
			loadSvgIcon(
				mapInstance,
				"pb-plane-ground",
				planeGroundIconRaw,
				iconColors.ground,
			),
		]);

		renderFrame(currentFrame.value);
		ensurePopupHandlers(mapInstance);
	}

	// ── GeoJSON 构建 ─────────────────────────────────────────────────────────
	function buildFlightGeoJson(idx: number): GeoJSON.FeatureCollection {
		const frame = frames.value[idx];
		if (!frame) return { type: "FeatureCollection", features: [] };
		return {
			type: "FeatureCollection",
			features: frame.flights.map((f) => ({
				type: "Feature" as const,
				geometry: {
					type: "Point" as const,
					coordinates: [f.lon, f.lat],
				},
				properties: {
					id: f.id,
					cs: f.cs ?? f.id,
					alt: f.alt ?? 0,
					hdg: f.hdg ?? 0,
					spd: f.spd ?? 0,
				},
			})),
		};
	}

	function buildTrailGeoJson(frameIdx: number): GeoJSON.FeatureCollection {
		const histStart = Math.max(0, frameIdx - TRAIL_LENGTH + 1);
		// 构建每帧的 ID→坐标 映射
		const frameMaps: Array<Map<string, [number, number]>> = [];
		for (let i = histStart; i <= frameIdx; i++) {
			const fm = new Map<string, [number, number]>();
			for (const f of frames.value[i].flights) {
				fm.set(f.id, [f.lon, f.lat]);
			}
			frameMaps.push(fm);
		}
		const currentFlights = frames.value[frameIdx]?.flights ?? [];
		const features: GeoJSON.Feature[] = [];
		for (const flight of currentFlights) {
			const coords: [number, number][] = [];
			for (const fm of frameMaps) {
				const pos = fm.get(flight.id);
				if (pos) coords.push(pos);
			}
			if (coords.length >= 2) {
				features.push({
					type: "Feature",
					properties: { alt: flight.alt ?? 0 },
					geometry: { type: "LineString", coordinates: coords },
				});
			}
		}
		return { type: "FeatureCollection", features };
	}

	// ── 渲染帧 ───────────────────────────────────────────────────────────────
	function renderFrame(idx: number) {
		if (!map) return;
		(map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined)?.setData(
			buildFlightGeoJson(idx),
		);
		(
			map.getSource(TRAIL_SOURCE_ID) as maplibregl.GeoJSONSource | undefined
		)?.setData(buildTrailGeoJson(idx));
	}

	// ── 数据加载 ─────────────────────────────────────────────────────────────
	async function loadPlayback() {
		if (!startInput.value || !endInput.value) return;
		loadingData.value = true;
		errorMsg.value = "";
		playing.value = false;
		clearPlayTimer();
		try {
			const data = await fetchPlaybackFrames(
				new Date(startInput.value).toISOString(),
				new Date(endInput.value).toISOString(),
				interval.value,
			);
			frames.value = data.frames ?? [];
			currentFrame.value = 0;
			renderFrame(0);
		} catch (e: unknown) {
			errorMsg.value = (e as Error).message ?? "加载失败";
		} finally {
			loadingData.value = false;
		}
	}

	// ── 回放控制 ─────────────────────────────────────────────────────────────
	function togglePlay() {
		playing.value = !playing.value;
		if (playing.value) scheduleNext();
		else clearPlayTimer();
	}

	function scheduleNext() {
		clearPlayTimer();
		const BASE_MS = 600; // 1× 速度下每帧 600ms
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

	// ── 地图初始化 ────────────────────────────────────────────────────────────
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
				refreshExpiredTiles: false,
				maxTileCacheSize: 2048,
				maxTileCacheZoomLevels: 8,
				cancelPendingTileRequestsWhileZooming: false,
				fadeDuration: 150,
				transformRequest,
			});

			map.addControl(new maplibregl.NavigationControl(), "top-right");
			map.addControl(
				new maplibregl.ScaleControl({ maxWidth: 120, unit: "metric" }),
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

	onMounted(() => {
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

	/* ── 顶部查询栏 */
	.query-bar {
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		padding: 8px 16px;
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
		flex-shrink: 0;
		z-index: 10;
	}

	.qb-label {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 12px;
		color: var(--text-secondary);
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

	.qb-summary {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1;
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
	.map-el {
		width: 100%;
		height: 100%;
	}

	/* ── 左上统计卡 */
	.stats-panel {
		position: absolute;
		top: 12px;
		left: 12px;
		background: var(--bg-overlay);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: 10px 14px;
		backdrop-filter: blur(8px);
		z-index: 1;
		min-width: 100px;
		pointer-events: none;
	}

	.stat-row {
		display: flex;
		align-items: baseline;
		gap: 6px;
		margin-bottom: 4px;
	}
	.stat-num {
		font-size: 17px;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
		color: var(--text-primary);
	}
	.stat-num.airborne {
		color: var(--accent);
	}
	.stat-num.ground {
		color: var(--text-secondary);
	}
	.stat-lbl {
		font-size: 11px;
		color: var(--text-muted);
	}

	.stat-progress {
		margin-top: 8px;
	}
	.prog-bar {
		width: 100%;
		height: 3px;
		background: var(--bg-raised);
		border-radius: 2px;
		overflow: hidden;
	}
	.prog-fill {
		height: 100%;
		background: var(--accent);
		border-radius: 2px;
		transition: width 0.3s;
	}
	.prog-lbl {
		font-size: 10px;
		color: var(--text-muted);
		float: right;
		margin-top: 2px;
	}

	/* ── 底部 Dock */
	.play-dock {
		flex-shrink: 0;
		background: var(--bg-surface);
		border-top: 1px solid var(--border);
		padding: 8px 16px 10px;
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
