import type { Map as MapLibreMap, GeoJSONSource, SymbolLayerSpecification } from "maplibre-gl";
import manifestData from "../data/placeLabelManifest.json";
import { OVERLAY_FONT } from "./mapBasemap";
import { ensureOverlayLayerOrder } from "./mapLayerOrder";

export const PLACE_SOURCE = "geonames-places";
export const PLACE_COUNTRIES = "geonames-country-labels";
export const PLACE_CITIES = "geonames-city-labels";
export type CityRecord = [number, string, number, number, number, number, string, string, "en" | "latin", string];
type CountryRecord = [string, string, number, number, "country" | "region", number, number];
type FileInfo = { file: string; sha256: string; count?: number };
type Manifest = { cellSize: number; overview: FileInfo; cells: Record<string, FileInfo> };
const manifest = manifestData as Manifest;
const fileCache = new Map<string, Promise<unknown>>();

export interface PlaceBounds { west: number; east: number; south: number; north: number }

/** Include every cell in the view, including views crossing the date line. */
export function placeCellKeys(bounds: PlaceBounds, cellSize = manifest.cellSize): string[] {
	const cols = 360 / cellSize;
	const rows = 180 / cellSize;
	const east = bounds.east < bounds.west ? bounds.east + 360 : bounds.east;
	const keys = new Set<string>();
	const start = Math.floor((bounds.west + 180) / cellSize);
	const end = Math.min(Math.floor((east + 180) / cellSize), start + cols - 1);
	const bottom = Math.max(0, Math.min(rows - 1, Math.floor((bounds.south + 90) / cellSize)));
	const top = Math.max(0, Math.min(rows - 1, Math.floor((bounds.north + 90) / cellSize)));
	for (let x = start; x <= end; x++) {
		for (let y = bottom; y <= top; y++) keys.add(`${((x % cols) + cols) % cols}-${y}`);
	}
	return [...keys];
}

function inView(lng: number, lat: number, bounds: PlaceBounds): boolean {
	if (lat < bounds.south || lat > bounds.north) return false;
	const east = bounds.east < bounds.west ? bounds.east + 360 : bounds.east;
	if (east - bounds.west >= 360) return true;
	const wrapped = lng + Math.ceil((bounds.west - lng) / 360) * 360;
	return wrapped <= east;
}

export function placeFeatures(countries: CountryRecord[], records: CityRecord[], zoom: number, bounds: PlaceBounds): GeoJSON.FeatureCollection<GeoJSON.Point> {
	const features = new Map<string, GeoJSON.Feature<GeoJSON.Point>>();
	for (const [code, name, lng, lat, kind, minZoom, maxZoom] of countries) {
		if (zoom < minZoom || zoom >= maxZoom) continue;
		features.set(`country-${code}`, { type: "Feature", id: `country-${code}`, geometry: { type: "Point", coordinates: [lng, lat] }, properties: { name, kind, countryCode: code.startsWith("CN-") ? "CN" : code, priority: kind === "country" ? 0 : 1 } });
	}
	for (const [id, name, lng, lat, population, minZoom, countryCode, regionCode, nameSource, featureCode] of records) {
		if (minZoom > zoom || !inView(lng, lat, bounds)) continue;
		features.set(`city-${id}`, { type: "Feature", id: `city-${id}`, geometry: { type: "Point", coordinates: [lng, lat] }, properties: { name, kind: "city", countryCode, regionCode, nameSource, featureCode, priority: -population } });
	}
	return { type: "FeatureCollection", features: [...features.values()] };
}

export function placeLabelLayers(dark = false): SymbolLayerSpecification[] {
	const paint = { "text-color": dark ? "#ffffff" : "#273b4e", "text-halo-color": dark ? "#15202b" : "#ffffff", "text-halo-width": dark ? 1.6 : 1.8 };
	const layers: SymbolLayerSpecification[] = [
		{ id: PLACE_COUNTRIES, type: "symbol", source: PLACE_SOURCE, filter: ["in", ["get", "kind"], ["literal", ["country", "region"]]],
			layout: { visibility: "none", "text-field": ["get", "name"], "text-font": [OVERLAY_FONT], "text-size": ["case", ["==", ["get", "kind"], "country"], 15, 12], "text-max-width": 12, "text-padding": 5, "symbol-sort-key": ["get", "priority"] }, paint },
		{ id: PLACE_CITIES, type: "symbol", source: PLACE_SOURCE, filter: ["==", ["get", "kind"], "city"],
			layout: { visibility: "none", "text-field": ["get", "name"], "text-font": [OVERLAY_FONT], "text-size": ["interpolate", ["linear"], ["zoom"], 3, 11, 8, 12, 14, 14], "text-max-width": 10, "text-padding": 3, "symbol-sort-key": ["get", "priority"] }, paint },
	];
	// MapLibre places upper symbol layers first; country/region names take
	// precedence so dense city labels cannot hide them through collision.
	return [layers[1], layers[0]];
}

async function readLocalFile(info: FileInfo): Promise<unknown> {
	let pending = fileCache.get(info.file);
	if (!pending) {
		pending = (async () => {
			const response = await fetch(`${import.meta.env.BASE_URL}place-labels/${info.file}`);
			if (!response.ok) throw new Error(`Local place data HTTP ${response.status}`);
			const bytes = await response.arrayBuffer();
			const digest = await crypto.subtle.digest("SHA-256", bytes);
			const hash = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
			if (hash !== info.sha256) throw new Error("Local place data checksum mismatch");
			return JSON.parse(new TextDecoder().decode(bytes));
		})();
		fileCache.set(info.file, pending);
		pending.catch(() => fileCache.delete(info.file));
		while (fileCache.size > 32) fileCache.delete(fileCache.keys().next().value!);
	}
	return pending;
}

/** Keeps business sources intact: language changes only replace place labels. */
export function createPlaceLabelController(map: MapLibreMap, options: {
	locale: () => string; style: () => string; onUnavailable: (unavailable: boolean) => void;
}) {
	let generation = 0;
	let disposed = false;
	// Created after map load; tile requests can still keep isStyleLoaded() false.
	let styleReady = true;
	const annotationIds = ["tianditu-cva", "tianditu-cia", "tianditu-cta"];
	function visible(english: boolean) {
		for (const id of annotationIds) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", english ? "none" : "visible");
		for (const id of [PLACE_COUNTRIES, PLACE_CITIES]) if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", english ? "visible" : "none");
	}
	function ensureLayers() {
		if (!map.getSource(PLACE_SOURCE)) map.addSource(PLACE_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] }, attribution: '<a href="https://www.geonames.org/" target="_blank" rel="noopener noreferrer">GeoNames</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener noreferrer">CC BY 4.0</a>' });
		const layers = map.getStyle().layers;
		const annotationIndex = layers.findIndex(l => annotationIds.includes(l.id));
		const before = annotationIndex >= 0 ? layers[annotationIndex + 1]?.id : undefined;
		for (const layer of placeLabelLayers(options.style() === "imagery")) {
			if (!map.getLayer(layer.id)) map.addLayer(layer, before);
		}
		ensureOverlayLayerOrder(map);
	}
	async function refresh() {
		const token = ++generation;
		if (disposed || !styleReady) return;
		if (options.locale() !== "en-US" || !annotationIds.some(id => map.getLayer(id))) {
			visible(false);
			options.onUnavailable(false);
			return;
		}
		try {
			const view = map.getBounds();
			const bounds: PlaceBounds = { west: view.getWest() - 2, east: view.getEast() + 2, south: view.getSouth() - 2, north: view.getNorth() + 2 };
			const zoom = map.getZoom();
			const overview = await readLocalFile(manifest.overview) as { countries: CountryRecord[]; cities: CityRecord[] };
			const chunks = zoom >= 6 ? await Promise.all(placeCellKeys(bounds).filter(key => manifest.cells[key]).map(key => readLocalFile(manifest.cells[key]) as Promise<CityRecord[]>)) : [];
			if (disposed || token !== generation || !styleReady) return;
			ensureLayers();
			(map.getSource(PLACE_SOURCE) as GeoJSONSource).setData(placeFeatures(overview.countries, [...overview.cities, ...chunks.flat()], zoom, bounds));
			visible(true);
			options.onUnavailable(false);
		} catch (error) {
			if (disposed || token !== generation || !styleReady) return;
			visible(false);
			options.onUnavailable(true);
			console.warn("[Place labels] Local English labels unavailable", error);
		}
	}
	const update = () => { void refresh(); };
	const invalidate = () => { styleReady = false; generation++; };
	const styleLoaded = () => { styleReady = true; update(); };
	map.on("moveend", update);
	map.on("styledataloading", invalidate);
	map.on("style.load", styleLoaded);
	return { refresh: update, dispose() { disposed = true; generation++; map.off("moveend", update); map.off("styledataloading", invalidate); map.off("style.load", styleLoaded); } };
}
