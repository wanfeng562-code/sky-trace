<template>
	<AppShell />
</template>

<script setup lang="ts">
	import AppShell from "./layouts/AppShell.vue";
</script>

<style>
	@import "./styles/tokens.css";

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

	* {
		scrollbar-width: thin;
		scrollbar-color: var(--scrollbar-thumb) var(--scrollbar-track);
	}

	*::-webkit-scrollbar {
		width: 8px;
		height: 8px;
	}

	*::-webkit-scrollbar-track {
		background: var(--scrollbar-track);
	}

	*::-webkit-scrollbar-thumb {
		background-color: var(--scrollbar-thumb);
		border-radius: 4px;
		border: 2px solid var(--scrollbar-track);
	}

	*::-webkit-scrollbar-thumb:hover {
		background-color: var(--scrollbar-thumb-hover);
	}

	*::-webkit-scrollbar-corner {
		background: var(--scrollbar-track);
	}
</style>
