<template>
	<div class="map-console">
		<div class="console-row">
			<button
				type="button"
				class="console-btn"
				:class="{ active: layersOpen }"
				:title="ui.layersTitle"
				@click="emit('update:layersOpen', !layersOpen)"
			>
				<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
					<path
						d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"
					/>
				</svg>
				<span>{{ ui.layers }}</span>
			</button>
			<button
				type="button"
				class="console-btn"
				:class="{ active: basemapOpen }"
				:title="ui.basemapTitle"
				@click="emit('update:basemapOpen', !basemapOpen)"
			>
				<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
					<path
						fill-rule="evenodd"
						d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm3 2h6v4H7V5zm8 8v2h2v-2h-2zm-2-2H7v4h6v-4zm2 2v2H9v-2h4z"
						clip-rule="evenodd"
					/>
				</svg>
				<span>{{ ui.basemap }}</span>
			</button>
			<button
				type="button"
				class="console-btn icon-only"
				:title="ui.myLocation"
				@click="emit('geolocate')"
			>
				<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
					<path
						d="M10 2a1 1 0 011 1v1.07A6 6 0 0116.93 9H18a1 1 0 110 2h-1.07A6 6 0 0111 15.93V17a1 1 0 11-2 0v-1.07A6 6 0 014.07 11H3a1 1 0 110-2h1.07A6 6 0 019 4.07V3a1 1 0 011-1zm0 4a4 4 0 100 8 4 4 0 000-8z"
					/>
				</svg>
			</button>
		</div>
		<div class="console-zoom">
			<button type="button" class="console-zoom-btn" :title="ui.zoomIn" @click="emit('zoom-in')">
				<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
					<path
						fill-rule="evenodd"
						d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<div class="console-zoom-divider" />
			<button type="button" class="console-zoom-btn" :title="ui.zoomOut" @click="emit('zoom-out')">
				<svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
					<path
						fill-rule="evenodd"
						d="M4 10a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<div class="console-zoom-divider" />
			<button
				ref="compassBtn"
				type="button"
				class="console-zoom-btn console-compass"
				:title="ui.compass"
			>
				<span
					class="console-compass-dial"
					:style="{ transform: `rotate(${mapBearing}deg)` }"
					aria-hidden="true"
				>
					<svg viewBox="0 0 29 29" fill="currentColor">
						<path d="m10.5 14 4-8 4 8z" class="compass-north" />
						<path d="m10.5 16 4 8 4-8z" class="compass-south" />
					</svg>
				</span>
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
	import { computed, onBeforeUnmount, ref, watch } from "vue";
	import type { Map as MapLibreMap } from "maplibre-gl";
	import { translate, useLocaleStore } from "../../i18n";
	import { attachCompassRotateControl } from "../../utils/mapCompassControl";

	const localeStore = useLocaleStore();
	const ui = computed(() => {
		const d = localeStore.t;
		return {
			layers: translate(d, "mapControls.layers"),
			layersTitle: translate(d, "mapLayers.title"),
			basemap: translate(d, "mapControls.basemap"),
			basemapTitle: translate(d, "basemap.title"),
			myLocation: translate(d, "mapControls.myLocation"),
			zoomIn: translate(d, "mapControls.zoomIn"),
			zoomOut: translate(d, "mapControls.zoomOut"),
			compass: translate(d, "mapControls.compass"),
		};
	});

	const props = withDefaults(
		defineProps<{
			layersOpen: boolean;
			basemapOpen: boolean;
			mapBearing?: number;
			map?: MapLibreMap | null;
		}>(),
		{ mapBearing: 0, map: null },
	);

	const compassBtn = ref<HTMLButtonElement | null>(null);
	let detachCompass: (() => void) | null = null;

	watch(
		[() => props.map, compassBtn],
		() => {
			detachCompass?.();
			detachCompass = null;
			if (props.map && compassBtn.value) {
				detachCompass = attachCompassRotateControl(
					props.map,
					compassBtn.value,
					() => emit("reset-bearing"),
				);
			}
		},
		{ immediate: true },
	);

	onBeforeUnmount(() => {
		detachCompass?.();
		detachCompass = null;
	});

	const emit = defineEmits<{
		"update:layersOpen": [value: boolean];
		"update:basemapOpen": [value: boolean];
		"zoom-in": [];
		"zoom-out": [];
		"reset-bearing": [];
		geolocate: [];
	}>();
</script>

<style scoped>
	.map-console {
		position: absolute;
		top: var(--map-console-top);
		right: var(--map-console-right);
		z-index: 12;
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 8px;
		pointer-events: none;
	}

	.console-row,
	.console-zoom {
		pointer-events: auto;
		display: flex;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		box-shadow: var(--shadow-md);
		overflow: hidden;
	}

	.console-row {
		flex-direction: row;
		align-items: stretch;
	}

	.console-btn {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 5px;
		height: 40px;
		padding: 0 12px;
		border: none;
		border-right: 1px solid var(--border);
		background: transparent;
		color: var(--text-secondary);
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		transition:
			background var(--t-fast),
			color var(--t-fast);
	}

	.console-btn:last-child {
		border-right: none;
	}

	.console-btn.icon-only {
		width: 40px;
		padding: 0;
	}

	.console-btn svg {
		width: 16px;
		height: 16px;
		flex-shrink: 0;
	}

	.console-btn:hover {
		background: var(--bg-elevated);
		color: var(--text-primary);
	}

	.console-btn.active {
		background: var(--accent-subtle);
		color: var(--accent);
	}

	.console-zoom {
		flex-direction: column;
		width: 40px;
	}

	.console-zoom-btn {
		width: 40px;
		height: 40px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		background: transparent;
		color: var(--text-secondary);
		cursor: pointer;
	}

	.console-zoom-btn:hover {
		background: var(--bg-elevated);
		color: var(--text-primary);
	}

	.console-zoom-btn svg {
		width: 16px;
		height: 16px;
	}

	.console-compass {
		cursor: grab;
		user-select: none;
		touch-action: none;
	}

	.console-compass.compass-dragging {
		cursor: grabbing;
	}

	.console-compass-dial {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		pointer-events: none;
		transition: transform 0.15s ease;
	}

	.console-compass-dial svg {
		width: 20px;
		height: 20px;
	}

	.compass-north {
		fill: var(--danger);
	}

	.compass-south {
		fill: var(--text-muted);
	}

	.console-zoom-divider {
		height: 1px;
		background: var(--border);
		margin: 0 6px;
		flex-shrink: 0;
	}
</style>
