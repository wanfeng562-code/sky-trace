import type { FilterSpecification } from "maplibre-gl";

/** 图层 filter：不匹配任何要素（勿用 flight_id === ""，可能误高亮） */
export const HIDE_ALL_FEATURES_FILTER = false;

/** 标记航班高亮圈：无标记时用 false，避免空字符串 filter 误匹配 */
export function markedFlightsFilter(
	ids: readonly string[],
): FilterSpecification {
	const list = ids.filter((id) => typeof id === "string" && id.length > 0);
	if (!list.length) return false;
	if (list.length === 1) {
		return ["==", ["get", "flight_id"], list[0]!];
	}
	return [
		"any",
		...list.map(
			(id) => ["==", ["get", "flight_id"], id] as FilterSpecification,
		),
	];
}
