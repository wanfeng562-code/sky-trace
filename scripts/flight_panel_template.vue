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
			<button
				:class="['fl-filter-toggle', { active: showFilters }]"
				type="button"
				@click="showFilters = !showFilters"
			>
				筛选
				<span v-if="store.activeFilterCount" class="fl-filter-badge">{{
					store.activeFilterCount
				}}</span>
			</button>
		</div>

		<div class="fl-status-row">
			<button
				v-for="tab in STATUS_TABS"
				:key="tab.value"
				:class="['fl-pill', { active: store.filterStatus === tab.value }]"
				type="button"
				@click="store.filterStatus = tab.value"
			>
				{{ tab.label }}
			</button>
		</div>

		<div v-if="showFilters" class="fl-filter-panel">
			<div class="fl-filter-head">
				<span class="fl-filter-title">高级筛选</span>
				<button
					v-if="store.activeFilterCount"
					type="button"
					class="fl-clear"
					@click="store.resetAdvancedFilters()"
				>
					清除全部
				</button>
			</div>

			<div class="fl-section">
				<div class="fl-section-label">飞行参数</div>
				<div class="fl-range-grid">
					<label class="fl-field">
						<span>高度 ft（最低）</span>
						<input
							v-model.number="store.filterAltMin"
							type="number"
							class="fl-input"
							placeholder="不限"
							min="0"
							step="500"
						/>
					</label>
					<label class="fl-field">
						<span>高度 ft（最高）</span>
						<input
							v-model.number="store.filterAltMax"
							type="number"
							class="fl-input"
							placeholder="不限"
							min="0"
							step="500"
						/>
					</label>
					<label class="fl-field">
						<span>航速 kts（最低）</span>
						<input
							v-model.number="store.filterSpeedMin"
							type="number"
							class="fl-input"
							placeholder="不限"
							min="0"
							step="10"
						/>
					</label>
					<label class="fl-field">
						<span>航速 kts（最高）</span>
						<input
							v-model.number="store.filterSpeedMax"
							type="number"
							class="fl-input"
							placeholder="不限"
							min="0"
							step="10"
						/>
					</label>
				</div>
				<div class="fl-preset-row">
					<button type="button" class="fl-preset" @click="applyAltPreset(0, 100)">
						地面
					</button>
					<button
						type="button"
						class="fl-preset"
						@click="applyAltPreset(1000, 25000)"
					>
						巡航
					</button>
					<button
						type="button"
						class="fl-preset"
						@click="applyAltPreset(25000, null)"
					>
						高空
					</button>
				</div>
			</div>

			<div class="fl-section">
				<div class="fl-section-label">飞行类型与机型</div>
				<select v-model="store.filterFlightType" class="fl-select">
					<option
						v-for="opt in FLIGHT_TYPE_OPTIONS"
						:key="opt.value"
						:value="opt.value"
					>
						{{ opt.label }}
					</option>
				</select>
				<div class="fl-cat-chips">
					<button
						v-for="cat in AIRCRAFT_CATEGORY_OPTIONS"
						:key="cat.value"
						type="button"
						:class="[
							'fl-cat-chip',
							{ active: store.filterAircraftCategories.includes(cat.value) },
						]"
						@click="toggleCategory(cat.value)"
					>
						{{ cat.label }}
					</button>
				</div>
			</div>

			<div class="fl-section">
				<div class="fl-section-label">地区（最多四级）</div>
				<div class="fl-geo-grid">
					<select
						class="fl-select"
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
						class="fl-select"
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
						class="fl-select"
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
						class="fl-select"
						:value="store.filterDistrict ?? ''"
						@change="onDistrictChange"
					>
						<option value="">{{ level4Label }}</option>
						<option v-for="d in districts" :key="d.code" :value="d.code">
							{{ d.nameZh }}
						</option>
					</select>
				</div>
				<div v-if="store.filterCountry" class="fl-mode-row">
					<button
						v-for="m in COUNTRY_MODES"
						:key="m.value"
						type="button"
						:class="[
							'fl-mode-chip',
							{ active: store.filterCountryMode === m.value },
						]"
						@click="store.filterCountryMode = m.value"
					>
						{{ m.label }}
					</button>
				</div>
			</div>
		</div>

		<div v-if="!store.wsOnline" class="fl-offline">
			实时连接已断开，正在重连…
		</div>

		<div class="fl-list-head">
			<span>结果</span>
			<strong>{{ flights.length }}</strong>
			<span class="fl-list-hint">架</span>
		</div>

		<RecycleScroller
			class="fl-scroller"
			:items="flights"
			:item-size="72"
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
				<div class="fl-card-main">
					<span class="fl-cs">{{ flight.callsign || flight.flight_id }}</span>
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
