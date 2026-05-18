import type { Map as MapLibreMap } from "maplibre-gl";
import { OPENFREEMAP_LABEL_FONTS } from "../utils/mapBasemap";

export type MapLabelProvider = "maptiler" | "stadia" | "openfreemap";

/** 双语底图标注用字体（applyBilingualLabels） */
export function labelFontsForProvider(
	provider: MapLabelProvider,
	weight: "regular" | "bold" = "regular",
): string[] {
	if (provider === "openfreemap") {
		return weight === "bold"
			? [...OPENFREEMAP_LABEL_FONTS]
			: ["Noto Sans Regular", "Noto Sans Bold"];
	}
	return weight === "bold"
		? ["Open Sans Bold", "Arial Unicode MS Regular"]
		: ["Open Sans Regular", "Arial Unicode MS Regular"];
}

/**
 * 叠加层 symbol 文字不强制 text-font，与 wind-arrows（↑）一致走样式默认 glyph。
 * 此前强制 Open Sans 且 moveLayer 不当会导致整层文字不渲染。
 */
export function applyOverlaySymbolFonts(
	_map: MapLibreMap,
	_provider: MapLabelProvider = "maptiler",
): void {
	/* intentional no-op */
}
