<template>
	<div class="app-shell">
		<nav class="app-nav">
			<div class="nav-brand">
				<svg
					class="brand-icon"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.8"
				>
					<circle cx="12" cy="12" r="9.5" />
					<path
						d="M12 2.5C12 2.5 16.5 6.5 16.5 12S12 21.5 12 21.5M12 2.5C12 2.5 7.5 6.5 7.5 12S12 21.5 12 21.5M2.5 12h19"
						stroke-linecap="round"
					/>
				</svg>
				<span class="brand-name">Sky-Trace</span>
			</div>
			<div class="nav-segment">
				<RouterLink to="/" class="nav-seg-link">
					<svg class="nav-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M12 1.586l-4 4v12.828l4-4V1.586zM3.707 3.293A1 1 0 002 4v10a1 1 0 00.293.707L6 18.414V5.586L3.707 3.293zM17.707 5.293L14 1.586v12.828l2.293 2.293A1 1 0 0018 16V6a1 1 0 00-.293-.707z"
							clip-rule="evenodd"
						/>
					</svg>
					{{ t("nav.map") }}
				</RouterLink>
				<RouterLink to="/stats" class="nav-seg-link">
					<svg class="nav-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"
						/>
					</svg>
					{{ t("nav.stats") }}
				</RouterLink>
				<RouterLink to="/playback" class="nav-seg-link">
					<svg class="nav-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
							clip-rule="evenodd"
						/>
					</svg>
					{{ t("nav.playback") }}
				</RouterLink>
			</div>
			<div class="nav-end">
				<div v-if="isMapRoute" class="nav-metrics-capsule">
					<span class="nav-stat">
						<strong>{{ store.flights.length.toLocaleString() }}</strong>
						{{ t("metrics.tracking") }}
					</span>
					<span class="nav-stat-sep">·</span>
					<span class="nav-stat nav-stat-air">
						<strong>{{ airborneCount.toLocaleString() }}</strong>
						{{ t("metrics.airborne") }}
					</span>
					<span class="nav-stat-sep">·</span>
					<span class="nav-stat nav-stat-gnd">
						<strong>{{ groundCount.toLocaleString() }}</strong>
						{{ t("metrics.ground") }}
					</span>
					<span class="nav-stat-sep">·</span>
					<span :class="['ws-inline', store.wsOnline ? 'online' : 'offline']">
						<span class="ws-dot"></span>
						{{ store.wsOnline ? t("metrics.live") : t("metrics.offline") }}
					</span>
				</div>
				<span
					v-else
					:class="['ws-pill', store.wsOnline ? 'online' : 'offline']"
				>
					<span class="ws-dot"></span>
					{{ store.wsOnline ? t("metrics.live") : t("metrics.offline") }}
				</span>
			</div>
		</nav>
		<main class="app-content">
			<RouterView v-slot="{ Component }">
				<KeepAlive :include="['MapView']">
					<component :is="Component" />
				</KeepAlive>
			</RouterView>
		</main>
	</div>
</template>

<script setup lang="ts">
	import { computed, KeepAlive } from "vue";
	import { useRoute } from "vue-router";
	import { translate, useLocaleStore } from "../i18n";
	import { useFlightStore } from "../stores/flight";

	const route = useRoute();
	const store = useFlightStore();
	const localeStore = useLocaleStore();

	const t = (key: string) => translate(localeStore.t, key);

	const isMapRoute = computed(() => route.path === "/");
	const airborneCount = computed(
		() => store.flights.filter((f) => (f.altitude_ft ?? 0) > 100).length,
	);
	const groundCount = computed(
		() => store.flights.filter((f) => (f.altitude_ft ?? 0) <= 100).length,
	);
</script>

<style scoped>
	.app-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
	}

	.app-nav {
		height: var(--nav-h);
		flex-shrink: 0;
		display: flex;
		align-items: center;
		padding: 0 20px;
		gap: 20px;
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		z-index: 200;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-shrink: 0;
	}

	.brand-icon {
		width: 22px;
		height: 22px;
		color: var(--accent);
	}

	.brand-name {
		font-size: 15px;
		font-weight: 700;
		color: var(--text-primary);
	}

	.nav-segment {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 4px;
		background: var(--bg-base);
		border-radius: var(--radius-md);
		border: 1px solid var(--border);
	}

	.nav-seg-link {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 8px 16px;
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
		text-decoration: none;
		font-size: 13px;
		font-weight: 500;
		transition:
			color var(--t-fast),
			background var(--t-fast);
	}

	.nav-seg-link:hover {
		color: var(--text-primary);
	}

	.nav-seg-link.router-link-active {
		background: var(--bg-raised);
		color: var(--accent);
		box-shadow: var(--shadow-sm);
	}

	.nav-icon {
		width: 15px;
		height: 15px;
		flex-shrink: 0;
	}

	.nav-end {
		margin-left: auto;
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.nav-metrics-capsule {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 8px 14px;
		background: var(--bg-elevated);
		border: 1px solid var(--border);
		border-radius: 999px;
		font-size: 12px;
		color: var(--text-muted);
	}

	.ws-inline {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		font-weight: 500;
	}

	.ws-inline.online {
		color: var(--success);
	}

	.ws-inline.offline {
		color: var(--text-muted);
	}

	.nav-stat strong {
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
		margin-right: 4px;
		font-variant-numeric: tabular-nums;
	}

	.nav-stat-air strong {
		color: var(--accent);
	}

	.nav-stat-sep {
		color: var(--border-strong);
	}

	.ws-pill {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 10px;
		border-radius: 999px;
		font-size: 12px;
		font-weight: 500;
	}

	.ws-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.ws-pill.online {
		background: var(--success-subtle);
		color: var(--success);
	}

	.ws-pill.online .ws-dot {
		background: var(--success);
	}

	.ws-pill.offline {
		background: var(--bg-elevated);
		color: var(--text-muted);
	}

	.ws-pill.offline .ws-dot {
		background: var(--text-muted);
	}

	.app-content {
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	@media (max-width: 768px) {
		.nav-seg-link span:not(.nav-icon) {
			display: none;
		}

		.nav-metrics-capsule {
			display: none;
		}
	}

	@media (max-width: 640px) {
		.brand-name {
			display: none;
		}
	}
</style>
