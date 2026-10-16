import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { test, after } from "node:test";
import { createServer } from "vite";
import { validateStyleMin } from "@maplibre/maplibre-gl-style-spec";
import Pbf from "pbf";

const root = fileURLToPath(new URL("../", import.meta.url));
const server = await createServer({ root, server: { middlewareMode: true, ws: false }, appType: "custom" });
after(() => server.close());
const basemap = await server.ssrLoadModule("/src/utils/mapBasemap.ts");
const geo = await server.ssrLoadModule("/src/data/countries.ts");
const layouts = await server.ssrLoadModule("/src/config/mapLayerStyles.ts");
const places = await server.ssrLoadModule("/src/utils/localPlaceLabels.ts");

test("all modes use official base and matching annotations without third-party resources", () => {
	for (const [id, base, annotation] of [["vector", "vec", "cva"], ["imagery", "img", "cia"], ["terrain", "ter", "cta"]]) {
		const style = basemap.createBasemapStyle(id, "test&key", "GS(test)<unsafe>", "https://example.test/");
		assert.deepEqual(validateStyleMin(style), []);
		assert.deepEqual(style.layers.slice(1).map(l => l.id), [`tianditu-${base}`, `tianditu-${annotation}`]);
		for (const source of Object.values(style.sources)) {
			const url = new URL(source.tiles[0]);
			assert.equal(url.protocol, "https:");
			assert.equal(url.hostname, "t0.tianditu.gov.cn");
			assert.equal(url.searchParams.get("TILEMATRIXSET"), "w");
			assert.equal(url.searchParams.get("tk"), "test&key");
			assert.equal(source.tileSize, 256);
		}
		assert.ok(style.sources[`tianditu-${base}`].attribution.includes("&lt;unsafe&gt;"));
		assert.equal(new URL(style.glyphs).hostname, "example.test");
	}
});

test("missing key and obsolete configuration never restore an overseas map", () => {
	for (const id of ["vector", "imagery", "terrain", "streets-v2-dark", "liberty"]) {
		const style = basemap.createBasemapStyle(id, "  ");
		assert.deepEqual(style.sources, {});
		assert.equal(style.layers.length, 1);
		assert.deepEqual(validateStyleMin(style), []);
	}
	assert.equal(basemap.normalizeBasemapStyle("liberty"), "vector");
	assert.throws(() => basemap.buildTiandituTileUrl("foreign", "key"));
});

test("Taiwan, Hong Kong and Macao remain regions of China and share its airport index", () => {
	const china = geo.COUNTRIES.find(c => c.code === "CN");
	for (const code of ["TW", "HK", "MO"]) {
		assert.ok(china.regions.some(r => r.code === code));
		assert.ok(!geo.COUNTRIES.some(c => c.code === code));
	}
	for (const airport of ["TPE", "TSA", "KHH", "HKG", "MFM"]) assert.equal(geo.AIRPORT_TO_COUNTRY[airport], "CN");
});

test("overlay layout properties validate with the new basemap", () => {
	const style = basemap.createBasemapStyle("vector", "test-key");
	style.sources.overlay = { type: "geojson", data: { type: "FeatureCollection", features: [] } };
	for (const [id, layout, paint] of [
		["aqi", layouts.aqiLabelLayout(), layouts.aqiLabelPaint()],
		["grid", layouts.weatherGridMarkerLayout(), layouts.weatherGridMarkerPaint()],
	]) style.layers.push({ id, type: "symbol", source: "overlay", layout, paint });
	assert.deepEqual(validateStyleMin(style), []);
});

test("packaged fonts have valid glyphs, checksums and a license", async () => {
	const fonts = new URL("../public-app/fonts/", import.meta.url);
	const manifest = JSON.parse(await readFile(new URL("manifest.json", fonts), "utf8"));
	for (const entry of manifest.files) {
		const data = await readFile(new URL(entry.file, fonts));
		assert.equal(createHash("sha256").update(data).digest("hex"), entry.sha256);
	}
	assert.ok(manifest.files.some(f => /license/i.test(f.file)));
	const ids = new Set();
	function glyph(tag, glyph, pbf) { if (tag === 1) glyph.id = pbf.readVarint(); }
	function stack(tag, _, pbf) { if (tag === 3) ids.add(pbf.readMessage(glyph, {}).id); }
	function font(tag, _, pbf) { if (tag === 1) pbf.readMessage(stack, {}); }
	for (const range of ["0-255", "8448-8703"]) {
		new Pbf(await readFile(new URL(`Noto Sans Regular/${range}.pbf`, fonts))).readFields(font, {});
	}
	for (const char of "CAN123°↑") assert.ok(ids.has(char.codePointAt(0)), `Missing glyph ${char}`);
});

test("published public directory excludes historical boundary datasets", async () => {
	assert.equal(server.config.publicDir.replaceAll("\\", "/"), `${root.replaceAll("\\", "/").replace(/\/$/, "")}/public-app`);
	const publishedFiles = await readdir(new URL("../public-app/", import.meta.url));
	assert.ok(!publishedFiles.includes("geo"));
	assert.ok(!publishedFiles.includes("404.html"), "Use Cloudflare Pages native SPA fallback");
	const redirects = await readFile(new URL("../public-app/_redirects", import.meta.url), "utf8");
	assert.ok(!/maptiler|stadia|openfreemap/i.test(redirects));
	assert.deepEqual(redirects.split(/\r?\n/).map(line => line.trim()).filter(line => line && !line.startsWith("#")), []);
});

test("all local city records are published once with matching checksums and CN region membership", async () => {
	const folder = new URL("../public-app/place-labels/", import.meta.url);
	const manifest = JSON.parse(await readFile(new URL("manifest.json", folder), "utf8"));
	assert.deepEqual(manifest, JSON.parse(await readFile(new URL("../src/data/placeLabelManifest.json", import.meta.url), "utf8")));
	const ids = new Set(), names = { en: 0, latin: 0 }, countryCounts = {}, chinaRegions = { TW: 0, HK: 0, MO: 0 };
	for (const [cell, entry] of Object.entries(manifest.cells)) {
		const bytes = await readFile(new URL(entry.file, folder));
		assert.equal(createHash("sha256").update(bytes).digest("hex"), entry.sha256);
		const rows = JSON.parse(bytes);
		assert.equal(rows.length, entry.count);
		for (const [id, name, lng, lat, population, zoom, country, region, nameSource] of rows) {
			assert.ok(!ids.has(id), `Duplicate ${id}`);
			ids.add(id);
			assert.ok(name && !/[\p{Script=Han}\p{Script=Cyrillic}\p{Script=Arabic}]/u.test(name));
			assert.ok(lng >= -180 && lng <= 180 && lat >= -90 && lat <= 90);
			assert.equal(cell, `${Math.min(17, Math.floor((lng + 180) / 20))}-${Math.min(8, Math.floor((lat + 90) / 20))}`);
			assert.ok(population >= 0 && zoom >= 3 && zoom <= 13);
			assert.ok(!["TW", "HK", "MO"].includes(country));
			if (country === "CN" && region in chinaRegions) chinaRegions[region]++;
			assert.ok(nameSource in names);
			names[nameSource]++;
			countryCounts[country] = (countryCounts[country] || 0) + 1;
		}
	}
	assert.equal(ids.size, manifest.recordCount);
	assert.equal(ids.size, 236046);
	assert.deepEqual(names, manifest.nameCounts);
	assert.deepEqual(countryCounts, manifest.countryCounts);
	assert.deepEqual(chinaRegions, { TW: 89, HK: 325, MO: 8 });
	const bytes = await readFile(new URL(manifest.overview.file, folder));
	assert.equal(createHash("sha256").update(bytes).digest("hex"), manifest.overview.sha256);
	const overview = JSON.parse(bytes);
	assert.equal(overview.countries.filter(r => r[4] === "country").length, 195);
	assert.equal(overview.countries.filter(r => r[4] === "region").length, 3);
	for (const [code, name, , , kind] of overview.countries) {
		assert.ok(!["TW", "HK", "MO"].includes(code));
		if (code.startsWith("CN-")) { assert.equal(kind, "region"); assert.ok(name.endsWith(", China")); }
	}
	for (const row of overview.cities) { assert.ok(ids.has(row[0])); assert.ok(row[5] < 6); }
	assert.ok((await readFile(new URL("LICENSE.txt", folder), "utf8")).includes("Attribution 4.0"));
});

test("English label styles validate over every official basemap", () => {
	for (const mode of ["vector", "imagery", "terrain"]) {
		const style = basemap.createBasemapStyle(mode, "test-key");
		style.sources[places.PLACE_SOURCE] = { type: "geojson", data: { type: "FeatureCollection", features: [] } };
		style.layers.push(...places.placeLabelLayers(mode === "imagery"));
		assert.deepEqual(validateStyleMin(style), []);
		assert.ok(style.layers.slice(-2).every(l => l.layout["text-font"][0] === basemap.OVERLAY_FONT));
		assert.equal(style.layers.at(-1).id, places.PLACE_COUNTRIES);
	}
});

test("spatial loading handles the date line, repeated worlds and polar views", () => {
	assert.deepEqual(new Set(places.placeCellKeys({west:170,east:-170,south:-5,north:5})), new Set(["17-4", "0-4"]));
	assert.deepEqual(new Set(places.placeCellKeys({west:530,east:550,south:-5,north:5})), new Set(["17-4", "0-4"]));
	assert.equal(places.placeCellKeys({west:-540,east:540,south:-90,north:90}).length, 162);
	assert.ok(places.placeCellKeys({west:0,east:1,south:89,north:92}).every(k => k.endsWith("-8")));
	const city = (id, lng, zoom) => [id, `City ${id}`, lng, 0, 10000, zoom, "CN", "TW", "en", "PPL"];
	const features = places.placeFeatures([], [city(1,179,4),city(1,179,4),city(2,-179,4),city(3,0,4),city(4,178,8)], 5, {west:170,east:-170,south:-5,north:5}).features;
	assert.deepEqual(features.map(f => f.id), ["city-1", "city-2"]);
	assert.ok(features.every(f => f.properties.countryCode === "CN"));
});
