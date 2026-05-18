<template>
	<div class="marked-panel">
		<div class="mk-head">
			<span>已标记</span>
			<strong>{{ markedFlights.length }}</strong>
		</div>
		<p v-if="!markedFlights.length" class="mk-empty">{{ i18n.marked.empty }}</p>
		<ul v-else class="mk-list">
			<li
				v-for="flight in markedFlights"
				:key="flight.flight_id"
				:class="['mk-item', { selected: flight.flight_id === selectedFlightId }]"
			>
				<button
					type="button"
					class="mk-main"
					@click="emit('select', flight.flight_id)"
				>
					<span class="mk-cs">{{ flight.callsign || flight.flight_id }}</span>
					<span class="mk-sub">
						{{ (flight.altitude_ft ?? 0) > 100 ? "空中" : "地面" }}
						·
						{{ flight.altitude_ft != null ? Math.round(flight.altitude_ft) : "--" }}
						ft
					</span>
				</button>
				<button
					type="button"
					class="mk-unmark"
					:title="i18n.marked.remove"
					@click.stop="store.unmarkFlight(flight.flight_id)"
				>
					×
				</button>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
	import { computed } from "vue";
	import { useLocaleStore } from "../../i18n";
	import { useFlightStore } from "../../stores/flight";
	import type { FlightBrief } from "../../types/flight";

	defineProps<{
		markedFlights: FlightBrief[];
		selectedFlightId?: string | null;
	}>();

	const emit = defineEmits<{
		select: [flightId: string];
	}>();

	const store = useFlightStore();
	const localeStore = useLocaleStore();
	const i18n = computed(() => localeStore.t);
</script>

<style scoped>
	.marked-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		min-height: 0;
	}

	.mk-head {
		display: flex;
		align-items: baseline;
		gap: 6px;
		padding: 0 4px 10px;
		font-size: 12px;
		color: var(--text-muted);
	}

	.mk-head strong {
		font-size: 14px;
		color: var(--accent);
	}

	.mk-empty {
		font-size: 13px;
		color: var(--text-muted);
		padding: 24px 8px;
		text-align: center;
	}

	.mk-list {
		list-style: none;
		margin: 0;
		padding: 0;
		overflow-y: auto;
		flex: 1;
	}

	.mk-item {
		display: flex;
		align-items: stretch;
		border-bottom: 1px solid var(--border);
	}

	.mk-item.selected .mk-main {
		background: var(--accent-subtle);
	}

	.mk-main {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 2px;
		padding: 10px 8px;
		border: none;
		background: transparent;
		cursor: pointer;
		text-align: left;
	}

	.mk-cs {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.mk-sub {
		font-size: 11px;
		color: var(--text-muted);
	}

	.mk-unmark {
		width: 36px;
		border: none;
		background: transparent;
		color: var(--text-muted);
		font-size: 18px;
		cursor: pointer;
	}

	.mk-unmark:hover {
		color: #f43f5e;
	}
</style>
