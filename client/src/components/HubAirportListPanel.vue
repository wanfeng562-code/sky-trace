<template>
	<div class="hub-list">
		<!-- 列表视图 -->
		<template v-if="!selected">
			<div class="hl-head">
				<label class="hl-search-wrap">
					<svg class="hl-search-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
							clip-rule="evenodd"
						/>
					</svg>
					<input
						v-model="keyword"
						class="hl-search-input"
						type="text"
						placeholder="IATA / 中文名 / 城市"
					/>
				</label>
				<span class="hl-count">{{ filtered.length }}</span>
			</div>
			<div class="hl-chips">
				<button
					:class="['hl-chip', { active: sortBy === 'traffic' }]"
					@click="sortBy = 'traffic'"
				>
					按航班量
				</button>
				<button
					:class="['hl-chip', { active: sortBy === 'iata' }]"
					@click="sortBy = 'iata'"
				>
					按 IATA
				</button>
			</div>
			<RecycleScroller
				class="hl-scroller"
				:items="filtered"
				:item-size="78"
				key-field="id"
				v-slot="{ item: hub }"
			>
				<div
					:class="['hl-card', { selected: hub.airport.iata === selectedIata }]"
					@click="openDetail(hub)"
				>
					<div class="hl-card-top">
						<span class="hl-iata">{{ hub.airport.iata }}</span>
						<span :class="['hl-tier', `tier-${hub.hubTier}`]">{{
							tierLabel(hub.hubTier)
						}}</span>
					</div>
					<div class="hl-name-zh">
						{{ formatAirportDisplay(hub.airport).nameZh }}
					</div>
					<div class="hl-meta">
						<span>离港 {{ hub.departures.length }}</span>
						<span>到港 {{ hub.arrivals.length }}</span>
						<span>相关 {{ hub.relatedFlights.length }}</span>
					</div>
				</div>
			</RecycleScroller>
			<div v-if="!filtered.length" class="hl-empty">无匹配枢纽机场</div>
		</template>

		<!-- 详情视图 -->
		<template v-else>
			<div class="hl-detail-head">
				<button class="hl-back" @click="onBack">← 返回列表</button>
				<div class="hl-detail-title">
					<span class="hl-iata-lg">{{ selected.airport.iata }}</span>
					<span :class="['hl-tier', `tier-${selected.hubTier}`]">{{
						tierLabel(selected.hubTier)
					}}</span>
				</div>
				<div class="hl-name-zh lg">
					{{ formatAirportDisplay(selected.airport).nameZh }}
				</div>
				<div class="hl-name-en">{{ selected.airport.name }}</div>
				<div class="hl-loc">
					{{ formatAirportDisplay(selected.airport).cityZh }}
					<span v-if="formatAirportDisplay(selected.airport).countryLabel">
						· {{ formatAirportDisplay(selected.airport).countryLabel }}
					</span>
				</div>
				<div class="hl-stats">
					<span>离港 {{ selected.departures.length }}</span>
					<span>到港 {{ selected.arrivals.length }}</span>
					<span>飞行中 {{ selected.airborneCount }}</span>
					<span>地面 {{ selected.groundCount }}</span>
				</div>
				<div class="hl-actions">
					<button
						:class="['hl-btn', { primary: hubAction === 'locate' }]"
						@click="onLocate"
					>
						地图定位
					</button>
					<button
						:class="['hl-btn', { primary: hubAction === 'schedule' }]"
						@click="onSchedule"
					>
						时刻表
					</button>
				</div>
			</div>

			<div class="hl-detail-body">
				<section class="hl-flight-section">
					<header class="hl-section-sticky">
						<div class="hl-section-title">
							离港航班
							<span class="hl-section-count">{{
								selected.departures.length
							}}</span>
						</div>
						<div class="hl-table-head">
							<span>呼号</span>
							<span>航路</span>
							<span>状态</span>
						</div>
					</header>
				<div v-if="!selected.departures.length" class="hl-section-empty">
					暂无离港航班
				</div>
				<div
					v-for="f in selected.departures"
					:key="'dep-' + f.flight_id"
					class="hl-flight-row"
					@click="emit('selectFlight', f.flight_id)"
				>
					<span class="hl-flight-cs">{{ f.callsign || f.flight_id }}</span>
					<span class="hl-flight-route"
						>{{ f.departure_airport ?? "--" }} →
						{{ f.arrival_airport ?? "--" }}</span
					>
					<span class="hl-flight-meta">{{
						(f.altitude_ft ?? 0) > 100 ? "飞行中" : "地面"
					}}</span>
				</div>
				</section>

				<section class="hl-flight-section">
					<header class="hl-section-sticky">
						<div class="hl-section-title">
							到港航班
							<span class="hl-section-count">{{
								selected.arrivals.length
							}}</span>
						</div>
						<div class="hl-table-head">
							<span>呼号</span>
							<span>航路</span>
							<span>状态</span>
						</div>
					</header>
				<div v-if="!selected.arrivals.length" class="hl-section-empty">
					暂无到港航班
				</div>
				<div
					v-for="f in selected.arrivals"
					:key="'arr-' + f.flight_id"
					class="hl-flight-row"
					@click="emit('selectFlight', f.flight_id)"
				>
					<span class="hl-flight-cs">{{ f.callsign || f.flight_id }}</span>
					<span class="hl-flight-route"
						>{{ f.departure_airport ?? "--" }} →
						{{ f.arrival_airport ?? "--" }}</span
					>
					<span class="hl-flight-meta">{{
						(f.altitude_ft ?? 0) > 100 ? "飞行中" : "地面"
					}}</span>
				</div>
				</section>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
	import { computed, ref, watch } from "vue";
	import { RecycleScroller } from "vue-virtual-scroller";
	import { formatAirportDisplay } from "../data/airportDisplay";
	import type { HubAirportSummary } from "../utils/hubAirportList";
	import { buildHubAirportSummaries } from "../utils/hubAirportList";
	import type { AirportInfo, FlightBrief } from "../types/flight";

	const props = defineProps<{
		airports: AirportInfo[];
		flights: FlightBrief[];
		selectedIata?: string | null;
	}>();

	const emit = defineEmits<{
		locate: [iata: string];
		schedule: [iata: string];
		selectFlight: [flightId: string];
		clear: [];
	}>();

	function onBack() {
		selected.value = null;
		emit("clear");
	}

	const keyword = ref("");
	const sortBy = ref<"traffic" | "iata">("traffic");
	const selected = ref<HubAirportSummary | null>(null);
	const hubAction = ref<"locate" | "schedule">("locate");

	const summaries = computed(() =>
		buildHubAirportSummaries(props.airports, props.flights),
	);

	const filtered = computed(() => {
		const kw = keyword.value.trim().toUpperCase();
		let list = summaries.value;
		if (kw) {
			list = list.filter((hub) => {
				const d = formatAirportDisplay(hub.airport);
				return (
					hub.airport.iata.toUpperCase().includes(kw) ||
					d.nameZh.toUpperCase().includes(kw) ||
					d.nameEn.toUpperCase().includes(kw) ||
					d.cityZh.toUpperCase().includes(kw)
				);
			});
		}
		const sorted =
			sortBy.value === "iata"
				? [...list].sort((a, b) =>
						a.airport.iata.localeCompare(b.airport.iata),
					)
				: list;
		return sorted.map((hub) => ({ ...hub, id: hub.airport.iata }));
	});

	watch(
		() => props.selectedIata,
		(iata) => {
			if (!iata) {
				selected.value = null;
				return;
			}
			const hub = summaries.value.find((h) => h.airport.iata === iata);
			if (hub) {
				selected.value = hub;
				hubAction.value = "locate";
			}
		},
	);

	function openDetail(hub: HubAirportSummary) {
		selected.value = hub;
		hubAction.value = "locate";
		emit("locate", hub.airport.iata);
	}

	function onLocate() {
		if (!selected.value) return;
		hubAction.value = "locate";
		emit("locate", selected.value.airport.iata);
	}

	function onSchedule() {
		if (!selected.value) return;
		hubAction.value = "schedule";
		emit("schedule", selected.value.airport.iata);
	}

	function tierLabel(tier: 1 | 2 | 3): string {
		if (tier === 1) return "繁忙";
		if (tier === 2) return "中等";
		return "一般";
	}
</script>

<style scoped>
	.hub-list {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
		background: var(--bg-surface);
		color: var(--text-primary);
	}

	.hl-head {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 10px 12px 0;
		border-bottom: 1px solid var(--border);
		padding-bottom: 8px;
	}

	.hl-search-wrap {
		flex: 1;
		position: relative;
		display: flex;
		align-items: center;
	}

	.hl-search-icon {
		position: absolute;
		left: 8px;
		width: 14px;
		height: 14px;
		color: var(--text-muted);
		pointer-events: none;
	}

	.hl-search-input {
		width: 100%;
		padding: 6px 10px 6px 28px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-primary);
		font-size: 13px;
		outline: none;
	}

	.hl-search-input:focus {
		border-color: var(--accent);
	}

	.hl-count {
		flex-shrink: 0;
		min-width: 28px;
		text-align: center;
		padding: 2px 7px;
		background: var(--bg-raised);
		border-radius: 999px;
		font-size: 11px;
		font-weight: 600;
		color: var(--text-secondary);
	}

	.hl-chips {
		display: flex;
		gap: 5px;
		padding: 8px 12px;
		border-bottom: 1px solid var(--border);
	}

	.hl-chip {
		padding: 3px 10px;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--bg-raised);
		color: var(--text-secondary);
		font-size: 12px;
		cursor: pointer;
	}

	.hl-chip.active {
		background: var(--accent-subtle);
		color: var(--accent);
		border-color: var(--accent);
	}

	.hl-scroller {
		flex: 1;
		min-height: 0;
	}

	.hl-card {
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 4px;
		height: 78px;
		padding: 0 12px;
		border-bottom: 1px solid var(--border);
		cursor: pointer;
		box-sizing: border-box;
	}

	.hl-card:hover {
		background: var(--bg-raised);
	}

	.hl-card.selected {
		background: var(--accent-subtle);
		border-left: 2px solid var(--accent);
		padding-left: 10px;
	}

	.hl-card-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.hl-iata {
		font-size: 14px;
		font-weight: 700;
		letter-spacing: 0.04em;
	}

	.hl-tier {
		font-size: 10px;
		font-weight: 600;
		padding: 1px 6px;
		border-radius: 999px;
	}

	.hl-tier.tier-1 {
		background: rgba(34, 229, 132, 0.2);
		color: #22e584;
	}

	.hl-tier.tier-2 {
		background: rgba(56, 189, 248, 0.2);
		color: #38bdf8;
	}

	.hl-tier.tier-3 {
		background: rgba(192, 132, 252, 0.2);
		color: #c084fc;
	}

	.hl-name-zh {
		font-size: 13px;
		font-weight: 500;
	}

	.hl-name-zh.lg {
		font-size: 15px;
		margin-top: 4px;
	}

	.hl-meta {
		display: flex;
		gap: 10px;
		font-size: 11px;
		color: var(--text-muted);
	}

	.hl-empty {
		padding: 24px;
		text-align: center;
		color: var(--text-muted);
		font-size: 13px;
	}

	.hl-detail-head {
		flex-shrink: 0;
		padding: 10px 12px 12px;
		border-bottom: 1px solid var(--border);
	}

	.hl-back {
		background: none;
		border: none;
		color: var(--accent);
		font-size: 12px;
		cursor: pointer;
		padding: 0 0 8px;
	}

	.hl-detail-title {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.hl-iata-lg {
		font-size: 20px;
		font-weight: 700;
	}

	.hl-name-en {
		font-size: 11px;
		color: var(--text-muted);
		margin-top: 2px;
		line-height: 1.4;
	}

	.hl-loc {
		font-size: 12px;
		color: var(--text-secondary);
		margin-top: 4px;
	}

	.hl-stats {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
		margin-top: 8px;
		font-size: 11px;
		color: var(--text-secondary);
	}

	.hl-actions {
		display: flex;
		gap: 8px;
		margin-top: 10px;
	}

	.hl-btn {
		flex: 1;
		padding: 6px 10px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--bg-raised);
		color: var(--text-primary);
		font-size: 12px;
		cursor: pointer;
	}

	.hl-btn.primary {
		background: var(--accent-subtle);
		border-color: var(--accent);
		color: var(--accent);
	}

	.hl-detail-body {
		flex: 1;
		min-height: 0;
		overflow-y: auto;
	}

	.hl-flight-section {
		padding-bottom: 4px;
	}

	.hl-section-sticky {
		position: sticky;
		top: 0;
		z-index: 2;
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		box-shadow: 0 1px 0 rgba(0, 0, 0, 0.2);
	}

	.hl-section-title {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 10px 12px 4px;
		font-size: 12px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.hl-section-count {
		font-size: 11px;
		font-weight: 500;
		color: var(--text-muted);
	}

	.hl-table-head {
		display: grid;
		grid-template-columns: 72px 1fr 48px;
		gap: 8px;
		padding: 0 12px 8px;
		font-size: 10px;
		font-weight: 500;
		color: var(--text-muted);
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}

	.hl-section-empty {
		padding: 12px;
		font-size: 12px;
		color: var(--text-muted);
	}

	.hl-flight-row {
		display: grid;
		grid-template-columns: 72px 1fr 48px;
		gap: 8px;
		align-items: center;
		padding: 8px 12px;
		border-bottom: 1px solid var(--border);
		cursor: pointer;
	}

	.hl-flight-row:hover {
		background: var(--bg-raised);
	}

	.hl-flight-cs {
		font-size: 13px;
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.hl-flight-route {
		font-size: 11px;
		color: var(--text-muted);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.hl-flight-meta {
		font-size: 10px;
		color: var(--text-secondary);
		text-align: right;
	}
</style>
