import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { test, after } from "node:test";
import { createServer } from "vite";
import axios from "axios";
axios.defaults.adapter = async config => ({data:{data:{upserted:JSON.parse(config.data || "{}").items?.length || 0}},status:200,statusText:"OK",headers:{},config});
const root = fileURLToPath(new URL("../", import.meta.url));
const server = await createServer({ root, server: { middlewareMode: true, ws: false }, appType: "custom" });
after(() => server.close());
const geo = await server.ssrLoadModule("/src/data/countries.ts");
const hierarchy = await server.ssrLoadModule("/src/data/geoHierarchy.ts");
const names = await server.ssrLoadModule("/src/data/geoNamesEn.ts");
const filters = await server.ssrLoadModule("/src/utils/flightFilters.ts");
const detail = await server.ssrLoadModule("/src/utils/flightDetailLocale.ts");
const airport = await server.ssrLoadModule("/src/data/airportDisplay.ts");
const english = (text) => { assert.ok(text); assert.ok(!/\p{Script=Han}/u.test(text), text); };

test("every geographic filter has an explicit English label at all four levels", () => {
  function check(node) { english(names.geoNameForLocale(node, "en-US")); assert.equal(names.geoNameForLocale(node, "zh-CN"), node.nameZh); if (!node.nameZh.startsWith("全")) assert.ok(names.GEO_NAMES_EN[node.nameZh], node.nameZh); }
  for (const country of geo.COUNTRIES) {
    check(country);
    for (const region of hierarchy.getCountryRegions(country.code)) {
      check(region);
      for (const city of hierarchy.getCitiesForRegion(country.code, region.code)) {
        check(city);
        for (const district of hierarchy.getDistrictsForCity(country.code, region.code, city.code)) check(district);
      }
    }
  }
  assert.equal(names.GEO_NAMES_EN["台湾省"], "Taiwan Province, China");
});
test("all aircraft and flight type options have English labels", () => {
  for (const row of filters.FLIGHT_TYPE_OPTIONS) english(filters.flightTypeLabel(row.value, "en-US"));
  for (const row of filters.AIRCRAFT_CATEGORY_OPTIONS) english(filters.aircraftCategoryLabel(row.value, "en-US"));
});
test("Chinese status/weather payloads and regional airport fields localize correctly", () => {
  assert.equal(detail.formatFlightStatusLabel("已取消", "en-US"), "Cancelled");
  assert.equal(detail.formatFlightStatusLabel("计划", "en-US"), "Scheduled");
  assert.equal(detail.formatWeatherDescription("小雨", "en-US"), "light rain");
  const ap = {iata:"TPE",name:"Taoyuan International Airport",city:"Taipei",country:"TW",lat:25,lon:121};
  assert.equal(airport.airportDisplayForLocale(ap,"en-US").country,"Taiwan Province, China");
  assert.equal(airport.airportDisplayForLocale(ap,"zh-CN").country,"中国台湾");
});
test("retired production endpoints are cleared and explicitly disabled", async () => {
  const fs = await readFile(new URL("../.env.production", import.meta.url), "utf8");
  const value = key => fs.split(/\r?\n/).find(line => line.startsWith(`${key}=`))?.slice(key.length + 1);
  assert.equal(value("VITE_BACKEND_ENABLED"), "false");
  assert.equal(value("VITE_API_BASE_URL"), "");
  assert.equal(value("VITE_WS_URL"), "");
});
