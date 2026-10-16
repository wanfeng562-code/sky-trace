import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { test } from "node:test";
import vm from "node:vm";

const attack = '<img src=x onerror="globalThis.compromised=1">';
async function dashboard(name) {
  const source = await readFile(new URL(`../../server/app/api/routes/${name}.py`, import.meta.url), "utf8");
  const script = source.match(/<script>([\s\S]*?)<\/script>/)[1].replaceAll("__AUTO_REFRESH_MS__", "10000");
  const elements = new Map();
  const context = vm.createContext({
    document: { getElementById(id) { if (!elements.has(id)) elements.set(id, {}); return elements.get(id); }, querySelectorAll() { return []; } },
    setInterval() {}, console: { error() {} },
    fetch: async () => { throw new Error("Network disabled in regression test"); },
  });
  vm.runInContext(script, context);
  // Initial auto-refresh rejects without mutating any rendered panel.
  await new Promise(resolve => setImmediate(resolve));
  return { context, elements };
}

test("flight debug dashboard escapes upstream text and attribute values", async () => {
  const { context, elements } = await dashboard("insights");
  const id = `fr24-" onclick="${attack}`;
  context.renderSummary({ total: attack }, {});
  context.renderFlights([{ flight_id: id, callsign: attack, lat: 0, lon: 0 }]);
  context.renderTrackRows([{ ts: attack, altitude_ft: 0 }]);
  for (const name of ["summaryCards", "flightRows", "trackRows"]) {
    const html = elements.get(name).innerHTML;
    assert.ok(!html.includes(attack));
    assert.ok(html.includes("&lt;img"));
  }
  const rows = elements.get("flightRows").innerHTML;
  assert.ok(rows.includes('data-id="fr24-&quot; onclick=&quot;'));
  assert.ok(rows.includes('data-fr24-id="fr24-&quot; onclick=&quot;'));
  assert.ok(rows.includes("<td>0</td>"));
});

test("API monitor displays provider errors and source strings as text", async () => {
  const { context, elements } = await dashboard("api_monitor");
  context.fetch = async () => ({ json: async () => ({ data: { status: {
    profile: { default_realtime_source: attack },
    realtime: { source: attack, last_error: attack, success_count: attack, failure_count: 0 },
  }, quota: {} } }) });
  await context.refresh();
  for (const name of ["quota-grid", "status-grid"]) {
    const html = elements.get(name).innerHTML;
    assert.ok(!html.includes(attack));
    assert.ok(html.includes("&lt;img"));
  }
});
