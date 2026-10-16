<template>
	<div class="wx-grid">
		<div class="wx-item">
			<span class="wx-val">{{ weather.temp_c ?? "--" }}</span>
			<span class="wx-unit">°C</span>
			<span class="wx-key">{{ ui.temperature }}</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{ weather.humidity_pct ?? "--" }}</span>
			<span class="wx-unit">%</span>
			<span class="wx-key">{{ ui.humidity }}</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{ weather.wind_speed_mps ?? "--" }}</span>
			<span class="wx-unit">m/s</span>
			<span class="wx-key">{{ ui.windSpeed }}</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{
				weather.wind_deg != null ? weather.wind_deg + "°" : "--"
			}}</span>
			<span class="wx-unit"></span>
			<span class="wx-key">{{ ui.windDirection }}</span>
		</div>
		<div class="wx-item">
			<span class="wx-val">{{
				weather.visibility_m != null
					? (weather.visibility_m / 1000).toFixed(1)
					: "--"
			}}</span>
			<span class="wx-unit">km</span>
			<span class="wx-key">{{ ui.visibility }}</span>
		</div>
		<div v-if="descriptionText" class="wx-item wx-desc">
			<span class="wx-val wx-val-sm">{{ descriptionText }}</span>
			<span class="wx-key">{{ ui.weather }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { useBusinessLocale } from "../i18n/useBusinessLocale";
	const { ui } = useBusinessLocale();
	import { computed } from "vue";
	import { useLocaleStore } from "../i18n";
	import type { WeatherInfo } from "../types/flight";
	import { formatWeatherDescription } from "../utils/flightDetailLocale";

	const props = defineProps<{
		weather: WeatherInfo;
	}>();

	const localeStore = useLocaleStore();

	const descriptionText = computed(() =>
		formatWeatherDescription(props.weather.description, localeStore.locale),
	);
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
