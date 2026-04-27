<template>
	<aside class="panel">
		<h2>航班列表</h2>
		<div v-if="!wsOnline" class="offline-banner">⚠ 实时连接已断开，正在重连...</div>
		<input
			v-model="localKeyword"
			class="search-input"
			type="text"
			placeholder="搜索呼号 / 航班号"
			@input="emit('search', localKeyword)"
		/>
		<div class="filter-tabs">
			<button
				v-for="tab in STATUS_TABS"
				:key="tab.value"
				:class="['tab-btn', { active: filterStatus === tab.value }]"
				@click="emit('filter', tab.value)"
			>
				{{ tab.label }}
			</button>
		</div>
		<p class="count-hint">共 {{ flights.length }} 架</p>
		<ul>
			<li
				v-for="flight in flights"
				:key="flight.flight_id"
				:class="{ selected: flight.flight_id === selectedFlightId }"
				@click="emit('select', flight.flight_id)"
			>
				<div class="flight-main">
					<strong>{{ flight.callsign || flight.flight_id }}</strong>
					<span class="altitude">{{ flight.altitude_ft ?? "--" }} ft</span>
				</div>
				<div class="flight-sub">
					<span>{{
						flight.speed_kts != null ? `${Math.round(flight.speed_kts)} kts` : ""
					}}</span>
					<span
						:class="
							flight.altitude_ft != null && flight.altitude_ft > 100
								? 'dot-air'
								: 'dot-ground'
						"
					>
						{{
							flight.altitude_ft != null && flight.altitude_ft > 100
								? "飞行中"
								: "地面"
						}}
					</span>
				</div>
			</li>
		</ul>
		<p v-if="!flights.length" class="empty-hint">无匹配航班</p>
	</aside>
</template>

<script setup lang="ts">
	import { ref } from "vue";
	import type { FlightBrief } from "../types/flight";

	const STATUS_TABS = [
		{ label: "全部", value: "all" as const },
		{ label: "飞行中", value: "airborne" as const },
		{ label: "地面", value: "on_ground" as const },
	];

	defineProps<{
		flights: FlightBrief[];
		selectedFlightId?: string | null;
		filterStatus?: "all" | "airborne" | "on_ground";
		wsOnline?: boolean;
	}>();

	const emit = defineEmits<{
		select: [flightId: string];
		search: [keyword: string];
		filter: [status: "all" | "airborne" | "on_ground"];
	}>();

	const localKeyword = ref("");
</script>

<style scoped>
	.panel {
		width: 320px;
		padding: 12px;
		border-left: 1px solid #d1d5db;
		background: #ffffff;
		overflow: auto;
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	h2 {
		margin: 0 0 8px;
		font-size: 15px;
	}

	.offline-banner {
		background: #fef3c7;
		color: #92400e;
		font-size: 12px;
		padding: 6px 8px;
		border-radius: 4px;
		margin-bottom: 8px;
	}

	.search-input {
		width: 100%;
		padding: 6px 10px;
		border: 1px solid #d1d5db;
		border-radius: 6px;
		font-size: 13px;
		box-sizing: border-box;
		outline: none;
		margin-bottom: 8px;
	}

	.search-input:focus {
		border-color: #2563eb;
		box-shadow: 0 0 0 2px #dbeafe;
	}

	.filter-tabs {
		display: flex;
		gap: 4px;
		margin-bottom: 6px;
	}

	.tab-btn {
		flex: 1;
		padding: 4px 0;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		background: #f9fafb;
		font-size: 12px;
		cursor: pointer;
		transition: all 0.15s;
	}

	.tab-btn.active {
		background: #2563eb;
		color: #ffffff;
		border-color: #2563eb;
	}

	.count-hint {
		font-size: 11px;
		color: #9ca3af;
		margin: 0 0 4px;
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 0;
		flex: 1;
		overflow-y: auto;
	}

	li {
		padding: 8px 4px;
		border-bottom: 1px solid #f3f4f6;
		cursor: pointer;
		transition: background-color 0.15s;
	}

	li:hover {
		background: #f8fafc;
	}

	li.selected {
		background: #eff6ff;
	}

	.flight-main {
		display: flex;
		justify-content: space-between;
		font-size: 13px;
	}

	.altitude {
		color: #6b7280;
		font-size: 12px;
	}

	.flight-sub {
		display: flex;
		justify-content: space-between;
		font-size: 11px;
		color: #9ca3af;
		margin-top: 2px;
	}

	.dot-air {
		color: #2563eb;
	}

	.dot-ground {
		color: #6b7280;
	}

	.empty-hint {
		text-align: center;
		color: #9ca3af;
		font-size: 13px;
		padding: 20px 0;
	}
</style>
