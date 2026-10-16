import type { StyleSpecification } from "maplibre-gl";
import verifiedApproval from "../data/mapApproval.json";
import { BUSINESS_EN, BUSINESS_ZH } from "../i18n/business";

export type MapProvider = "tianditu";
export const TIANDITU_STYLE_IDS = ["vector", "imagery", "terrain"] as const;
export type BasemapStyleId = (typeof TIANDITU_STYLE_IDS)[number];
export const OVERLAY_FONT = "Noto Sans Regular";

export function normalizeBasemapStyle(styleId: string): BasemapStyleId {
	return TIANDITU_STYLE_IDS.includes(styleId as BasemapStyleId) ? styleId as BasemapStyleId : "vector";
}

const LAYERS = { vector: ["vec", "cva"], imagery: ["img", "cia"], terrain: ["ter", "cta"] } as const;

export function buildTiandituTileUrl(layer: string, key: string): string {
	if (!["vec", "cva", "img", "cia", "ter", "cta"].includes(layer)) throw new Error("Unsupported Tianditu layer");
	return `https://t0.tianditu.gov.cn/${layer}_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${layer}&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${encodeURIComponent(key)}`;
}

/** Use the original service's base tiles together with its official annotation tiles. */
export function createBasemapStyle(
	styleId: string, key: string, approvalNumber = "",
	assetBase = typeof window === "undefined" ? "http://localhost/" : window.location.href,
): StyleSpecification {
	const id = normalizeBasemapStyle(styleId);
	const [base, annotation] = LAYERS[id];
	const glyphs = new URL(`${import.meta.env.BASE_URL}fonts/`, assetBase).href + "{fontstack}/{range}.pbf";
	const attribution = '<a href="https://www.tianditu.gov.cn/" target="_blank" rel="noopener noreferrer">© 天地图</a>';
	const approval = approvalNumber.trim().replace(/[&<>"']/g, (char) => ({
		"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
	}[char]!));
	const style: StyleSpecification = {
		version: 8, name: `天地图 ${id}`, glyphs, sources: {},
		layers: [{ id: "background", type: "background", paint: { "background-color": "#e8edf2" } }],
	};
	// Missing authorization never triggers a fallback to another map provider.
	if (!key.trim()) return style;
	for (const [index, layer] of [base, annotation].entries()) {
		const source = `tianditu-${layer}`;
		style.sources[source] = {
			type: "raster", tiles: [buildTiandituTileUrl(layer, key.trim())], tileSize: 256,
			minzoom: 1, maxzoom: id === "terrain" ? 14 : 18,
			...(index === 0 ? { attribution: `${attribution}${approval ? ` | 审图号：${approval}` : ""}` } : {}),
		};
		style.layers.push({ id: source, type: "raster", source, paint: { "raster-fade-duration": 0 } });
	}
	return style;
}

export const TIANDITU_KEY = (import.meta.env.VITE_TIANDITU_KEY || "").trim();
export const MAP_APPROVAL_NUMBER = (import.meta.env.VITE_MAP_APPROVAL_NUMBER || verifiedApproval.number).trim();
export const DEFAULT_BASEMAP_STYLE = normalizeBasemapStyle(import.meta.env.VITE_MAP_DEFAULT_STYLE || "vector");

export function basemapApprovalNumber(styleId: string): string {
	const approvals = {
		vector: import.meta.env.VITE_MAP_APPROVAL_VECTOR,
		imagery: import.meta.env.VITE_MAP_APPROVAL_IMAGERY,
		terrain: import.meta.env.VITE_MAP_APPROVAL_TERRAIN,
	};
	return (approvals[normalizeBasemapStyle(styleId)] || MAP_APPROVAL_NUMBER).trim();
}

export function basemapStatusMessage(status?: number, locale = "zh-CN"): string {
	const ui = locale === "zh-CN" ? BUSINESS_ZH : BUSINESS_EN;
	if (!TIANDITU_KEY) return ui.basemapMissing;
	if (status === 401 || status === 403) return ui.basemapDenied;
	if (status === 429) return ui.basemapRateLimit;
	return ui.basemapFailed;
}
