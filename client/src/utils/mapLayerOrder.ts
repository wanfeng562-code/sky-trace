import type { Map as MapLibreMap } from "maplibre-gl";

/** 底图标注之下：区划、网格、飞机 */
const STACK_BELOW_LABELS = [
	"basemap-dim",
	"terrain-hillshade",
	"region-highlight-fill",
	"region-highlight-glow",
	"weather-grid-fill",
	"weather-grid-outline",
	"region-highlight-line",
	"flight-altitude-glow",
	"flight-points",
] as const;

/** 环境连续场：压在飞机之上、底图标注之下 */
const STACK_FIELD_OVER_FLIGHTS = [
	"aqi-heatmap",
	"flight-density",
	"temp-heatmap",
] as const;

/**
 * 必须压在底图地名标注之上的 symbol 文字层（按从下到上顺序排列）。
 * 后移入栈顶的层会盖住先前的层。
 */
const STACK_TEXT_ABOVE_BASEMAP = [
	"aqi-circles",
	"aqi-labels",
	"weather-grid-markers",
	"temp-circles",
	"wind-arrows",
	"wind-speed-labels",
	"selected-flight-point",
	"marked-flight-ring",
	"playback-marked-flight",
	"flight-track-history-segments",
	"planned-route-line",
	"flight-track-history",
	"airport-route-highlight-points",
	"airport-points",
	"airport-labels",
	"airport-highlight-labels",
	"flight-hover-icon",
	"flight-hover-label",
] as const;

const ALL_OVERLAY_LAYER_IDS = new Set<string>([
	...STACK_BELOW_LABELS,
	...STACK_FIELD_OVER_FLIGHTS,
	...STACK_TEXT_ABOVE_BASEMAP,
]);

/** 底图第一个 symbol 层（用于把飞机/场等压到地名标注下面） */
function firstBasemapSymbolLayerId(map: MapLibreMap): string | undefined {
	return map.getStyle().layers.find((l) => l.type === "symbol")?.id;
}

/** 底图中最后一个「地名类」symbol 层（非本项目 overlay） */
function lastBasemapLabelSymbolIndex(map: MapLibreMap): number {
	const layers = map.getStyle().layers;
	let last = -1;
	for (let i = 0; i < layers.length; i++) {
		const layer = layers[i];
		if (layer.type !== "symbol") continue;
		if (ALL_OVERLAY_LAYER_IDS.has(layer.id)) continue;
		try {
			if (map.getLayoutProperty(layer.id, "text-field")) {
				last = i;
			}
		} catch {
			/* ignore */
		}
	}
	return last;
}

/** 将图层移到「底图最后一个地名 symbol」之上 */
function moveAboveBasemapLabels(map: MapLibreMap, layerId: string): void {
	if (!map.getLayer(layerId)) return;

	const layers = map.getStyle().layers;
	const lastBasemapIdx = lastBasemapLabelSymbolIndex(map);

	if (lastBasemapIdx < 0) {
		map.moveLayer(layerId);
		return;
	}

	const anchor = layers[lastBasemapIdx + 1]?.id;
	if (anchor && anchor !== layerId) {
		map.moveLayer(layerId, anchor);
	} else {
		map.moveLayer(layerId);
	}
}

/** 将图层移到样式栈最顶 */
function moveToStyleTop(map: MapLibreMap, layerId: string): void {
	if (!map.getLayer(layerId)) return;
	try {
		map.moveLayer(layerId);
	} catch {
		/* ignore */
	}
}

/**
 * 统一叠加层 z 序：
 * 1. 飞机/网格等在底图第一个 symbol 之下
 * 2. 环境热力场在底图 symbol 之下、飞机之上
 * 3. 所有文字标注在底图最后一个地名 symbol 之上，且整体位于栈顶
 */
export function ensureOverlayLayerOrder(map: MapLibreMap): void {
	const firstSymbol = firstBasemapSymbolLayerId(map);

	if (firstSymbol) {
		for (const id of STACK_BELOW_LABELS) {
			if (!map.getLayer(id)) continue;
			try {
				map.moveLayer(id, firstSymbol);
			} catch {
				/* ignore */
			}
		}

		for (const id of STACK_FIELD_OVER_FLIGHTS) {
			if (!map.getLayer(id)) continue;
			try {
				map.moveLayer(id, firstSymbol);
			} catch {
				/* ignore */
			}
		}
	}

	// 先压到「底图地名」之上，再依次移到栈顶以保持相对顺序
	for (const id of STACK_TEXT_ABOVE_BASEMAP) {
		moveAboveBasemapLabels(map, id);
	}

	for (const id of STACK_TEXT_ABOVE_BASEMAP) {
		moveToStyleTop(map, id);
	}
}

/** @deprecated 使用 STACK_TEXT_ABOVE_BASEMAP */
export const STACK_ON_TOP = STACK_TEXT_ABOVE_BASEMAP;
