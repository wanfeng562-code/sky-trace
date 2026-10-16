<template>
	<Teleport to="body">
		<div v-if="open" class="popover-backdrop" @click="emit('update:open', false)" />
		<div
			v-if="open"
			class="basemap-popover"
			:style="anchorStyle"
			@click.stop
		>
			<div class="bp-header">
				<span class="bp-title">{{ i18n.basemap.title }}</span>
				<button type="button" class="bp-close" @click="emit('update:open', false)">
					<svg viewBox="0 0 16 16" fill="currentColor">
						<path
							d="M4.293 4.293a1 1 0 011.414 0L8 6.586l2.293-2.293a1 1 0 111.414 1.414L9.414 8l2.293 2.293a1 1 0 01-1.414 1.414L8 9.414l-2.293 2.293a1 1 0 01-1.414-1.414L6.586 8 4.293 5.707a1 1 0 010-1.414z"
						/>
					</svg>
				</button>
			</div>
			<div class="bp-body">
				<div class="bp-section">
					<div class="bp-label">{{ i18n.basemap.uiLang }}</div>
					<select
						class="bp-select bp-select-full"
						:value="localeStore.locale"
						@change="onUiLocaleChange"
					>
						<option
							v-for="opt in LOCALE_OPTIONS"
							:key="opt.id"
							:value="opt.id"
							:disabled="!opt.uiReady"
						>
							{{ opt.label }}
						</option>
					</select>
				</div>
				<div class="bp-section">
					<div class="bp-label">{{ i18n.basemap.source }}</div>
					<div class="bp-grid"><span class="bp-chip active">{{ i18n.business.provider }}</span></div>
					<p v-if="unavailable" class="bp-note bp-warning">{{ i18n.basemap.unavailable }}</p>
				</div>
				<div class="bp-section">
					<div class="bp-label">{{ i18n.basemap.style }}</div>
					<div class="bp-grid">
						<button
							v-for="s in styles"
							:key="s.id"
							type="button"
							:class="['bp-chip', { active: styleId === s.id }]"
							@click="emit('switch-style', s.id)"
						>
							{{ s.label }}
						</button>
					</div>
				</div>
				<p class="bp-note">{{ i18n.basemap.officialLabels }}</p>
			</div>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
	import { computed } from "vue";
	import { LOCALE_OPTIONS, useLocaleStore } from "../../i18n";
	import type { MapProvider } from "../../utils/mapBasemap";

	const props = defineProps<{
		open: boolean;
		provider: MapProvider;
		styleId: string;
		styles: { id: string; label: string }[];
		unavailable: boolean;
	}>();

	const emit = defineEmits<{
		"update:open": [value: boolean];
		"switch-style": [styleId: string];
	}>();

	const localeStore = useLocaleStore();
	const i18n = computed(() => localeStore.t);


	const anchorStyle = computed(() => ({
		top: "calc(var(--nav-h, 64px) + var(--map-console-top, 16px))",
		right: "16px",
	}));

	function onUiLocaleChange(e: Event) {
		const v = (e.target as HTMLSelectElement).value;
		if (v === "zh-CN" || v === "en-US") {
			localeStore.setLocale(v);
		}
	}
</script>

<style scoped>
	.popover-backdrop {
		position: fixed;
		inset: 0;
		z-index: 150;
	}

	.basemap-popover {
		position: fixed;
		z-index: 160;
		width: min(300px, calc(100vw - 32px));
		max-height: min(70vh, 520px);
		display: flex;
		flex-direction: column;
		background: var(--bg-surface);
		border: 1px solid var(--border);
		border-radius: var(--radius-xl);
		box-shadow: var(--shadow-panel);
		overflow: hidden;
	}

	.bp-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 14px;
		border-bottom: 1px solid var(--border);
	}

	.bp-title {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.bp-close {
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

	.bp-close:hover {
		background: var(--bg-elevated);
	}

	.bp-close svg {
		width: 14px;
		height: 14px;
	}

	.bp-body {
		overflow-y: auto;
		padding: 12px 14px 14px;
	}

	.bp-section {
		margin-bottom: 16px;
		padding-bottom: 16px;
		border-bottom: 1px solid var(--border);
	}

	.bp-section:last-child {
		margin-bottom: 0;
		padding-bottom: 0;
		border-bottom: none;
	}

	.bp-label {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-muted);
		margin-bottom: 8px;
	}

	.bp-grid {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}

	.bp-chip {
		padding: 6px 10px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-elevated);
		color: var(--text-secondary);
		font-size: 12px;
		cursor: pointer;
	}

	.bp-chip:hover {
		color: var(--text-primary);
	}

	.bp-chip.active {
		background: var(--accent);
		border-color: var(--accent);
		color: #fff;
	}

	.bp-note {
		margin: 8px 0 0;
		font-size: 11px;
		color: var(--text-muted);
	}

	.bp-warning { color: var(--warning); }

	.bp-row {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 8px;
	}

	.bp-row-label {
		font-size: 12px;
		color: var(--text-muted);
		min-width: 44px;
	}

	.bp-select {
		flex: 1;
		padding: 6px 8px;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		background: var(--bg-elevated);
		font-size: 12px;
		color: var(--text-primary);
	}

	.bp-select-full {
		width: 100%;
	}
</style>
