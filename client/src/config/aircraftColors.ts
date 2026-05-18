/**

 * 飞机图标颜色：全图统一琥珀金（FlightAware 暖色流纹理风格）。

 * 用户手动选色已关闭；下方 PRESETS 保留供日后复用。

 */



import { AIRCRAFT_AMBER } from "./mapVisualTheme";



export const AIRCRAFT_COLOR = {

	amber: AIRCRAFT_AMBER,

	coral: "#FF7F50",

	charcoal: "#333333",

	lime: "#CCFF00",

	orangered: "#FF4500",

	yellow: "#FFFF00",

	deepBlue: "#1A237E",

} as const;



/** 各底图统一琥珀金（fly = ground） */

export const STYLE_AIRCRAFT_COLORS: Record<string, string> = {

	"streets-v2-dark": AIRCRAFT_COLOR.amber,

	"streets-v2": AIRCRAFT_COLOR.amber,

	"outdoor-v2": AIRCRAFT_COLOR.amber,

	hybrid: AIRCRAFT_COLOR.amber,

	satellite: AIRCRAFT_COLOR.amber,

	"satellite-hybrid": AIRCRAFT_COLOR.amber,

	"dataviz-dark": AIRCRAFT_COLOR.amber,

	dataviz: AIRCRAFT_COLOR.amber,

	alidade_smooth_dark: AIRCRAFT_COLOR.amber,

	alidade_smooth: AIRCRAFT_COLOR.amber,

	stamen_terrain: AIRCRAFT_COLOR.amber,

	alidade_satellite: AIRCRAFT_COLOR.amber,

	liberty: AIRCRAFT_COLOR.amber,

	bright: AIRCRAFT_COLOR.amber,

	positron: AIRCRAFT_COLOR.amber,

};



export const DEFAULT_AIRCRAFT_COLOR = AIRCRAFT_COLOR.amber;



const STYLE_ALIASES: Record<string, string> = {

	"satellite-hybrid": "hybrid",

};



export function resolveStyleAircraftColor(styleId: string): string {

	const key = STYLE_ALIASES[styleId] ?? styleId;

	return STYLE_AIRCRAFT_COLORS[key] ?? DEFAULT_AIRCRAFT_COLOR;

}



/** 历史手动预设（图层选色已关闭，保留配置供以后启用） */

export const AIRCRAFT_COLOR_PRESETS = [

	{ id: "auto", label: "自动（随底图）", fly: "#60a5fa", ground: "#94a3b8" },

	{ id: "ocean-blue", label: "海洋蓝", fly: "#60a5fa", ground: "#94a3b8" },

	{ id: "yellow", label: "荧光黄 #FFFF00", fly: "#FFFF00", ground: "#f1f5f9" },

	{ id: "lime", label: "亮明黄 #CCFF00", fly: "#CCFF00", ground: "#e2e8f0" },

	{ id: "white", label: "纯白 #FFFFFF", fly: "#FFFFFF", ground: "#e2e8f0" },

	{ id: "ice", label: "浅冰白 #F8FAFC", fly: "#F8FAFC", ground: "#cbd5e1" },

	{ id: "orangered", label: "橙红 #FF4500", fly: "#FF4500", ground: "#f1f5f9" },

	{ id: "coral", label: "珊瑚红 #FF7F50", fly: "#FF7F50", ground: "#e2e8f0" },

	{

		id: "deep-blue",

		label: "深海蓝 #1A237E（专业商务风）",

		fly: "#1A237E",

		ground: "#e2e8f0",

	},

	{

		id: "charcoal",

		label: "深炭灰 #333333（极致清晰）",

		fly: "#333333",

		ground: "#f1f5f9",

	},

	{

		id: "jade-green",

		label: "翡翠绿 #2E7D32（清新自然风）",

		fly: "#2E7D32",

		ground: "#e2e8f0",

	},

] as const;



export type AircraftColorPresetId =

	(typeof AIRCRAFT_COLOR_PRESETS)[number]["id"];


