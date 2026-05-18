import type { Map as MapLibreMap } from "maplibre-gl";

type HighlightOpts = {
	selectedId: string | null;
	markedIds: readonly string[];
	hoveredId: string | null;
};

let lastSelected: string | null = null;
let lastHovered: string | null = null;
const lastMarked = new Set<string>();

function setState(
	map: MapLibreMap,
	sourceId: string,
	featureId: string,
	key: string,
	value: boolean,
) {
	try {
		if (value) {
			map.setFeatureState({ source: sourceId, id: featureId }, { [key]: true });
		} else {
			map.removeFeatureState({ source: sourceId, id: featureId }, key);
		}
	} catch {
		/* feature may not exist yet */
	}
}

/** Sync selected / marked / hover rings via feature-state (no setData). */
export function syncFlightHighlightStates(
	map: MapLibreMap,
	sourceId: string,
	opts: HighlightOpts,
): void {
	const { selectedId, markedIds, hoveredId } = opts;

	if (lastSelected !== selectedId) {
		if (lastSelected) {
			setState(map, sourceId, lastSelected, "selected", false);
		}
		if (selectedId) {
			setState(map, sourceId, selectedId, "selected", true);
		}
		lastSelected = selectedId;
	}

	if (lastHovered !== hoveredId) {
		if (lastHovered) {
			setState(map, sourceId, lastHovered, "hover", false);
		}
		if (hoveredId) {
			setState(map, sourceId, hoveredId, "hover", true);
		}
		lastHovered = hoveredId;
	}

	const nextMarked = new Set(markedIds);
	for (const id of lastMarked) {
		if (!nextMarked.has(id)) {
			setState(map, sourceId, id, "marked", false);
		}
	}
	for (const id of nextMarked) {
		if (!lastMarked.has(id)) {
			setState(map, sourceId, id, "marked", true);
		}
	}
	lastMarked.clear();
	for (const id of nextMarked) {
		lastMarked.add(id);
	}
}

export function clearFlightFeatureStates(
	map: MapLibreMap,
	sourceId: string,
	removedIds: Iterable<string>,
): void {
	for (const id of removedIds) {
		try {
			map.removeFeatureState({ source: sourceId, id });
		} catch {
			/* ignore */
		}
		if (id === lastSelected) lastSelected = null;
		if (id === lastHovered) lastHovered = null;
		lastMarked.delete(id);
	}
}

export function resetFlightFeatureStateTracking(): void {
	lastSelected = null;
	lastHovered = null;
	lastMarked.clear();
}
