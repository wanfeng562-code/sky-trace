import type { Map as MapLibreMap } from "maplibre-gl";

const CLICK_TOLERANCE_PX = 5;

function pointerAngle(
	map: MapLibreMap,
	clientX: number,
	clientY: number,
): number {
	const rect = map.getContainer().getBoundingClientRect();
	const cx = rect.left + rect.width / 2;
	const cy = rect.top + rect.height / 2;
	return (Math.atan2(clientY - cy, clientX - cx) * 180) / Math.PI;
}

function normalizeAngleDelta(delta: number): number {
	if (delta > 180) return delta - 360;
	if (delta < -180) return delta + 360;
	return delta;
}

/**
 * 为自定义指南针按钮绑定拖拽旋转；短按无位移时触发复位北向。
 * 行为对齐 MapLibre NavigationControl 指南针。
 */
export function attachCompassRotateControl(
	map: MapLibreMap,
	element: HTMLElement,
	onReset: () => void,
): () => void {
	let dragging = false;
	let prevAngle = 0;
	let startX = 0;
	let startY = 0;
	let hasMoved = false;

	const beginPointer = (clientX: number, clientY: number) => {
		dragging = true;
		hasMoved = false;
		startX = clientX;
		startY = clientY;
		prevAngle = pointerAngle(map, clientX, clientY);
		map.dragPan.disable();
		element.classList.add("compass-dragging");
	};

	const movePointer = (clientX: number, clientY: number) => {
		if (!dragging) return;
		const dx = clientX - startX;
		const dy = clientY - startY;
		if (dx * dx + dy * dy > CLICK_TOLERANCE_PX * CLICK_TOLERANCE_PX) {
			hasMoved = true;
		}
		const angle = pointerAngle(map, clientX, clientY);
		const delta = normalizeAngleDelta(angle - prevAngle);
		if (Math.abs(delta) > 0.01) {
			map.setBearing(map.getBearing() + delta);
		}
		prevAngle = angle;
	};

	const endPointer = () => {
		if (!dragging) return;
		dragging = false;
		map.dragPan.enable();
		element.classList.remove("compass-dragging");
		if (!hasMoved) onReset();
	};

	const onMouseMove = (e: MouseEvent) => movePointer(e.clientX, e.clientY);
	const onMouseUp = () => {
		document.removeEventListener("mousemove", onMouseMove);
		document.removeEventListener("mouseup", onMouseUp);
		endPointer();
	};

	const onMouseDown = (e: MouseEvent) => {
		if (e.button !== 0) return;
		e.preventDefault();
		e.stopPropagation();
		beginPointer(e.clientX, e.clientY);
		document.addEventListener("mousemove", onMouseMove);
		document.addEventListener("mouseup", onMouseUp);
	};

	const onTouchMove = (e: TouchEvent) => {
		if (e.touches.length !== 1) return;
		e.preventDefault();
		movePointer(e.touches[0].clientX, e.touches[0].clientY);
	};

	const onTouchEnd = (e: TouchEvent) => {
		document.removeEventListener("touchmove", onTouchMove);
		document.removeEventListener("touchend", onTouchEnd);
		document.removeEventListener("touchcancel", onTouchEnd);
		if (e.changedTouches.length === 1) {
			const t = e.changedTouches[0];
			movePointer(t.clientX, t.clientY);
		}
		endPointer();
	};

	const onTouchStart = (e: TouchEvent) => {
		if (e.touches.length !== 1) return;
		e.preventDefault();
		beginPointer(e.touches[0].clientX, e.touches[0].clientY);
		document.addEventListener("touchmove", onTouchMove, { passive: false });
		document.addEventListener("touchend", onTouchEnd);
		document.addEventListener("touchcancel", onTouchEnd);
	};

	// 复位在 mouseup 处理；阻止浏览器再触发 click 导致重复复位
	const onClick = (e: MouseEvent) => {
		e.preventDefault();
		e.stopPropagation();
	};

	element.addEventListener("mousedown", onMouseDown);
	element.addEventListener("touchstart", onTouchStart, { passive: false });
	element.addEventListener("click", onClick, true);

	return () => {
		document.removeEventListener("mousemove", onMouseMove);
		document.removeEventListener("mouseup", onMouseUp);
		document.removeEventListener("touchmove", onTouchMove);
		document.removeEventListener("touchend", onTouchEnd);
		document.removeEventListener("touchcancel", onTouchEnd);
		element.removeEventListener("mousedown", onMouseDown);
		element.removeEventListener("touchstart", onTouchStart);
		element.removeEventListener("click", onClick, true);
		if (dragging) {
			map.dragPan.enable();
			element.classList.remove("compass-dragging");
		}
	};
}
