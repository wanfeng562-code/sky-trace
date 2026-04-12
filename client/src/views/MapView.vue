<template>
	<div class="layout">
		<section class="map-area">
			<header class="toolbar">
				<h1>Sky-Trace</h1>
				<span>{{
					store.loading ? "loading..." : `${store.flights.length} flights`
				}}</span>
			</header>

			<div id="map-canvas" class="map-canvas">
				TODO: Integrate MapLibre/Leaflet map and render markers + track
				polylines.
			</div>
		</section>

		<FlightListPanel :flights="store.flights" />
	</div>
</template>

<script setup lang="ts">
	import { onMounted, onUnmounted } from "vue";

	import FlightListPanel from "../components/FlightListPanel.vue";
	import { useFlightStore } from "../stores/flight";

	const store = useFlightStore();

	onMounted(async () => {
		await store.loadInitialFlights();
		store.connectSocket();
	});

	onUnmounted(() => {
		store.disconnectSocket();
	});
</script>

<style scoped>
	.layout {
		height: 100vh;
		display: flex;
	}

	.map-area {
		flex: 1;
		display: flex;
		flex-direction: column;
	}

	.toolbar {
		height: 56px;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 16px;
		border-bottom: 1px solid #d1d5db;
		background: #f8fafc;
	}

	.map-canvas {
		flex: 1;
		display: grid;
		place-items: center;
		color: #4b5563;
		background: linear-gradient(135deg, #e0f2fe 0%, #f0f9ff 100%);
	}
</style>
