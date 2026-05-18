<template>
	<div class="stats-page">
		<div v-if="loading" class="stats-loading">
			<div class="stats-spinner"></div>
			<span>{{ t("stats.loading") }}</span>
		</div>

		<div v-else class="stats-body">
			<!-- KPI 英雄行 -->
			<div class="kpi-row">
				<div class="kpi-card">
					<div class="kpi-icon kpi-total">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M10 2a8 8 0 100 16A8 8 0 0010 2zm1 11H9v-4h2v4zm0-6H9V5h2v2z"
							/>
						</svg>
					</div>
					<div class="kpi-main">
						<div class="kpi-num">{{ stats.total }}</div>
						<div class="kpi-label">{{ t("stats.kpiTotal") }}</div>
					</div>
				</div>
				<div class="kpi-card kpi-airborne">
					<div class="kpi-icon">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								d="M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z"
							/>
						</svg>
					</div>
					<div class="kpi-main">
						<div class="kpi-num">{{ stats.airborne_count }}</div>
						<div class="kpi-label">{{ t("stats.kpiAirborne") }}</div>
						<div class="kpi-pct" v-if="stats.total > 0">
							{{ ((stats.airborne_count / stats.total) * 100).toFixed(1) }}%
						</div>
					</div>
				</div>
				<div class="kpi-card kpi-ground">
					<div class="kpi-icon">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M5 2a2 2 0 00-2 2v14l3.5-2 3.5 2 3.5-2 3.5 2V4a2 2 0 00-2-2H5zm4.707 3.707a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L8.414 9H11a1 1 0 000-2H8.414l1.293-1.293z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class="kpi-main">
						<div class="kpi-num">{{ stats.on_ground_count }}</div>
						<div class="kpi-label">{{ t("stats.kpiGround") }}</div>
						<div class="kpi-pct" v-if="stats.total > 0">
							{{ ((stats.on_ground_count / stats.total) * 100).toFixed(1) }}%
						</div>
					</div>
				</div>
				<div
					v-for="(cnt, src) in stats.by_source"
					:key="src"
					class="kpi-card kpi-source"
				>
					<div class="kpi-icon">
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<div class="kpi-main">
						<div class="kpi-num">{{ cnt }}</div>
						<div class="kpi-label">{{ srcLabel(src) }}</div>
					</div>
				</div>
			</div>

			<!-- 图表区域 -->
			<div class="charts-grid">
				<div class="chart-panel">
					<div class="chart-title">{{ t("stats.chartStatus") }}</div>
					<div ref="statusChartEl" class="chart-canvas"></div>
				</div>
				<div class="chart-panel">
					<div class="chart-title">{{ t("stats.chartAlt") }}</div>
					<div ref="altChartEl" class="chart-canvas"></div>
				</div>
				<div class="chart-panel">
					<div class="chart-title">{{ t("stats.chartSpd") }}</div>
					<div ref="spdChartEl" class="chart-canvas"></div>
				</div>
				<div class="chart-panel chart-wide">
					<div class="chart-title">
						{{ t("stats.chartPrefixTitle") }}
					</div>
					<p class="chart-subtitle">
						{{ t("stats.chartPrefixSub") }}
					</p>
					<div ref="prefixChartEl" class="chart-canvas chart-tall"></div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { nextTick, onMounted, onUnmounted, ref, watch } from "vue";
	import * as echarts from "echarts/core";
	import { BarChart, PieChart } from "echarts/charts";
	import {
		GridComponent,
		LegendComponent,
		TooltipComponent,
	} from "echarts/components";
	import { CanvasRenderer } from "echarts/renderers";
	import { fetchFlightStats } from "../services/api";
	import { translate, useLocaleStore } from "../i18n";
	import { useFlightStore } from "../stores/flight";

	echarts.use([
		BarChart,
		PieChart,
		GridComponent,
		TooltipComponent,
		LegendComponent,
		CanvasRenderer,
	]);

	const store = useFlightStore();
	const localeStore = useLocaleStore();
	const t = (path: string) => translate(localeStore.t, path);

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
	let refreshTimer: ReturnType<typeof setInterval> | null = null;
	let statsLoading = false;

	function srcLabel(src: string) {
		const map: Record<string, string> = {
			opensky: "OpenSky",
			fr24: "FR24",
			mock: "Mock",
			other: t("stats.srcOther"),
		};
		return map[src] ?? src;
	}
	const CHART_AXIS = { color: "#94a3b8", fontSize: 11 };
	const CHART_LINE = { lineStyle: { color: "#475569" } };
	const CHART_SPLIT = { lineStyle: { color: "rgba(148, 163, 184, 0.12)" } };

	function valueAxisOpts() {
		return {
			axisLabel: CHART_AXIS,
			axisLine: CHART_LINE,
			splitLine: CHART_SPLIT,
		};
	}

	function categoryAxisOpts() {
		return {
			axisLabel: CHART_AXIS,
			axisLine: CHART_LINE,
			splitLine: { show: false },
		};
	}

	function bandLabel(key: string): string {
		return translate(localeStore.t, `stats.bands.${key}` as never);
	}

	async function loadStats() {
		if (statsLoading) return;
		statsLoading = true;
		try {
			stats.value = await fetchFlightStats();
			loading.value = false;
			// nextTick ensures v-else chart containers are in the DOM before echarts.init
			await nextTick();
			renderCharts();
		} catch {
			// keep loading state, retry on next interval
		} finally {
			statsLoading = false;
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
			backgroundColor: "transparent",
			tooltip: { trigger: "item" },
			legend: {
				bottom: 0,
				itemWidth: 12,
				itemHeight: 12,
				textStyle: { fontSize: 11, color: "#cbd5e1" },
			},
			series: [
				{
					type: "pie",
					radius: ["40%", "68%"],
					center: ["50%", "44%"],
					data: [
						{
							name: t("stats.pieAirborne"),
							value: stats.value.airborne_count,
							itemStyle: { color: "#2563eb" },
						},
						{
							name: t("stats.pieGround"),
							value: stats.value.on_ground_count,
							itemStyle: { color: "#9ca3af" },
						},
					],
					label: {
						show: true,
						formatter: "{b}\n{d}%",
						fontSize: 11,
						color: "#e2e8f0",
					},
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
			backgroundColor: "transparent",
			tooltip: { trigger: "axis" },
			grid: { left: 10, right: 10, bottom: 30, top: 16, containLabel: true },
			xAxis: {
				type: "category",
				data: keys.map((k) => bandLabel(k)),
				axisLabel: { ...CHART_AXIS, rotate: 20 },
				axisLine: CHART_LINE,
			},
			yAxis: {
				type: "value",
				name: t("stats.axisCount"),
				nameLocation: "middle",
				nameGap: 36,
				...valueAxisOpts(),
			},
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
			backgroundColor: "transparent",
			tooltip: { trigger: "axis" },
			grid: { left: 10, right: 10, bottom: 30, top: 16, containLabel: true },
			xAxis: {
				type: "category",
				data: keys.map((k) => bandLabel(k)),
				axisLabel: { ...CHART_AXIS, rotate: 20 },
				axisLine: CHART_LINE,
			},
			yAxis: {
				type: "value",
				name: t("stats.axisCount"),
				nameLocation: "middle",
				nameGap: 36,
				...valueAxisOpts(),
			},
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
			backgroundColor: "transparent",
			tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
			grid: {
				left: 8,
				right: 72,
				bottom: 24,
				top: 8,
				containLabel: true,
			},
			xAxis: {
				type: "value",
				name: t("stats.axisCount"),
				nameLocation: "middle",
				nameGap: 28,
				...valueAxisOpts(),
				axisLabel: {
					...CHART_AXIS,
					margin: 10,
					formatter: (v: number) =>
						Number(v) >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v),
				},
			},
			yAxis: {
				type: "category",
				name: t("stats.prefixAxis"),
				nameLocation: "middle",
				nameGap: 42,
				data: top.map((p) => p.prefix).reverse(),
				...categoryAxisOpts(),
				axisLabel: {
					...CHART_AXIS,
					width: 72,
					overflow: "none",
					interval: 0,
				},
			},
			series: [
				{
					type: "bar",
					data: top.map((p) => p.count).reverse(),
					itemStyle: { color: "#f59e0b" },
					barMaxWidth: 14,
					barCategoryGap: "30%",
					label: {
						show: true,
						position: "right",
						fontSize: 11,
						color: "#e2e8f0",
					},
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

	let statsFlightTimer: ReturnType<typeof setTimeout> | null = null;
	// WS 推送时节流刷新统计，避免高频 setData 触发重复请求
	watch(
		() => store.flights.length,
		() => {
			if (statsFlightTimer !== null) clearTimeout(statsFlightTimer);
			statsFlightTimer = setTimeout(() => {
				statsFlightTimer = null;
				void loadStats();
			}, 4000);
		},
	);

	watch(
		() => localeStore.locale,
		() => {
			if (!loading.value) renderCharts();
		},
	);

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
		background: var(--bg-base);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.stats-loading {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 10px;
		color: var(--text-secondary);
		font-size: 14px;
	}

	.stats-spinner {
		width: 20px;
		height: 20px;
		border-radius: 50%;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.stats-body {
		flex: 1;
		padding: 24px;
		overflow-y: auto;
		max-width: 1280px;
		margin: 0 auto;
		width: 100%;
		box-sizing: border-box;
	}

	/* ── KPI 英雄行 */
	.kpi-row {
		display: flex;
		gap: 24px;
		flex-wrap: wrap;
		margin-bottom: 24px;
	}

	.kpi-card {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 14px 18px;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		min-width: 140px;
		flex: 1;
	}

	.kpi-icon {
		width: 36px;
		height: 36px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-md);
		background: var(--bg-raised);
		color: var(--text-muted);
		flex-shrink: 0;
	}

	.kpi-icon svg {
		width: 18px;
		height: 18px;
	}

	.kpi-total .kpi-icon {
		background: var(--accent-subtle);
		color: var(--accent);
	}
	.kpi-airborne .kpi-icon {
		background: var(--success-subtle);
		color: var(--success);
	}
	.kpi-ground .kpi-icon {
		background: rgba(148, 163, 184, 0.15);
		color: var(--text-secondary);
	}
	.kpi-source .kpi-icon {
		background: rgba(14, 165, 233, 0.15);
		color: #0ea5e9;
	}

	.kpi-main {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.kpi-num {
		font-size: 26px;
		font-weight: 700;
		color: var(--text-primary);
		line-height: 1;
		font-variant-numeric: tabular-nums;
	}

	.kpi-airborne .kpi-num {
		color: var(--success);
	}
	.kpi-source .kpi-num {
		color: #0ea5e9;
	}

	.kpi-label {
		font-size: 12px;
		color: var(--text-muted);
	}

	.kpi-pct {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	/* ── 图表区域 */
	.charts-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 24px;
	}

	.chart-panel {
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: 14px 16px;
	}

	.chart-wide {
		grid-column: 1 / -1;
	}

	.chart-title {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-secondary);
		margin-bottom: 10px;
	}

	.chart-canvas {
		width: 100%;
		height: 220px;
	}

	.chart-subtitle {
		font-size: 11px;
		color: var(--text-muted);
		margin: -6px 0 10px;
	}

	.chart-tall {
		height: 560px;
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
