<template>
	<div class="wx-grid">
		<div class="wx-item">
			<span class="wx-val">{{ weather.temp_c ?? "--" }}</span>
			<span class="wx-unit">°C</span>
			<span class="wx-key">温度</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{ weather.humidity_pct ?? "--" }}</span>
			<span class="wx-unit">%</span>
			<span class="wx-key">湿度</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{ weather.wind_speed_mps ?? "--" }}</span>
			<span class="wx-unit">m/s</span>
			<span class="wx-key">风速</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{
				weather.wind_deg != null ? weather.wind_deg + "°" : "--"
			}}</span>
			<span class="wx-unit"></span>
			<span class="wx-key">风向</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{
				weather.visibility_m != null
					? (weather.visibility_m / 1000).toFixed(1)
					: "--"
			}}</span>
			<span class="wx-unit">km</span>
			<span class="wx-key">能见度</span>
		</div>
		<div v-if="weather.description" class="wx-item wx-desc">
			<span class="wx-val wx-val-sm">{{ weather.description }}</span>
			<span class="wx-key">天气</span>
		</div>
	</div>
</template>

<script setup lang="ts">
	import type { WeatherInfo } from "../types/flight";

	defineProps<{
		weather: WeatherInfo;
	}>();
</script>

<style scoped>
	.wx-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 6px;
		padding: 8px 0;
	}

	.wx-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 2px;
		background: var(--bg-raised, #263349);
		border-radius: var(--radius-sm, 4px);
		padding: 6px 4px;
	}

	.wx-val {
		font-size: 16px;
		font-weight: 700;
		color: var(--text-primary, #e2e8f0);
		line-height: 1;
		font-variant-numeric: tabular-nums;
	}

	.wx-val-sm {
		font-size: 11px;
		text-align: center;
	}

	.wx-unit {
		font-size: 10px;
		color: var(--text-muted, #64748b);
		line-height: 1;
	}

	.wx-key {
		font-size: 10px;
		color: var(--text-secondary, #94a3b8);
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	.wx-desc {
		grid-column: 1 / -1;
	}
</style>
