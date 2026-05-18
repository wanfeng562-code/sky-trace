/**
 * 叠加图层 SaaS 级视觉规范（暗色 App Shell + MapLibre）
 * 参考 FlightRadar24 / FlightAware：分级可见、柔和渐变、碰撞避让、半透明叠加。
 */
import type {
	CircleLayerSpecification,
	FillLayerSpecification,
	HeatmapLayerSpecification,
	LineLayerSpecification,
	Map as MapLibreMap,
	SymbolLayerSpecification,
} from "maplibre-gl";
import type { MapLabelProvider } from "./mapLabelFonts";
import {
	HUB_CIRCLE_STROKE,
	HUB_CIRCLE_TIER_1,
	HUB_CIRCLE_TIER_2,
	HUB_CIRCLE_TIER_3,
	HUB_LABEL_COLOR,
	HUB_LABEL_HALO,
} from "./mapVisualTheme";

/** 与 tokens.css / 墨夜蓝 Shell 对齐 */
export const SHELL_BG = "#0f172a";
export const SHELL_HALO = "rgba(15, 23, 42, 0.85)";

/** AQI 莫兰迪色阶（替代交通灯纯色） */
export const AQI_COLORS = [
	"rgba(110, 231, 183, 0.82)",
	"rgba(163, 230, 138, 0.82)",
	"rgba(253, 224, 138, 0.85)",
	"rgba(251, 146, 164, 0.88)",
	"rgba(167, 139, 250, 0.88)",
] as const;

/** applyBilingualLabels 不得改写的 symbol 文字层 */
export const MARKER_LABEL_LAYER_IDS = [
	"airport-labels",
	"airport-highlight-labels",
	"wind-speed-labels",
	"flight-hover-label",
] as const;

export const OVERLAY_LAYER_IDS = {
	hubPoints: "airport-points",
	hubLabels: "airport-labels",
	aqiCircles: "aqi-circles",
	aqiLabels: "aqi-labels",
	aqiHeatmap: "aqi-heatmap",
	weatherGridFill: "weather-grid-fill",
	weatherGridOutline: "weather-grid-outline",
	weatherGridMarkers: "weather-grid-markers",
	regionFill: "region-highlight-fill",
	regionGlow: "region-highlight-glow",
	regionLine: "region-highlight-line",
	flightDensity: "flight-density",
	tempCircles: "temp-circles",
	tempHeatmap: "temp-heatmap",
	windArrows: "wind-arrows",
	windLabels: "wind-speed-labels",
} as const;

export function hubAirportCirclePaint(): CircleLayerSpecification["paint"] {
	return {
		"circle-radius": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			6,
			5,
			7.5,
			7,
			9,
			10,
			10.5,
			13,
			12,
		],
		"circle-color": [
			"match",
			["get", "hub_tier"],
			1,
			HUB_CIRCLE_TIER_1,
			2,
			HUB_CIRCLE_TIER_2,
			HUB_CIRCLE_TIER_3,
		],
		"circle-opacity": 1,
		"circle-stroke-width": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			1.5,
			8,
			2.5,
		],
		"circle-stroke-color": HUB_CIRCLE_STROKE,
		"circle-stroke-opacity": 1,
		"circle-pitch-alignment": "viewport",
		"circle-blur": 0,
	};
}

/** 选中枢纽：IATA + 机场名（concat + 字面量换行） */
export function hubAirportLabelTextField(): NonNullable<
	SymbolLayerSpecification["layout"]
>["text-field"] {
	return [
		"concat",
		["to-string", ["get", "iata"]],
		"\n",
		["to-string", ["get", "name"]],
	];
}

/** 未选中枢纽：仅 IATA */
export function hubAirportIataOnlyTextField(): NonNullable<
	SymbolLayerSpecification["layout"]
>["text-field"] {
	return ["to-string", ["get", "iata"]];
}

/** 未选中枢纽 IATA 标注 */
export function hubAirportLabelLayout(): SymbolLayerSpecification["layout"] {
	return {
		"text-field": hubAirportIataOnlyTextField(),
		"text-size": 12,
		"text-anchor": "top",
		"text-offset": [0, 0.8],
		"text-allow-overlap": true,
		"text-ignore-placement": true,
		"text-optional": false,
		"symbol-placement": "point",
	};
}

/** 选中高亮枢纽：IATA + 名称 */
export function hubAirportHighlightLabelLayout(): SymbolLayerSpecification["layout"] {
	return {
		"text-field": hubAirportLabelTextField(),
		"text-size": 13,
		"text-anchor": "top",
		"text-offset": [0, 1],
		"text-allow-overlap": true,
		"text-ignore-placement": true,
		"text-optional": false,
		"symbol-placement": "point",
	};
}

export function hubAirportLabelPaint(): SymbolLayerSpecification["paint"] {
	return {
		"text-color": HUB_LABEL_COLOR,
		"text-halo-color": HUB_LABEL_HALO,
		"text-halo-width": 2.5,
	};
}

export function aqiCirclePaint(): CircleLayerSpecification["paint"] {
	return {
		"circle-radius": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			["step", ["get", "aqi"], 6, 2, 8, 3, 10, 4, 12, 5, 14],
			7,
			["step", ["get", "aqi"], 9, 2, 12, 3, 15, 4, 18, 5, 21],
		],
		"circle-blur": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			1.2,
			6,
			0.65,
			9,
			0.35,
		],
		"circle-opacity": 0.4,
		"circle-stroke-width": 1,
		"circle-stroke-color": "rgba(248, 250, 252, 0.35)",
		"circle-pitch-alignment": "viewport",
		"circle-color": [
			"step",
			["get", "aqi"],
			AQI_COLORS[0],
			2,
			AQI_COLORS[1],
			3,
			AQI_COLORS[2],
			4,
			AQI_COLORS[3],
			5,
			AQI_COLORS[4],
		],
	};
}

export function aqiLabelLayout(): SymbolLayerSpecification["layout"] {
	return {
		"text-field": [
			"concat",
			["get", "iata"],
			"\n",
			["to-string", ["get", "aqi"]],
		],
		"text-size": 10,
		"text-anchor": "center",
		"text-font": ["Noto Sans Regular"],
		"text-allow-overlap": false,
		"text-ignore-placement": false,
		"text-optional": true,
		"text-opacity": [
			"interpolate",
			["linear"],
			["zoom"],
			5,
			0,
			6.5,
			1,
		],
	};
}

export function aqiLabelPaint(): SymbolLayerSpecification["paint"] {
	return {
		"text-color": "#e2e8f0",
		"text-halo-color": SHELL_HALO,
		"text-halo-width": 1.25,
	};
}

export function aqiHeatmapPaint(): HeatmapLayerSpecification["paint"] {
	return {
		"heatmap-weight": [
			"interpolate",
			["linear"],
			["coalesce", ["get", "pm2_5"], 0],
			0,
			0,
			75,
			1,
		],
		"heatmap-intensity": [
			"interpolate",
			["linear"],
			["zoom"],
			2,
			0.85,
			5,
			1.35,
			9,
			1.75,
		],
		"heatmap-radius": [
			"interpolate",
			["linear"],
			["zoom"],
			2,
			55,
			5,
			85,
			8,
			110,
			11,
			130,
		],
		"heatmap-opacity": 0.88,
		"heatmap-color": [
			"interpolate",
			["linear"],
			["heatmap-density"],
			0,
			"rgba(15, 23, 42, 0)",
			0.12,
			"rgba(110, 231, 183, 0.5)",
			0.38,
			"rgba(253, 224, 138, 0.68)",
			0.62,
			"rgba(251, 146, 164, 0.75)",
			1,
			"rgba(167, 139, 250, 0.85)",
		],
	};
}

export function weatherGridFillPaint(): FillLayerSpecification["paint"] {
	return {
		"fill-color": [
			"case",
			["==", ["get", "has_weather"], 1],
			[
				"interpolate",
				["linear"],
				["coalesce", ["get", "temperature_c"], 12],
				-25,
				"rgba(94, 234, 212, 0.55)",
				0,
				"rgba(147, 197, 253, 0.5)",
				15,
				"rgba(253, 230, 138, 0.52)",
				28,
				"rgba(251, 146, 164, 0.52)",
				40,
				"rgba(196, 181, 253, 0.55)",
			],
			"rgba(71, 85, 105, 0.22)",
		],
		"fill-opacity": [
			"case",
			["==", ["get", "has_weather"], 1],
			0.6,
			0.32,
		],
		"fill-antialias": true,
	};
}

export function weatherGridOutlinePaint(): LineLayerSpecification["paint"] {
	return {
		"line-color": [
			"case",
			["==", ["get", "has_weather"], 1],
			"rgba(148, 163, 184, 0.45)",
			"rgba(51, 65, 85, 0.55)",
		],
		"line-width": 1,
		"line-opacity": 0.85,
	};
}

export function weatherGridMarkerLayout(): SymbolLayerSpecification["layout"] {
	return {
		"text-field": "+",
		"text-size": [
			"interpolate",
			["linear"],
			["zoom"],
			2,
			8,
			5,
			10,
			8,
			12,
		],
		"text-allow-overlap": true,
		"text-ignore-placement": true,
		"text-font": ["Noto Sans Regular"],
		"text-opacity": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			0.25,
			6,
			0.5,
		],
	};
}

export function weatherGridMarkerPaint(): SymbolLayerSpecification["paint"] {
	return {
		"text-color": [
			"case",
			["==", ["get", "has_weather"], 1],
			"rgba(148, 163, 184, 0.7)",
			"rgba(100, 116, 139, 0.45)",
		],
		"text-halo-color": SHELL_HALO,
		"text-halo-width": 0.75,
	};
}

export function regionHighlightFillPaint(): FillLayerSpecification["paint"] {
	return {
		"fill-color": "rgba(56, 189, 248, 0.12)",
		"fill-opacity": 1,
		"fill-antialias": true,
		"fill-outline-color": "rgba(125, 211, 252, 0.35)",
	};
}

export function regionHighlightGlowPaint(): LineLayerSpecification["paint"] {
	return {
		"line-color": "rgba(14, 165, 233, 0.55)",
		"line-width": 8,
		"line-blur": 5,
		"line-opacity": 0.55,
	};
}

export function regionHighlightLinePaint(): LineLayerSpecification["paint"] {
	return {
		"line-color": "rgba(224, 242, 254, 0.95)",
		"line-width": 2,
		"line-opacity": 0.9,
		"line-dasharray": [5, 3],
	};
}

export function flightDensityHeatmapPaint(): HeatmapLayerSpecification["paint"] {
	return {
		"heatmap-weight": 0.45,
		"heatmap-intensity": [
			"interpolate",
			["linear"],
			["zoom"],
			2,
			0.9,
			4,
			1.2,
			7,
			1.55,
			10,
			1.85,
		],
		"heatmap-radius": [
			"interpolate",
			["linear"],
			["zoom"],
			2,
			28,
			4,
			42,
			7,
			58,
			10,
			72,
		],
		"heatmap-opacity": 0.9,
		"heatmap-color": [
			"interpolate",
			["linear"],
			["heatmap-density"],
			0,
			"rgba(15, 23, 42, 0)",
			0.08,
			"rgba(49, 46, 129, 0.62)",
			0.28,
			"rgba(124, 58, 237, 0.75)",
			0.48,
			"rgba(34, 211, 238, 0.82)",
			0.68,
			"rgba(250, 204, 21, 0.88)",
			1,
			"rgba(251, 113, 133, 0.92)",
		],
	};
}

export function tempHeatmapPaint(): HeatmapLayerSpecification["paint"] {
	return {
		"heatmap-weight": [
			"interpolate",
			["linear"],
			["coalesce", ["get", "temperature_c"], 10],
			-20,
			0.2,
			0,
			0.45,
			15,
			0.7,
			35,
			1,
		],
		"heatmap-intensity": [
			"interpolate",
			["linear"],
			["zoom"],
			2,
			0.75,
			5,
			1.25,
			9,
			1.65,
		],
		"heatmap-radius": [
			"interpolate",
			["linear"],
			["zoom"],
			2,
			45,
			5,
			75,
			8,
			95,
			11,
			115,
		],
		"heatmap-opacity": 0.85,
		"heatmap-color": [
			"interpolate",
			["linear"],
			["heatmap-density"],
			0,
			"rgba(15, 23, 42, 0)",
			0.15,
			"rgba(94, 234, 212, 0.45)",
			0.4,
			"rgba(147, 197, 253, 0.55)",
			0.65,
			"rgba(253, 230, 138, 0.68)",
			1,
			"rgba(251, 146, 164, 0.78)",
		],
	};
}

export function tempCirclePaint(): CircleLayerSpecification["paint"] {
	return {
		"circle-radius": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			10,
			7,
			14,
			10,
			18,
		],
		"circle-opacity": 0.35,
		"circle-blur": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			0.9,
			8,
			0.45,
		],
		"circle-stroke-width": 1,
		"circle-stroke-color": "rgba(248, 250, 252, 0.25)",
		"circle-color": [
			"interpolate",
			["linear"],
			["get", "temperature_c"],
			-20,
			"rgba(94, 234, 212, 0.75)",
			0,
			"rgba(147, 197, 253, 0.75)",
			15,
			"rgba(253, 230, 138, 0.78)",
			28,
			"rgba(251, 146, 164, 0.8)",
			40,
			"rgba(196, 181, 253, 0.82)",
		],
		"circle-pitch-alignment": "viewport",
	};
}

export function windArrowLayout(): SymbolLayerSpecification["layout"] {
	return {
		"text-field": "↑",
		"text-size": [
			"interpolate",
			["linear"],
			["zoom"],
			3,
			14,
			8,
			18,
			11,
			22,
		],
		"text-rotate": ["get", "wind_deg"],
		"text-rotation-alignment": "map",
		"text-allow-overlap": true,
		"text-ignore-placement": true,
		"text-optional": false,
	};
}

export function windArrowPaint(): SymbolLayerSpecification["paint"] {
	return {
		"text-color": "rgba(224, 242, 254, 0.88)",
		"text-halo-color": SHELL_HALO,
		"text-halo-width": 1.25,
	};
}

export function windLabelLayout(): SymbolLayerSpecification["layout"] {
	return {
		"text-field": [
			"concat",
			["to-string", ["get", "iata"]],
			"\n",
			["to-string", ["round", ["coalesce", ["get", "wind_speed_mps"], 0]]],
			" m/s · ",
			["to-string", ["round", ["coalesce", ["get", "wind_deg"], 0]]],
			"°",
		],
		"text-size": [
			"interpolate",
			["linear"],
			["zoom"],
			4,
			10,
			8,
			11,
			12,
			12,
		],
		"text-anchor": "top",
		"text-offset": [0, 1.6],
		"text-allow-overlap": true,
		"text-ignore-placement": true,
		"text-optional": false,
	};
}

export function windLabelPaint(): SymbolLayerSpecification["paint"] {
	return {
		"text-color": "#f1f5f9",
		"text-halo-color": SHELL_HALO,
		"text-halo-width": 1.5,
	};
}

/** 风速风向 symbol 标注（两行：站点 + 风速·风向） */
/** 悬浮航班信息（三行：呼号 / 高度速度 / 起降） */
export function formatFlightHoverLabel(props: {
	callsign?: string;
	flight_id?: string;
	altitude_ft?: number | null;
	speed_kts?: number | null;
	departure_airport?: string;
	arrival_airport?: string;
}): string {
	const line1 = (props.callsign ?? props.flight_id ?? "").trim() || "—";
	const alt =
		props.altitude_ft != null && Number.isFinite(props.altitude_ft)
			? Math.round(props.altitude_ft)
			: null;
	const spd =
		props.speed_kts != null && Number.isFinite(props.speed_kts)
			? Math.round(props.speed_kts)
			: null;
	const line2 =
		alt != null && spd != null
			? `${alt}  ${spd}`
			: alt != null
				? String(alt)
				: spd != null
					? String(spd)
					: "";
	const dep = props.departure_airport?.trim() ?? "";
	const arr = props.arrival_airport?.trim() ?? "";
	const line3 = dep || arr ? `${dep} ${arr}`.trim() : "";
	return [line1, line2, line3].filter(Boolean).join("\n");
}

export function flightHoverLabelLayout(): SymbolLayerSpecification["layout"] {
	return {
		"text-field": [
			"concat",
			["to-string", ["get", "l1"]],
			[
				"case",
				[
					"!=",
					["to-string", ["coalesce", ["get", "l2"], ""]],
					"",
				],
				["concat", "\n", ["to-string", ["get", "l2"]]],
				"",
			],
			[
				"case",
				[
					"!=",
					["to-string", ["coalesce", ["get", "l3"], ""]],
					"",
				],
				["concat", "\n", ["to-string", ["get", "l3"]]],
				"",
			],
		],
		"text-size": 11,
		"text-anchor": "top",
		"text-offset": [0, 1.1],
		"text-allow-overlap": true,
		"text-ignore-placement": true,
		"text-optional": false,
		"symbol-placement": "point",
	};
}

export function flightHoverLabelPaint(): SymbolLayerSpecification["paint"] {
	return {
		"text-color": "#ffffff",
		"text-halo-color": "rgba(0, 0, 0, 0.92)",
		"text-halo-width": 2,
	};
}

/** 飞机图标（琥珀金，不依赖 feature-state） */
export function flightIconImageLayout(): NonNullable<
	SymbolLayerSpecification["layout"]
>["icon-image"] {
	return [
		"case",
		[">", ["coalesce", ["get", "altitude_ft"], 0], 100],
		"icon-plane",
		"icon-plane-ground",
	];
}

export function flightIconSizeLayout(): NonNullable<
	SymbolLayerSpecification["layout"]
>["icon-size"] {
	return [
		"interpolate",
		["linear"],
		["zoom"],
		1,
		0.05,
		3,
		0.08,
		5,
		0.1,
		8,
		0.12,
		11,
		0.14,
		14,
		0.16,
	];
}

/** 悬浮高亮飞机（珊瑚红） */
export function flightHoverIconImageLayout(): NonNullable<
	SymbolLayerSpecification["layout"]
>["icon-image"] {
	return [
		"case",
		[">", ["coalesce", ["get", "altitude_ft"], 0], 100],
		"icon-plane-coral",
		"icon-plane-ground-coral",
	];
}

export function formatWindLabel(props: {
	iata?: string;
	wind_speed_mps?: number | null;
	wind_deg?: number | null;
}): string {
	const head = props.iata?.trim() ?? "";
	const speed =
		props.wind_speed_mps != null && Number.isFinite(props.wind_speed_mps)
			? Math.round(props.wind_speed_mps)
			: null;
	const deg =
		props.wind_deg != null && Number.isFinite(props.wind_deg)
			? Math.round(props.wind_deg)
			: null;
	let detail = "";
	if (speed != null && deg != null) detail = `${speed} m/s · ${deg}°`;
	else if (speed != null) detail = `${speed} m/s`;
	else if (deg != null) detail = `${deg}°`;
	if (!detail) return head;
	return head ? `${head}\n${detail}` : detail;
}

type PaintProps = Record<string, unknown>;
type LayoutProps = Record<string, unknown>;

function setPaint(map: MapLibreMap, layerId: string, props: PaintProps) {
	if (!map.getLayer(layerId)) return;
	for (const [key, value] of Object.entries(props)) {
		map.setPaintProperty(layerId, key, value);
	}
}

function setLayout(map: MapLibreMap, layerId: string, props: LayoutProps) {
	if (!map.getLayer(layerId)) return;
	for (const [key, value] of Object.entries(props)) {
		map.setLayoutProperty(layerId, key, value);
	}
}

/** 重新套用「已验证可显示」的 symbol 文字 layout（须在图层创建后、排序后调用） */
export function applyMapMarkerLabelStyles(map: MapLibreMap): void {
	const hubLayout = hubAirportLabelLayout() as LayoutProps;
	const hubHighlightLayout = hubAirportHighlightLabelLayout() as LayoutProps;
	const hubPaint = hubAirportLabelPaint() as PaintProps;
	if (map.getLayer(OVERLAY_LAYER_IDS.hubLabels)) {
		setLayout(map, OVERLAY_LAYER_IDS.hubLabels, hubLayout);
		setPaint(map, OVERLAY_LAYER_IDS.hubLabels, hubPaint);
	}
	if (map.getLayer("airport-highlight-labels")) {
		setLayout(map, "airport-highlight-labels", hubHighlightLayout);
		setPaint(map, "airport-highlight-labels", hubPaint);
	}
	const windLayout = windLabelLayout() as LayoutProps;
	const windPaint = windLabelPaint() as PaintProps;
	if (map.getLayer(OVERLAY_LAYER_IDS.windLabels)) {
		setLayout(map, OVERLAY_LAYER_IDS.windLabels, windLayout);
		setPaint(map, OVERLAY_LAYER_IDS.windLabels, windPaint);
	}
	const hoverLayout = flightHoverLabelLayout() as LayoutProps;
	const hoverPaint = flightHoverLabelPaint() as PaintProps;
	if (map.getLayer("flight-hover-label")) {
		setLayout(map, "flight-hover-label", hoverLayout);
		setPaint(map, "flight-hover-label", hoverPaint);
	}
}

/** 底图切换后或图层已存在时，统一刷新叠加层视觉参数 */
export function applyPremiumOverlayStyles(
	map: MapLibreMap,
	_provider: MapLabelProvider = "maptiler",
): void {
	const ids = OVERLAY_LAYER_IDS;
	setPaint(map, ids.hubPoints, hubAirportCirclePaint() as PaintProps);
	// 枢纽/风场/悬浮文字层勿在此覆盖 layout，见 applyMapMarkerLabelStyles
	setPaint(map, ids.aqiCircles, aqiCirclePaint() as PaintProps);
	setLayout(map, ids.aqiLabels, aqiLabelLayout() as LayoutProps);
	setPaint(map, ids.aqiLabels, aqiLabelPaint() as PaintProps);
	setPaint(map, ids.aqiHeatmap, aqiHeatmapPaint() as PaintProps);
	setPaint(map, ids.weatherGridFill, weatherGridFillPaint() as PaintProps);
	setPaint(map, ids.weatherGridOutline, weatherGridOutlinePaint() as PaintProps);
	setLayout(
		map,
		ids.weatherGridMarkers,
		weatherGridMarkerLayout() as LayoutProps,
	);
	setPaint(map, ids.weatherGridMarkers, weatherGridMarkerPaint() as PaintProps);
	setPaint(map, ids.regionFill, regionHighlightFillPaint() as PaintProps);
	setPaint(map, ids.regionGlow, regionHighlightGlowPaint() as PaintProps);
	setPaint(map, ids.regionLine, regionHighlightLinePaint() as PaintProps);
	setPaint(map, ids.flightDensity, flightDensityHeatmapPaint() as PaintProps);
	setPaint(map, ids.tempHeatmap, tempHeatmapPaint() as PaintProps);
	setPaint(map, ids.tempCircles, tempCirclePaint() as PaintProps);
	setLayout(map, ids.windArrows, windArrowLayout() as LayoutProps);
	setPaint(map, ids.windArrows, windArrowPaint() as PaintProps);
	if (map.getLayer("flight-points")) {
		setLayout(map, "flight-points", {
			"icon-image": flightIconImageLayout(),
			"icon-size": flightIconSizeLayout(),
		} as LayoutProps);
	}
	if (map.getLayer("flight-hover-icon")) {
		setLayout(map, "flight-hover-icon", {
			"icon-image": flightHoverIconImageLayout(),
			"icon-size": flightIconSizeLayout(),
		} as LayoutProps);
	}
	applyMapMarkerLabelStyles(map);
}
