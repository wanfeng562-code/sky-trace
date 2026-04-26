<template>
	<table class="info-table">
		<tbody>
			<tr>
				<td>温度</td>
				<td>{{ weather.temp_c ?? "--" }} °C</td>
			</tr>
			<tr>
				<td>湿度</td>
				<td>{{ weather.humidity_pct ?? "--" }} %</td>
			</tr>
			<tr>
				<td>风速</td>
				<td>{{ weather.wind_speed_mps ?? "--" }} m/s</td>
			</tr>
			<tr v-if="weather.wind_deg != null">
				<td>风向</td>
				<td>{{ weather.wind_deg }}°</td>
			</tr>
			<tr>
				<td>能见度</td>
				<td>{{ weather.visibility_m ?? "--" }} m</td>
			</tr>
			<tr v-if="weather.description">
				<td>天气</td>
				<td>{{ weather.description }}</td>
			</tr>
		</tbody>
	</table>
</template>

<script setup lang="ts">
	import type { WeatherInfo } from "../types/flight";

	defineProps<{
		weather: WeatherInfo;
	}>();
</script>

<style scoped>
	.info-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 13px;
	}

	.info-table td {
		padding: 4px 0;
		vertical-align: top;
	}

	.info-table td:first-child {
		color: #6b7280;
		width: 80px;
	}
</style>
