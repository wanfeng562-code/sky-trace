<template>
	<Teleport to="body">
		<div v-if="open" class="layer-backdrop" @click="emit('update:open', false)" />
		<div
			v-if="open"
			class="layer-popover"
			:style="anchorStyle"
			@click.stop
		>
			<div class="lp-header">
				<span class="lp-title">{{ ui.title }}</span>
				<button type="button" class="lp-close" @click="emit('update:open', false)">
					<svg viewBox="0 0 16 16" fill="currentColor">
						<path
							d="M4.293 4.293a1 1 0 011.414 0L8 6.586l2.293-2.293a1 1 0 111.414 1.414L9.414 8l2.293 2.293a1 1 0 01-1.414 1.414L8 9.414l-2.293 2.293a1 1 0 01-1.414-1.414L6.586 8 4.293 5.707a1 1 0 010-1.414z"
						/>
					</svg>
				</button>
			</div>
			<div class="lp-body">
				<label
					v-for="layer in MAP_OVERLAY_LAYERS"
					:key="layer.key"
					class="lp-row"
					@click.stop
				>
					<input
						type="checkbox"
						class="lp-check"
						:checked="isLayerOn(layer.key)"
						@change="onLayerToggle(layer.key, $event)"
					/>
					<span class="lp-row-text">
						<span class="lp-row-label">{{ layerLabel(layer.key) }}</span>
						<span class="lp-row-desc">{{ layerDesc(layer.key) }}</span>
					</span>
				</label>
			</div>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
	import { computed } from "vue";
	import {
		MAP_OVERLAY_LAYERS,
		type OverlayLayerKey,
	} from "../../config/mapOverlayMeta";
	import { translate, useLocaleStore } from "../../i18n";

	export type MapProvider = "maptiler" | "stadia" | "openfreemap";

	const localeStore = useLocaleStore();
	const ui = computed(() => ({
		title: translate(localeStore.t, "mapLayers.title"),
	}));

	function layerLabel(key: OverlayLayerKey): string {
		return translate(localeStore.t, `overlays.${key}.label`);
	}
	function layerDesc(key: OverlayLayerKey): string {
		return translate(localeStore.t, `overlays.${key}.desc`);
	}

	const props = defineProps<{
		open: boolean;
		showAqi: boolean;
		showAqiHeatmap: boolean;
		showWind: boolean;
		showTemp: boolean;
		showDensity: boolean;
		showHubs: boolean;
		showGrid: boolean;
	}>();

	const emit = defineEmits<{
		"update:open": [value: boolean];
		"update:showAqi": [value: boolean];
		"update:showAqiHeatmap": [value: boolean];
		"update:showWind": [value: boolean];
		"update:showTemp": [value: boolean];
		"update:showDensity": [value: boolean];
		"update:showHubs": [value: boolean];
		"update:showGrid": [value: boolean];
	}>();

	const anchorStyle = {
		top: "64px",
		right: "16px",
	};

	function isLayerOn(key: OverlayLayerKey): boolean {
		switch (key) {
			case "showAqi":
				return props.showAqi;
			case "showAqiHeatmap":
				return props.showAqiHeatmap;
			case "showWind":
				return props.showWind;
			case "showTemp":
				return props.showTemp;
			case "showDensity":
				return props.showDensity;
			case "showHubs":
				return props.showHubs;
			case "showGrid":
				return props.showGrid;
		}
	}

	function onLayerToggle(key: OverlayLayerKey, event: Event) {
		const checked = (event.target as HTMLInputElement).checked;
		switch (key) {
			case "showAqi":
				emit("update:showAqi", checked);
				break;
			case "showAqiHeatmap":
				emit("update:showAqiHeatmap", checked);
				break;
			case "showWind":
				emit("update:showWind", checked);
				break;
			case "showTemp":
				emit("update:showTemp", checked);
				break;
			case "showDensity":
				emit("update:showDensity", checked);
				break;
			case "showHubs":
				emit("update:showHubs", checked);
				break;
			case "showGrid":
				emit("update:showGrid", checked);
				break;
		}
	}
</script>

<style scoped>
	.layer-backdrop {
		position: fixed;
		inset: 0;
		z-index: 150;
	}

	.layer-popover {
		position: fixed;
		z-index: 160;
		width: min(280px, calc(100vw - 32px));
		display: flex;
		flex-direction: column;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-xl);
		box-shadow: var(--shadow-panel);
		overflow: hidden;
	}

	.lp-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 14px;
		border-bottom: 1px solid var(--border);
	}

	.lp-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.lp-close {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border: none;
		border-radius: var(--radius-sm);
		background: transparent;
		color: var(--text-muted);
		cursor: pointer;
	}

	.lp-close:hover {
		background: var(--bg-elevated);
	}

	.lp-close svg {
		width: 14px;
		height: 14px;
	}

	.lp-body {
		padding: 10px 14px 14px;
		max-height: min(70vh, 480px);
		overflow-y: auto;
	}

	.lp-row {
		display: flex;
		align-items: flex-start;
		gap: 10px;
		padding: 10px 0;
		cursor: pointer;
		border-bottom: 1px solid var(--border);
	}

	.lp-row:last-child {
		border-bottom: none;
	}

	.lp-check {
		margin-top: 3px;
		accent-color: var(--accent);
		flex-shrink: 0;
	}

	.lp-row-text {
		display: flex;
		flex-direction: column;
		gap: 3px;
		min-width: 0;
	}

	.lp-row-label {
		font-size: 13px;
		font-weight: 500;
		color: var(--text-primary);
		line-height: 1.35;
	}

	.lp-row-desc {
		font-size: 11px;
		line-height: 1.4;
		color: var(--text-muted);
	}
</style>
