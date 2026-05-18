import type { IControl, Map as MapLibreMap } from "maplibre-gl";

/** 约 50km 视野对应的 zoom（按纬度估算） */
export function zoomForScaleKm(lat: number, km: number): number {
	const latRad = (lat * Math.PI) / 180;
	const mPerPxAtZ0 = 156543.03 * Math.cos(latRad);
	const targetMPerPx = (km * 1000) / 520;
	return Math.min(14, Math.max(3, Math.log2(mPerPxAtZ0 / targetMPerPx)));
}

/**
 * 置于 NavigationControl 下方的「定位到我的位置」按钮。
 */
export class GeolocateControl implements IControl {
	private _map?: MapLibreMap;
	private _container?: HTMLDivElement;
	private _onLocate?: (lat: number, lon: number) => void;

	constructor(options?: { onLocate?: (lat: number, lon: number) => void }) {
		this._onLocate = options?.onLocate;
	}

	onAdd(map: MapLibreMap): HTMLElement {
		this._map = map;
		const container = document.createElement("div");
		container.className =
			"maplibregl-ctrl maplibregl-ctrl-group sky-geolocate-control";

		const btn = document.createElement("button");
		btn.type = "button";
		btn.className = "maplibregl-ctrl-icon sky-geolocate-btn";
		btn.title = "缩放到我的位置（约 50km）";
		btn.setAttribute("aria-label", "定位到我的位置");
		btn.innerHTML =
			'<svg viewBox="0 0 20 20" width="18" height="18" fill="currentColor"><path d="M10 2a1 1 0 011 1v1.07A6 6 0 0116.93 9H18a1 1 0 110 2h-1.07A6 6 0 0111 15.93V17a1 1 0 11-2 0v-1.07A6 6 0 014.07 11H3a1 1 0 110-2h1.07A6 6 0 019 4.07V3a1 1 0 011-1zm0 4a4 4 0 100 8 4 4 0 000-8z"/></svg>';
		btn.addEventListener("click", () => this.locate());
		container.appendChild(btn);
		this._container = container;
		return container;
	}

	onRemove(): void {
		this._container?.remove();
		this._map = undefined;
	}

	locate(): void {
		if (!this._map) return;
		void flyToUserLocation(this._map, this._onLocate);
	}
}

/** 从 Vue 地图控制台调用：飞到用户位置（约 50km 视野） */
export function flyToUserLocation(
	map: MapLibreMap,
	onLocate?: (lat: number, lon: number) => void,
): Promise<void> {
	return new Promise((resolve) => {
		if (!navigator.geolocation) {
			window.alert("当前浏览器不支持定位");
			resolve();
			return;
		}
		navigator.geolocation.getCurrentPosition(
			(pos) => {
				const { latitude, longitude } = pos.coords;
				const zoom = zoomForScaleKm(latitude, 50);
				map.flyTo({
					center: [longitude, latitude],
					zoom,
					essential: true,
				});
				onLocate?.(latitude, longitude);
				resolve();
			},
			(err) => {
				const msg =
					err.code === err.PERMISSION_DENIED
						? "需要位置权限才能定位"
						: `定位失败：${err.message}`;
				window.alert(msg);
				resolve();
			},
			{ enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 },
		);
	});
}
