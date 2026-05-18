from pathlib import Path

p = Path(__file__).resolve().parents[1] / "client" / "src" / "views" / "MapView.vue"
text = p.read_text(encoding="utf-8")
start = text.index("<template>")
end = text.index("</template>") + len("</template>")

new_template = r"""<template>
	<div class="map-layout">
		<transition name="toast">
			<div
				v-if="showFallbackToast"
				class="fallback-toast"
				@click="showFallbackToast = false"
			>
				{{ mapFallbackReason }}，已切换至备用底图（{{ currentProvider }}）。点击关闭
			</div>
		</transition>

		<div class="map-workspace">
			<MapSidebar
				v-model:collapsed="sidebarCollapsed"
				v-model:active-tab="sidebarTab"
				:flights="store.filteredFlights"
				:all-flights="store.flights"
				:airports="store.airports"
				:selected-flight-id="store.selectedFlightId"
				:selected-hub-iata="selectedHubIata"
				:hub-count="hubAirportCount"
				@select-flight="handleSelectFlight"
				@hub-locate="handleHubLocate"
				@hub-schedule="handleHubSchedule"
				@collapse="onSidebarCollapse"
			/>

			<div class="map-shell">
				<div ref="mapContainer" class="map-canvas"></div>
				<MapControlsOverlay v-model:layers-open="showLayerPanel" />
				<MapLayerPopover
					v-model:open="showLayerPanel"
					:provider="currentProvider"
					:style-id="currentStyleId"
					:styles="currentProviderStyles"
					:has-maptiler="!!MAPTILER_KEY"
					:has-stadia="!!STADIA_KEY"
					:fallback-active="mapFallbackActive"
					v-model:show-aqi="store.showAqiLayer"
					v-model:show-aqi-heatmap="showAqiHeatmap"
					v-model:show-wind="showWindLayer"
					v-model:show-temp="showTempLayer"
					v-model:show-density="showDensityLayer"
					v-model:show-hubs="showHubAirports"
					v-model:show-grid="showGridPoints"
					v-model:label-lines="labelLines"
					v-model:label-line1="labelLine1"
					v-model:label-line2="labelLine2"
					:label-options="LABEL_LANG_OPTIONS"
					@switch-provider="switchProvider"
					@switch-style="switchStyle"
				/>
				<div v-if="store.loading" class="map-status">正在加载航班数据...</div>
				<div v-else-if="store.trackLoading" class="map-status">
					正在加载选中航班轨迹...
				</div>
				<div v-else-if="!store.flights.length" class="map-status">
					暂无航班数据，等待后端返回快照。
				</div>
			</div>

			<MapContextPanel
				v-model:active-tab="contextTab"
				:open="contextPanelOpen"
				:show-detail-tab="showDetailTab"
				:show-schedule-tab="!!store.scheduleAirport"
				:detail="store.flightDetail"
				:detail-loading="store.detailLoading"
				:pinned="contextPinned"
				@close="closeContextPanel"
				@close-detail="handleSelectFlight(null)"
				@toggle-pin="contextPinned = !contextPinned"
			/>
		</motion>
	</motion>
</template>"""

new_template = new_template.replace("</motion>", "</div>")

text = text[:start] + new_template + text[end:]
p.write_text(text, encoding="utf-8")
print("done")
