/**
 * 浏览器端持久缓存（localStorage），用于机场/地名、区划边界、API 结果等。
 * 减轻重复请求并加速二次打开页面时的渲染。
 */

const PREFIX = "skytrace.cache.v1.";
const MAX_KEY_LENGTH = 180;

type CacheEnvelope<T> = {
	exp: number;
	v: T;
};

function safeKey(key: string): string {
	const k = key.replace(/[^\w|:.-]/g, "_").slice(0, MAX_KEY_LENGTH);
	return `${PREFIX}${k}`;
}

export function readPersistentCache<T>(key: string): T | null {
	if (typeof localStorage === "undefined") return null;
	try {
		const raw = localStorage.getItem(safeKey(key));
		if (!raw) return null;
		const entry = JSON.parse(raw) as CacheEnvelope<T>;
		if (entry.exp > 0 && Date.now() > entry.exp) {
			localStorage.removeItem(safeKey(key));
			return null;
		}
		return entry.v;
	} catch {
		return null;
	}
}

export function writePersistentCache<T>(
	key: string,
	value: T,
	ttlMs: number,
): void {
	if (typeof localStorage === "undefined") return;
	try {
		const envelope: CacheEnvelope<T> = {
			exp: ttlMs > 0 ? Date.now() + ttlMs : 0,
			v: value,
		};
		localStorage.setItem(safeKey(key), JSON.stringify(envelope));
	} catch {
		/* quota exceeded — ignore */
	}
}

export function removePersistentCache(key: string): void {
	try {
		localStorage.removeItem(safeKey(key));
	} catch {
		/* ignore */
	}
}

/** 地名/区域中文：默认保留 90 天 */
export const NAME_CACHE_TTL_MS = 90 * 24 * 60 * 60 * 1000;

/** 机场列表：与 API 内存缓存对齐 */
export const AIRPORTS_CACHE_TTL_MS = 30 * 60 * 1000;

/** 区划边界 GeoJSON：7 天 */
export const BOUNDARY_CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

/** 回放帧数据：10 分钟（同参数重复查询） */
export const PLAYBACK_CACHE_TTL_MS = 10 * 60 * 1000;
