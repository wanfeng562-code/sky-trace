<template>
	<aside class="panel">
		<h2>Flights</h2>
		<p class="hint">点击航班可在地图中自动定位并高亮。</p>
		<ul>
			<li
				v-for="flight in flights"
				:key="flight.flight_id"
				:class="{ selected: flight.flight_id === selectedFlightId }"
				@click="emit('select', flight.flight_id)"
			>
				<strong>{{ flight.callsign || flight.flight_id }}</strong>
				<span>{{ flight.altitude_ft ?? "--" }} ft</span>
			</li>
		</ul>
	</aside>
</template>

<script setup lang="ts">
	import type { FlightBrief } from "../types/flight";

	defineProps<{
		flights: FlightBrief[];
		selectedFlightId?: string | null;
	}>();

	const emit = defineEmits<{
		select: [flightId: string];
	}>();
</script>

<style scoped>
	.panel {
		width: 320px;
		padding: 12px;
		border-left: 1px solid #d1d5db;
		background: #ffffff;
		overflow: auto;
	}

	.hint {
		color: #6b7280;
		font-size: 12px;
	}

	ul {
		list-style: none;
		padding: 0;
		margin: 8px 0 0;
	}

	li {
		display: flex;
		justify-content: space-between;
		padding: 6px 0;
		border-bottom: 1px solid #f3f4f6;
		cursor: pointer;
		transition: background-color 0.2s ease;
	}

	li:hover {
		background: #f8fafc;
	}

	li.selected {
		background: #eff6ff;
		color: #1d4ed8;
	}
</style>
