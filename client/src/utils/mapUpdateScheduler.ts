/**
 * 将同一帧内的多次地图 setData / 图层更新合并为一次 requestAnimationFrame 回调，
 * 降低 MapLibre 重复重绘导致的卡顿。
 */

const pending = new Set<() => void>();
let rafId: number | null = null;

export function scheduleMapUpdate(fn: () => void): void {
	pending.add(fn);
	if (rafId !== null) return;
	rafId = requestAnimationFrame(() => {
		rafId = null;
		const batch = [...pending];
		pending.clear();
		for (const run of batch) {
			try {
				run();
			} catch (e) {
				console.warn("[mapUpdateScheduler]", e);
			}
		}
	});
}

export function cancelScheduledMapUpdates(): void {
	pending.clear();
	if (rafId !== null) {
		cancelAnimationFrame(rafId);
		rafId = null;
	}
}
