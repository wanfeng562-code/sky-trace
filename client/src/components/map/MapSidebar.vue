<template>

	<aside

		:class="['map-sidebar', { collapsed }]"

		@transitionend="onTransitionEnd"

	>

		<div v-show="collapsed" class="ms-rail">

			<button

				v-for="t in tabs"

				:key="t.id"

				:class="['ms-rail-btn', { active: activeTab === t.id }]"

				:title="t.label"

				@click="expandTo(t.id)"

			>

				<component :is="t.icon" class="ms-rail-icon" />

				<span v-if="t.badge != null" class="ms-rail-badge">{{ t.badge }}</span>

			</button>

			<button class="ms-rail-btn ms-expand" title="展开侧栏" @click="collapsed = false">

				<svg viewBox="0 0 20 20" fill="currentColor" class="ms-rail-icon">

					<path

						fill-rule="evenodd"

						d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"

						clip-rule="evenodd"

					/>

				</svg>

			</button>

		</div>

		<div v-show="!collapsed" class="ms-panel">

			<div class="ms-header">

				<div class="ms-tabs">

					<button

						v-for="t in tabs"

						:key="t.id"

						:class="['ms-tab', { active: activeTab === t.id }]"

						:title="tabTitle(t)"

						@click="activeTab = t.id"

					>

						<span class="ms-tab-label">{{ t.label }}</span>

						<span v-if="t.badge != null" class="ms-badge">{{ formatTabBadge(t.badge) }}</span>

					</button>

				</div>

				<button class="ms-collapse" title="收起侧栏" @click="collapsed = true">

					<svg viewBox="0 0 20 20" fill="currentColor">

						<path

							fill-rule="evenodd"

							d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"

							clip-rule="evenodd"

						/>

					</svg>

				</button>

			</div>

			<div class="ms-body">

				<FlightListPanel

					v-show="activeTab === 'flights'"

					:flights="flights"

					:selected-flight-id="selectedFlightId"

					@select="(id) => emit('select-flight', id)"

				/>

				<FlightFilterPanel v-show="activeTab === 'filters'" />

				<HubAirportListPanel

					v-show="activeTab === 'hubs'"

					:airports="airports"

					:flights="allFlights"

					:selected-iata="selectedHubIata"

					@locate="(iata) => emit('hub-locate', iata)"

					@schedule="(iata) => emit('hub-schedule', iata)"

					@select-flight="(id) => emit('select-flight', id)"

					@clear="emit('hub-clear')"

				/>

				<MarkedFlightsPanel

					v-show="activeTab === 'marked'"

					:marked-flights="store.markedFlights"

					:selected-flight-id="selectedFlightId"

					@select="(id) => emit('select-flight', id)"

				/>

			</div>

		</div>

	</aside>

</template>



<script setup lang="ts">

	import { computed, h, onMounted, watch } from "vue";

	import FlightFilterPanel from "../flight/FlightFilterPanel.vue";

	import FlightListPanel from "../flight/FlightListPanel.vue";

	import HubAirportListPanel from "../HubAirportListPanel.vue";
	import MarkedFlightsPanel from "../flight/MarkedFlightsPanel.vue";
	import { translate, useLocaleStore } from "../../i18n";

	import { useFlightStore } from "../../stores/flight";

	import type { AirportInfo, FlightBrief } from "../../types/flight";



	const SIDEBAR_KEY = "map.sidebar.collapsed";



	const props = defineProps<{

		flights: FlightBrief[];

		allFlights: FlightBrief[];

		airports: AirportInfo[];

		selectedFlightId?: string | null;

		selectedHubIata?: string | null;

		hubCount: number;

	}>();



	const emit = defineEmits<{

		"select-flight": [flightId: string];

		"hub-locate": [iata: string];

		"hub-schedule": [iata: string];

		"hub-clear": [];

		collapse: [collapsed: boolean];

		"layout-settled": [];

	}>();



	const store = useFlightStore();



	const collapsed = defineModel<boolean>("collapsed", { default: false });

	const activeTab = defineModel<"flights" | "filters" | "hubs" | "marked">(
		"activeTab",
		{
			default: "flights",
		},
	);

	const localeStore = useLocaleStore();



	const tabs = computed(() => [

		{

			id: "flights" as const,

			label: translate(localeStore.t, "sidebar.flights"),

			badge: props.allFlights.length,

			icon: FlightsIcon,

		},

		{

			id: "filters" as const,

			label: translate(localeStore.t, "sidebar.filters"),

			badge: store.activeFilterCount || null,

			icon: FilterIcon,

		},

		{

			id: "hubs" as const,

			label: translate(localeStore.t, "sidebar.hubs"),

			badge: props.hubCount,

			icon: HubIcon,

		},

		{

			id: "marked" as const,

			label: translate(localeStore.t, "marked.tab"),

			badge: store.markedFlights.length || null,

			icon: MarkedIcon,

		},

	]);



	function formatTabBadge(n: number): string {

		if (n >= 10_000) return `${Math.round(n / 1000)}k`;

		if (n >= 1000) {

			const k = n / 1000;

			return k % 1 === 0 ? `${k}k` : `${k.toFixed(1).replace(/\.0$/, "")}k`;

		}

		return String(n);

	}



	function tabTitle(t: (typeof tabs.value)[number]): string {

		if (t.badge == null) return t.label;

		const raw = t.badge.toLocaleString();

		const shown = formatTabBadge(t.badge);

		return shown === raw ? t.label : `${t.label} (${raw})`;

	}



	function expandTo(tab: "flights" | "filters" | "hubs" | "marked") {

		activeTab.value = tab;

		collapsed.value = false;

	}



	function onTransitionEnd(event: TransitionEvent) {

		if (event.propertyName !== "width") return;

		emit("layout-settled");

	}



	onMounted(() => {

		const saved = localStorage.getItem(SIDEBAR_KEY);

		if (saved === "1") collapsed.value = true;

	});



	watch(collapsed, (v) => {

		localStorage.setItem(SIDEBAR_KEY, v ? "1" : "0");

		emit("collapse", v);

	});



	const FlightsIcon = {

		render: () =>

			h("svg", { viewBox: "0 0 20 20", fill: "currentColor" }, [

				h("path", {

					d: "M10.894 2.553a1 1 0 00-1.788 0l-7 14a1 1 0 001.169 1.409l5-1.429A1 1 0 009 15.571V11a1 1 0 112 0v4.571a1 1 0 00.725.962l5 1.428a1 1 0 001.17-1.408l-7-14z",

				}),

			]),

	};



	const FilterIcon = {

		render: () =>

			h("svg", { viewBox: "0 0 20 20", fill: "currentColor" }, [

				h("path", {

					"fill-rule": "evenodd",

					d: "M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.29.684l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z",

					"clip-rule": "evenodd",

				}),

			]),

	};



	const HubIcon = {

		render: () =>

			h("svg", { viewBox: "0 0 20 20", fill: "currentColor" }, [

				h("path", {

					d: "M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z",

				}),

			]),

	};

	const MarkedIcon = {
		render: () =>
			h("svg", { viewBox: "0 0 20 20", fill: "currentColor" }, [
				h("path", {
					d: "M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z",
				}),
			]),
	};

</script>



<style scoped>

	.map-sidebar {

		width: var(--sidebar-w);

		flex-shrink: 0;

		display: flex;

		flex-direction: column;

		background: var(--bg-surface);

		border-right: 1px solid var(--border);

		transition: width var(--t-sidebar);

		overflow: hidden;

		contain: layout style;

		will-change: width;

	}



	.map-sidebar.collapsed {

		width: var(--sidebar-collapsed-w);

	}



	.ms-rail,

	.ms-panel {

		display: flex;

		flex-direction: column;

		height: 100%;

		min-height: 0;

	}



	.ms-rail {

		align-items: center;

		padding: 8px 0;

		gap: 4px;

	}



	.ms-rail-btn {

		position: relative;

		width: 36px;

		height: 36px;

		display: flex;

		align-items: center;

		justify-content: center;

		border: none;

		border-radius: var(--radius-md);

		background: transparent;

		color: var(--text-secondary);

		cursor: pointer;

	}



	.ms-rail-btn:hover,

	.ms-rail-btn.active {

		background: var(--accent-subtle);

		color: var(--accent);

	}



	.ms-rail-icon {

		width: 18px;

		height: 18px;

	}



	.ms-rail-badge {

		position: absolute;

		top: 2px;

		right: 2px;

		min-width: 14px;

		height: 14px;

		padding: 0 3px;

		border-radius: 999px;

		background: var(--accent);

		color: #fff;

		font-size: 9px;

		line-height: 14px;

		text-align: center;

	}



	.ms-expand {

		margin-top: auto;

	}



	.ms-header {

		display: flex;

		align-items: center;

		border-bottom: 1px solid var(--border);

		flex-shrink: 0;

	}



	.ms-tabs {

		display: flex;

		flex: 1;

		min-width: 0;

		flex-wrap: nowrap;

		padding: 0 2px;

	}



	.ms-tab {

		flex: 1;

		min-width: 0;

		display: inline-flex;

		align-items: center;

		justify-content: center;

		gap: 4px;

		padding: 10px 4px;

		background: none;

		border: none;

		border-bottom: 2px solid transparent;

		color: var(--text-secondary);

		font-size: 12px;

		font-weight: 500;

		cursor: pointer;

		margin-bottom: -1px;

		white-space: nowrap;

	}



	.ms-tab-label {

		overflow: hidden;

		text-overflow: ellipsis;

		min-width: 0;

	}



	.ms-tab:hover {

		color: var(--text-primary);

	}



	.ms-tab.active {

		color: var(--accent);

		border-bottom-color: var(--accent);

	}



	.ms-badge {

		flex-shrink: 0;

		padding: 0 5px;

		border-radius: 999px;

		background: var(--bg-elevated);

		font-size: 10px;

		font-variant-numeric: tabular-nums;

		line-height: 16px;

		color: var(--text-muted);

	}



	.ms-tab.active .ms-badge {

		background: var(--accent-subtle);

		color: var(--accent);

	}



	.ms-collapse {

		width: 36px;

		height: 36px;

		margin-right: 8px;

		display: flex;

		align-items: center;

		justify-content: center;

		border: none;

		border-radius: var(--radius-sm);

		background: transparent;

		color: var(--text-muted);

		cursor: pointer;

		flex-shrink: 0;

	}



	.ms-collapse svg {

		width: 16px;

		height: 16px;

	}



	.ms-collapse:hover {

		background: var(--bg-elevated);

		color: var(--text-primary);

	}



	.ms-body {

		flex: 1;

		min-height: 0;

		display: flex;

		flex-direction: column;

		overflow: hidden;

		contain: strict;

	}

</style>

