<!-- @deprecated import from components/flight/FlightListPanel.vue -->
<script setup lang="ts">
	import FlightListPanel from "./flight/FlightListPanel.vue";
</script>

<template>
	<FlightListPanel
		:flights="($attrs.flights as any) ?? []"
		:selected-flight-id="($attrs['selected-flight-id'] as any) ?? null"
		@select="(id: string) => $emit('select', id)"
	/>
</template>
