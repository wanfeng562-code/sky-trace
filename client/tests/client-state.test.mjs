import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { after, test } from "node:test";
import axios from "axios";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";
import { createServer } from "vite";

const calls = [];
const oldAdapter = axios.defaults.adapter;
axios.defaults.adapter = async config => {
	const body = typeof config.data === "string" ? JSON.parse(config.data) : config.data;
	calls.push({ method: config.method, body });
	return { data: { code: 0, data: { upserted: body?.items?.length || 0, items: [] } }, status: 200, statusText: "OK", headers: {}, config };
};
const root = fileURLToPath(new URL("../", import.meta.url));
const server = await createServer({ root, server: { middlewareMode: true, ws: false }, appType: "custom" });
const api = await server.ssrLoadModule("/src/services/api.ts");
const cache = await server.ssrLoadModule("/src/services/persistentCache.ts");
const names = await server.ssrLoadModule("/src/services/placeNameSync.ts");
const airports = await server.ssrLoadModule("/src/data/airportDisplay.ts");
const sockets = await server.ssrLoadModule("/src/services/ws.ts");
const zh = await server.ssrLoadModule("/src/utils/zhLocale.ts");
const flightStore = await server.ssrLoadModule("/src/stores/flight.ts");
const local = new Map();
globalThis.localStorage = { getItem: k => local.get(k) ?? null, setItem: (k, v) => local.set(k, v), removeItem: k => local.delete(k) };
after(async () => { axios.defaults.adapter = oldAdapter; delete globalThis.localStorage; await server.close(); });

test("departure and arrival region filters cannot expand to the whole country", async () => {
	setActivePinia(createPinia());
	const store = flightStore.useFlightStore();
	try {
		store.flights = [
			{ flight_id: "beijing", lat: 0, lon: 0, departure_airport: "PEK", arrival_airport: "CAN" },
			{ flight_id: "guangzhou", lat: 0, lon: 0, departure_airport: "CAN", arrival_airport: "PEK" },
			{ flight_id: "taipei", lat: 0, lon: 0, departure_airport: "TPE", arrival_airport: "TPE" },
		];
		store.filterCountry = "CN";
		await nextTick();
		store.filterCountryMode = "departure";
		assert.equal(store.filteredFlights.length, 3);
		store.filterRegion = "BJ";
		await nextTick();
		assert.deepEqual(store.filteredFlights.map(f => f.flight_id), ["beijing"]);
		store.filterCountryMode = "arrival";
		assert.deepEqual(store.filteredFlights.map(f => f.flight_id), ["guangzhou"]);
		store.filterRegion = "TW";
		await nextTick();
		assert.deepEqual(store.filteredFlights.map(f => f.flight_id), ["taipei"]);
	} finally { store.$dispose(); }
});

test("place name writes split large batches and match backend string limits", async () => {
	calls.length = 0;
	const items = Array.from({ length: 1001 }, (_, i) => ({ cache_key: `ap.zh:T${i}`, name_zh: "测试", name_en: "x".repeat(600), source_text: "y".repeat(600) }));
	assert.equal(await api.upsertPlaceNames([...items, { cache_key: "x".repeat(181), name_zh: "invalid" }, { cache_key: "empty", name_zh: " " }]), 1001);
	assert.deepEqual(calls.map(call => call.body.items.length), [500, 500, 1]);
	for (const call of calls) for (const item of call.body.items) {
		assert.equal(item.name_en.length, 500); assert.equal(item.source_text.length, 500);
	}
});

test("older airport display objects migrate without preserving outdated country labels", () => {
	const key = "ap.zh:v2:TPE";
	cache.writePersistentCache(key, { iata: "TPE", nameZh: "桃园机场", countryLabel: "Taiwan", cityZh: "old city" }, cache.NAME_CACHE_TTL_MS);
	const display = airports.formatAirportDisplay({ iata: "TPE", name: "Taoyuan International", city: "Taipei", country: "TW", lat: 25, lon: 121 });
	assert.equal(display.nameZh, "桃园机场");
	assert.equal(display.countryLabel, "中国台湾");
	assert.equal(display.nameEn, "Taoyuan International");
	assert.equal(cache.readPersistentCache(key), "桃园机场");
});

test("queued place names also stay within the server batch contract", async () => {
	calls.length = 0;
	for (let i = 0; i < 700; i++) names.queuePlaceNameSync({ cache_key: `test.queue:${i}`, name_zh: "名称" });
	await new Promise(resolve => setTimeout(resolve, 1050));
	assert.deepEqual(calls.map(call => call.body.items.length), [500, 200]);
	assert.equal(names.readCachedPlaceNameZh("test.queue:699"), "名称");
});

test("simplified names are stable and traditional airport names convert correctly", () => {
	for (const name of ["中国台湾", "中国香港", "中国澳门", "广州白云国际机场", "北京首都国际机场", "Beijing Capital"])
		assert.equal(zh.toSimplifiedChinese(name), name);
	assert.equal(zh.toSimplifiedChinese("臺灣桃園國際機場"), "台湾桃园国际机场");
	assert.equal(zh.toSimplifiedChinese("香港國際機場"), "香港国际机场");
	assert.ok(zh.containsTraditionalChinese("臺灣"));
	assert.ok(!zh.containsTraditionalChinese("台湾"));
});

test("closing an offline socket cancels its scheduled reconnection", () => {
	const saved = { WebSocket: globalThis.WebSocket, setTimeout: globalThis.setTimeout, clearTimeout: globalThis.clearTimeout };
	const pending = new Map(), created = [];
	globalThis.setTimeout = fn => { pending.set(1, fn); return 1; };
	globalThis.clearTimeout = id => pending.delete(id);
	globalThis.WebSocket = class { constructor() { created.push(this); } close() { this.onclose?.(); } };
	try {
		const socket = sockets.createFlightsSocket(() => {});
		created[0].onclose();
		assert.equal(pending.size, 1);
		const stale = pending.get(1);
		socket.close();
		assert.equal(pending.size, 0);
		stale();
		assert.equal(created.length, 1);
	} finally { Object.assign(globalThis, saved); }
});

test("v1 corrupt names cannot override freshly generated airport names", () => {
	cache.writePersistentCache("ap.zh:HKG", "旧转换错误", cache.NAME_CACHE_TTL_MS);
	const display = airports.formatAirportDisplay({ iata: "HKG", name: "Hong Kong International", city: "Hong Kong", country: "HK", lat: 22, lon: 114 });
	assert.equal(display.nameZh, "香港");
	assert.equal(display.countryLabel, "中国香港");
	assert.equal(cache.readPersistentCache("ap.zh:v2:HKG"), "香港");
});
