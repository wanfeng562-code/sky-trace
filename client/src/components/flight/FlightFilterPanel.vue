<template>
	<div class="filter-panel">
		<div class="fp-head">
			<span class="fp-title">高级筛选</span>
			<button
				v-if="store.activeFilterCount"
				type="button"
				class="fp-clear"
				@click="store.resetAdvancedFilters()"
			>
				清除全部
			</button>
		</div>
		<p v-if="store.activeFilterCount" class="fp-summary">
			已启用 <strong>{{ store.activeFilterCount }}</strong> 项条件
		</p>

		<div class="fp-section">
			<div class="fp-section-label">飞行参数</div>
			<div class="fp-range-grid">
				<label class="fp-field">
					<span>高度 ft（最低）</span>
					<input
						v-model.number="store.filterAltMin"
						type="number"
						class="fp-input"
						placeholder="不限"
						min="0"
						step="500"
					/>
				</label>
				<label class="fp-field">
					<span>高度 ft（最高）</span>
					<input
						v-model.number="store.filterAltMax"
						type="number"
						class="fp-input"
						placeholder="不限"
						min="0"
						step="500"
					/>
				</label>
				<label class="fp-field">
					<span>航速 kts（最低）</span>
					<input
						v-model.number="store.filterSpeedMin"
						type="number"
						class="fp-input"
						placeholder="不限"
						min="0"
						step="10"
					/>
				</label>
				<label class="fp-field">
					<span>航速 kts（最高）</span>
					<input
						v-model.number="store.filterSpeedMax"
						type="number"
						class="fp-input"
						placeholder="不限"
						min="0"
						step="10"
					/>
				</label>
			</div>
			<div class="fp-preset-row">
				<button
					type="button"
					:class="['fp-preset', { active: isAltPresetActive(0, 100) }]"
					@click="store.applyAltitudePreset(0, 100)"
				>
					地面
				</button>
				<button
					type="button"
					:class="['fp-preset', { active: isAltPresetActive(1000, 25000) }]"
					@click="store.applyAltitudePreset(1000, 25000)"
				>
					巡航
				</button>
				<button
					type="button"
					:class="['fp-preset', { active: isAltPresetActive(25000, null) }]"
					@click="store.applyAltitudePreset(25000, null)"
				>
					高空
				</button>
			</div>
		</div>

		<div class="fp-section">
			<div class="fp-section-label">飞行类型与机型</div>
			<label class="fp-field fp-field-block">
				<span>飞行类型</span>
				<select v-model="store.filterFlightType" class="fp-select">
					<option
						v-for="opt in FLIGHT_TYPE_OPTIONS"
						:key="opt.value"
						:value="opt.value"
					>
						{{ opt.label }}
					</option>
				</select>
			</label>
			<label class="fp-field fp-field-block">
				<span>机型类别</span>
				<select
					class="fp-select"
					:value="aircraftCategorySelectValue"
					@change="onAircraftCategoryChange"
				>
					<option value="">全部机型</option>
					<option
						v-for="cat in AIRCRAFT_CATEGORY_OPTIONS"
						:key="cat.value"
						:value="String(cat.value)"
					>
						{{ cat.label }}
					</option>
				</select>
			</label>
		</div>

		<div class="fp-section">
			<div class="fp-section-label">地区（最多四级）</div>
			<div class="fp-geo-grid">
				<select
					class="fp-select"
					:value="store.filterCountry ?? ''"
					@change="onCountryChange"
				>
					<option value="">国家/地区</option>
					<option v-for="c in COUNTRIES" :key="c.code" :value="c.code">
						{{ c.nameZh }}
					</option>
				</select>
				<select
					v-if="store.filterCountry && provinces.length"
					class="fp-select"
					:value="store.filterRegion ?? ''"
					@change="onProvinceChange"
				>
					<option value="">{{ level2Label }}</option>
					<option v-for="r in provinces" :key="r.code" :value="r.code">
						{{ r.nameZh }}
					</option>
				</select>
				<select
					v-if="store.filterRegion && cities.length"
					class="fp-select"
					:value="store.filterCity ?? ''"
					@change="onCityChange"
				>
					<option value="">{{ level3Label }}</option>
					<option v-for="c in cities" :key="c.code" :value="c.code">
						{{ c.nameZh }}
					</option>
				</select>
				<select
					v-if="store.filterCity && districts.length"
					class="fp-select"
					:value="store.filterDistrict ?? ''"
					@change="onDistrictChange"
				>
					<option value="">{{ level4Label }}</option>
					<option v-for="d in districts" :key="d.code" :value="d.code">
						{{ d.nameZh }}
					</option>
				</select>
			</div>
			<div v-if="store.filterCountry" class="fp-mode-row">
				<button
					v-for="m in COUNTRY_MODES"
					:key="m.value"
					type="button"
					:class="['fp-mode-chip', { active: store.filterCountryMode === m.value }]"
					@click="store.filterCountryMode = m.value"
				>
					{{ m.label }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { computed } from "vue";
	import { COUNTRIES, type CountryFilterMode } from "../../data/countries";
	import {
		getCitiesForRegion,
		getCountryRegions,
		getDistrictsForCity,
	} from "../../data/geoHierarchy";
	import { useFlightStore } from "../../stores/flight";
	import {
		AIRCRAFT_CATEGORY_OPTIONS,
		FLIGHT_TYPE_OPTIONS,
	} from "../../utils/flightFilters";

	const COUNTRY_MODES: { label: string; value: CountryFilterMode }[] = [
		{ label: "领空", value: "airspace" },
		{ label: "出发", value: "departure" },
		{ label: "到达", value: "arrival" },
	];

	const store = useFlightStore();

	const aircraftCategorySelectValue = computed(() =>
		store.filterAircraftCategory == null
			? ""
			: String(store.filterAircraftCategory),
	);

	const provinces = computed(() =>
		store.filterCountry ? getCountryRegions(store.filterCountry) : [],
	);

	const cities = computed(() =>
		store.filterCountry && store.filterRegion
			? getCitiesForRegion(store.filterCountry, store.filterRegion)
			: [],
	);

	const districts = computed(() =>
		store.filterCountry && store.filterRegion && store.filterCity
			? getDistrictsForCity(
					store.filterCountry,
					store.filterRegion,
					store.filterCity,
				)
			: [],
	);

	const level2Label = computed(() => {
		if (store.filterCountry === "CN") return "全部省份";
		if (store.filterCountry === "US") return "全部州";
		return "全部地区";
	});

	const level3Label = computed(() =>
		store.filterCountry === "CN" ? "全部城市" : "全部城市/都会区",
	);

	const level4Label = computed(() =>
		store.filterCountry === "CN" ? "全部区县" : "全部细分区",
	);

	function onCountryChange(e: Event) {
		const v = (e.target as HTMLSelectElement).value;
		store.filterCountry = v || null;
	}

	function onProvinceChange(e: Event) {
		const v = (e.target as HTMLSelectElement).value;
		store.filterRegion = v || null;
	}

	function onCityChange(e: Event) {
		const v = (e.target as HTMLSelectElement).value;
		store.filterCity = v || null;
	}

	function onDistrictChange(e: Event) {
		const v = (e.target as HTMLSelectElement).value;
		store.filterDistrict = v || null;
	}

	function onAircraftCategoryChange(e: Event) {
		const v = (e.target as HTMLSelectElement).value;
		store.filterAircraftCategory = v === "" ? null : Number(v);
	}

	function isAltPresetActive(min: number, max: number | null): boolean {
		return store.filterAltMin === min && store.filterAltMax === max;
	}
</script>

<style scoped>
	.filter-panel {
		flex: 1;
		overflow-y: auto;
		padding: 12px 16px 16px;
	}

	.fp-head {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 8px;
	}

	.fp-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.fp-clear {
		border: none;
		background: none;
		color: var(--accent);
		font-size: 12px;
		cursor: pointer;
	}

	.fp-summary {
		font-size: 12px;
		color: var(--text-muted);
		margin: 0 0 12px;
	}

	.fp-summary strong {
		color: var(--accent);
	}

	.fp-hint {
		font-size: 11px;
		line-height: 1.45;
		color: var(--text-muted);
		margin: 8px 0 10px;
	}

	.fp-section {
		margin-bottom: 20px;
		padding-bottom: 20px;
		border-bottom: 1px solid var(--border);
	}

	.fp-section:last-child {
		border-bottom: none;
		padding-bottom: 0;
		margin-bottom: 0;
	}

	.fp-section-label {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-muted);
		margin-bottom: 8px;
	}

	.fp-range-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}

	.fp-field {
		display: flex;
		flex-direction: column;
		gap: 4px;
		font-size: 11px;
		color: var(--text-muted);
	}

	.fp-input,
	.fp-select {
		width: 100%;
		padding: 8px 10px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-surface);
		color: var(--text-primary);
		font-size: 13px;
		outline: none;
	}

	.fp-input:focus,
	.fp-select:focus {
		border-color: var(--accent);
	}

	.fp-field-block {
		margin-bottom: 8px;
	}

	.fp-field-block:last-child {
		margin-bottom: 0;
	}

	.fp-preset-row {
		display: grid;
		grid-template-columns: 1fr 1fr 1fr;
		gap: 8px;
		margin-top: 8px;
	}

	.fp-preset {
		width: 100%;
		padding: 8px 10px;
		border-radius: var(--radius-sm);
		border: 1px solid var(--border);
		background: var(--bg-elevated);
		font-size: 13px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.fp-preset:hover {
		border-color: var(--accent);
		color: var(--accent);
	}

	.fp-preset.active {
		background: var(--accent-subtle);
		border-color: var(--accent);
		color: var(--accent);
		font-weight: 600;
	}

	.fp-geo-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}

	.fp-mode-row {
		display: flex;
		gap: 6px;
		margin-top: 8px;
	}

	.fp-mode-chip {
		flex: 1;
		padding: 6px 0;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-surface);
		font-size: 12px;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.fp-mode-chip.active {
		border-color: var(--accent);
		color: var(--accent);
		background: var(--accent-subtle);
	}
</style>
