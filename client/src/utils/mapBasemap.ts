/** OpenFreeMap 样式 ID → style.json URL
 * 生产环境直接访问 OFM CDN；开发环境走 Vite dev proxy（支持 HTTP_PROXY）。
 */
export function buildOpenFreeMapStyleUrl(styleId: string): string {
	if (import.meta.env.PROD) {
		return `https://tiles.openfreemap.org/styles/${styleId}`;
	}
	const origin = typeof window !== "undefined" ? window.location.origin : "";
	if (origin) {
		return `${origin}/openfreemap-proxy/styles/${styleId}`;
	}
	return `https://tiles.openfreemap.org/styles/${styleId}`;
}

/** MapLibre transformRequest：重写瓦片/字体/精灵 URL。
 * - 生产环境：直接访问外部 CDN（tile 供应商均支持浏览器跨域请求）。
 * - 开发环境：改写为本地 Vite dev proxy 路径，以便 HTTP_PROXY 环境变量生效。
 */
export function rewriteMapResourceUrl(url: string): string {
	if (import.meta.env.PROD) {
		return url;
	}
	const origin = typeof window !== "undefined" ? window.location.origin : "";
	if (url.startsWith("https://api.maptiler.com")) {
		return url.replace("https://api.maptiler.com", `${origin}/maptiler-proxy`);
	}
	if (url.startsWith("https://tiles.stadiamaps.com")) {
		return url.replace(
			"https://tiles.stadiamaps.com",
			`${origin}/stadia-proxy`,
		);
	}
	if (url.startsWith("https://tiles.openfreemap.org")) {
		return url.replace(
			"https://tiles.openfreemap.org",
			`${origin}/openfreemap-proxy`,
		);
	}
	return url;
}

/** OpenFreeMap 字体栈（glyphs 托管于 tiles.openfreemap.org/fonts） */
export const OPENFREEMAP_LABEL_FONTS = [
	"Noto Sans Bold",
	"Noto Sans Regular",
] as const;

/** 行政/地名标注图层：保留样式内置 text-field，仅调整字体 */
export function isOpenFreeMapPlaceLabelLayer(layerId: string): boolean {
	return (
		layerId.startsWith("label_") ||
		layerId === "airport" ||
		layerId.startsWith("water_name")
	);
}
