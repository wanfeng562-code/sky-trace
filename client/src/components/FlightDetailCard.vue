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
		<!-- 顶部：呼号 + 航空公司 Logo + 关闭 -->
		<div class="dp-header">
			<div class="dp-header-info">
				<div class="dp-callsign">{{ detail.callsign || detail.flight_id }}</div>
				<div class="dp-flight-id">{{ detail.flight_id }}</div>
			</div>
			<div class="dp-header-actions">
				<img
					v-if="detail.airline_iata"
					:src="`https://airlabs.co/img/airline/m/${detail.airline_iata}.png`"
					class="dp-logo"
					:alt="detail.airline_iata"
					@error="
						(e) => ((e.target as HTMLImageElement).style.display = 'none')
					"
				/>
				<button class="dp-close" @click="emit('close')" title="关闭">
					<svg viewBox="0 0 16 16" fill="currentColor">
						<path
							d="M4.293 4.293a1 1 0 011.414 0L8 6.586l2.293-2.293a1 1 0 111.414 1.414L9.414 8l2.293 2.293a1 1 0 01-1.414 1.414L8 9.414l-2.293 2.293a1 1 0 01-1.414-1.414L6.586 8 4.293 5.707a1 1 0 010-1.414z"
						/>
					</svg>
				</button>
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
	import type { FlightDetail } from "../types/flight";

	const props = defineProps<{
		detail: FlightDetail | null;
		loading?: boolean;
	}>();

	const emit = defineEmits<{
		close: [];
	}>();

	const STATUS_MAP: Record<string, { label: string; cls: string }> = {
		en_route: { label: "飞行中", cls: "status-airborne" },
		landed: { label: "已落地", cls: "status-ground" },
		scheduled: { label: "计划中", cls: "status-scheduled" },
		cancelled: { label: "已取消", cls: "status-cancelled" },
	};

	const statusLabel = computed(() => {
		if (!props.detail?.status) {
			return (props.detail?.altitude_ft ?? 0) > 100 ? "飞行中" : "地面";
		}
		return STATUS_MAP[props.detail.status]?.label ?? props.detail.status;
	});

	const statusClass = computed(() => {
		if (!props.detail?.status) {
			return (props.detail?.altitude_ft ?? 0) > 100
				? "status-airborne"
				: "status-ground";
		}
		return STATUS_MAP[props.detail.status]?.cls ?? "";
	});
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
		justify-content: space-between;
		align-items: flex-start;
		margin-bottom: 10px;
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
	}

	.dp-header-actions {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	.dp-logo {
		width: 36px;
		height: 36px;
		object-fit: contain;
		border-radius: var(--radius-sm);
		background: var(--bg-raised);
		padding: 2px;
	}

	.dp-close {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all var(--t-fast);
		padding: 0;
		flex-shrink: 0;
	}

	.dp-close svg {
		width: 12px;
		height: 12px;
	}

	.dp-close:hover {
		background: var(--danger-subtle);
		color: var(--danger);
		border-color: var(--danger);
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
