<template>
	<!-- 无机场选中时的空态 -->
	<div v-if="!store.scheduleAirport" class="sp-empty">
		<svg
			viewBox="0 0 48 48"
			fill="none"
			stroke="currentColor"
			stroke-width="1.5"
			class="sp-empty-icon"
		>
			<rect x="8" y="10" width="32" height="32" rx="3" />
			<path d="M16 10V6M32 10V6M8 20h32" stroke-linecap="round" />
		</svg>
		<span>点击地图上的机场图标查看时刻表</span>
	</div>

	<!-- 时刻表内容 -->
	<div v-else class="sp-panel">
		<div class="sp-header">
			<div class="sp-title-wrap">
				<svg class="sp-title-icon" viewBox="0 0 20 20" fill="currentColor">
					<path
						fill-rule="evenodd"
						d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
						clip-rule="evenodd"
					/>
				</svg>
				<span class="sp-title">{{ store.scheduleAirport }}</span>
				<span class="sp-subtitle">时刻表</span>
			</div>
			<button class="sp-close" @click="close" title="关闭">
				<svg viewBox="0 0 16 16" fill="currentColor">
					<path
						d="M4.293 4.293a1 1 0 011.414 0L8 6.586l2.293-2.293a1 1 0 111.414 1.414L9.414 8l2.293 2.293a1 1 0 01-1.414 1.414L8 9.414l-2.293 2.293a1 1 0 01-1.414-1.414L6.586 8 4.293 5.707a1 1 0 010-1.414z"
					/>
				</svg>
			</button>
		</div>

		<div class="sp-dir-tabs">
			<button
				:class="['sp-tab', { active: direction === 'dep' }]"
				@click="switchDir('dep')"
			>
				<svg class="sp-tab-icon" viewBox="0 0 16 16" fill="currentColor">
					<path
						d="M2 5a1 1 0 011-1h10a1 1 0 010 2H3a1 1 0 01-1-1zm0 5a1 1 0 011-1h6a1 1 0 010 2H3a1 1 0 01-1-1z"
					/>
				</svg>
				离港
			</button>
			<button
				:class="['sp-tab', { active: direction === 'arr' }]"
				@click="switchDir('arr')"
			>
				<svg class="sp-tab-icon" viewBox="0 0 16 16" fill="currentColor">
					<path
						d="M2 5a1 1 0 011-1h6a1 1 0 010 2H3a1 1 0 01-1-1zm0 5a1 1 0 011-1h10a1 1 0 010 2H3a1 1 0 01-1-1z"
					/>
				</svg>
				到港
			</button>
		</div>

		<div v-if="store.scheduleLoading" class="sp-status">
			<div class="sp-spinner"></div>
			加载中...
		</div>
		<div v-else-if="!store.scheduleEntries.length" class="sp-status">
			暂无时刻数据
		</div>
		<div v-else class="sp-list">
			<div
				v-for="(entry, idx) in store.scheduleEntries.slice(0, 50)"
				:key="idx"
				class="sp-row"
			>
				<div class="sp-row-top">
					<span class="sp-flight">{{ entry.flight_iata ?? "--" }}</span>
					<span :class="['sp-status', statusClass(entry.status)]">{{
						entry.status ?? "计划"
					}}</span>
				</div>
				<div class="sp-row-route">
					<span class="sp-iata">{{ entry.dep_iata ?? "--" }}</span>
					<span class="sp-arrow">→</span>
					<span class="sp-iata">{{ entry.arr_iata ?? "--" }}</span>
				</div>
				<div class="sp-row-times">
					<span v-if="entry.dep_time" class="sp-time"
						>起 {{ entry.dep_time }}</span
					>
					<span v-if="entry.arr_time" class="sp-time"
						>落 {{ entry.arr_time }}</span
					>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { ref, watch } from "vue";
	import { useFlightStore } from "../stores/flight";

	const store = useFlightStore();
	const direction = ref<"dep" | "arr">("dep");

	function close() {
		store.scheduleAirport = null;
		store.scheduleEntries = [];
	}

	function switchDir(dir: "dep" | "arr") {
		direction.value = dir;
		if (store.scheduleAirport) {
			store.loadSchedules(store.scheduleAirport, dir);
		}
	}

	watch(
		() => store.scheduleAirport,
		(iata) => {
			if (iata) {
				direction.value = "dep";
				store.loadSchedules(iata, "dep");
			}
		},
	);

	function statusClass(status?: string): string {
		if (!status) return "";
		const s = status.toLowerCase();
		if (s.includes("land") || s.includes("arrived")) return "status-ok";
		if (s.includes("cancel")) return "status-cancel";
		if (s.includes("delay")) return "status-delay";
		return "";
	}
</script>

<style scoped>
	/* ── 空态 */
	.sp-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100%;
		gap: 12px;
		color: var(--text-muted);
		font-size: 13px;
		text-align: center;
		padding: 24px;
	}

	.sp-empty-icon {
		width: 48px;
		height: 48px;
		opacity: 0.3;
	}

	/* ── 时刻表面板 */
	.sp-panel {
		display: flex;
		flex-direction: column;
		height: 100%;
		background: var(--bg-surface);
		color: var(--text-primary);
	}

	/* ── Header */
	.sp-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 14px 8px;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.sp-title-wrap {
		display: flex;
		align-items: baseline;
		gap: 6px;
	}

	.sp-title-icon {
		width: 14px;
		height: 14px;
		color: var(--accent);
	}

	.sp-title {
		font-size: 16px;
		font-weight: 700;
		color: var(--text-primary);
	}

	.sp-subtitle {
		font-size: 12px;
		color: var(--text-muted);
	}

	.sp-close {
		width: 26px;
		height: 26px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
		cursor: pointer;
		padding: 0;
	}

	.sp-close svg {
		width: 11px;
		height: 11px;
	}

	.sp-close:hover {
		background: var(--danger-subtle);
		color: var(--danger);
	}

	/* ── Direction tabs */
	.sp-dir-tabs {
		display: flex;
		gap: 6px;
		padding: 8px 14px;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.sp-tab {
		display: flex;
		align-items: center;
		gap: 5px;
		flex: 1;
		justify-content: center;
		padding: 5px 8px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-raised);
		color: var(--text-secondary);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition: all var(--t-fast);
	}

	.sp-tab-icon {
		width: 12px;
		height: 12px;
	}

	.sp-tab.active {
		background: var(--accent-subtle);
		color: var(--accent);
		border-color: var(--accent);
	}

	/* ── Status */
	.sp-status {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 8px;
		color: var(--text-muted);
		font-size: 13px;
		padding: 20px;
		flex: 1;
	}

	.sp-spinner {
		width: 18px;
		height: 18px;
		border: 2px solid var(--border);
		border-top-color: var(--accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		flex-shrink: 0;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	/* ── List */
	.sp-list {
		flex: 1;
		overflow-y: auto;
		padding: 6px 0;
	}

	.sp-row {
		padding: 8px 14px;
		border-bottom: 1px solid var(--border);
		cursor: default;
		transition: background var(--t-fast);
	}

	.sp-row:hover {
		background: var(--bg-raised);
	}

	.sp-row-top {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 3px;
	}

	.sp-flight {
		font-weight: 600;
		font-size: 13px;
		color: var(--text-primary);
	}

	.sp-status {
		font-size: 11px;
		padding: 1px 7px;
		border-radius: var(--radius-sm);
		background: var(--bg-raised);
		color: var(--text-secondary);
	}

	.sp-status.status-ok {
		background: var(--success-subtle);
		color: var(--success);
	}

	.sp-status.status-cancel {
		background: var(--danger-subtle);
		color: var(--danger);
	}

	.sp-status.status-delay {
		background: var(--warning-subtle);
		color: var(--warning);
	}

	.sp-row-route {
		display: flex;
		align-items: center;
		gap: 6px;
		margin-bottom: 2px;
	}

	.sp-iata {
		font-size: 12px;
		font-weight: 600;
		color: var(--text-secondary);
	}

	.sp-arrow {
		color: var(--text-muted);
		font-size: 10px;
	}

	.sp-row-times {
		display: flex;
		gap: 10px;
	}

	.sp-time {
		font-size: 11px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}
</style>
