<template>
	<!-- 空状态：无航班选中 -->
	<div v-if="!detail && !loading" class="dp-empty">
		<svg
			viewBox="0 0 48 48"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			class="dp-empty-icon"
		>
			<circle cx="24" cy="24" r="20" />
			<path d="M24 14v12M24 32v2" stroke-linecap="round" />
		</svg>
		<span>点击地图上的航班图标查看详情</span>
	</div>

	<!-- 加载中 -->
	<div v-else-if="loading" class="dp-loading">
		<div class="dp-spinner"></div>
		<span>加载中...</span>
	</div>

	<!-- 详情内容 -->
	<div v-else-if="detail" class="dp-panel">
		<!-- 顶部：呼号 + 航空公司 Logo -->
		<div class="dp-header">
			<div class="dp-header-info">
				<div class="dp-callsign">{{ detail.callsign || detail.flight_id }}</div>
				<div class="dp-flight-id">{{ detail.flight_id }}</div>
			</div>
			<button
				type="button"
				:class="['dp-mark-star', { on: isMarked }]"
				:title="markTitle"
				@click="toggleMark"
			>
				★
			</button>
			<div v-if="detail.airline_iata" class="dp-logo-wrap">
				<img
					:src="`https://airlabs.co/img/airline/m/${detail.airline_iata}.png`"
					class="dp-logo"
					:alt="detail.airline_iata"
					@error="onLogoError"
				/>
			</div>
		</div>

		<!-- 状态 + 机型 -->
		<div class="dp-badge-row">
			<span :class="['status-badge', statusClass]">{{ statusLabel }}</span>
			<span v-if="detail.aircraft_type" class="type-badge">{{
				detail.aircraft_type
			}}</span>
		</div>

		<!-- 核心指标网格 -->
		<div class="dp-metrics">
			<div class="dp-metric">
				<span class="dm-val">{{
					detail.altitude_ft != null
						? Math.round(detail.altitude_ft).toLocaleString()
						: "--"
				}}</span>
				<span class="dm-unit">ft</span>
				<span class="dm-key">高度</span>
			</div>
			<div class="dp-metric">
				<span class="dm-val">{{
					detail.speed_kts != null ? Math.round(detail.speed_kts) : "--"
				}}</span>
				<span class="dm-unit">kts</span>
				<span class="dm-key">速度</span>
			</div>
			<div class="dp-metric">
				<span class="dm-val">{{
					detail.heading != null ? detail.heading : "--"
				}}</span>
				<span class="dm-unit">°</span>
				<span class="dm-key">航向</span>
			</div>
		</div>

		<!-- 路线信息 -->
		<div
			v-if="detail.departure_airport || detail.arrival_airport"
			class="dp-route"
		>
			<div class="dp-route-stop">
				<span class="dp-iata">{{ detail.departure_airport || "--" }}</span>
				<span v-if="depAirportZh" class="dp-airport-zh">{{ depAirportZh }}</span>
				<span class="dp-route-role">出发</span>
				<span v-if="detail.dep_time" class="dp-route-time">{{
					detail.dep_time
				}}</span>
			</div>
			<div class="dp-route-arrow">
				<svg
					viewBox="0 0 20 8"
					fill="none"
					stroke="currentColor"
					stroke-width="1.5"
				>
					<path
						d="M1 4h18M14 1l4 3-4 3"
						stroke-linecap="round"
						stroke-linejoin="round"
					/>
				</svg>
			</div>
			<div class="dp-route-stop dp-route-stop-right">
				<span class="dp-iata">{{ detail.arrival_airport || "--" }}</span>
				<span v-if="arrAirportZh" class="dp-airport-zh">{{ arrAirportZh }}</span>
				<span class="dp-route-role">到达</span>
				<span v-if="detail.arr_time" class="dp-route-time">{{
					detail.arr_time
				}}</span>
			</div>
		</div>

		<!-- 天气信息 -->
		<div class="dp-weather-sections">
			<template v-if="detail.current_weather">
				<div class="dp-section-title">
					<svg class="ds-icon" viewBox="0 0 16 16" fill="currentColor">
						<path
							d="M8 2a.5.5 0 01.5.5v1a.5.5 0 01-1 0v-1A.5.5 0 018 2zM8 12a.5.5 0 01.5.5v1a.5.5 0 01-1 0v-1A.5.5 0 018 12zM2 8a.5.5 0 01.5-.5h1a.5.5 0 010 1h-1A.5.5 0 012 8zm10 0a.5.5 0 01.5-.5h1a.5.5 0 010 1h-1A.5.5 0 0112 8zM5 8a3 3 0 116 0A3 3 0 015 8z"
						/>
					</svg>
					当前位置天气
				</div>
				<WeatherBlock :weather="detail.current_weather" />
			</template>
			<template v-if="detail.departure_weather">
				<div class="dp-section-title">
					出发地天气 · {{ detail.departure_airport }}
				</div>
				<WeatherBlock :weather="detail.departure_weather" />
			</template>
			<template v-if="detail.arrival_weather">
				<div class="dp-section-title">
					到达地天气 · {{ detail.arrival_airport }}
				</div>
				<WeatherBlock :weather="detail.arrival_weather" />
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { computed } from "vue";
	import WeatherBlock from "./WeatherBlock.vue";
	import { translate, useLocaleStore } from "../i18n";
	import { airportNameZh } from "../data/airportDisplay";
	import { toSimplifiedChinese } from "../utils/zhLocale";
	import { useFlightStore } from "../stores/flight";
	import type { FlightDetail } from "../types/flight";
	import {
		flightStatusClass,
		formatFlightStatusLabel,
	} from "../utils/flightDetailLocale";

	const props = defineProps<{
		detail: FlightDetail | null;
		loading?: boolean;
	}>();

	const store = useFlightStore();
	const localeStore = useLocaleStore();

	const isMarked = computed(() =>
		props.detail ? store.isMarked(props.detail.flight_id) : false,
	);

	const markTitle = computed(() =>
		isMarked.value
			? translate(localeStore.t, "marked.remove")
			: translate(localeStore.t, "marked.add"),
	);

	function toggleMark() {
		if (props.detail) store.toggleMarkFlight(props.detail.flight_id);
	}

	const statusLabel = computed(() =>
		formatFlightStatusLabel(
			props.detail?.status,
			localeStore.locale,
			props.detail?.altitude_ft,
		),
	);

	const statusClass = computed(() =>
		flightStatusClass(props.detail?.status, props.detail?.altitude_ft),
	);

	const depAirportZh = computed(() => {
		if (localeStore.locale !== "zh-CN") return "";
		const raw =
			props.detail?.departure_airport_zh?.trim() ||
			airportNameZh(props.detail?.departure_airport, store.airports);
		return toSimplifiedChinese(raw);
	});

	const arrAirportZh = computed(() => {
		if (localeStore.locale !== "zh-CN") return "";
		const raw =
			props.detail?.arrival_airport_zh?.trim() ||
			airportNameZh(props.detail?.arrival_airport, store.airports);
		return toSimplifiedChinese(raw);
	});

	function onLogoError(event: Event) {
		const wrap = (event.target as HTMLImageElement).closest(".dp-logo-wrap");
		if (wrap) (wrap as HTMLElement).style.display = "none";
	}
</script>

<style scoped>
	/* ── 容器（嵌入侧栏，不再绝对定位） */
	.dp-empty,
	.dp-loading,
	.dp-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow-y: auto;
		padding: 16px;
		background: var(--bg-surface);
		color: var(--text-primary);
	}

	/* ── 空态 */
	.dp-empty {
		align-items: center;
		justify-content: center;
		gap: 12px;
		color: var(--text-muted);
		text-align: center;
		font-size: 13px;
	}

	.dp-empty-icon {
		width: 48px;
		height: 48px;
		opacity: 0.35;
	}

	/* ── 加载 */
	.dp-loading {
		align-items: center;
		justify-content: center;
		gap: 10px;
		color: var(--text-secondary);
		font-size: 13px;
	}

	.dp-spinner {
		width: 24px;
		height: 24px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ── Header */
	.dp-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		margin-bottom: 10px;
	}

	.dp-header-info {
		flex: 1;
		min-width: 0;
	}

	.dp-mark-star {
		flex-shrink: 0;
		width: 36px;
		height: 36px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-elevated);
		font-size: 18px;
		line-height: 1;
		color: var(--text-muted);
		cursor: pointer;
	}

	.dp-mark-star.on {
		border-color: #f43f5e;
		color: #f43f5e;
		background: rgba(244, 63, 94, 0.12);
	}

	.dp-callsign {
		font-size: 18px;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1.1;
	}

	.dp-flight-id {
		font-size: 11px;
		color: var(--text-muted);
		margin-top: 2px;
		word-break: break-all;
	}

	.dp-logo-wrap {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		min-width: 80px;
		max-width: 112px;
		height: 48px;
		padding: 6px 12px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
	}

	.dp-logo {
		display: block;
		width: auto;
		height: auto;
		max-width: 100%;
		max-height: 40px;
		object-fit: contain;
		object-position: center;
	}


	/* ── Badges */
	.dp-badge-row {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-bottom: 12px;
	}

	.status-badge {
		padding: 2px 10px;
		border-radius: 999px;
		font-size: 11px;
		font-weight: 600;
	}

	.status-airborne {
		background: var(--accent-subtle);
		color: var(--accent);
	}

	.status-ground {
		background: var(--bg-raised);
		color: var(--text-secondary);
	}

	.status-scheduled {
		background: var(--warning-subtle);
		color: var(--warning);
	}

	.status-cancelled {
		background: var(--danger-subtle);
		color: var(--danger);
	}

	.type-badge {
		padding: 2px 8px;
		border-radius: var(--radius-sm);
		font-size: 11px;
		background: var(--bg-raised);
		color: var(--text-secondary);
		border: 1px solid var(--border);
	}

	/* ── Metrics 指标网格 */
	.dp-metrics {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 6px;
		margin-bottom: 12px;
	}

	.dp-metric {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		background: var(--bg-raised);
		border-radius: var(--radius-md);
		padding: 10px 6px 8px;
		border: 1px solid var(--border);
	}

	.dm-val {
		font-size: 18px;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1;
		font-variant-numeric: tabular-nums;
	}

	.dm-unit {
		font-size: 10px;
		color: var(--text-muted);
	}

	.dm-key {
		font-size: 10px;
		color: var(--text-secondary);
		text-transform: uppercase;
		letter-spacing: 0.04em;
		margin-top: 2px;
	}

	/* ── Route */
	.dp-route {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 12px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		margin-bottom: 12px;
	}

	.dp-route-stop {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1;
	}

	.dp-route-stop-right {
		align-items: flex-end;
		text-align: right;
	}

	.dp-iata {
		font-size: 20px;
		font-weight: 700;
		color: var(--text-primary);
		letter-spacing: 0.04em;
	}

	.dp-airport-zh {
		font-size: 11px;
		color: var(--text-secondary);
		line-height: 1.3;
		max-width: 120px;
	}

	.dp-route-stop-right .dp-airport-zh {
		text-align: right;
		margin-left: auto;
	}

	.dp-route-role {
		font-size: 10px;
		color: var(--text-muted);
		text-transform: uppercase;
	}

	.dp-route-time {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.dp-route-arrow {
		flex-shrink: 0;
		width: 32px;
		color: var(--text-muted);
	}

	.dp-route-arrow svg {
		width: 32px;
		height: 12px;
	}

	/* ── Weather sections */
	.dp-weather-sections {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.dp-section-title {
		display: flex;
		align-items: center;
		gap: 5px;
		font-size: 11px;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.05em;
		color: var(--text-secondary);
		padding: 8px 0 2px;
		border-top: 1px solid var(--border);
		margin-top: 4px;
	}

	.ds-icon {
		width: 12px;
		height: 12px;
		flex-shrink: 0;
	}
</style>
