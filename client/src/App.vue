<template>
	<nav class="app-nav">
		<RouterLink to="/" class="nav-link">🗺 地图</RouterLink>
		<RouterLink to="/stats" class="nav-link">📊 统计</RouterLink>
		<RouterLink to="/playback" class="nav-link">⏪ 历史回放</RouterLink>
		<span class="app-title">Sky-Trace</span>
	</nav>
	<div class="app-content">
		<router-view />
	</div>
</template>

<script setup lang="ts"></script>

<style>
	* {
		box-sizing: border-box;
	}

	body {
		margin: 0;
		font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
	}

	.app-nav {
		height: 44px;
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 0 16px;
		background: #1e293b;
		border-bottom: 1px solid #334155;
		z-index: 100;
		position: relative;
	}

	.nav-link {
		padding: 6px 12px;
		color: #94a3b8;
		text-decoration: none;
		border-radius: 4px;
		font-size: 13px;
		transition: all 0.15s;
	}

	.nav-link:hover {
		color: #e2e8f0;
		background: #334155;
	}

	.nav-link.router-link-active {
		color: #60a5fa;
		background: #1e3a5f;
	}

	.app-title {
		margin-left: auto;
		color: #60a5fa;
		font-weight: 700;
		font-size: 15px;
		letter-spacing: 0.5px;
	}

	.app-content {
		height: calc(100vh - 44px);
		overflow: hidden;
	}
</style>
