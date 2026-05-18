<template>
	<aside class="pb-flight-list">
		<div class="pb-fl-head">
			<div class="pb-fl-title-row">
				<h3 class="pb-fl-title">{{ t("playback.flightListTitle") }}</h3>
				<span class="pb-fl-badge">{{ filtered.length.toLocaleString() }}</span>
			</div>
			<p class="pb-fl-hint">{{ t("playback.flightListHint") }}</p>
			<label class="pb-fl-search-wrap">
				<svg class="pb-fl-search-icon" viewBox="0 0 20 20" fill="currentColor">
					<path
						fill-rule="evenodd"
						d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
						clip-rule="evenodd"
					/>
				</svg>
				<input
					v-model="keyword"
					type="search"
					class="pb-fl-search"
					:placeholder="t('playback.flightListSearch')"
				/>
			</label>
		</div>

		<div v-if="mode === 'single' && !selectedId" class="pb-fl-pick">
			{{ t("playback.pickFlightFirst") }}
		</div>

		<RecycleScroller
			class="pb-fl-scroller"
			:items="filtered"
			:item-size="72"
			key-field="id"
			v-slot="{ item: flight }"
		>
			<button
				type="button"
				:class="['pb-fl-card', { selected: flight.id === selectedId }]"
				@click="emit('select', flight.id)"
			>
				<div class="pb-fl-card-top">
					<span class="pb-fl-cs">{{ flight.callsign }}</span>
					<span v-if="flight.departure_airport || flight.arrival_airport" class="pb-fl-route">
						{{ flight.departure_airport || "?" }} → {{ flight.arrival_airport || "?" }}
					</span>
				</div>
				<div class="pb-fl-meta">
					<span>{{ fmtShort(flight.first_seen) }}</span>
					<span class="pb-fl-meta-sep">→</span>
					<span>{{ fmtShort(flight.last_seen) }}</span>
					<span class="pb-fl-meta-sep">·</span>
					<span>{{ flight.appear_frames }} {{ t("playback.framesWord") }}</span>
				</div>
			</button>
		</RecycleScroller>
	</aside>
</template>

<script setup lang="ts">
	import { computed, ref } from "vue";
	import { RecycleScroller } from "vue-virtual-scroller";
	import "vue-virtual-scroller/dist/vue-virtual-scroller.css";
	import { translate, useLocaleStore } from "../../i18n";
	import type { PlaybackCatalogFlight } from "../../utils/playbackCatalog";
	import { filterCatalog } from "../../utils/playbackCatalog";

	const props = defineProps<{
		flights: PlaybackCatalogFlight[];
		selectedId: string | null;
		mode: "global" | "single";
	}>();

	const emit = defineEmits<{
		select: [flightId: string];
	}>();

	const localeStore = useLocaleStore();
	const t = (path: string) => translate(localeStore.t, path);
	const keyword = ref("");

	const filtered = computed(() => filterCatalog(props.flights, keyword.value));

	function fmtShort(iso: string): string {
		if (!iso) return "--";
		const d = new Date(iso);
		const pad = (n: number) => String(n).padStart(2, "0");
		return `${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
	}
</script>

<style scoped>
	.pb-flight-list {
		position: absolute;
		top: 12px;
		left: 12px;
		bottom: 12px;
		width: min(300px, calc(100% - 24px));
		display: flex;
		flex-direction: column;
		background: color-mix(in srgb, var(--bg-surface) 94%, transparent);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-lg);
		z-index: 6;
		overflow: hidden;
		backdrop-filter: blur(8px);
	}

	.pb-fl-head {
		flex-shrink: 0;
		padding: 12px 12px 8px;
		border-bottom: 1px solid var(--border);
	}

	.pb-fl-title-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
	}

	.pb-fl-title {
		margin: 0;
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.pb-fl-badge {
		padding: 2px 8px;
		border-radius: 999px;
		background: var(--accent-subtle);
		color: var(--accent);
		font-size: 11px;
		font-variant-numeric: tabular-nums;
	}

	.pb-fl-hint {
		margin: 6px 0 10px;
		font-size: 11px;
		line-height: 1.45;
		color: var(--text-muted);
	}

	.pb-fl-search-wrap {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 0 8px;
		background: var(--bg-raised);
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
	}

	.pb-fl-search-icon {
		width: 14px;
		height: 14px;
		color: var(--text-muted);
		flex-shrink: 0;
	}

	.pb-fl-search {
		flex: 1;
		min-width: 0;
		border: none;
		background: transparent;
		color: var(--text-primary);
		font-size: 12px;
		padding: 6px 0;
		outline: none;
	}

	.pb-fl-pick {
		flex-shrink: 0;
		margin: 8px 12px 0;
		padding: 8px 10px;
		font-size: 11px;
		line-height: 1.45;
		color: var(--accent);
		background: var(--accent-subtle);
		border-radius: var(--radius-sm);
	}

	.pb-fl-scroller {
		flex: 1;
		min-height: 0;
		padding: 6px;
	}

	.pb-fl-card {
		display: block;
		width: 100%;
		margin-bottom: 6px;
		padding: 10px 10px;
		text-align: left;
		background: var(--bg-elevated);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		cursor: pointer;
		transition:
			border-color 0.15s,
			background 0.15s;
	}

	.pb-fl-card:hover {
		border-color: var(--accent);
	}

	.pb-fl-card.selected {
		border-color: var(--accent);
		background: var(--accent-subtle);
	}

	.pb-fl-card-top {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 8px;
		margin-bottom: 4px;
	}

	.pb-fl-cs {
		font-size: 13px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.pb-fl-route {
		font-size: 11px;
		color: var(--text-secondary);
		font-variant-numeric: tabular-nums;
	}

	.pb-fl-meta {
		font-size: 10px;
		color: var(--text-muted);
		font-variant-numeric: tabular-nums;
	}

	.pb-fl-meta-sep {
		margin: 0 3px;
		opacity: 0.6;
	}
</style>
