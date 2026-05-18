/** FlightAware 风格地图视觉常量 */

/** 全图统一飞机琥珀金 */
export const AIRCRAFT_AMBER = "#FFBF00";

/** 飞机图标暗描边（沙漠/绿地也不融入背景） */
export const AIRCRAFT_ICON_STROKE = "#140f08";
export const AIRCRAFT_ICON_STROKE_WIDTH = 42;

/** 枢纽实心圆：FlightAware 式高对比绿 / 青 / 蓝 */
export const HUB_CIRCLE_TIER_1 = "#22e584";
export const HUB_CIRCLE_TIER_2 = "#22d3ee";
export const HUB_CIRCLE_TIER_3 = "#38bdf8";
export const HUB_CIRCLE_STROKE = "rgba(0, 0, 0, 0.75)";

/** 枢纽 IATA：黄字 + 深色描边，远 zoom 也易辨认 */
export const HUB_LABEL_COLOR = "#fde047";
export const HUB_LABEL_HALO = "rgba(0, 0, 0, 0.88)";

/** 略降底图对比度的暗色样式 */
const DARK_BASEMAP_STYLE_IDS = new Set([
	"streets-v2-dark",
	"dataviz-dark",
	"alidade_smooth_dark",
	"liberty",
	"hybrid",
	"satellite",
	"satellite-hybrid",
	"alidade_satellite",
]);

export function isDarkBasemapStyle(styleId: string): boolean {
	const key = styleId === "satellite-hybrid" ? "hybrid" : styleId;
	return DARK_BASEMAP_STYLE_IDS.has(key);
}
