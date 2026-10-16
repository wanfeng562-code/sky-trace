import type { Map as MapLibreMap } from "maplibre-gl";
import { OVERLAY_FONT, type MapProvider } from "../utils/mapBasemap";

export type MapLabelProvider = MapProvider;
export function labelFontsForProvider(_provider: MapLabelProvider, _weight: "regular" | "bold" = "regular"): string[] {
	return [OVERLAY_FONT];
}

export function applyOverlaySymbolFonts(map: MapLibreMap, _provider: MapLabelProvider = "tianditu"): void {
	for (const layer of map.getStyle().layers) {
		if (layer.type === "symbol" && layer.layout?.["text-field"]) {
			map.setLayoutProperty(layer.id, "text-font", [OVERLAY_FONT]);
		}
	}
}
