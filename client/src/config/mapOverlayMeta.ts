/** 叠加图层开关说明（图层 Popover 展示） */
export type OverlayLayerKey =
	| "showAqi"
	| "showAqiHeatmap"
	| "showWind"
	| "showTemp"
	| "showDensity"
	| "showHubs"
	| "showGrid";

export interface OverlayLayerMeta {
	key: OverlayLayerKey;
	label: string;
	description: string;
}

export const MAP_OVERLAY_LAYERS: OverlayLayerMeta[] = [
	{
		key: "showAqi",
		label: "AQI 空气质量",
		description: "机场周边空气质量热力分布",
	},
	{
		key: "showAqiHeatmap",
		label: "PM2.5 热力图",
		description: "细颗粒物浓度空间分布",
	},
	{
		key: "showWind",
		label: "风速风向",
		description: "各观测点风向箭头与风速标注",
	},
	{
		key: "showTemp",
		label: "温度分布",
		description: "气温冷暖分布热力图",
	},
	{
		key: "showDensity",
		label: "航班密度热力图",
		description: "实时航班密集区域",
	},
	{
		key: "showHubs",
		label: "枢纽机场点位",
		description: "主要机场位置与 IATA 代码",
	},
	{
		key: "showGrid",
		label: "天气网格（5°×5°）",
		description: "大范围格点气温采集状态",
	},
];
