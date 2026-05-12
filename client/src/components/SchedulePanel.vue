<template>
	<aside v-if="store.scheduleAirport" class="schedule-panel">
		<div class="panel-header">
			<span class="panel-title">{{ store.scheduleAirport }} 时刻表</span>
			<button class="close-btn" @click="close">✕</button>
		</div>

		<div class="dir-tabs">
			<button
				:class="['tab-btn', { active: direction === 'dep' }]"
				@click="switchDir('dep')"
			>
				离港
			</button>
			<button
				:class="['tab-btn', { active: direction === 'arr' }]"
				@click="switchDir('arr')"
			>
				到港
			</button>
		</div>

		<div v-if="store.scheduleLoading" class="status-text">加载中...</div>
		<div v-else-if="!store.scheduleEntries.length" class="status-text">
			暂无时刻数据
		</div>
		<div v-else class="schedule-list">
			<div
				v-for="(entry, idx) in store.scheduleEntries.slice(0, 50)"
				:key="idx"
				class="schedule-row"
			>
				<div class="sched-main">
					<span class="sched-flight">{{ entry.flight_iata ?? "--" }}</span>
					<span :class="['sched-status', statusClass(entry.status)]">
						{{ entry.status ?? "计划" }}
					</span>
				</div>
				<div class="sched-route">
					<span>{{ entry.dep_iata ?? "--" }}</span>
					<span class="arrow">→</span>
					<span>{{ entry.arr_iata ?? "--" }}</span>
				</div>
				<div class="sched-times">
					<span v-if="entry.dep_time">起: {{ entry.dep_time }}</span>
					<span v-if="entry.arr_time">落: {{ entry.arr_time }}</span>
				</div>
			</div>
		</div>
	</aside>
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
	.schedule-panel {
		position: absolute;
		bottom: 24px;
		right: 24px;
		width: 300px;
		max-height: 55vh;
		background: #ffffff;
		border-radius: 8px;
		box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
		display: flex;
		flex-direction: column;
		z-index: 10;
		overflow: hidden;
	}

	.panel-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 10px 12px 6px;
		border-bottom: 1px solid #e5e7eb;
	}

	.panel-title {
		font-size: 14px;
		font-weight: 600;
	}

	.close-btn {
		background: none;
		border: none;
		cursor: pointer;
		font-size: 13px;
		color: #6b7280;
		padding: 0 2px;
	}

	.close-btn:hover {
		color: #111827;
	}

	.dir-tabs {
		display: flex;
		gap: 4px;
		padding: 6px 10px;
	}

	.tab-btn {
		flex: 1;
		padding: 4px 0;
		border: 1px solid #e5e7eb;
		border-radius: 4px;
		background: #f9fafb;
		font-size: 12px;
		cursor: pointer;
		transition: all 0.15s;
	}

	.tab-btn.active {
		background: #2563eb;
		color: #fff;
		border-color: #2563eb;
	}

	.status-text {
		text-align: center;
		color: #9ca3af;
		font-size: 13px;
		padding: 16px;
	}

	.schedule-list {
		overflow-y: auto;
		flex: 1;
		padding: 0 10px 8px;
	}

	.schedule-row {
		padding: 6px 0;
		border-bottom: 1px solid #f3f4f6;
		font-size: 12px;
	}

	.sched-main {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2px;
	}

	.sched-flight {
		font-weight: 600;
		font-size: 13px;
	}

	.sched-status {
		font-size: 11px;
		padding: 1px 6px;
		border-radius: 3px;
		background: #f3f4f6;
		color: #6b7280;
	}

	.sched-status.status-ok {
		background: #d1fae5;
		color: #065f46;
	}

	.sched-status.status-cancel {
		background: #fee2e2;
		color: #b91c1c;
	}

	.sched-status.status-delay {
		background: #fef3c7;
		color: #92400e;
	}

	.sched-route {
		color: #374151;
		margin-bottom: 2px;
	}

	.arrow {
		margin: 0 4px;
		color: #9ca3af;
	}

	.sched-times {
		color: #9ca3af;
		display: flex;
		gap: 8px;
	}
</style>
