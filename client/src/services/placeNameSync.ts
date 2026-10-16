import {
	fetchPlaceNames,
	upsertPlaceNames,
	type PlaceNameRecord,
} from "./api";
import { BACKEND_ENABLED } from "../config/backend";
import {
	NAME_CACHE_TTL_MS,
	readPersistentCache,
	writePersistentCache,
} from "./persistentCache";

const serverMem = new Map<string, PlaceNameRecord>();
const pendingUpsert = new Map<string, PlaceNameRecord>();
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let hydratePromise: Promise<void> | null = null;
let retryDelay = 800;

function scheduleFlush() {
	if (flushTimer !== null) return;
	flushTimer = setTimeout(() => {
		flushTimer = null;
		void flushPendingToServer();
	}, retryDelay);
}

async function flushPendingToServer(): Promise<void> {
	if (!pendingUpsert.size) return;
	const items = [...pendingUpsert.values()];
	pendingUpsert.clear();
	try {
		await upsertPlaceNames(items);
		retryDelay = 800;
		for (const item of items) {
			serverMem.set(item.cache_key, item);
		}
	} catch (e) {
		console.warn("[placeNameSync] upsert failed", e);
		retryDelay = Math.min(retryDelay * 2, 30_000);
		for (const item of items) {
			if (!pendingUpsert.has(item.cache_key)) pendingUpsert.set(item.cache_key, item);
		}
		scheduleFlush();
	}
}

export async function hydratePlaceNamesFromServer(
	keys: string[],
): Promise<void> {
	const missing = keys.filter(
		(k) => k && !serverMem.has(k) && !readPersistentCache(k),
	);
	if (!missing.length) return;

	const chunkSize = 80;
	for (let i = 0; i < missing.length; i += chunkSize) {
		const chunk = missing.slice(i, i + chunkSize);
		try {
			const rows = await fetchPlaceNames(chunk);
			for (const row of rows) {
				serverMem.set(row.cache_key, row);
				writePersistentCache(row.cache_key, row.name_zh, NAME_CACHE_TTL_MS);
			}
		} catch (e) {
			console.warn("[placeNameSync] hydrate chunk failed", e);
		}
	}
}

export function queuePlaceNameSync(record: PlaceNameRecord): void {
	if (!record.cache_key || !record.name_zh) return;
	writePersistentCache(record.cache_key, record.name_zh, NAME_CACHE_TTL_MS);
	serverMem.set(record.cache_key, record);
	if (!BACKEND_ENABLED) return;
	pendingUpsert.set(record.cache_key, record);
	scheduleFlush();
}

export function readCachedPlaceNameZh(cacheKey: string): string | null {
	const mem = serverMem.get(cacheKey);
	if (mem?.name_zh) return mem.name_zh;
	const local = readPersistentCache<unknown>(cacheKey);
	if (typeof local === "string" && local) return local;
	// Older clients stored an entire AirportDisplayNames object under this key.
	// Keep its display name, but rebuild country/city fields from current data.
	if (local && typeof local === "object" && "nameZh" in local && typeof local.nameZh === "string" && local.nameZh) {
		writePersistentCache(cacheKey, local.nameZh, NAME_CACHE_TTL_MS);
		return local.nameZh;
	}
	return null;
}

export function preloadPlaceNames(keys: string[]): Promise<void> {
	if (!keys.length) return Promise.resolve();
	if (hydratePromise) return hydratePromise;
	hydratePromise = hydratePlaceNamesFromServer(keys).finally(() => {
		hydratePromise = null;
	});
	return hydratePromise;
}
