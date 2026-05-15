<template>
	<div class="flight-list">
		<!-- 粘性头部 -->
		<div class="fl-head">
			<!-- 搜索行 -->
			<div class="fl-search-row">
				<label class="fl-search-wrap">
					<svg class="fl-search-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
							clip-rule="evenodd"
						/>
					</svg>
					<input
						v-model="localKeyword"
						class="fl-search-input"
						type="text"
						placeholder="呼号 / 航班号"
						@input="emit('search', localKeyword)"
					/>
				</label>
				<span class="fl-count">{{ flights.length }}</span>
			</div>

			<!-- 状态芯片 -->
			<div class="fl-chips">
				<button
					v-for="tab in STATUS_TABS"
					:key="tab.value"
					:class="['fl-chip', { active: filterStatus === tab.value }]"
					@click="emit('filter', tab.value)"
				>
					{{ tab.label }}
				</button>
				<button
					:class="['fl-chip fl-chip-adv', { active: showAdvFilter }]"
					@click="showAdvFilter = !showAdvFilter"
					title="高级筛选"
				>
					<svg class="fl-chip-icon" viewBox="0 0 16 16" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M3 3a1 1 0 011-1h8a1 1 0 011 1v2a1 1 0 01-.293.707L9 9.414V13a1 1 0 01-.553.894l-2 1A1 1 0 015 14v-4.586L3.293 5.707A1 1 0 013 5V3z"
							clip-rule="evenodd"
						/>
					</svg>
					筛选
					<span v-if="hasActiveFilter" class="fl-adv-dot"></span>
				</button>
			</div>

			<!-- 高级筛选面板（可折叠） -->
			<div v-if="showAdvFilter" class="fl-adv">
				<select
					class="fl-select"
					:value="filterCountry ?? ''"
					@change="onCountryChange"
				>
					<option value="">全部国家/地区</option>
					<option v-for="c in COUNTRIES" :key="c.code" :value="c.code">
						{{ c.nameZh }}
					</option>
				</select>
				<div v-if="filterCountry" class="fl-mode-chips">
					<button
						v-for="m in COUNTRY_MODES"
						:key="m.value"
						:class="['fl-mode-chip', { active: filterCountryMode === m.value }]"
						@click="emit('filterCountryMode', m.value)"
					>
						{{ m.label }}
					</button>
				</div>
				<select
					v-if="filterCountry && currentRegions.length"
					class="fl-select"
					:value="filterRegion ?? ''"
					@change="onRegionChange"
				>
					<option value="">全部{{ currentCountryName }}地区</option>
					<option v-for="r in currentRegions" :key="r.code" :value="r.code">
						{{ r.nameZh }}
					</option>
				</select>
			</div>

			<!-- 离线横幅 -->
			<div v-if="!wsOnline" class="fl-offline">
				<svg class="fl-offline-icon" viewBox="0 0 20 20" fill="currentColor">
					<path
						fill-rule="evenodd"
						d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
						clip-rule="evenodd"
					/>
				</svg>
				实时连接已断开，正在重连...
			</div>
		</div>

		<!-- 列表主体 -->
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
					{ selected: flight.flight_id === selectedFlightId },
				]"
				@click="emit('select', flight.flight_id)"
			>
				<div class="fl-card-row1">
					<span class="fl-cs">{{ flight.callsign || flight.flight_id }}</span>
					<div class="fl-card-right">
						<img
							v-if="flight.airline_iata"
							:src="`https://airlabs.co/img/airline/m/${flight.airline_iata}.png`"
							class="fl-logo"
							:alt="flight.airline_iata"
							@error="
								(e) => ((e.target as HTMLImageElement).style.display = 'none')
							"
						/>
						<span
							:class="[
								'fl-status',
								(flight.altitude_ft ?? 0) > 100 ? 'st-air' : 'st-gnd',
							]"
						>
							{{ (flight.altitude_ft ?? 0) > 100 ? "飞行中" : "地面" }}
						</span>
					</div>
				</div>
				<div class="fl-card-row2">
					<span class="fl-meta">{{
						flight.speed_kts != null
							? Math.round(flight.speed_kts) + " kts"
							: ""
					}}</span>
					<span class="fl-meta">{{
						flight.altitude_ft != null
							? Math.round(flight.altitude_ft).toLocaleString() + " ft"
							: "--"
					}}</span>
				</div>
			</div>
		</RecycleScroller>

		<div v-if="!flights.length" class="fl-empty">
			<svg
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				class="fl-empty-icon"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M6 18L18 6M6 6l12 12"
				/>
			</svg>
			无匹配航班
		</div>
	</div>
</template>

<script setup lang="ts">
	import { computed, ref } from "vue";
	import { RecycleScroller } from "vue-virtual-scroller";
	import {
		COUNTRIES,
		type CountryFilterMode,
		type SubRegion,
	} from "../data/countries";
	import type { FlightBrief } from "../types/flight";

	const STATUS_TABS = [
		{ label: "全部", value: "all" as const },
		{ label: "飞行中", value: "airborne" as const },
		{ label: "地面", value: "on_ground" as const },
	];

	const COUNTRY_MODES: { label: string; value: CountryFilterMode }[] = [
		{ label: "领空内", value: "airspace" },
		{ label: "出发", value: "departure" },
		{ label: "到达", value: "arrival" },
	];

	const props = defineProps<{
		flights: FlightBrief[];
		selectedFlightId?: string | null;
		filterStatus?: "all" | "airborne" | "on_ground";
		filterCountry?: string | null;
		filterCountryMode?: CountryFilterMode;
		filterRegion?: string | null;
		wsOnline?: boolean;
	}>();

	const emit = defineEmits<{
		select: [flightId: string];
		search: [keyword: string];
		filter: [status: "all" | "airborne" | "on_ground"];
		filterCountry: [country: string | null];
		filterCountryMode: [mode: CountryFilterMode];
		filterRegion: [region: string | null];
	}>();

	const localKeyword = ref("");
	const showAdvFilter = ref(false);

	const hasActiveFilter = computed(
		() =>
			!!(
				props.filterCountry ||
				(props.filterStatus && props.filterStatus !== "all")
			),
	);

	const currentRegions = computed<SubRegion[]>(
		() => COUNTRIES.find((c) => c.code === props.filterCountry)?.regions ?? [],
	);
	const currentCountryName = computed(
		() => COUNTRIES.find((c) => c.code === props.filterCountry)?.nameZh ?? "",
	);

	function onCountryChange(event: Event) {
		const val = (event.target as HTMLSelectElement).value;
		emit("filterCountry", val || null);
	}
	function onRegionChange(event: Event) {
		const val = (event.target as HTMLSelectElement).value;
		emit("filterRegion", val || null);
	}
</script>

<style scoped>
	/* ── 根容器：撑满父级 */
	.flight-list {
		display: flex;
		flex-direction: column;
		height: 100%;
		overflow: hidden;
		background: var(--bg-surface);
		color: var(--text-primary);
	}

	/* ── 粘性头部 */
	.fl-head {
		flex-shrink: 0;
		padding: 10px 12px 0;
		border-bottom: 1px solid var(--border);
		background: var(--bg-surface);
	}

	/* ── 搜索行 */
	.fl-search-row {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
	}

	.fl-search-wrap {
		flex: 1;
		position: relative;
		display: flex;
		align-items: center;
	}

	.fl-search-icon {
		position: absolute;
		left: 8px;
		width: 14px;
		height: 14px;
		color: var(--text-muted);
		pointer-events: none;
		flex-shrink: 0;
	}

	.fl-search-input {
		width: 100%;
		padding: 6px 10px 6px 28px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-primary);
		font-size: 13px;
		outline: none;
		transition: border-color var(--t-fast);
	}

	.fl-search-input::placeholder {
		color: var(--text-muted);
	}

	.fl-search-input:focus {
		border-color: var(--accent);
	}

	.fl-count {
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

	/* ── 芯片行 */
	.fl-chips {
		display: flex;
		gap: 5px;
		margin-bottom: 8px;
		flexwrap: wrap;
	}

	.fl-chip {
		padding: 3px 10px;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--bg-raised);
		color: var(--text-secondary);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--t-fast);
	}

	.fl-chip.active {
		background: var(--accent-subtle);
		color: var(--accent);
		border-color: var(--accent);
	}

	.fl-chip-adv {
		display: flex;
		align-items: center;
		gap: 4px;
		position: relative;
	}

	.fl-chip-icon {
		width: 11px;
		height: 11px;
	}

	.fl-adv-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--warning);
		position: absolute;
		top: -2px;
		right: -2px;
	}

	/* ── 高级筛选面板 */
	.fl-adv {
		padding: 8px 0;
		display: flex;
		flex-direction: column;
		gap: 6px;
		border-top: 1px dashed var(--border);
		margin-bottom: 8px;
	}

	.fl-select {
		width: 100%;
		padding: 5px 8px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-primary);
		font-size: 12px;
		outline: none;
		cursor: pointer;
	}

	.fl-select:focus {
		border-color: var(--accent);
	}

	.fl-mode-chips {
		display: flex;
		gap: 4px;
	}

	.fl-mode-chip {
		flex: 1;
		padding: 4px 0;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-raised);
		color: var(--text-secondary);
		font-size: 11px;
		cursor: pointer;
		transition: all var(--t-fast);
	}

	.fl-mode-chip.active {
		background: var(--accent-subtle);
		color: var(--accent);
		border-color: var(--accent);
	}

	/* ── 离线横幅 */
	.fl-offline {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 8px;
		margin-bottom: 6px;
		background: var(--warning-subtle);
		border-radius: var(--radius-sm);
		color: var(--warning);
		font-size: 12px;
	}

	.fl-offline-icon {
		width: 14px;
		height: 14px;
		flex-shrink: 0;
	}

	/* ── 虚拟列表 */
	.fl-scroller {
		flex: 1;
		min-height: 0;
	}

	/* ── 航班卡片 */
	.fl-card {
		display: flex;
		flex-direction: column;
		justify-content: center;
		gap: 4px;
		height: 64px;
		padding: 0 12px;
		border-bottom: 1px solid var(--border);
		cursor: pointer;
		transition: background var(--t-fast);
		box-sizing: border-box;
		overflow: hidden;
	}

	.fl-card:hover {
		background: var(--bg-raised);
	}

	.fl-card.selected {
		background: var(--accent-subtle);
		border-left: 2px solid var(--accent);
		padding-left: 10px;
	}

	.fl-card-row1 {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.fl-cs {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.fl-card-right {
		display: flex;
		align-items: center;
		gap: 6px;
	}

	.fl-logo {
		width: 20px;
		height: 20px;
		object-fit: contain;
		border-radius: 2px;
	}

	.fl-status {
		font-size: 10px;
		font-weight: 600;
		padding: 1px 6px;
		border-radius: 999px;
	}

	.st-air {
		background: var(--accent-subtle);
		color: var(--accent);
	}

	.st-gnd {
		background: var(--bg-raised);
		color: var(--text-muted);
	}

	.fl-card-row2 {
		display: flex;
		justify-content: space-between;
	}

	.fl-meta {
		font-size: 11px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}

	/* ── 空态 */
	.fl-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 8px;
		padding: 32px 16px;
		color: var(--text-muted);
		font-size: 13px;
	}

	.fl-empty-icon {
		width: 28px;
		height: 28px;
		opacity: 0.4;
	}
</style>
