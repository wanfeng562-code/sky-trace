import {
	fetchPlaceNames,
	upsertPlaceNames,
	type PlaceNameRecord,
} from "./api";
import {
	NAME_CACHE_TTL_MS,
	readPersistentCache,
	writePersistentCache,
} from "./persistentCache";

const serverMem = new Map<string, PlaceNameRecord>();
const pendingUpsert = new Map<string, PlaceNameRecord>();
let flushTimer: ReturnType<typeof setTimeout> | null = null;
let hydratePromise: Promise<void> | null = null;

function scheduleFlush() {
	if (flushTimer !== null) return;
	flushTimer = setTimeout(() => {
		flushTimer = null;
		void flushPendingToServer();
	}, 800);
}

async function flushPendingToServer(): Promise<void> {
	if (!pendingUpsert.size) return;
	const items = [...pendingUpsert.values()];
	pendingUpsert.clear();
	try {
		await upsertPlaceNames(items);
		for (const item of items) {
			serverMem.set(item.cache_key, item);
		}
	} catch (e) {
		console.warn("[placeNameSync] upsert failed", e);
		for (const item of items) {
			pendingUpsert.set(item.cache_key, item);
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
	pendingUpsert.set(record.cache_key, record);
	scheduleFlush();
}

export function readCachedPlaceNameZh(cacheKey: string): string | null {
	const mem = serverMem.get(cacheKey);
	if (mem?.name_zh) return mem.name_zh;
	const local = readPersistentCache<string>(cacheKey);
	if (typeof local === "string" && local) return local;
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
