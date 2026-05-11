<template>
	<div class="playback-page">
		<!-- 控制栏 -->
		<div class="control-bar">
			<div class="time-inputs">
				<label>
					开始
					<input
						v-model="startInput"
						type="datetime-local"
						:max="endInput"
						class="time-input"
					/>
				</label>
				<label>
					结束
					<input
						v-model="endInput"
						type="datetime-local"
						:min="startInput"
						class="time-input"
					/>
				</label>
				<label>
					采样间隔
					<select v-model.number="interval" class="interval-select">
						<option :value="60">1 分钟</option>
						<option :value="300">5 分钟</option>
						<option :value="600">10 分钟</option>
						<option :value="1800">30 分钟</option>
					</select>
				</label>
				<button class="btn-load" :disabled="loadingData" @click="loadPlayback">
					{{ loadingData ? "加载中..." : "加载数据" }}
				</button>
			</div>
			<div class="playback-controls" v-if="frames.length">
				<button class="btn-play" @click="togglePlay">
					{{ playing ? "⏸ 暂停" : "▶ 播放" }}
				</button>
				<label class="speed-label">
					倍速
					<select v-model.number="speed" class="speed-select">
						<option :value="0.5">0.5×</option>
						<option :value="1">1×</option>
						<option :value="2">2×</option>
						<option :value="5">5×</option>
						<option :value="10">10×</option>
					</select>
				</label>
				<div class="timeline">
					<span class="ts-label">{{ currentTs }}</span>
					<input
						v-model.number="currentFrame"
						type="range"
						min="0"
						:max="frames.length - 1"
						class="timeline-slider"
						@input="onSliderInput"
					/>
					<span class="frame-label"
						>{{ currentFrame + 1 }} / {{ frames.length }}</span
					>
				</div>
			</div>
			<p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
		</div>

		<!-- 地图 -->
		<div ref="mapEl" class="map-container"></div>
	</div>
</template>

<script setup lang="ts">
	import { computed, onMounted, onUnmounted, ref, watch } from "vue";
	import maplibregl from "maplibre-gl";
	import "maplibre-gl/dist/maplibre-gl.css";
	import { fetchPlaybackFrames } from "../services/api";
	import type { PlaybackFrame } from "../types/flight";

	const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY as string;
	const SOURCE_ID = "playback-flights";
	const LAYER_ID = "playback-dots";

	const mapEl = ref<HTMLElement | null>(null);
	let map: maplibregl.Map | null = null;

	// --- form state ---
	const startInput = ref(fmtDatetimeLocal(Date.now() - 3600_000));
	const endInput = ref(fmtDatetimeLocal(Date.now()));
	const interval = ref(300);

	// --- playback state ---
	const loadingData = ref(false);
	const errorMsg = ref("");
	const frames = ref<PlaybackFrame[]>([]);
	const currentFrame = ref(0);
	const playing = ref(false);
	const speed = ref(1);
	let playTimer: ReturnType<typeof setTimeout> | null = null;

	const currentTs = computed(() => frames.value[currentFrame.value]?.ts ?? "");

	function fmtDatetimeLocal(ms: number) {
		const d = new Date(ms);
		const pad = (n: number) => String(n).padStart(2, "0");
		return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}

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

	function togglePlay() {
		playing.value = !playing.value;
		if (playing.value) scheduleNext();
		else clearPlayTimer();
	}

	function scheduleNext() {
		clearPlayTimer();
		const frameMs = (interval.value * 1000) / speed.value;
		playTimer = setTimeout(
			() => {
				if (!playing.value) return;
				if (currentFrame.value < frames.value.length - 1) {
					currentFrame.value++;
					renderFrame(currentFrame.value);
					scheduleNext();
				} else {
					playing.value = false;
				}
			},
			Math.max(100, frameMs),
		);
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

	watch(speed, () => {
		if (playing.value) scheduleNext();
	});

	function renderFrame(index: number) {
		const frame = frames.value[index];
		if (!frame || !map) return;

		const geojson: GeoJSON.FeatureCollection = {
			type: "FeatureCollection",
			features: frame.flights.map((f) => ({
				type: "Feature",
				geometry: {
					type: "Point",
					coordinates: [f.lon, f.lat],
				},
				properties: {
					id: f.id,
					cs: f.cs ?? f.id,
					alt: f.alt ?? 0,
				},
			})),
		};

		const src = map.getSource(SOURCE_ID) as
			| maplibregl.GeoJSONSource
			| undefined;
		if (src) {
			src.setData(geojson);
		}
	}

	function initMap() {
		if (!mapEl.value) return;
		map = new maplibregl.Map({
			container: mapEl.value,
			style: `https://api.maptiler.com/maps/streets/style.json?key=${MAPTILER_KEY}`,
			center: [105, 35],
			zoom: 3,
			attributionControl: false,
		});

		map.addControl(new maplibregl.NavigationControl(), "top-right");

		map.on("load", () => {
			map!.addSource(SOURCE_ID, {
				type: "geojson",
				data: { type: "FeatureCollection", features: [] },
			});

			map!.addLayer({
				id: LAYER_ID,
				type: "circle",
				source: SOURCE_ID,
				paint: {
					"circle-radius": ["interpolate", ["linear"], ["zoom"], 2, 3, 8, 6],
					"circle-color": [
						"interpolate",
						["linear"],
						["get", "alt"],
						0,
						"#9ca3af",
						5000,
						"#2563eb",
						25000,
						"#06b6d4",
						45000,
						"#a855f7",
					],
					"circle-stroke-width": 1,
					"circle-stroke-color": "#ffffff",
				},
			});

			// Add tooltip
			const popup = new maplibregl.Popup({
				closeButton: false,
				closeOnClick: false,
			});

			map!.on("mouseenter", LAYER_ID, (e) => {
				map!.getCanvas().style.cursor = "pointer";
				const feat = e.features?.[0];
				if (!feat || feat.geometry.type !== "Point") return;
				const [lng, lat] = feat.geometry.coordinates as [number, number];
				const { cs, alt } = feat.properties as { cs: string; alt: number };
				popup
					.setLngLat([lng, lat])
					.setHTML(`<strong>${cs}</strong><br>${Math.round(alt ?? 0)} ft`)
					.addTo(map!);
			});

			map!.on("mouseleave", LAYER_ID, () => {
				map!.getCanvas().style.cursor = "";
				popup.remove();
			});
		});
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
	.playback-page {
		height: 100%;
		display: flex;
		flex-direction: column;
		background: #0f172a;
		color: #e2e8f0;
	}

	.control-bar {
		background: #1e293b;
		border-bottom: 1px solid #334155;
		padding: 10px 20px;
		display: flex;
		flex-direction: column;
		gap: 8px;
		flex-shrink: 0;
		z-index: 10;
	}

	.time-inputs {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}

	.time-inputs label,
	.speed-label {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: #94a3b8;
	}

	.time-input,
	.interval-select,
	.speed-select {
		background: #0f172a;
		border: 1px solid #475569;
		border-radius: 4px;
		color: #e2e8f0;
		padding: 4px 8px;
		font-size: 12px;
		outline: none;
	}

	.time-input:focus,
	.interval-select:focus,
	.speed-select:focus {
		border-color: #60a5fa;
	}

	.btn-load {
		padding: 6px 16px;
		background: #2563eb;
		color: #ffffff;
		border: none;
		border-radius: 4px;
		font-size: 13px;
		cursor: pointer;
	}

	.btn-load:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.playback-controls {
		display: flex;
		align-items: center;
		gap: 12px;
		flex-wrap: wrap;
	}

	.btn-play {
		padding: 5px 14px;
		background: #059669;
		color: #ffffff;
		border: none;
		border-radius: 4px;
		font-size: 13px;
		cursor: pointer;
		min-width: 80px;
	}

	.btn-play:hover {
		background: #047857;
	}

	.timeline {
		display: flex;
		align-items: center;
		gap: 8px;
		flex: 1;
		min-width: 260px;
	}

	.ts-label {
		font-size: 11px;
		color: #94a3b8;
		min-width: 120px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.timeline-slider {
		flex: 1;
		accent-color: #2563eb;
		cursor: pointer;
	}

	.frame-label {
		font-size: 11px;
		color: #64748b;
		white-space: nowrap;
	}

	.error-msg {
		color: #f87171;
		font-size: 12px;
		margin: 0;
	}

	.map-container {
		flex: 1;
		min-height: 0;
	}
</style>
