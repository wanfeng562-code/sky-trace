<template>
	<aside
		:class="[
			'map-context',
			{ collapsed: !open, 'has-rail': !open && showRail },
		]"
		@transitionend="onTransitionEnd"
	>
		<div v-if="!open && showRail" class="mc-rail">
			<button
				class="mc-rail-btn"
				:title="UI.expandPanel"
				@click="emit('expand')"
			>
				<svg viewBox="0 0 20 20" fill="currentColor" class="mc-rail-icon">
					<path
						fill-rule="evenodd"
						d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<span v-if="railLabel" class="mc-rail-label" :title="railLabel">{{
				railLabel
			}}</span>
		</div>
		<template v-if="open">
			<div class="mc-header">
				<div class="mc-tabs">
					<button
						v-if="showDetailTab"
						:class="['mc-tab', { active: activeTab === 'detail' }]"
						@click="activeTab = 'detail'"
					>
						{{ UI.tabDetail }}
					</button>
					<button
						v-if="showScheduleTab"
						:class="['mc-tab', { active: activeTab === 'schedule' }]"
						@click="activeTab = 'schedule'"
					>
						{{ UI.tabSchedule }}
					</button>
				</div>
				<div class="mc-actions">
					<button
						class="mc-collapse"
						:title="UI.collapsePanel"
						@click="emit('collapse')"
					>
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
					<button
						class="mc-close"
						:title="UI.deselectFlight"
						@click="emit('close')"
					>
						<svg viewBox="0 0 20 20" fill="currentColor">
							<path
								fill-rule="evenodd"
								d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
				</div>
			</div>
			<div class="mc-body">
				<FlightDetailCard
					v-show="activeTab === 'detail'"
					:detail="detail"
					:loading="detailLoading"
				/>
				<SchedulePanel v-show="activeTab === 'schedule'" />
			</div>
		</template>
	</aside>
</template>

<script setup lang="ts">
	import FlightDetailCard from "../FlightDetailCard.vue";
	import SchedulePanel from "../SchedulePanel.vue";
	import type { FlightDetail } from "../../types/flight";

	const UI = {
		tabDetail: "\u8be6\u60c5",
		tabSchedule: "\u65f6\u523b",
		expandPanel: "\u5c55\u5f00\u8be6\u60c5\u680f",
		collapsePanel: "\u6536\u8d77\uff08\u4fdd\u6301\u9009\u4e2d\uff09",
		deselectFlight: "\u53d6\u6d88\u9009\u4e2d",
	} as const;

	defineProps<{
		open: boolean;
		showRail: boolean;
		railLabel?: string;
		showDetailTab: boolean;
		showScheduleTab: boolean;
		detail: FlightDetail | null;
		detailLoading: boolean;
	}>();

	const activeTab = defineModel<"detail" | "schedule">("activeTab", {
		default: "detail",
	});

	const emit = defineEmits<{
		collapse: [];
		expand: [];
		close: [];
		"layout-settled": [];
	}>();

	function onTransitionEnd(event: TransitionEvent) {
		if (event.propertyName === "width") {
			emit("layout-settled");
		}
	}
</script>

<style scoped>
	.map-context {
		width: var(--panel-w);
		flex-shrink: 0;
		display: flex;
		flex-direction: column;
		background: var(--bg-surface);
		border-left: 1px solid var(--border);
		transition: width var(--t-base);
		overflow: hidden;
	}

	.map-context.collapsed:not(.has-rail) {
		width: 0;
		border-left: none;
	}

	.map-context.collapsed.has-rail {
		width: 40px;
	}

	.mc-rail {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 8px 0;
		gap: 8px;
		height: 100%;
	}

	.mc-rail-btn {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
	}

	.mc-rail-btn:hover {
		background: var(--bg-elevated);
		color: var(--accent);
	}

	.mc-rail-icon {
		width: 18px;
		height: 18px;
	}

	.mc-rail-label {
		writing-mode: vertical-rl;
		text-orientation: mixed;
		font-size: 11px;
		font-weight: 600;
		color: var(--accent);
		letter-spacing: 0.04em;
		max-height: 120px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.mc-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		padding-right: 4px;
	}

	.mc-tabs {
		display: flex;
		padding: 0 4px;
	}

	.mc-tab {
		padding: 12px 16px;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text-secondary);
		font-size: 13px;
		font-weight: 500;
		cursor: pointer;
		margin-bottom: -1px;
	}

	.mc-tab.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
	}

	.mc-actions {
		display: flex;
		gap: 2px;
	}

	.mc-collapse,
	.mc-close {
		width: 32px;
		height: 32px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
	}

	.mc-collapse svg,
	.mc-close svg {
		width: 16px;
		height: 16px;
	}

	.mc-collapse:hover,
	.mc-close:hover {
		background: var(--bg-elevated);
		color: var(--text-primary);
	}

	.mc-body {
		flex: 1;
		min-height: 0;
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}
</style>
