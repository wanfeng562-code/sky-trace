<template>
	<aside v-if="detail || loading" class="detail-card">
		<button class="close-btn" @click="emit('close')">X</button>

		<div v-if="loading" class="loading-text">加载中...</div>

		<template v-else-if="detail">
			<h3>{{ detail.callsign || detail.flight_id }}</h3>
			<p class="flight-id">{{ detail.flight_id }}</p>

			<table class="info-table">
				<tbody>
					<tr>
						<td>状态</td>
						<td>
							<span :class="['status-tag', statusClass]">
								{{ statusLabel }}
							</span>
						</td>
					</tr>
					<tr>
						<td>高度</td>
						<td>{{ detail.altitude_ft ?? "--" }} ft</td>
					</tr>
					<tr>
						<td>速度</td>
						<td>{{ detail.speed_kts ?? "--" }} kts</td>
					</tr>
					<tr>
						<td>航向</td>
						<td>{{ detail.heading != null ? `${detail.heading}°` : "--" }}</td>
					</tr>
					<tr v-if="detail.departure_airport">
						<td>出发机场</td>
						<td>{{ detail.departure_airport }}</td>
					</tr>
					<tr v-if="detail.arrival_airport">
						<td>目的机场</td>
						<td>{{ detail.arrival_airport }}</td>
					</tr>
					<tr v-if="detail.aircraft_type">
						<td>机型</td>
						<td>{{ detail.aircraft_type }}</td>
					</tr>
				</tbody>
			</table>

			<template v-if="detail.departure_weather">
				<h4>出发地天气（{{ detail.departure_airport }}）</h4>
				<WeatherBlock :weather="detail.departure_weather" />
			</template>

			<template v-if="detail.arrival_weather">
				<h4>到达地天气（{{ detail.arrival_airport }}）</h4>
				<WeatherBlock :weather="detail.arrival_weather" />
			</template>
		</template>
	</aside>
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
	.detail-card {
		position: absolute;
		bottom: 24px;
		left: 24px;
		width: 280px;
		background: #ffffff;
		border-radius: 8px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
		padding: 16px;
		z-index: 10;
		max-height: 60vh;
		overflow-y: auto;
	}

	.close-btn {
		position: absolute;
		top: 8px;
		right: 10px;
		background: none;
		border: none;
		cursor: pointer;
		font-size: 14px;
		color: #6b7280;
	}

	.close-btn:hover {
		color: #111827;
	}

	h3 {
		margin: 0 24px 2px 0;
		font-size: 16px;
	}

	h4 {
		margin: 12px 0 4px;
		font-size: 13px;
		color: #374151;
	}

	.flight-id {
		font-size: 11px;
		color: #9ca3af;
		margin: 0 0 10px;
	}

	.loading-text {
		color: #6b7280;
		font-size: 14px;
		text-align: center;
		padding: 20px 0;
	}

	.info-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}

	.info-table td {
		padding: 4px 0;
		vertical-align: top;
	}

	.info-table td:first-child {
		color: #6b7280;
		width: 80px;
		flex-shrink: 0;
	}

	.status-tag {
		display: inline-block;
		padding: 1px 8px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 500;
	}

	.status-airborne {
		background: #dbeafe;
		color: #1d4ed8;
	}

	.status-ground {
		background: #f3f4f6;
		color: #374151;
	}

	.status-scheduled {
		background: #fef9c3;
		color: #92400e;
	}

	.status-cancelled {
		background: #fee2e2;
		color: #b91c1c;
	}
</style>
