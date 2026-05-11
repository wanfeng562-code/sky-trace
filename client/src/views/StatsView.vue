<template>
	<div class="stats-page">
		<div v-if="loading" class="loading-overlay">加载中...</div>

		<div v-else class="stats-body">
			<h2 class="stats-title">
				航班统计看板 <span class="refresh-hint">自动刷新 30s</span>
			</h2>
			<div class="summary-cards">
				<div class="card">
					<div class="card-value">{{ stats.total }}</div>
					<div class="card-label">总追踪航班</div>
				</div>
				<div class="card card-air">
					<div class="card-value">{{ stats.airborne_count }}</div>
					<div class="card-label">飞行中</div>
				</div>
				<div class="card card-ground">
					<div class="card-value">{{ stats.on_ground_count }}</div>
					<div class="card-label">在地面</div>
				</div>
				<div
					v-for="(cnt, src) in stats.by_source"
					:key="src"
					class="card card-source"
				>
					<div class="card-value">{{ cnt }}</div>
					<div class="card-label">{{ srcLabel(src) }}</div>
				</div>
			</div>

			<!-- 图表区域 -->
			<div class="charts-grid">
				<div class="chart-panel">
					<h3>飞行状态分布</h3>
					<div ref="statusChartEl" class="chart-canvas"></div>
				</div>
				<div class="chart-panel">
					<h3>高度分布</h3>
					<div ref="altChartEl" class="chart-canvas"></div>
				</div>
				<div class="chart-panel">
					<h3>速度分布</h3>
					<div ref="spdChartEl" class="chart-canvas"></div>
				</div>
				<div class="chart-panel chart-wide">
					<h3>前 20 航司前缀排行</h3>
					<div ref="prefixChartEl" class="chart-canvas chart-tall"></div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { onMounted, onUnmounted, ref } from "vue";
	import * as echarts from "echarts/core";
	import { BarChart, PieChart } from "echarts/charts";
	import {
		GridComponent,
		LegendComponent,
		TooltipComponent,
	} from "echarts/components";
	import { CanvasRenderer } from "echarts/renderers";
	import axios from "axios";

	echarts.use([
		BarChart,
		PieChart,
		GridComponent,
		TooltipComponent,
		LegendComponent,
		CanvasRenderer,
	]);

	const API = import.meta.env.VITE_API_BASE_URL as string;

	interface StatsData {
		total: number;
		on_ground_count: number;
		airborne_count: number;
		by_source: Record<string, number>;
		by_altitude_band: Record<string, number>;
		by_speed_band: Record<string, number>;
		top_callsign_prefixes: { prefix: string; count: number }[];
	}

	const loading = ref(true);
	const stats = ref<StatsData>({
		total: 0,
		on_ground_count: 0,
		airborne_count: 0,
		by_source: {},
		by_altitude_band: {},
		by_speed_band: {},
		top_callsign_prefixes: [],
	});

	const statusChartEl = ref<HTMLElement | null>(null);
	const altChartEl = ref<HTMLElement | null>(null);
	const spdChartEl = ref<HTMLElement | null>(null);
	const prefixChartEl = ref<HTMLElement | null>(null);

	let statusChart: echarts.ECharts | null = null;
	let altChart: echarts.ECharts | null = null;
	let spdChart: echarts.ECharts | null = null;
	let prefixChart: echarts.ECharts | null = null;
	let refreshTimer: ReturnType<typeof setTimeout> | null = null;

	const ALT_LABELS: Record<string, string> = {
		ground: "地面 ≤100ft",
		"low_<5k": "低空 <5000ft",
		"medium_5-25k": "中空 5000-25000ft",
		"high_>25k": "高空 >25000ft",
		unknown: "未知",
	};

	const SPD_LABELS: Record<string, string> = {
		"stationary_<30kts": "静止 <30kts",
		"slow_30-150kts": "低速 30-150kts",
		"cruise_150-400kts": "巡航 150-400kts",
		"fast_>400kts": "高速 >400kts",
		unknown: "未知",
	};

	function srcLabel(src: string) {
		const map: Record<string, string> = {
			opensky: "OpenSky",
			fr24: "FR24",
			mock: "Mock",
			other: "其他",
		};
		return map[src] ?? src;
	}

	async function loadStats() {
		try {
			const res = await axios.get(`${API}/flights/summary/stats`);
			stats.value = res.data.data;
			loading.value = false;
			renderCharts();
		} catch {
			// keep loading state, retry on next interval
		}
	}

	function renderCharts() {
		renderStatusChart();
		renderAltChart();
		renderSpdChart();
		renderPrefixChart();
	}

	function renderStatusChart() {
		if (!statusChartEl.value) return;
		if (!statusChart) statusChart = echarts.init(statusChartEl.value);
		statusChart.setOption({
			tooltip: { trigger: "item" },
			legend: {
				bottom: 0,
				itemWidth: 12,
				itemHeight: 12,
				textStyle: { fontSize: 11 },
			},
			series: [
				{
					type: "pie",
					radius: ["40%", "68%"],
					center: ["50%", "44%"],
					data: [
						{
							name: "飞行中",
							value: stats.value.airborne_count,
							itemStyle: { color: "#2563eb" },
						},
						{
							name: "在地面",
							value: stats.value.on_ground_count,
							itemStyle: { color: "#9ca3af" },
						},
					],
					label: { show: true, formatter: "{b}\n{d}%", fontSize: 11 },
				},
			],
		});
	}

	function renderAltChart() {
		if (!altChartEl.value) return;
		if (!altChart) altChart = echarts.init(altChartEl.value);
		const band = stats.value.by_altitude_band;
		const keys = ["ground", "low_<5k", "medium_5-25k", "high_>25k", "unknown"];
		altChart.setOption({
			tooltip: { trigger: "axis" },
			grid: { left: 10, right: 10, bottom: 30, top: 16, containLabel: true },
			xAxis: {
				type: "category",
				data: keys.map((k) => ALT_LABELS[k] ?? k),
				axisLabel: { fontSize: 10, rotate: 15 },
			},
			yAxis: { type: "value", axisLabel: { fontSize: 10 } },
			series: [
				{
					type: "bar",
					data: keys.map((k) => band[k] ?? 0),
					itemStyle: { color: "#0891b2" },
					barMaxWidth: 48,
				},
			],
		});
	}

	function renderSpdChart() {
		if (!spdChartEl.value) return;
		if (!spdChart) spdChart = echarts.init(spdChartEl.value);
		const band = stats.value.by_speed_band;
		const keys = [
			"stationary_<30kts",
			"slow_30-150kts",
			"cruise_150-400kts",
			"fast_>400kts",
			"unknown",
		];
		spdChart.setOption({
			tooltip: { trigger: "axis" },
			grid: { left: 10, right: 10, bottom: 30, top: 16, containLabel: true },
			xAxis: {
				type: "category",
				data: keys.map((k) => SPD_LABELS[k] ?? k),
				axisLabel: { fontSize: 10, rotate: 15 },
			},
			yAxis: { type: "value", axisLabel: { fontSize: 10 } },
			series: [
				{
					type: "bar",
					data: keys.map((k) => band[k] ?? 0),
					itemStyle: { color: "#7c3aed" },
					barMaxWidth: 48,
				},
			],
		});
	}

	function renderPrefixChart() {
		if (!prefixChartEl.value) return;
		if (!prefixChart) prefixChart = echarts.init(prefixChartEl.value);
		const top = stats.value.top_callsign_prefixes.slice(0, 20);
		prefixChart.setOption({
			tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
			grid: { left: 60, right: 20, bottom: 10, top: 10, containLabel: false },
			xAxis: { type: "value", axisLabel: { fontSize: 10 } },
			yAxis: {
				type: "category",
				data: top.map((p) => p.prefix).reverse(),
				axisLabel: { fontSize: 11 },
			},
			series: [
				{
					type: "bar",
					data: top.map((p) => p.count).reverse(),
					itemStyle: { color: "#f59e0b" },
					barMaxWidth: 20,
					label: { show: true, position: "right", fontSize: 10 },
				},
			],
		});
	}

	function onResize() {
		statusChart?.resize();
		altChart?.resize();
		spdChart?.resize();
		prefixChart?.resize();
	}

	onMounted(() => {
		loadStats();
		refreshTimer = setInterval(loadStats, 30_000);
		window.addEventListener("resize", onResize);
	});

	onUnmounted(() => {
		if (refreshTimer !== null) clearInterval(refreshTimer);
		window.removeEventListener("resize", onResize);
		statusChart?.dispose();
		altChart?.dispose();
		spdChart?.dispose();
		prefixChart?.dispose();
	});
</script>

<style scoped>
	.stats-page {
		height: 100%;
		background: #f5f7fb;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.stats-title {
		margin: 0 0 16px;
		font-size: 17px;
		color: #111827;
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.refresh-hint {
		font-size: 12px;
		color: #9ca3af;
		font-weight: 400;
	}

	.loading-overlay {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 18px;
		color: #6b7280;
	}

	.stats-body {
		flex: 1;
		padding: 20px 24px;
		overflow-y: auto;
	}

	.summary-cards {
		display: flex;
		gap: 12px;
		flex-wrap: wrap;
		margin-bottom: 20px;
	}

	.card {
		background: #ffffff;
		border-radius: 8px;
		padding: 16px 20px;
		min-width: 120px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
	}

	.card-value {
		font-size: 28px;
		font-weight: 700;
		color: #111827;
		line-height: 1;
	}

	.card-label {
		font-size: 12px;
		color: #6b7280;
		margin-top: 4px;
	}

	.card-air .card-value {
		color: #2563eb;
	}

	.card-ground .card-value {
		color: #6b7280;
	}

	.card-source .card-value {
		color: #0891b2;
	}

	.charts-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 16px;
	}

	.chart-panel {
		background: #ffffff;
		border-radius: 8px;
		padding: 16px;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
	}

	.chart-wide {
		grid-column: 1 / -1;
	}

	.chart-panel h3 {
		margin: 0 0 12px;
		font-size: 13px;
		color: #374151;
	}

	.chart-canvas {
		width: 100%;
		height: 220px;
	}

	.chart-tall {
		height: 340px;
	}

	@media (max-width: 900px) {
		.charts-grid {
			grid-template-columns: 1fr;
		}

		.chart-wide {
			grid-column: 1;
		}
	}
</style>
