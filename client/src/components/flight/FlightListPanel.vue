<template>
	<div class="flight-list">
		<div class="fl-toolbar">
			<label class="fl-search-wrap">
				<svg class="fl-search-icon" viewBox="0 0 20 20" fill="currentColor">
					<path
						fill-rule="evenodd"
						d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
						clip-rule="evenodd"
					/>
				</svg>
				<input
					v-model="store.searchKeyword"
					class="fl-search-input"
					type="text"
					placeholder="呼号 / 航班号"
				/>
			</label>
		</div>

		<div class="fl-status-row">
			<button
				v-for="tab in STATUS_TABS"
				:key="tab.value"
				:class="['fl-pill', { active: store.filterStatus === tab.value }]"
				type="button"
				@click="store.applyStatusPreset(tab.value)"
			>
				{{ tab.label }}
			</button>
		</div>

		<div v-if="!store.wsOnline" class="fl-offline">
			实时连接已断开，正在重连…
		</div>

		<div class="fl-list-head">
			<span>结果</span>
			<strong>{{ flights.length.toLocaleString() }}</strong>
			<span class="fl-list-hint">架</span>
			<span
				v-if="store.flights.length > flights.length"
				class="fl-filter-hint"
			>
				· 共 {{ store.flights.length.toLocaleString() }} 架
			</span>
			<span v-else-if="store.activeFilterCount" class="fl-filter-hint">
				· {{ store.activeFilterCount }} 项筛选
			</span>
		</div>

		<RecycleScroller
			class="fl-scroller"
			:items="flights"
			:item-size="64"
			key-field="flight_id"
			v-slot="{ item: flight }"
		>
			<div
				:class="[
					'fl-card',
					{
						selected: flight.flight_id === selectedFlightId,
						marked: store.isMarked(flight.flight_id),
					},
				]"
				@click="emit('select', flight.flight_id)"
			>
				<button
					type="button"
					:class="['fl-mark', { on: store.isMarked(flight.flight_id) }]"
					:title="store.isMarked(flight.flight_id) ? '取消标记' : '标记航班'"
					@click.stop="store.toggleMarkFlight(flight.flight_id)"
				>
					★
				</button>
				<div class="fl-card-main">
					<div class="fl-cs-row">
						<span v-if="airlinePrefix(flight)" class="fl-airline">{{
							airlinePrefix(flight)
						}}</span>
						<span class="fl-cs">{{ flight.callsign || flight.flight_id }}</span>
					</div>
					<span
						:class="[
							'fl-status',
							(flight.altitude_ft ?? 0) > 100 ? 'st-air' : 'st-gnd',
						]"
					>
						{{ (flight.altitude_ft ?? 0) > 100 ? "空中" : "地面" }}
					</span>
				</div>
				<div class="fl-card-sub">
					<span v-if="flight.departure_airport || flight.arrival_airport">
						{{ flight.departure_airport ?? "?" }} →
						{{ flight.arrival_airport ?? "?" }}
					</span>
					<span v-else class="fl-muted">航路未知</span>
				</div>
				<div class="fl-card-meta">
					<span>{{
						flight.altitude_ft != null
							? Math.round(flight.altitude_ft).toLocaleString() + " ft"
							: "--"
					}}</span>
					<span>{{
						flight.speed_kts != null
							? Math.round(flight.speed_kts) + " kts"
							: "--"
					}}</span>
				</div>
			</div>
		</RecycleScroller>

		<div v-if="!flights.length" class="fl-empty">无匹配航班</div>
	</div>
</template>

<script setup lang="ts">
	import { RecycleScroller } from "vue-virtual-scroller";
	import { useFlightStore } from "../../stores/flight";
	import type { FlightBrief } from "../../types/flight";

	const STATUS_TABS = [
		{ label: "全部", value: "all" as const },
		{ label: "空中", value: "airborne" as const },
		{ label: "地面", value: "on_ground" as const },
	];

	defineProps<{
		flights: FlightBrief[];
		selectedFlightId?: string | null;
	}>();

	const emit = defineEmits<{
		select: [flightId: string];
	}>();

	const store = useFlightStore();

	function airlinePrefix(flight: FlightBrief): string | null {
		const cs = (flight.callsign || "").trim().toUpperCase();
		const m = cs.match(/^([A-Z]{2,3})/);
		return m ? m[1] : null;
	}
</script>

<style scoped>
	.flight-list {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
	}

	.fl-toolbar {
		padding: 12px 16px 8px;
	}

	.fl-search-wrap {
		position: relative;
		display: flex;
		align-items: center;
	}

	.fl-search-icon {
		position: absolute;
		left: 10px;
		width: 14px;
		height: 14px;
		color: var(--text-muted);
		pointer-events: none;
	}

	.fl-search-input {
		width: 100%;
		height: 36px;
		padding: 0 12px 0 32px;
		background: var(--bg-elevated);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: 13px;
		color: var(--text-primary);
		outline: none;
	}

	.fl-search-input:focus {
		border-color: var(--accent);
	}

	.fl-status-row {
		display: flex;
		gap: 6px;
		padding: 0 16px 8px;
	}

	.fl-pill {
		flex: 1;
		height: 32px;
		border-radius: var(--radius-md);
		border: 1px solid var(--border);
		background: var(--bg-surface);
		font-size: 12px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.fl-pill.active {
		background: var(--accent-subtle);
		border-color: var(--accent);
		color: var(--accent);
		font-weight: 600;
	}

	.fl-offline {
		margin: 0 16px 8px;
		padding: 8px 10px;
		border-radius: var(--radius-sm);
		background: var(--warning-subtle);
		color: var(--warning);
		font-size: 12px;
	}

	.fl-list-head {
		display: flex;
		align-items: baseline;
		gap: 4px;
		padding: 8px 16px;
		font-size: 12px;
		color: var(--text-muted);
		border-top: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		background: var(--bg-elevated);
	}

	.fl-list-head strong {
		font-size: 16px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.fl-filter-hint {
		margin-left: 4px;
		color: var(--accent);
	}

	.fl-scroller {
		flex: 1;
		min-height: 0;
	}

	.fl-card {
		position: relative;
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 4px;
		height: 64px;
		padding: 0 36px 0 16px;
		border-bottom: 1px solid var(--border);
		cursor: pointer;
		box-sizing: border-box;
	}

	.fl-card:hover {
		background: var(--bg-elevated);
	}

	.fl-card.selected {
		background: var(--accent-subtle);
		border-left: 3px solid var(--accent);
		padding-left: 13px;
	}

	.fl-card.marked {
		box-shadow: inset 3px 0 0 #f43f5e;
	}

	.fl-mark {
		position: absolute;
		right: 8px;
		top: 50%;
		transform: translateY(-50%);
		width: 28px;
		height: 28px;
		border: none;
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-muted);
		font-size: 16px;
		line-height: 1;
		cursor: pointer;
	}

	.fl-mark.on {
		color: #f43f5e;
	}

	.fl-card-main {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.fl-cs-row {
		display: flex;
		align-items: center;
		gap: 8px;
		min-width: 0;
	}

	.fl-airline {
		flex-shrink: 0;
		padding: 2px 6px;
		border-radius: var(--radius-sm);
		background: var(--bg-elevated);
		border: 1px solid var(--border);
		font-size: 10px;
		font-weight: 600;
		color: var(--text-muted);
		letter-spacing: 0.03em;
	}

	.fl-cs {
		font-size: 15px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.fl-status {
		font-size: 10px;
		font-weight: 600;
		padding: 2px 8px;
		border-radius: 999px;
	}

	.st-air {
		background: rgba(255, 191, 0, 0.15);
		color: #b45309;
	}

	.st-gnd {
		background: var(--bg-elevated);
		color: var(--text-muted);
	}

	.fl-card-sub {
		font-size: 11px;
		color: var(--text-secondary);
	}

	.fl-muted {
		color: var(--text-muted);
	}

	.fl-card-meta {
		display: flex;
		gap: 12px;
		font-size: 11px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}

	.fl-empty {
		padding: 32px;
		text-align: center;
		color: var(--text-muted);
		font-size: 13px;
	}
</style>
