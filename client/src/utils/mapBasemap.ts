/** OpenFreeMap 样式 ID → 代理后的 style.json URL */
export function buildOpenFreeMapStyleUrl(styleId: string): string {
	const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
		/\/$/,
		"",
	);
	if (apiBase) {
		return `${apiBase}/tiles/openfreemap/styles/${styleId}`;
	}
	const origin =
		typeof window !== "undefined" ? window.location.origin : "";
	if (origin) {
		return `${origin}/openfreemap-proxy/styles/${styleId}`;
	}
	return `https://tiles.openfreemap.org/styles/${styleId}`;
}

/** MapLibre transformRequest：将外网瓦片域名改写为本地/后端代理 */
export function rewriteMapResourceUrl(url: string): string {
	const origin =
		typeof window !== "undefined" ? window.location.origin : "";
	const apiBase = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(
		/\/$/,
		"",
	);

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
		if (apiBase) {
			return url.replace(
				"https://tiles.openfreemap.org",
				`${apiBase}/tiles/openfreemap`,
			);
		}
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
