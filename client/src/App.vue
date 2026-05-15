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
			<div class="nav-links">
				<RouterLink to="/" class="nav-link">
					<svg class="nav-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M12 1.586l-4 4v12.828l4-4V1.586zM3.707 3.293A1 1 0 002 4v10a1 1 0 00.293.707L6 18.414V5.586L3.707 3.293zM17.707 5.293L14 1.586v12.828l2.293 2.293A1 1 0 0018 16V6a1 1 0 00-.293-.707z"
							clip-rule="evenodd"
						/>
					</svg>
					地图
				</RouterLink>
				<RouterLink to="/stats" class="nav-link">
					<svg class="nav-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zm6-4a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zm6-3a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"
						/>
					</svg>
					统计
				</RouterLink>
				<RouterLink to="/playback" class="nav-link">
					<svg class="nav-icon" viewBox="0 0 20 20" fill="currentColor">
						<path
							fill-rule="evenodd"
							d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
							clip-rule="evenodd"
						/>
					</svg>
					回放
				</RouterLink>
			</div>
			<div class="nav-end">
				<span :class="['ws-pill', wsOnline ? 'online' : 'offline']">
					<span class="ws-dot"></span>
					{{ wsOnline ? "实时" : "断线" }}
				</span>
			</div>
		</nav>
		<main class="app-content">
			<RouterView />
		</main>
	</div>
</template>

<script setup lang="ts">
	import { computed } from "vue";
	import { useFlightStore } from "./stores/flight";
	const store = useFlightStore();
	const wsOnline = computed(() => store.wsOnline);
</script>

<style>
	/* ── Design Tokens ──────────────────────────────────────────────── */
	:root {
		--bg-base: #0f172a;
		--bg-surface: #1e293b;
		--bg-raised: #263349;
		--bg-overlay: rgba(15, 23, 42, 0.93);

		--text-primary: #e2e8f0;
		--text-secondary: #94a3b8;
		--text-muted: #64748b;

		--accent: #3b82f6;
		--accent-hover: #2563eb;
		--accent-subtle: rgba(59, 130, 246, 0.15);

		--success: #10b981;
		--success-subtle: rgba(16, 185, 129, 0.15);
		--warning: #f59e0b;
		--warning-subtle: rgba(245, 158, 11, 0.15);
		--danger: #ef4444;
		--danger-subtle: rgba(239, 68, 68, 0.15);

		--border: #334155;
		--border-strong: #475569;

		--radius-sm: 4px;
		--radius-md: 6px;
		--radius-lg: 10px;

		--shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.4);
		--shadow-md: 0 4px 12px rgba(0, 0, 0, 0.5);
		--shadow-lg: 0 8px 28px rgba(0, 0, 0, 0.6);

		--t-fast: 0.12s ease;
		--t-base: 0.2s ease;

		--nav-h: 48px;
		--panel-w: 320px;
	}

	/* ── Reset ──────────────────────────────────────────────────────── */
	*,
	*::before,
	*::after {
		box-sizing: border-box;
	}

	html,
	body {
		margin: 0;
		height: 100%;
		overflow: hidden;
	}

	body {
		font-family:
			-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", sans-serif;
		font-size: 13px;
		background: var(--bg-base);
		color: var(--text-primary);
		-webkit-font-smoothing: antialiased;
	}

	/* ── App Shell ──────────────────────────────────────────────────── */
	.app-shell {
		display: flex;
		flex-direction: column;
		height: 100vh;
	}

	/* ── Nav ────────────────────────────────────────────────────────── */
	.app-nav {
		height: var(--nav-h);
		flex-shrink: 0;
		display: flex;
		align-items: center;
		padding: 0 12px;
		gap: 8px;
		background: var(--bg-surface);
		border-bottom: 1px solid var(--border);
		z-index: 200;
	}

	.nav-brand {
		display: flex;
		align-items: center;
		gap: 8px;
		padding-right: 16px;
		margin-right: 4px;
		border-right: 1px solid var(--border);
	}

	.brand-icon {
		width: 20px;
		height: 20px;
		color: var(--accent);
		flex-shrink: 0;
	}

	.brand-name {
		font-size: 14px;
		font-weight: 700;
		color: var(--text-primary);
		letter-spacing: 0.5px;
	}

	.nav-links {
		display: flex;
		align-items: center;
		gap: 2px;
		flex: 1;
	}

	.nav-link {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 5px 12px;
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		text-decoration: none;
		font-size: 13px;
		font-weight: 500;
		transition:
			color var(--t-fast),
			background var(--t-fast);
	}

	.nav-link:hover {
		color: var(--text-primary);
		background: var(--bg-raised);
	}

	.nav-link.router-link-active {
		color: var(--accent);
		background: var(--accent-subtle);
	}

	.nav-icon {
		width: 15px;
		height: 15px;
		flex-shrink: 0;
	}

	.nav-end {
		margin-left: auto;
	}

	.ws-pill {
		display: inline-flex;
		align-items: center;
		gap: 5px;
		padding: 3px 10px;
		border-radius: 999px;
		font-size: 11px;
		font-weight: 600;
		letter-spacing: 0.05em;
		text-transform: uppercase;
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
		box-shadow: 0 0 6px var(--success);
	}

	.ws-pill.offline {
		background: var(--bg-raised);
		color: var(--text-muted);
	}

	.ws-pill.offline .ws-dot {
		background: var(--text-muted);
	}

	/* ── Content ────────────────────────────────────────────────────── */
	.app-content {
		flex: 1;
		min-height: 0;
		overflow: hidden;
	}

	/* ── Responsive ─────────────────────────────────────────────────── */
	@media (max-width: 640px) {
		.nav-link span {
			display: none;
		}

		.nav-link {
			padding: 5px 8px;
		}

		.brand-name {
			display: none;
		}
	}
</style>
